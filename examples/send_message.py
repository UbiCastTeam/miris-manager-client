#!/usr/bin/env python3
'''
Script to send a message
'''
import argparse
import datetime

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

    client = MirisManagerClient(args.conf)
    client.api_request('ADD_MESSAGE', data=dict(
        content='%s\nTest message' % datetime.datetime.now(),
        content_debug='Debug content with some special characters:\n\tđ€¶←←ħ¶ŧħ<< "\' fF5ef',
        level='warning'
    ))
    print('Message sent')
