#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Miris Manager long polling management
This module is not intended to be used directly, only the client class should be used.
'''
import datetime
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

    def loop(self):
        # Check if systemd-notify should be called
        self.run_systemd_notify = self.client.conf.get('WATCHDOG') and os.system('which systemd-notify') == 0
        # Start connection loop
        logger.info('Miris Manager server is %s.', self.client.conf['SERVER_URL'])
        logger.info('Starting connection loop using url: %s.', self.client.get_url_info('LONG_POLLING'))
        self.loop_running = True

        def exit_handler(signum, frame):
            self.loop_running = False
            logger.warning('Loop as been interrupted')
            sys.exit(1)

        signal.signal(signal.SIGINT, exit_handler)
        signal.signal(signal.SIGTERM, exit_handler)

        while self.loop_running:
            start = datetime.datetime.utcnow()
            success = self.call_long_polling()
            if not success:
                # Avoid starting too often new connections
                duration = (datetime.datetime.utcnow() - start).seconds
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
                    result = self.process_long_polling(response)
                except Exception as e:
                    logger.error('Failed to process response: %s\n%s', e, traceback.format_exc())
                    self.client.set_command_status(uid, 'FAILED', str(e))
                else:
                    self.client.set_command_status(uid, 'DONE', result)
        finally:
            if self.run_systemd_notify:
                logger.debug('Notifying systemd watchdog.')
                os.system('systemd-notify WATCHDOG=1')
        return success

    def process_long_polling(self, response):
        logger.debug('Processing response.')
        if self.client.conf.get('API_KEY'):
            invalid = check_signature(self.client, response)
            if invalid:
                raise Exception('Invalid signature: %s' % invalid)
        action = response.get('action')
        if not action:
            raise Exception('No action received.')
        params = response.get('params', dict())
        logger.debug('Received command "%s": %s.', response.get('uid'), action)
        if action == 'PING':
            pass
        else:
            return self.client.handle_action(action, params)
