#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Campus Manager client class
'''
import datetime
import json
import logging
import os
import sys
import requests
import time
import traceback
import signal
from cm_client import lib as cm_lib
from cm_client import signing

__version__ = '3.0'
logger = logging.getLogger('cm_client')


class CampusManagerClient():
    DEFAULT_CONF = None  # can be either a path or a dict
    LOCAL_CONF = os.path.expanduser('~/.cm_client.json')  # can be either a path or a dict

    def __init__(self, setup_logging=True):
        # Setup logging
        if setup_logging:
            log_format = '%(asctime)s %(name)s %(levelname)s %(message)s'
            logging.basicConfig(level=logging.INFO, format=log_format)
        # Read conf file
        self.conf = self.load_conf()
        # Configure logging
        if setup_logging:
            level = getattr(logging, self.conf['LOG_LEVEL']) if self.conf.get('LOG_LEVEL') else logging.INFO
            root_logger = logging.getLogger('root')
            root_logger.setLevel(level)
            logger.setLevel(level)
            logging.captureWarnings(False)
            urllib3_logger = logging.getLogger('urllib3')
            urllib3_logger.setLevel(logging.WARNING)
            urllib3_logger = logging.getLogger('requests.packages.urllib3')
            urllib3_logger.setLevel(logging.WARNING)
            requests.packages.urllib3.disable_warnings()
            logger.debug('Logging conf set.')
        self.run_systemd_notify = False
        self.last_lp_error = None

    def load_conf(self):
        return cm_lib.load_conf(self.DEFAULT_CONF, self.LOCAL_CONF)

    def update_conf(self, key, value):
        self.conf[key] = value
        cm_lib.update_conf(self.LOCAL_CONF, key, value)

    def get_url_info(self, url_or_action):
        if url_or_action.startswith('/'):
            return dict(url=url_or_action)
        if url_or_action not in self.conf['API_CALLS']:
            raise Exception('Invalid url requested: %s does not exist in API_CALLS configuration.' % url_or_action)
        return self.conf['API_CALLS'][url_or_action]

    def _register(self):
        if self.conf.get('API_KEY'):
            return
        logger.info('No API key in configuration, requesting system registration...')
        data = cm_lib.get_host_info(self.conf['URL'])
        data['capabilities'] = json.dumps(self.conf['CAPABILITIES'])
        data['hostname'] = data['alt_hostname']
        req = requests.post(
            url=self.conf['URL'] + self.get_url_info('REGISTER_SYSTEM')['url'],
            data=data,
            proxies=self.conf.get('PROXIES'),
            verify=self.conf['CHECK_SSL'],
            timeout=self.conf['TIMEOUT']
        )
        response = req.text.strip()
        if req.status_code != 200:
            raise Exception('Request failed with status code %s:\n%s.' % (req.status_code, response[:200]))
        response = json.loads(response) if response else dict()
        secret_key = response.get('secret_key')
        if not secret_key:
            raise Exception('No secret key received.')
        api_key = response.get('api_key')
        if not api_key:
            raise Exception('No API key received.')
        self.update_conf('SECRET_KEY', secret_key)
        self.update_conf('API_KEY', api_key)
        logger.info('System registration done.')

    def api_request(self, url_or_action, method='get', headers=None, params=None, data=None, files=None, anonymous=None, timeout=None):
        url_info = self.get_url_info(url_or_action)
        if anonymous is None:
            anonymous = bool(url_info.get('anonymous'))
        if anonymous:
            _headers = headers
        else:
            # Register system if no API key
            if not self.conf.get('API_KEY'):
                try:
                    self._register()
                except Exception as e:
                    logger.error('Registration failed: %s', e)
                    raise Exception('Registration failed: %s' % e)
            # Add signature in headers
            _headers = signing.get_signature(self) if not anonymous else dict()
            if headers:
                _headers.update(headers)
        # Make API request
        req = getattr(requests, url_info.get('method', method))(
            url=self.conf['URL'] + url_info['url'],
            headers=_headers,
            params=params,
            data=data,
            files=files,
            proxies=self.conf.get('PROXIES'),
            verify=self.conf['CHECK_SSL'],
            timeout=timeout or self.conf['TIMEOUT']
        )
        response = req.text.strip()
        if req.status_code != 200:
            raise Exception('Request failed with status code %s:\n%s.' % (req.status_code, response[:200]))
        if response:
            response = json.loads(response)
        return response

    def long_polling_loop(self):
        # Check if systemd-notify should be called
        self.run_systemd_notify = self.conf.get('WATCHDOG') and os.system('which systemd-notify') == 0
        # Start connection loop
        logger.info('Campus Manager server is %s.', self.conf['URL'])
        logger.info('Starting connection loop using url: %s.', self.get_url_info('LONG_POLLING'))
        self.long_polling_loop_running = True

        def exit_handler(signum, frame):
            message = 'Loop as been interrupted'
            self.long_polling_loop_running = False
            logger.warning(message)
            sys.exit(1)

        signal.signal(signal.SIGINT, exit_handler)
        signal.signal(signal.SIGTERM, exit_handler)

        while self.long_polling_loop_running:
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
            response = self.api_request('LONG_POLLING', timeout=300)
        except Exception as e:
            if 'timeout=300' not in str(e):
                msg = 'Long polling connection failed: %s: %s' % (e.__class__.__name__, e)
                if self.last_lp_error == e.__class__.__name__:
                    logger.debug(msg)  # Avoid spamming
                else:
                    logger.info(msg)
                    self.last_lp_error = e.__class__.__name__
        else:
            self.last_lp_error = None
            if response:
                logger.info('Received long polling response: %s', response)
                success = True
                uid = response.get('uid')
                try:
                    result = self.process_long_polling(response)
                except Exception as e:
                    logger.error('Failed to process response: %s\n%s', e, traceback.format_exc())
                    self.set_command_status(uid, 'FAILED', str(e))
                else:
                    self.set_command_status(uid, 'DONE', result)
        finally:
            if self.run_systemd_notify:
                logger.debug('Notifying systemd watchdog.')
                os.system('systemd-notify WATCHDOG=1')
        return success

    def process_long_polling(self, response):
        logger.debug('Processing response.')
        if self.conf.get('API_KEY'):
            invalid = signing.check_signature(self, response)
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
            return self.handle_action(action, params)

    def handle_action(self, action, params):
        # IMPORTANT: Any code written here should not be blocking more than 5s
        # because of the delay after which the system is considered as offline
        # in Campus Manager.
        raise NotImplementedError('Your class should override the "handle_action" method.')

    def set_command_status(self, command_uid, status='DONE', data=None):
        if not command_uid:
            return
        try:
            self.api_request('SET_COMMAND_STATUS', data=dict(
                uid=command_uid,
                status=status,
                data=data or '',
            ))
        except Exception as e:
            logger.error('Unable to communicate command status: %s %s', type(e), e)

    def set_info(self):
        data = cm_lib.get_host_info(self.conf['URL'])
        data['capabilities'] = json.dumps(self.conf['CAPABILITIES'])
        # Make API request
        response = self.api_request('SET_INFO', data=data)
        return response

    def update_capabilities(self):
        data = dict()
        data['capabilities'] = json.dumps(self.conf['CAPABILITIES'])
        # Make API request
        response = self.api_request('SET_INFO', data=data)
        return response

    def set_status(self, status=None, status_info=None, remaining_space=None, remaining_time=None):
        data = dict()
        if status is not None:
            data['status'] = status
        if status_info is not None:
            data['status_info'] = status_info
        if remaining_space == 'auto':
            remaining_space = cm_lib.get_remaining_space()
        if remaining_space is not None:
            data['remaining_space'] = remaining_space
        if remaining_time is not None:
            data['remaining_time'] = remaining_time
        if not data:
            raise ValueError('No data to update.')
        response = self.api_request('SET_STATUS', data=data)
        return response

    def set_screenshot(self, path, file_name=None):
        with open(path, 'rb') as file_obj:
            response = self.api_request('SET_SCREENSHOT', files=dict(
                screenshot=(file_name or os.path.basename(path), file_obj)
            ))
        return response

    def establish_tunnel(self):
        public_key = cm_lib.get_ssh_public_key()
        response = self.api_request('PREPARE_TUNNEL', data=dict(public_key=public_key))
        cm_lib.start_tunnel(response['command'])

    def close_tunnel(self):
        cm_lib.stop_tunnel()
