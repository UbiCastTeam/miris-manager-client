#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Fake MediaCoder client for tests.
'''
import os
import json
import logging
from mm_client import MirisManagerClient

logger = logging.getLogger('fake_mediacoder')


class FakeMediaCoder(MirisManagerClient):
    DEFAULT_CONF = {
        'URL': 'http://localhost:9000',
        'CAPABILITIES': ['record', 'network_record', 'web_control', 'screenshot'],
    }
    PROFILES = {'main': {'has_password': False, 'can_live': False, 'name': 'main', 'label': 'Main', 'type': 'recorder'}}

    def handle_action(self, action, params):
        if action == 'START_RECORDING':
            logger.info('Starting recording with params %s', params)
            self.set_status(status='recording', status_info='{"playlist": "/videos/BigBuckBunny_320x180.m3u8"}', remaining_space='auto')

        elif action == 'STOP_RECORDING':
            logger.info('Stopping recording.')
            self.set_status(status='recorder_idle', remaining_space='auto')

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
    client = FakeMediaCoder()
    client.update_capabilities()
    client.set_status(status='ready', status_message='Ready to record', remaining_space='auto')
    try:
        client.long_polling_loop()
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt received, stopping application.')
