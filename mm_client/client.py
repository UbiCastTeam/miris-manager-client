'''
Miris Manager client main module
'''
import logging
from pathlib import Path

import requests

from .lib import configuration as configuration_lib
from .lib import info as info_lib
from .lib import long_polling as long_polling_lib
from .lib import signing as signing_lib
from .lib import ssh_tunnel as ssh_tunnel_lib

logger = logging.getLogger('mm_client.client')


class MirisManagerRequestError(Exception):
    def __init__(self, *args, **kwargs):
        self.status_code = kwargs.pop('status_code', None)
        self.error_code = kwargs.pop('error_code', None)
        super().__init__(*args, **kwargs)


class MirisManagerClient():
    '''
    Miris Manager client class
    '''
    DEFAULT_CONF = None  # can be either a dict or a path (`str` object)

    def __init__(self, local_conf=None, setup_logging=True):
        # "local_conf" can be either a dict or a path (`str` object)
        # Setup logging
        if setup_logging:
            logging.basicConfig(
                format='%(asctime)s.%(msecs)03d pid:%(process)d %(name)s %(levelname)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                level=logging.INFO,
            )
        # Read conf file
        self.conf_checked = False
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
            return {'url': url_or_action}
        if url_or_action not in self.conf['API_CALLS']:
            raise MirisManagerRequestError(
                f'Invalid url requested: {url_or_action} does not exist in API_CALLS configuration.',
                status_code=0,
                error_code='invalid_url'
            )
        return self.conf['API_CALLS'][url_or_action]

    def _request(self, url, method='get', headers=None, params=None,
                 data=None, files=None, anonymous=None, timeout=None):
        req = getattr(requests, method)(
            url=self.conf['SERVER_URL'] + url,
            headers=headers,
            params=params,
            data=data,
            files=files,
            proxies=self.conf.get('PROXIES'),
            verify=self.conf['VERIFY_SSL'],
            timeout=timeout or self.conf['TIMEOUT']
        )
        status_code = req.status_code
        error_code = None
        body = req.text.strip()
        if req.status_code != 200:
            try:
                response = req.json()
                error = response['error']
                error_code = response.get('code')
            except Exception:
                error = 'Request failed with status code %s:\n%s.' % (req.status_code, body[:200])
            raise MirisManagerRequestError(
                error,
                status_code=status_code,
                error_code=error_code
            )
        response = req.json() if body else {}
        return response

    def _register(self):
        if self.conf.get('API_KEY'):
            return
        logger.info('No API key in configuration, requesting system registration...')
        data = info_lib.get_host_info(self.conf['SERVER_URL'])
        data['capabilities'] = ' '.join(self.conf['CAPABILITIES'])
        # Make API request
        response = self._request(self.get_url_info('REGISTER_SYSTEM')['url'], method='post', data=data)
        # Check response
        secret_key = response.get('secret_key')
        if not secret_key:
            raise MirisManagerRequestError(
                'No secret key received.',
                status_code=200,
                error_code='no_secret'
            )
        api_key = response.get('api_key')
        if not api_key:
            raise MirisManagerRequestError(
                'No API key received.',
                status_code=200,
                error_code='no_api_key'
            )
        self.update_conf('SECRET_KEY', secret_key)
        self.update_conf('API_KEY', api_key)
        logger.info('System registration done.')
        return True

    def api_request(self, url_or_action, method='get', headers=None, params=None,
                    data=None, files=None, anonymous=None, timeout=None):
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
                    raise ValueError('The client auto registration is disabled and no API_KEY is set in conf file, '
                                     'please set one or turn on auto registration.')
                try:
                    self._register()
                except Exception as e:
                    logger.error('Registration failed: %s', e)
                    raise
            # Add signature in headers
            # headers with "_" are ignored by Django
            _headers = {'api-key': self.conf['API_KEY']}
            if not anonymous:
                signature = signing_lib.get_signature(self.conf)
                if signature:
                    _headers.update(signature)
            if headers:
                _headers.update(headers)
        # Make API request
        response = self._request(
            url_info['url'],
            method=url_info.get('method', method),
            headers=_headers,
            params=params,
            data=data,
            files=files,
            timeout=timeout
        )
        return response

    def long_polling_loop(self, single_loop=False):
        if not self._long_polling_manager:
            self._long_polling_manager = long_polling_lib.LongPollingManager(self)
        self._long_polling_manager.loop(single_loop)

    def handle_action(self, uid, action, params):
        '''
        Function that should be implemented in your client to process the long polling responses.
        IMPORTANT: Any code written here should not be blocking more than 5s because of the
                   delay after which the system is considered as offline in Miris Manager.
        Arguments:
        - uid: The system command unique identifier.
        - action: The action to run.
        - params: The action parameters.
        Must return a tuple: (status, data)
        - status: The system command status (string). Possible values:
        - "DONE": The command has been executed successfully.
        - "IN_PROGRESS": The command has been started but is not yet completed.
        - "FAILED": The command execution has failed.
        - data: The command result data (string). It can be a json dump or a message. Empty strings are allowed.
        '''
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
        data = {
            'capabilities': ' '.join(self.conf['CAPABILITIES']),
        }
        # Make API request
        response = self.api_request('SET_INFO', data=data)
        return response

    def set_status(self, status=None, status_info=None, status_message=None,
                   profile=None, remaining_space=None, remaining_time=None):
        data = {}
        if status is not None:
            data['status'] = status
        if status_info is not None:
            data['status_info'] = status_info
        if status_message is not None or status is not None:
            data['status_message'] = status_message or ''
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
                screenshot=(file_name or Path(path).name, file_obj)
            ))
        return response

    def open_tunnel(self, status_callback=None):
        if not self._ssh_tunnel_manager:
            self._ssh_tunnel_manager = ssh_tunnel_lib.SSHTunnelManager(self, status_callback)
        self._ssh_tunnel_manager.tunnel_loop()

    def close_tunnel(self):
        if self._ssh_tunnel_manager:
            self._ssh_tunnel_manager.close_tunnel()
