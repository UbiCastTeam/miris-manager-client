#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Script to poll a profile status in a Miris Manager server.
The script is intended to be used with a user API key and not a system API key.
'''
import os
import sys
import time


if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mm_client.client import MirisManagerClient

    local_conf = sys.argv[1] if len(sys.argv) > 1 else None
    mmc = MirisManagerClient(local_conf)
    # ping
    print(mmc.api_request('PING'))
    # poll profile status
    while True:
        print(mmc.api_request('GET_STATUS', params=dict(profile='common')))
        time.sleep(5)
