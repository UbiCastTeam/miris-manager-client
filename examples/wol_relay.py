#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
An example of Campus Manager client usage.
This script is intended to create devices acting as wake on lan relay and video displayer.
'''
import logging
import os
import re
from cm_client import CampusManagerClient

logger = logging.getLogger('wol_relay')


class WOLRelay(CampusManagerClient):
    DEFAULT_CONF = {
        'CAPABILITIES': ['send_wake_on_lan'],
        'WOL_PATH': 'wakeonlan',  # Path to the wake on lan binary
    }

    def handle_action(self, action, params):
        # This method must be implemented in your client
        if action == 'WAKE_ON_LAN':  # wol_relay capability
            # Send wake on lan
            success, message = self.send_wake_on_lan(params)
            logger.info('Running wake on lan: success: %s, message: %s', success, message)
            if not success:
                raise Exception('Failed to send wake on lan: %s' % message)
        else:
            raise Exception('Unsupported action: %s.' % action)

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
    client = WOLRelay()
    client.update_capabilities()
    try:
        client.long_polling_loop()
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt received, stopping application.')
