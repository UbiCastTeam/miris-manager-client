#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Miris Manager client library
This module is not intended to be used directly, only the client class should be used.
'''
import logging
import socket
import uuid
import os

logger = logging.getLogger('mm_client.lib.info')


def get_host_info(url):
    # get hostname
    hostname = socket.gethostname()
    logger.debug('Hostname is %s.', hostname)
    # get local IP address
    logger.debug('check local ip of %s' % url)
    host = url.split('://')[-1]
    if ':' in host:
        host, port = host.split(':')
        port = int(port)
    elif url.startswith('http:'):
        port = 80
    else:
        port = 443
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if host.endswith('/'):
        host = host[:-1]
    s.connect((host, port))
    local_ip = s.getsockname()[0]
    s.close()
    logger.debug('Local IP is %s.', local_ip)
    # get MAC address
    node = uuid.getnode()
    mac = ':'.join(('%012x' % node)[i:i + 2] for i in range(0, 12, 2))
    logger.debug('Client mac address is: %s.', mac)
    return dict(
        hostname=hostname,
        local_ip=local_ip,
        mac=mac,
    )


def get_free_space_bytes(path):
    statvfs = os.statvfs(path)
    free = statvfs.f_frsize * statvfs.f_bavail
    return free


def get_remaining_space():
    '''
    Return remaining space in /home in MB
    '''
    return int(get_free_space_bytes('/home') / (1024 * 1024))
