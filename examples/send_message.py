#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Script to send a message
'''
import datetime
from mm_client.client import MirisManagerClient


if __name__ == '__main__':
    client = MirisManagerClient()
    client.api_request('ADD_MESSAGE', data=dict(
        content='%s\nTest message' % datetime.datetime.now(),
        content_debug='Debug content with some special characters:\n\tđ€¶←←ħ¶ŧħ<< "\' fF5ef',
        level='warning'
    ))
    print('Message sent')
