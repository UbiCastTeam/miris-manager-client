#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
An example of Campus Manager client usage.
This script is intended to send screenshot and handle click requests.
'''
import logging
import os
from cm_client import CampusManagerClient

logger = logging.getLogger('cm_screen_controller')


class ScreenController(CampusManagerClient):
    DEFAULT_CONF = {
        'CAPABILITIES': {  # This list makes available or not actions buttons in Campus Manager
            'gcontrol': {'version': 1},
        },
    }

    def handle_action(self, action, params):
        if action == 'SHUTDOWN':
            logger.info('Shutdown requested.')
            # TODO

        elif action == 'REBOOT':
            logger.info('Reboot requested.')
            # TODO

        elif action == 'GET_SCREENSHOT':
            self.set_status(remaining_space='auto')  # Send remaining space to Campus Manager
            self.set_screenshot('/var/lib/AccountsService/icons/%s' % (os.env.get('USER') or 'root'), file_name='screen.png')
            logger.info('Screenshot sent.')

        elif action == 'SIMULATE_CLICK':
            logger.info('Click requested: %s.', params)
            # TODO

        elif action == 'SEND_TEXT':
            logger.info('Text received: %s.', params)
            # TODO

        else:
            raise Exception('Unsupported action: %s.' % action)


if __name__ == '__main__':
    client = ScreenController()
    try:
        client.long_polling_loop()
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt received, stopping application.')
