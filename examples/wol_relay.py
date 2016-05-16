#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
An example of Campus Manager client usage.
This script is intended to create devices acting as wake on lan relay and video displayer.
"""
import logging
import os
import re
from cm_client import CampusManagerClient

logger = logging.getLogger('cm_wol_relay')


class WOLRelay(CampusManagerClient):
    CONF_PATH = os.path.expanduser('~/.cm_example.py')
    CONF = dict(CampusManagerClient.CONF)
    CONF.update({
        'CAPABILITIES': {  # This list makes available or not actions buttons in Campus Manager
            'wol_relay': {'version': 1},
            'player': {'version': 1},
        },
        'WOL_PATH': 'wakeonlan',  # Path to wake on lan binary
    })

    def handle_action(self, action, params):
        # This method must be implemented in your client
        if action == 'WAKE_ON_LAN_SEND':  # wol_relay capability
            # Send wake on lan
            success, message = self.send_wake_on_lan(params)
            logger.info('Running wake on lan: success: %s, message: %s', success, message)
            if not success:
                raise Exception('Failed to send wake on lan: %s' % message)
        elif action == 'PLAY_STREAM':  # player capability
            # Play a video stream
            # http://www.sample-videos.com/video/mp4/240/big_buck_bunny_240p_1mb.mp4
            stream_uri = params.get('stream_uri')
            if not stream_uri:
                raise Exception('No stream URI to play.')
            if '"' in stream_uri or '\'' in stream_uri:
                raise Exception('Invalid stream URI.')
            os.system('(vlc "%s" &)' % stream_uri)
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
            cmd = '%s -i "%s" "%s"' % (self.CONF['WOL_PATH'], ip_address, mac_address)
        else:
            cmd = '%s "%s"' % (self.CONF['WOL_PATH'], mac_address)
        ret_code = os.system(cmd)
        if ret_code != 0:
            return False, 'Tool returned code %s.' % (ret_code >> 8)
        return True, 'Wake on lan package sent.'


if __name__ == '__main__':
    WOLRelay()
