#!/usr/bin/env python3
'''
Script to send a message
'''
import datetime
import sys
from mm_client.client import MirisManagerClient


if __name__ == '__main__':
    local_conf = sys.argv[1] if len(sys.argv) > 1 else None
    client = MirisManagerClient(local_conf)
    client.api_request('ADD_MESSAGE', data=dict(
        content='%s\nTest message' % datetime.datetime.now(),
        content_debug='Debug content with some special characters:\n\tđ€¶←←ħ¶ŧħ<< "\' fF5ef',
        level='warning'
    ))
    print('Message sent')
