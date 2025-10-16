#!/usr/bin/env python3
'''
A script to create devices acting as wake on lan relay.
'''
import argparse
import logging
import os
import re

from mm_client.client import MirisManagerClient

logger = logging.getLogger('wol_relay')


class WOLRelay(MirisManagerClient):
    DEFAULT_CONF = {
        'CAPABILITIES': ['send_wake_on_lan'],
        'WOL_PATH': 'wakeonlan',  # Path to the wake on lan binary, installed with `apt install wakeonlan`
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.update_capabilities()
        try:
            self.long_polling_loop()
        except KeyboardInterrupt:
            logger.info('KeyboardInterrupt received, stopping application.')

    def handle_action(self, uid, action, params):
        # See help on the handle action function:
        # https://github.com/UbiCastTeam/miris-manager-client/blob/main/mm_client/client.py#L184
        # Possible actions:
        # https://mirismanager.ubicast.eu/static/skyreach/docs/api/values.html#system-command-actions
        if action == 'WAKE_ON_LAN':  # wol_relay capability
            # Send wake on lan
            success, message = self.send_wake_on_lan(params)
            logger.info('Running wake on lan: success: %s, message: %s', success, message)
            if not success:
                raise RuntimeError('Failed to send wake on lan: %s' % message)
            return 'DONE', ''
        else:
            raise NotImplementedError('Unsupported action: %s.' % action)

    def send_wake_on_lan(self, params):
        # Check that arguments are valid
        if 'mac' not in params:
            return False, 'No mac address in request.'
        mac_address = params['mac'].lower()
        matching = re.match(r'^([\da-f]{2}:){5}([\da-f]{2})$', mac_address)
        if not matching:
            return False, 'The given mac address is not valid.'
        ip_address = None
        if params.get('ip'):
            matching = re.match(r'^(\d{1,3}\.){3}\d{1,3}$', params['ip'])
            if not matching:
                return False, 'The given IP address is not valid.'
            ip_address = params['ip']
        # Launch wake on lan
        if ip_address:
            cmd = '%s -i "%s" "%s"' % (self.conf['WOL_PATH'], ip_address, mac_address)
        else:
            cmd = '%s "%s"' % (self.conf['WOL_PATH'], mac_address)
        ret_code = os.system(cmd)
        if ret_code != 0:
            return False, 'Tool returned code %s.' % (ret_code >> 8)
        return True, 'Wake on lan package sent.'


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

    WOLRelay(args.conf)
