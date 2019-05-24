#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Miris Manager SSH tunnel management
This module is not intended to be used directly, only the client class should be used.
The SSH tunnel goal is to access the system web interface (HTTPS) from Miris Manager using a connection from the system to the Miris Manager.
'''
import logging
import os
import subprocess
import time
import multiprocessing
import re
import signal

logger = logging.getLogger('mm_client.lib.ssh_tunnel')


def get_ssh_public_key():
    ssh_key_path = os.path.join(os.path.expanduser('~/.ssh/miris-manager-client-key'))
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
    ssh_key_path = os.path.join(os.path.expanduser('~/.ssh/miris-manager-client-key'))
    command = ['ssh', '-i', ssh_key_path, '-o', 'IdentitiesOnly yes', '-nvNT', '-o', 'NumberOfPasswordPrompts 0', '-o' 'CheckHostIP no', '-o', 'StrictHostKeyChecking no', '-R', '%s:127.0.0.1:443' % port, 'skyreach@%s' % target]
    logger.info('Running following command to establish SSH tunnel: %s', command)
    return command


class SSHTunnelManager():

    def __init__(self, client, status_callback=None):
        self.client = client
        self.status_callback = status_callback
        self.pattern_list = [
            dict(id='connecting', pattern=re.compile(r'debug1: Connecting to (?P<hostname>[^ ]+) \[(?P<ip>[0-9\.]{7,15})\] port (?P<port>\d{1,5}).\r\n')),
            dict(id='connected', pattern=re.compile(r'debug1: Connection established.\r\n')),
            dict(id='authenticated', pattern=re.compile(r'debug1: Authentication succeeded \((?P<method>[^\)]+)\).\r\n')),
            dict(id='authenticated', pattern=re.compile(r'Authenticated to (?P<hostname>[^ ]+) \(\[(?P<ip>[0-9\.]{7,15})\]:(?P<port>\d{1,5})\).\r\n')),
            dict(id='running', pattern=re.compile(r'debug1: Entering interactive session.\r\n')),
            dict(id='not_known', pattern=re.compile(r'ssh: [^:]+: Name or service not known\r\n')),
            dict(id='port_refused', pattern=re.compile(r'Warning: remote port forwarding failed for listen port (?P<port>\d{1,5})')),
            dict(id='refused', pattern=re.compile(r'ssh: connect to host [^:]+: Connection refused\r\n')),
            dict(id='denied', pattern=re.compile(r'Permission denied \(publickey,password\).\r\n')),
            dict(id='closed', pattern=re.compile(r'Connection to (?P<hostname>[^ ]+) closed.\r\n')),
        ]
        self.loop_ssh_tunnel = True
        self.process = None
        self.stdout_queue = None
        self.stdout_reader = None
        self.stderr_reader = None
        self.ssh_tunnel_state = {
            'port': 0,
            'state': 'Not running',
            'command': '',
            'last_tunnel_info': ''
        }

    def establish_tunnel(self):
        public_key = None
        response = None
        logging.debug('establishing new tunnel')
        self._try_closing_process()
        self._stop_reader()
        try:
            logging.debug('prepare tunnel')
            public_key = get_ssh_public_key()
            response = self.client.api_request('PREPARE_TUNNEL', data=dict(public_key=public_key))
        except Exception as e:
            logger.error('Cannot prepare ssh tunnel : %s' % str(e))
            return
        self.update_ssh_state('port', response['port'])
        target = self.client.conf['SERVER_URL'].split('://')[-1]
        if target.endswith('/'):
            target = target[:-1]
        self.update_ssh_state('command', prepare_ssh_command(target, self.ssh_tunnel_state['port']))
        logger.debug('Starting SSH with command:\n    %s', self.ssh_tunnel_state['command'])
        self.process = subprocess.Popen(self.ssh_tunnel_state['command'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
        self.stdout_queue = multiprocessing.Queue()
        self.stdout_reader = AsynchronousFileReader(self.process.stdout, self.stdout_queue)
        self.stdout_reader.start()
        self.stderr_reader = AsynchronousFileReader(self.process.stderr, self.stdout_queue)
        self.stderr_reader.start()

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
        self._stop_reader()
        self._try_closing_process()

    def _try_closing_process(self):
        if self.process:
            logger.debug('Wait for ssh process')
            self.process.terminate()
            timeout = 5
            while self.process.poll() is None and timeout:
                timeout -= 1
                time.sleep(1)
            if not timeout:
                logger.error('SSH tunnel has not terminate try to kill')
                os.system('kill -- -$(ps hopgid %s | sed \'s/^ *//g\')' % self.process.pid)
                self.process.kill()
            else:
                logger.warning('SSH tunnel terminated')

    def _stop_reader(self):
        if self.stdout_reader:
            logger.debug('Wait for stdout process')
            self.stdout_reader.terminate()
            timeout = 5
            while self.stdout_reader.is_alive() and timeout:
                timeout -= 1
                time.sleep(1)
            if not timeout:
                os.kill(self.stdout_reader.pid, signal.SIGKILL)
                logger.warning('SSH stdout_reader killed')
            else:
                logger.warning('SSH stdout_reader terminated')
        if self.stderr_reader:
            logger.debug('Wait for stderr process')
            self.stderr_reader.terminate()
            timeout = 5
            while self.stderr_reader.is_alive() and timeout:
                timeout -= 1
                time.sleep(1)
            if not timeout:
                os.kill(self.stderr_reader.pid, signal.SIGKILL)
                logger.warning('SSH stderr_reader killed')
            else:
                logger.warning('SSH stderr_reader terminated')
        if self.stdout_queue:
            logger.debug('Wait for ssh queue')
            self.stdout_queue.close()
            self.stdout_queue.cancel_join_thread()
            logger.warning('SSH queue closed')

    def tunnel_loop(self):
        check_delay = 10
        while self.loop_ssh_tunnel:
            need_retry = False
            if self.process:
                return_code = self.process.poll()
                if return_code is not None:
                    ssh_logs = ''
                    while not self.stdout_queue.empty():
                        ssh_logs += self.stdout_queue.get_nowait()
                    self.update_ssh_state('state', 'error')
                    self.update_ssh_state('last_tunnel_info', ssh_logs)
                    logger.error('SSH tunnel process error. Return: %s' % ssh_logs)
                    need_retry = True
                else:
                    while not self.stdout_queue.empty():
                        ssh_stdout = self.stdout_queue.get_nowait()
                        id_founded = None
                        for pattern_dict in self.pattern_list:
                            if pattern_dict['pattern'].match(ssh_stdout):
                                id_founded = pattern_dict['id']
                                self.update_ssh_state('state', id_founded)
                                self.update_ssh_state('last_tunnel_info', ssh_stdout)
                                break
                        if not id_founded:
                            if ssh_stdout.startswith('debug1:') or ssh_stdout.startswith('OpenSSH_'):
                                logger.debug(ssh_stdout)
                            else:
                                logger.warning(ssh_stdout)
                        elif id_founded not in ['connecting', 'connected', 'authenticated', 'running']:
                            logger.error('Need to retry tunnel because ssh command failed in stdout %s' % id_founded)
                            need_retry = True
                            break
            else:
                logger.debug('Need to retry tunnel because no process')
                need_retry = True
            if need_retry:
                try:
                    self.establish_tunnel()
                except Exception as e:
                    logger.error('error while establishing tunnel %s' % str(e))

            time.sleep(check_delay)


class AsynchronousFileReader(multiprocessing.Process):
    def __init__(self, fd, data_queue):
        multiprocessing.Process.__init__(self)
        self._fd = fd
        self._queue = data_queue

    def run(self):
        while self.is_alive():
            line = self._fd.readline().decode('utf-8')
            if line:
                self._queue.put(line)
                continue
            time.sleep(2)

    def eof(self):
        return not self.is_alive() and self._queue.empty()
