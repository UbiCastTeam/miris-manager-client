#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
An example of Miris Manager client usage.
This script is intended to send screenshot and handle click requests.
'''
import logging
import os
from mm_client.client import MirisManagerClient

logger = logging.getLogger('screen_controller')


class ScreenController(MirisManagerClient):
    DEFAULT_CONF = {
        'CAPABILITIES': ['screen_control', 'screenshot'],
    }

    def handle_action(self, action, params):
        if action == 'SHUTDOWN':
            logger.info('Shutdown requested.')
            # TODO

        elif action == 'REBOOT':
            logger.info('Reboot requested.')
            # TODO

        elif action == 'GET_SCREENSHOT':
            self.set_status(remaining_space='auto')  # Send remaining space to Miris Manager
            self.set_screenshot('/var/lib/AccountsService/icons/%s' % (os.environ.get('USER') or 'root'), file_name='screen.png')
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
    client.update_capabilities()
    try:
        client.long_polling_loop()
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt received, stopping application.')
