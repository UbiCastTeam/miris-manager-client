#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Campus Manager client library
This module is not intended to be used directly, only the client class should be used.
'''
import json
import logging
import os
import re
import socket
import subprocess
import uuid

logger = logging.getLogger('cm_client.lib')

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
                    logger.info('Config file "%s" is empty.', conf_override)
                else:
                    logger.info('Config file "%s" loaded.', conf_override)
                    if not isinstance(conf_mod, dict):
                        raise ValueError('The configuration in "%s" is not a dict.' % conf_override)
                    conf.update(conf_mod)
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
        with open(local_conf, 'r') as fo:
            content = fo.read()
        content = content.strip()
    data = json.loads(content) if content else dict()
    data[key] = value
    new_content = json.dumps(data, sort_keys=True, indent=4)
    with open(local_conf, 'w') as fo:
        fo.write(new_content)
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


def get_ssh_public_key():
    ssh_key_path = os.path.join(os.path.expanduser('~/.ssh/campus-manager-client-key'))
    ssh_dir = os.path.dirname(ssh_key_path)
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir)
        os.chmod(ssh_dir, 0o700)
    if os.path.exists(ssh_key_path):
        if not os.path.exists(ssh_key_path + '.pub'):
            raise Exception('Weird state detetected: "%s" exists but not "%s" !' % (ssh_key_path, ssh_key_path + '.pub'))
        logger.info('Using existing SSH key: "%s".', ssh_key_path)
    else:
        logger.info('Creating new SSH key: "%s".', ssh_key_path)
        p = subprocess.Popen(['ssh-keygen', '-b', '4096', '-f', ssh_key_path, '-N', ''], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate(input=b'\n\n\n')
        if p.returncode != 0:
            out = p.stdout.decode('utf-8') + '\n' + p.stderr.decode('utf-8')
            raise Exception('Failed to generate SSH key:\n%s' % out)
        os.chmod(ssh_key_path, 0o600)
        os.chmod(ssh_key_path + '.pub', 0o600)
    with open(ssh_key_path + '.pub', 'r') as fo:
        public_key = fo.read()
    return public_key


def prepare_ssh_command(target, port):
    ssh_key_path = os.path.join(os.path.expanduser('~/.ssh/campus-manager-client-key'))
    command = ['ssh', '-i', ssh_key_path, '-o', 'IdentitiesOnly yes', '-nvNT', '-o', 'NumberOfPasswordPrompts 0', '-o' 'CheckHostIP no', '-o', 'StrictHostKeyChecking no', '-R', '%s:127.0.0.1:443' % port, 'skyreach@%s' % target]
    logger.info('Running following command to establish SSH tunnel: %s', command)
    return command
