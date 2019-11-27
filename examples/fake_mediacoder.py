#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Fake MediaCoder client for tests.
'''
import json
import logging
import os
import sys
import time
from mm_client.client import MirisManagerClient

logger = logging.getLogger('fake_mediacoder')


class FakeMediaCoder(MirisManagerClient):
    DEFAULT_CONF = {
        'CAPABILITIES': ['record', 'network_record', 'web_control', 'screenshot'],
    }
    PROFILES = {'main': {'has_password': False, 'can_live': False, 'name': 'main', 'label': 'Main', 'type': 'recorder'}}

    def handle_action(self, action, params):
        if action == 'START_RECORDING':
            logger.info('Starting recording with params %s', params)
            self.set_status(status='initializing', status_message='', remaining_space='auto')
            time.sleep(3)
            self.set_status(status='running', status_message='', status_info='{"playlist": "/videos/BigBuckBunny_320x180.m3u8"}', remaining_space='auto')

        elif action == 'STOP_RECORDING':
            logger.info('Stopping recording.')
            self.set_status(status='ready', status_message='', remaining_space='auto')

        elif action == 'LIST_PROFILES':
            logger.info('Returning list of profiles.')
            return json.dumps(self.PROFILES)

        elif action == 'GET_SCREENSHOT':
            self.set_status(remaining_space='auto')  # Send remaining space to Miris Manager
            self.set_screenshot('/var/lib/AccountsService/icons/%s' % (os.environ.get('USER') or 'root'), file_name='screen.png')
            logger.info('Screenshot sent.')

        else:
            raise Exception('Unsupported action: %s.' % action)


if __name__ == '__main__':
    local_conf = sys.argv[1] if len(sys.argv) > 1 else None
    client = FakeMediaCoder(local_conf)
    client.update_capabilities()
    client.set_status(status='ready', status_message='Ready to record', remaining_space='auto')
    try:
        client.long_polling_loop()
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt received, stopping application.')
