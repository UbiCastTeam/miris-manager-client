#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Campus Manager client library
This module is not intended to be used directly, only the client class should be used.
'''
import imp
import logging
import os
import re
import socket
import subprocess
import uuid
from cm_client import conf as base_conf

logger = logging.getLogger('cm_client.lib')


def load_conf(default_conf=None, local_conf=None):
    # copy default configuration
    conf = dict()
    for key in dir(base_conf):
        if not key.startswith('_'):
            conf[key] = getattr(base_conf, key)
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
                try:
                    conf_mod = imp.load_source('conf_mod_%s' % index, conf_override)
                except ImportError as e:
                    logger.error('Unable to load config file %s: %s', conf_override, e)
                else:
                    logger.info('Config file "%s" loaded.', conf_override)
                    for key in dir(conf_mod):
                        if not key.startswith('_'):
                            conf[key] = getattr(conf_mod, key)
            else:
                logger.info('Config file does not exists, using default config.')
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
        with open(local_conf, 'r') as fd:
            content = fd.read()
        content = content.strip()
    new_content = ''
    for line in content.split('\n'):
        if not line.startswith(key):
            new_content += '%s\n' % line
    new_content += '%s = \'%s\'\n' % (key, value)
    with open(local_conf, 'w') as fd:
        fd.write(new_content)
    logger.info('Configuration file "%s" updated: "%s" set to "%s".', local_conf, key, value)


def get_host_info(cm_url):
    # get hostname
    hostname = socket.gethostname()
    logger.info('Hostname is %s.', hostname)
    # get local IP address
    cm_host = cm_url.split('://')[-1]
    if ':' in cm_host:
        cm_host, cm_port = cm_host.split(':')
        cm_port = int(cm_port)
    elif cm_url.startswith('http:'):
        cm_port = 80
    else:
        cm_port = 443
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((cm_host, cm_port))
    local_ip = s.getsockname()[0]
    s.close()
    logger.info('Local IP is %s.', local_ip)
    # get MAC address
    node = uuid.getnode()
    mac = ':'.join(('%012x' % node)[i:i + 2] for i in range(0, 12, 2))
    logger.info('Client mac address is: %s.', mac)
    return dict(
        alt_hostname=hostname,
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
