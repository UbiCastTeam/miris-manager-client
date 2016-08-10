#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Campus Manager remote control client (Python3 script)
"""
import datetime
import imp
import json
import logging
import os
import requests
import socket
import time
import traceback
import uuid
from cm_client import lib as cm_lib

__version__ = '1.0'
logger = logging.getLogger('cm_client')


class CampusManagerClient():
    CONF_PATH = os.path.expanduser('~/.cm_client.py')
    CONF = {
        'LOG_LEVEL': 'INFO',  # Logging level
        'URL': 'https://campusmanager',  # URL of Campus Manager server
        'MAC': '',  # Mac address of the client (an unique value per client, leave empty to get it automatically)
        'API_KEY': '',  # API key of this system in Campus Manager
        'SECRET_KEY': '',  # Secret key of this system in Campus Manager, used to sign messages
        'WATCHDOG': False,  # Notify systemd watchdog
        'CHECK_SSL': False,  # Check server SSL certificate
        'TIMEOUT': 5,  # API requests max duration in seconds
        # 'PROXIES': {
        #     # Examples
        #     'http': 'http://10.10.1.10:3128',
        #     'https': 'http://10.10.1.10:1080',
        # },
        'CAPABILITIES': {},  # This list makes available or not actions buttons in Campus Manager
        'URLS': {  # List of Campus Manager urls (do not overwritte this)
            'LONG_POLLING': '/remote-event/v2',
            'COMMAND_STATUS': '/fleet/api/v2/command-status/',
            'POST_SCREENSHOT': '/fleet/api/v2/post-screenshot/',
            'POST_STATUS': '/fleet/api/v2/post-status/',
        },
    }

    def __init__(self, setup_logging=True):
        # Setup logging
        if setup_logging:
            log_format = '%(asctime)s %(name)s %(levelname)s %(message)s'
            logging.basicConfig(level=logging.INFO, format=log_format)
        # Read conf file
        if os.path.exists(self.CONF_PATH):
            try:
                conf = imp.load_source('conf', self.CONF_PATH)
            except ImportError as e:
                logger.error('Unable to load config file %s: %s', self.CONF_PATH, e)
            else:
                logger.info('Config file "%s" loaded.', self.CONF_PATH)
                for key in dir(conf):
                    if not key.startswith('_'):
                        self.CONF[key] = getattr(conf, key)
        else:
            logger.info('Config file does not exists, using default config.')
        # Configure logging
        if setup_logging:
            level = getattr(logging, self.CONF['LOG_LEVEL']) if self.CONF.get('LOG_LEVEL') else logging.INFO
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
        # Prepare urls
        logger.info('Campus Manager server is %s.', self.CONF['URL'])
        #    Get host and port
        url = self.CONF['URL']
        if url.endswith('/'):
            url = url[:-1]
        self.cm_host = url.split('://')[-1]
        self.cm_port = 80
        if ':' in self.cm_host:
            self.cm_host, self.cm_port = self.cm_host.split(':')
            self.cm_port = int(self.cm_port)
        self.cm_url = url
        # Start connection loop
        try:
            self.connection_loop()
        except KeyboardInterrupt as e:
            logger.info('KeyboardInterrupt received, stopping application.')

    def update_conf(self, key, value):
        content = ''
        if os.path.isfile(self.CONF_PATH):
            with open(self.CONF_PATH, 'r') as fd:
                content = fd.read()
            content = content.strip()
        new_content = ''
        for line in content.split('\n'):
            if not line.startswith(key):
                new_content += '%s\n' % line
        new_content += '%s = \'%s\'\n' % (key, value)
        with open(self.CONF_PATH, 'w') as fd:
            fd.write(new_content)
        self.CONF[key] = value

    def get_url(self, name):
        if name not in self.CONF['URLS']:
            raise Exception('Invalid url requested: %s does not exist in urls configuration.' % name)
        return self.cm_url + self.CONF['URLS'][name]

    def connection_loop(self):
        # Get local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((self.cm_host, self.cm_port))
        local_ip = s.getsockname()[0]
        hostname = socket.gethostname()
        s.close()
        logger.info('Local IP is %s.', local_ip)
        # Get MAC address
        if self.CONF.get('MAC'):
            self.mac = self.CONF['MAC']
        else:
            mac = uuid.getnode()
            self.mac = ':'.join(('%012x' % mac)[i:i + 2] for i in range(0, 12, 2))
        logger.info('Client mac address is: %s.', self.mac)
        # Get capabilities
        capabilities = json.dumps(self.CONF['CAPABILITIES'])
        # Check if systemd-notify should be called
        run_systemd_notify = self.CONF.get('WATCHDOG') and os.system('which systemd-notify') == 0
        # Start connection loop
        logger.info('Starting connection loop using url: %s.', self.get_url('LONG_POLLING'))
        last_con_error = None
        while True:
            success = False
            start = datetime.datetime.utcnow()
            try:
                signature = cm_lib.get_signature(self)
                req = requests.get(
                    url=self.get_url('LONG_POLLING'),
                    headers=dict(
                        ip=local_ip,
                        id=self.mac,
                        name=hostname,
                        capabilities=capabilities,
                        **signature
                    ),
                    proxies=self.CONF.get('PROXIES'),
                    verify=self.CONF.get('CHECK_SSL'),
                    timeout=300
                )
                response = req.text.strip()
                if req.status_code != 200:
                    raise Exception('Long polling request failed with status code %s.\n    %s.' % (req.status_code, response[:200]))
            except Exception as e:
                if 'timeout=300' not in str(e):
                    msg = 'Long polling connection failed: %s %s' % (type(e), e)
                    if last_con_error == e.__class__.__name__:
                        logger.debug(msg)  # Avoid spamming
                    else:
                        logger.info(msg)
                        last_con_error = e.__class__.__name__
            else:
                last_con_error = None
                if response:
                    try:
                        rdata = json.loads(response)
                        logger.info('Received long polling response: %s', rdata)
                    except Exception as e:
                        logger.error('Failed to read response: %s %s', type(e), e)
                    else:
                        success = True
                        uid = rdata.get('uid')
                        try:
                            result = self.process_response(rdata)
                        except Exception as e:
                            logger.error('Failed to process response: %s\n%s', e, traceback.format_exc())
                            cm_lib.set_command_status(self, uid, 'FAILED', str(e))
                        else:
                            cm_lib.set_command_status(self, uid, 'DONE', result)
            finally:
                if run_systemd_notify:
                    logger.debug('Notifying systemd watchdog.')
                    os.system('systemd-notify WATCHDOG=1')
            if not success:
                # Avoid starting too often new connections
                duration = (datetime.datetime.utcnow() - start).seconds
                if duration < 5:
                    time.sleep(5 - duration)

    def process_response(self, rdata):
        # IMPORTANT: Any code written here should not be blocking more than 5s
        logger.debug('Processing response.')
        invalid = cm_lib.check_signature(self, rdata)
        if invalid:
            raise Exception('Invalid signature: %s' % invalid)
        action = rdata.get('action')
        if not action:
            raise Exception('No action received.')
        if (not self.CONF.get('SECRET_KEY') or not self.CONF.get('API_KEY')) and action != 'SETUP':
            raise Exception('Invalid action requested. Since no API key or no secret key is available, the only possible action is setup.')
        params = rdata.get('params', dict())
        logger.debug('Received command "%s": %s.', rdata.get('uid'), action)
        if action == 'SETUP':
            # Set some config
            secret_key = params.get('secret_key')
            if not secret_key:
                raise Exception('Setup failed, no secret key given.')
            api_key = params.get('api_key')
            if not api_key:
                raise Exception('Setup failed, no API key given.')
            self.update_conf('SECRET_KEY', secret_key)
            self.update_conf('API_KEY', api_key)
            logger.info('Setup command received. New API key is: "%s".', api_key)
        elif action == 'PING':
            pass
        else:
            return self.handle_action(action, params)

    def handle_action(self, action, params):
        raise NotImplementedError('Your class should override the "handle_action" method.')
