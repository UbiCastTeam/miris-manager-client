#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Campus Manager SSH tunnel management
This module is not intended to be used directly, only the client class should be used.
The SSH tunnel goal is to access the system web interface (HTTPS) from Campus Manager using a connection from the system to the Campus Manager.
'''
import logging
import os
import subprocess
import time

logger = logging.getLogger('cm_client.ssh_tunnel')


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


class SSHTunnelManager():

    def __init__(self, client, status_callback=None):
        self.client = client
        self.status_callback = status_callback
        '''
        self.pattern_list = [
            dict(id='connecting', pattern=re.compile(b'debug1: Connecting to (?P<hostname>[^ ]+) \[(?P<ip>[0-9\.]{7,15})\] port (?P<port>\d{1,5}).\r\r\n')),
            dict(id='connected', pattern=re.compile(b'debug1: Connection established.\r\r\n')),
            dict(id='authenticated', pattern=re.compile(b'debug1: Authentication succeeded \((?P<method>[^\)]+)\).\r\r\n')),
            dict(id='ready', pattern=re.compile(b'debug1: Entering interactive session.\r\r\n')),
            dict(id='not_known', pattern=re.compile(b'ssh: [^:]+: Name or service not known\r\r\n')),
            dict(id='refused', pattern=re.compile(b'ssh: connect to host [^:]+: Connection refused\r\r\n')),
            dict(id='denied', pattern=re.compile(b'Permission denied \(publickey,password\).\r\r\n')),
            dict(id='closed', pattern=re.compile(b'Connection to (?P<hostname>[^ ]+) closed.\r\r\n')),
        ]
        '''
        self.loop_ssh_tunnel = True
        self.process = None
        self.ssh_tunnel_state = {
            'port': 0,
            'state': 'Not running',
            'command': '',
            'last_tunnel_info': ''
        }

    def establish_tunnel(self):
        public_key = get_ssh_public_key()
        response = self.client.api_request('PREPARE_TUNNEL', data=dict(public_key=public_key))
        self.update_ssh_state('port', response['port'])
        target = self.client.conf['URL'].split('://')[-1]
        self.update_ssh_state('command', prepare_ssh_command(target, self.ssh_tunnel_state['port']))
        logger.info('Starting SSH with command:\n    %s', self.ssh_tunnel_state['command'])
        self.process = subprocess.Popen(self.ssh_tunnel_state['command'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def update_ssh_state(self, key, value):
        if self.ssh_tunnel_state.get(key) is not None:
            self.ssh_tunnel_state[key] = value
        else:
            logger.warning('Key %s not exists in ssh state dict' % key)
        if self.status_callback:
            self.status_callback(self.ssh_tunnel_state)

    def close_tunnel(self):
        logger.warning('Close ssh tunnel asked')
        self.loop_ssh_tunnel = False
        if self.process:
            self.process.kill()
        logger.warning('SSH tunnel killed')

    def tunnel_loop(self):
        check_delay = 10
        while self.loop_ssh_tunnel:
            logger.debug('Checking ssh tunnel process.')
            if self.process:
                return_code = self.process.poll()
                if return_code is not None:
                    data = return_code
                    try:
                        data = self.process.stderr.read().decode('utf-8').split('\r\n')[-2]
                    except Exception:
                        logger.warning('Can\'t read stderr of ssh connection')
                    logger.error('SSH tunnel process error. Return: %s' % data)
                    self.update_ssh_state('state', 'error')
                    self.update_ssh_state('last_tunnel_info', data)
                    try:
                        self.establish_tunnel()
                    except Exception as e:
                        logger.error(e)
                else:
                    # Reading stdout without blocking not exists in standard python
                    self.update_ssh_state('state', 'running')
                    self.update_ssh_state('last_tunnel_info', '')
                    logger.debug('SSH tunnel process running')
                    # stdout_text = self.process.stdout.readline()
                    # print('************************************************')
                    # print(stdout_text)
                    # pattern_id = 'test'
                    # logger.info('Pattern recognized: %s', pattern_id)
                    # self.update_ssh_state('state', pattern_id)
                    # if pattern_id in ('not_known', 'refused', 'denied', 'closed'):
                    #     logger.warning('SSH tunnel connection problem: %s', pattern_id)
                    #     check_delay = 30
            else:
                try:
                    self.establish_tunnel()
                except Exception as e:
                    logger.error(e)

            time.sleep(check_delay)