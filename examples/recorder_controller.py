#!/usr/bin/env python3
'''
Fake MediaCoder client for tests.
'''
import argparse
import json
import logging
import os
import time

from mm_client.client import MirisManagerClient

logger = logging.getLogger('recorder_controller')


class RecorderController(MirisManagerClient):
    DEFAULT_CONF = {
        'CAPABILITIES': ['record', 'network_record', 'web_control', 'screenshot'],
    }
    PROFILES = {
        'main': {
            'has_password': False,
            'can_live': False,
            'name': 'main',
            'label': 'Main',
            'type': 'recorder'
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.update_capabilities()
        self.set_status(
            status='ready',
            status_message='Ready to record',
            remaining_space='auto'
        )
        try:
            self.long_polling_loop()
        except KeyboardInterrupt:
            logger.info('KeyboardInterrupt received, stopping application.')

    def handle_action(self, uid, action, params):
        # See help on the handle action function:
        # https://github.com/UbiCastTeam/miris-manager-client/blob/main/mm_client/client.py#L184
        # Possible actions:
        # https://mirismanager.ubicast.eu/static/skyreach/docs/api/values.html#system-command-actions
        if action == 'START_RECORDING':
            logger.info('Starting recording with params %s', params)
            self.set_status(
                status='initializing',
                status_message='',
                remaining_space='auto'
            )
            time.sleep(3)
            self.set_status(
                status='running',
                status_message='',
                status_info='{"playlist": "/videos/BigBuckBunny_320x180.m3u8"}',
                remaining_space='auto'
            )
            return 'DONE', ''

        elif action == 'STOP_RECORDING':
            logger.info('Stopping recording.')
            self.set_status(
                status='ready',
                status_message='',
                remaining_space='auto'
            )
            return 'DONE', ''

        elif action == 'LIST_PROFILES':
            logger.info('Returning list of profiles.')
            return 'DONE', json.dumps(self.PROFILES)

        elif action == 'GET_SCREENSHOT':
            self.set_status(remaining_space='auto')  # Send remaining space to Miris Manager
            self.set_screenshot(
                path='/var/lib/AccountsService/icons/%s' % (os.environ.get('USER') or 'root'),
                file_name='screen.png'
            )
            logger.info('Screenshot sent.')
            return 'DONE', ''

        elif action == 'UPGRADE':
            logger.info('Starting upgrade.')

            # Start your asynchronous upgrade process here then call:
            # self.set_command_status(uid, 'DONE', '')

            return 'IN_PROGRESS', ''

        else:
            raise NotImplementedError('Unsupported action: %s.' % action)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument(
        'conf',
        default=None,
        help='The path of the configuration to use.',
        nargs='?',
        type=str,
    )
    args = parser.parse_args()

    RecorderController(args.conf)
