#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Script to send a message
'''
import datetime
from cm_client import CampusManagerClient


if __name__ == '__main__':
    client = CampusManagerClient()
    client.api_request('ADD_MESSAGE', data=dict(
        content='%s\nTest message' % datetime.datetime.now(),
        content_debug='Debug content with some special characters:\n\tđ€¶←←ħ¶ŧħ<< "\' fF5ef',
        level='warning'
    ))
    print('Message sent')
