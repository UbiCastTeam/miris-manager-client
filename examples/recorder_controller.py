#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
An example of Miris Manager client usage.
This script is intended to control a recorder.
'''
import json
import logging
from mm_client.client import MirisManagerClient

logger = logging.getLogger('recorder_controller')


class RecorderController(MirisManagerClient):
    DEFAULT_CONF = {
        'CAPABILITIES': ['record', 'shutdown'],
    }
    PROFILES = {'main': {'has_password': False, 'can_live': False, 'name': 'main', 'label': 'Main', 'type': 'recorder'}}

    def handle_action(self, action, params):
        if action == 'SHUTDOWN':
            logger.info('Shutdown requested.')
            # TODO

        elif action == 'REBOOT':
            logger.info('Reboot requested.')
            # TODO

        elif action == 'START_RECORDING':
            logger.info('Starting recording with params %s', params)
            self.set_status(status='recording', remaining_space='auto')
            # TODO

        elif action == 'STOP_RECORDING':
            logger.info('Stopping recording.')
            self.set_status(status='recorder_idle', remaining_space='auto')
            # TODO

        elif action == 'LIST_PROFILES':
            logger.info('Returning list of profiles.')
            return json.dumps(self.PROFILES)

        else:
            raise Exception('Unsupported action: %s.' % action)


if __name__ == '__main__':
    client = RecorderController()
    try:
        client.long_polling_loop()
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt received, stopping application.')
