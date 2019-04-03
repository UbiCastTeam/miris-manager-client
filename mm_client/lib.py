#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Miris Manager client library
This module is not intended to be used directly, only the client class should be used.
'''
import json
import logging
import os
import re
import socket
import subprocess
import uuid

logger = logging.getLogger('mm_client.lib')

BASE_CONF_PATH = os.path.join(os.path.dirname(__file__), 'conf.json')


def load_conf(default_conf=None, local_conf=None):
    # copy default configuration
    with open(BASE_CONF_PATH, 'r') as fo:
        content = fo.read()
    content = re.sub(r'\n\s*//.*', '\n', content)  # remove comments
    conf = json.loads(content)
    # update with default and local configuration
    for index, conf_override in enumerate((default_conf, local_conf)):
        if not conf_override:
            continue
        if isinstance(conf_override, dict):
            for key, val in conf_override.items():
                if not key.startswith('_'):
                    conf[key] = val
        elif isinstance(conf_override, str):
            if os.path.exists(conf_override):
                with open(conf_override, 'r') as fo:
                    content = fo.read()
                content = re.sub(r'\n\s*//.*', '\n', content)  # remove comments
                conf_mod = json.loads(content) if content else None
                if not conf_mod:
                    logger.debug('Config file "%s" is empty.', conf_override)
                else:
                    logger.debug('Config file "%s" loaded.', conf_override)
                    if not isinstance(conf_mod, dict):
                        raise ValueError('The configuration in "%s" is not a dict.' % conf_override)
                    conf.update(conf_mod)
            else:
                logger.debug('Config file does not exists, using default config.')
        else:
            raise ValueError('Unsupported type for configuration.')
    if conf['URL'].endswith('/'):
        conf['URL'] = conf['URL'].rstrip('/')
    return conf


def update_conf(local_conf, key, value):
    if not local_conf or not isinstance(local_conf, str):
        logger.debug('Cannot update configuration, "local_conf" is not a path.')
        return
    content = ''
    if os.path.isfile(local_conf):
        with open(local_conf, 'r') as fo:
            content = fo.read()
        content = content.strip()
    data = json.loads(content) if content else dict()
    data[key] = value
    new_content = json.dumps(data, sort_keys=True, indent=4)
    with open(local_conf, 'w') as fo:
        fo.write(new_content)
    logger.debug('Configuration file "%s" updated: "%s" set to "%s".', local_conf, key, value)


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


def get_remaining_space():
    # return remaining space in /home
    p = subprocess.Popen('df -x fuse.gvfs-fuse-daemon 2>/dev/null', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    out = out.decode('utf-8') if out else ''
    remaining_space = None
    for line in out.split('\n'):
        if line.endswith(' /home') or not remaining_space and line.endswith(' /'):
            line = re.sub(r' +', ' ', line)
            splitted = line.split(' ')
            if len(splitted) == 6:
                filesystem, size, used, available, used_percent, mount_point = splitted
                try:
                    remaining_space = int(int(available) / 1000)
                except ValueError:
                    pass
    return remaining_space
