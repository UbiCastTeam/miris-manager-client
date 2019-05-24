#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Miris Manager client class
'''
import json
import logging
import os
import requests
from .lib import configuration as configuration_lib
from .lib import info as info_lib
from .lib import long_polling as long_polling_lib
from .lib import signing as signing_lib
from .lib import ssh_tunnel as ssh_tunnel_lib

logger = logging.getLogger('mm_client.client')


class MirisManagerClient():
    '''
    Miris Manager client class
    '''
    DEFAULT_CONF = None  # can be either a dict or a path (`str` object)

    def __init__(self, local_conf=None, setup_logging=True):
        # "local_conf" can be either a dict or a path (`str` object)
        # Setup logging
        if setup_logging:
            log_format = '%(asctime)s %(name)s %(levelname)s %(message)s'
            logging.basicConfig(level=logging.INFO, format=log_format)
        # Read conf file
        self.conf = self.load_conf(local_conf)
        # Configure logging
        if setup_logging:
            level = getattr(logging, self.conf['LOG_LEVEL']) if self.conf.get('LOG_LEVEL') else logging.INFO
            root_logger = logging.getLogger('root')
            root_logger.setLevel(level)
            logger.setLevel(level)
            logging.captureWarnings(False)
            logger.debug('Logging conf set.')
        if not self.conf['VERIFY_SSL']:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self._long_polling_manager = None
        self._ssh_tunnel_manager = None

    def load_conf(self, local_conf):
        self.local_conf = local_conf
        conf = configuration_lib.load_conf(self.DEFAULT_CONF, self.local_conf)
        self.conf_checked = False
        return conf

    def update_conf(self, key, value):
        self.conf[key] = value
        # write change in local_conf if it is a path
        configuration_lib.update_conf(self.local_conf, key, value)

    def check_conf(self):
        if not self.conf_checked:
            configuration_lib.check_conf(self.conf)
            self.conf_checked = True

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
        data = info_lib.get_host_info(self.conf['SERVER_URL'])
        data['capabilities'] = ' '.join(self.conf['CAPABILITIES'])
        req = requests.post(
            url=self.conf['SERVER_URL'] + self.get_url_info('REGISTER_SYSTEM')['url'],
            data=data,
            proxies=self.conf.get('PROXIES'),
            verify=self.conf['VERIFY_SSL'],
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
        return True

    def api_request(self, url_or_action, method='get', headers=None, params=None, data=None, files=None, anonymous=None, timeout=None):
        self.check_conf()
        url_info = self.get_url_info(url_or_action)
        if anonymous is None:
            anonymous = bool(url_info.get('anonymous'))
        if anonymous:
            _headers = headers
        else:
            # Register system if no API key and auto registration
            if not self.conf.get('API_KEY'):
                if not self.conf['AUTO_REGISTRATION']:
                    raise Exception('The client auto registration is disabled and no API_KEY is set in conf file, please set one or turn on auto registration.')
                try:
                    self._register()
                except Exception as e:
                    logger.error('Registration failed: %s', e)
                    raise Exception('Registration failed: %s' % e)
            # Add signature in headers
            _headers = signing_lib.get_signature(self) if not anonymous else dict()
            if headers:
                _headers.update(headers)
        # Make API request
        req = getattr(requests, url_info.get('method', method))(
            url=self.conf['SERVER_URL'] + url_info['url'],
            headers=_headers,
            params=params,
            data=data,
            files=files,
            proxies=self.conf.get('PROXIES'),
            verify=self.conf['VERIFY_SSL'],
            timeout=timeout or self.conf['TIMEOUT']
        )
        response = req.text.strip()
        if req.status_code != 200:
            raise Exception('Request failed with status code %s:\n%s.' % (req.status_code, response[:200]))
        if response:
            response = json.loads(response)
        return response

    def long_polling_loop(self):
        if not self._long_polling_manager:
            self._long_polling_manager = long_polling_lib.LongPollingManager(self)
        self._long_polling_manager.loop()

    def handle_action(self, action, params):
        # Function that should be implemented in your client to process the
        # long polling responses.
        # IMPORTANT: Any code written here should not be blocking more than 5s
        # because of the delay after which the system is considered as offline
        # in Miris Manager.
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
        data = info_lib.get_host_info(self.conf['SERVER_URL'])
        data['capabilities'] = ' '.join(self.conf['CAPABILITIES'])
        # Make API request
        response = self.api_request('SET_INFO', data=data)
        return response

    def update_capabilities(self):
        data = dict()
        data['capabilities'] = ' '.join(self.conf['CAPABILITIES'])
        # Make API request
        response = self.api_request('SET_INFO', data=data)
        return response

    def set_status(self, status=None, status_info=None, status_message=None, profile=None, remaining_space=None, remaining_time=None):
        data = dict()
        if status is not None:
            data['status'] = status
        if status_info is not None:
            data['status_info'] = status_info
        if status_message is not None:
            data['status_message'] = status_message
        if profile is not None:
            data['profile'] = profile
        if remaining_space == 'auto':
            remaining_space = info_lib.get_remaining_space()
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

    def open_tunnel(self, status_callback=None):
        if not self._ssh_tunnel_manager:
            self._ssh_tunnel_manager = ssh_tunnel_lib.SSHTunnelManager(self, status_callback)
        self._ssh_tunnel_manager.tunnel_loop()

    def close_tunnel(self):
        if self._ssh_tunnel_manager:
            self._ssh_tunnel_manager.close_tunnel()
