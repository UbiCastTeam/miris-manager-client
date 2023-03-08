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
    '''
    Collect information on local system.
    '''
    # get hostname
    hostname = socket.gethostname()
    # get local IP address
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
    try:
        s.connect((host, port))
    except Exception as e:
        s.close()
        raise e
    local_ip = s.getsockname()[0]
    s.close()
    # get MAC address
    node = uuid.getnode()
    mac = ':'.join(('%012x' % node)[i:i + 2] for i in range(0, 12, 2))
    info = dict(
        hostname=hostname,
        local_ip=local_ip,
        mac=mac,
    )
    logger.debug('[%s] Client info is %s' % (host, info))
    return info


def get_free_space_bytes(path):
    '''
    Get free space on partition used for given path.
    '''
    statvfs = os.statvfs(path)
    free = statvfs.f_frsize * statvfs.f_bavail
    return free


def get_remaining_space():
    '''
    Return remaining space in /home in MB.
    '''
    return int(get_free_space_bytes('/home') / 1000000)
