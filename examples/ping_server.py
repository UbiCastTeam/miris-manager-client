#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Script to ping a Miris Manager server.
'''
import os
import sys


if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mm_client.client import MirisManagerClient

    local_conf = sys.argv[1] if len(sys.argv) > 1 else None
    mmc = MirisManagerClient(local_conf)
    # ping
    print(mmc.api_request('PING'))
