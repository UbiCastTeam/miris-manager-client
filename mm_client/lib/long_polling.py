'''
Miris Manager long polling management
This module is not intended to be used directly, only the client class should be used.
'''
import logging
import os
import signal
import sys
import time
import traceback

from .signing import check_signature

logger = logging.getLogger('mm_client.lib.long_polling')


class LongPollingManager():

    def __init__(self, client):
        self.client = client
        self.run_systemd_notify = False
        self.last_error = None
        self.loop_running = False

    def loop(self, single_loop=False):
        # Check if systemd-notify should be called
        self.run_systemd_notify = self.client.conf.get('WATCHDOG') and os.system('which systemd-notify') == 0
        # Start connection loop
        logger.info('Starting long polling to %s' % self.client.conf['SERVER_URL'])
        self.loop_running = True

        def exit_handler(*args, **kwargs):
            self.loop_running = False
            logger.info('Long polling loop stopped')
            sys.exit(1)

        signal.signal(signal.SIGINT, exit_handler)
        signal.signal(signal.SIGTERM, exit_handler)

        while self.loop_running:
            start = time.time()
            success = self.call_long_polling()
            if single_loop:
                break
            if not success:
                # Avoid starting too often new connections
                duration = time.time() - start
                if duration < 5:
                    time.sleep(5 - duration)

    def call_long_polling(self):
        success = False
        try:
            logger.debug('Make long polling request')
            response = self.client.api_request('LONG_POLLING', timeout=300)
        except Exception as e:
            if 'timeout=300' not in str(e):
                msg = 'Long polling connection failed: %s: %s' % (e.__class__.__name__, e)
                if self.last_error == e.__class__.__name__:
                    logger.debug(msg)  # Avoid spamming
                else:
                    logger.error(msg)
                    self.last_error = e.__class__.__name__
        else:
            self.last_error = None
            if response:
                logger.info('Received long polling response: %s', response)
                success = True
                uid = response.get('uid')
                try:
                    status, data = self.process_long_polling(response)
                except Exception as e:
                    success = False
                    logger.error('Failed to process response: %s\n%s', e, traceback.format_exc())
                    self.client.set_command_status(uid, 'FAILED', str(e))
                    if os.environ.get('CI_PIPELINE_ID'):
                        # Propagate exception so that it can be detected in CI
                        raise
                else:
                    self.client.set_command_status(uid, status, data)
        finally:
            if self.run_systemd_notify:
                logger.debug('Notifying systemd watchdog.')
                os.system('systemd-notify WATCHDOG=1')
        return success

    def process_long_polling(self, response):
        logger.debug('Processing response.')
        if self.client.conf.get('API_KEY'):
            invalid = check_signature(self.client.conf, response)
            if invalid:
                raise ValueError('Invalid signature: %s' % invalid)
        uid = response.get('uid')
        action = response.get('action')
        if not action:
            raise ValueError('No action received.')
        params = response.get('params', {})
        logger.debug('Received command "%s": %s.', uid, action)
        if action == 'PING':
            return 'DONE', ''
        status, data = self.client.handle_action(uid=uid, action=action, params=params)
        if status not in ('DONE', 'IN_PROGRESS', 'FAILED'):
            logger.error('Your client has returned an invalid status in "handle_action".')
            raise ValueError('An error occurred during the processing of the action by the client.')
        if data is not None and not isinstance(data, str):
            logger.error('Your client has returned an invalid type for data in "handle_action".')
            raise ValueError('An error occurred during the processing of the action by the client.')
        return status, data
