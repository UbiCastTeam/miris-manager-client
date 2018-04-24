#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
An example of Campus Manager client usage.
This script is intended to control a recorder.
'''
import json
import logging
from cm_client import CampusManagerClient

logger = logging.getLogger('cm_recorder_controller')


class RecorderController(CampusManagerClient):
    DEFAULT_CONF = {
        'CAPABILITIES': {  # This list makes available or not actions buttons in Campus Manager
            'recording': {'version': 1},
        },
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
