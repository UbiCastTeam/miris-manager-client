#!/usr/bin/env python3
'''
Script to ping a Miris Manager server.
'''
import argparse

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
