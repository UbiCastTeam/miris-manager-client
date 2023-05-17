#!/usr/bin/env python3
'''
An example of Miris Manager client usage.
This script is intended to send screenshot and handle click requests.
'''
import logging
import os
import sys
from mm_client.client import MirisManagerClient

logger = logging.getLogger('screen_controller')


class ScreenController(MirisManagerClient):
    DEFAULT_CONF = {
        'CAPABILITIES': ['screen_control', 'screenshot'],
    }

    def handle_action(self, uid, action, params):
        if action == 'GET_SCREENSHOT':
            self.set_status(remaining_space='auto')  # Send remaining space to Miris Manager
            self.set_screenshot(
                path='/var/lib/AccountsService/icons/%s' % (os.environ.get('USER') or 'root'),
                file_name='screen.png'
            )
            logger.info('Screenshot sent.')
            return 'DONE', ''

        elif action == 'SIMULATE_CLICK':
            logger.info('Click requested: %s.', params)
            return 'DONE', ''

        elif action == 'SEND_TEXT':
            logger.info('Text received: %s.', params)
            return 'DONE', ''

        else:
            raise NotImplementedError('Unsupported action: %s.' % action)


if __name__ == '__main__':
    local_conf = sys.argv[1] if len(sys.argv) > 1 else None
    client = ScreenController(local_conf)
    client.update_capabilities()
    try:
        client.long_polling_loop()
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt received, stopping application.')
