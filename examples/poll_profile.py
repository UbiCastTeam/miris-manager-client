#!/usr/bin/env python3
'''
Script to poll a profile status in a Miris Manager server.
The script is intended to be used with a user API key and not a system API key.
'''
import argparse
import time

from mm_client.client import MirisManagerClient


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

    mmc = MirisManagerClient(args.conf)
    # ping
    print(mmc.api_request('PING'))
    # poll profile status
    while True:
        print(mmc.api_request('GET_STATUS', params=dict(profile='common')))
        time.sleep(5)
