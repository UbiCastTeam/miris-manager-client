'''
Miris Manager SSH tunnel management
This module is not intended to be used directly, only the client class should be used.

The SSH tunnel goal is to access the system web interface (HTTPS) from
Miris Manager using a connection from the system to the Miris Manager.
'''
import logging
import os
import subprocess
import time
import multiprocessing
import re
import signal
from pathlib import Path

logger = logging.getLogger('mm_client.lib.ssh_tunnel')


class MirisManagerTunnelError(Exception):
    pass


def get_ssh_public_key():
    ssh_dir = Path('~/.ssh').expanduser()
    ssh_key_path = ssh_dir / 'miris-manager-client-key'
    ssh_pub_path = ssh_dir / 'miris-manager-client-key.pub'
    if not ssh_dir.exists():
        ssh_dir.mkdir(parents=True)
        ssh_dir.chmod(0o700)
    if ssh_key_path.exists():
        if not ssh_pub_path.exists():
            raise MirisManagerTunnelError(
                f'Weird state detetected: "{ssh_key_path}" exists but not "{ssh_pub_path}" !'
            )
        logger.debug('Using existing SSH key: "%s".', ssh_key_path)
    else:
        logger.info('Creating new SSH key: "%s".', ssh_key_path)
        p = subprocess.Popen(
            ['ssh-keygen', '-t', 'rsa', '-b', '4096', '-f', str(ssh_key_path), '-N', ''],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        p.communicate(input=b'\n\n\n')
        if p.returncode != 0:
            out = p.stdout.decode('utf-8').strip()
            raise MirisManagerTunnelError(
                f'Failed to generate SSH key:\n{out}'
            )
        ssh_key_path.chmod(0o600)
        ssh_pub_path.chmod(0o600)
    public_key = ssh_pub_path.read_text()
    return public_key


def prepare_ssh_command(host, info):
    ssh_key_path = Path('~/.ssh/miris-manager-client-key').expanduser()
    command = ['ssh',
               '-i', str(ssh_key_path),
               '-nvNT',
               '-o', 'IdentitiesOnly=yes',
               '-o', 'NumberOfPasswordPrompts=0',
               '-o', 'CheckHostIP=no',
               '-o', 'StrictHostKeyChecking=no',
               '-o', 'ServerAliveInterval=10',
               '-R', '%s:127.0.0.1:443' % info['control_port'],
               '-R', '%s:127.0.0.1:22' % info['maintenance_port'],
               '-p', str(info['ssh_port']),
               '%s@%s' % (info['ssh_user'], host)]
    return command


class SSHTunnelManager():

    def __init__(self, client, status_callback=None):
        self.client = client
        self.status_callback = status_callback
        self.pattern_list = [
            dict(id='connecting', pattern=re.compile(
                r'debug1: Connecting to (?P<hostname>[^ ]+) \[(?P<ip>[0-9\.]{7,15})\] port (?P<port>\d{1,5}).\r\n'
            )),
            dict(id='connected', pattern=re.compile(
                r'debug1: Connection established.\r\n'
            )),
            dict(id='authenticated', pattern=re.compile(
                r'debug1: Authentication succeeded \((?P<method>[^\)]+)\).\r\n'
            )),
            dict(id='authenticated', pattern=re.compile(
                r'Authenticated to (?P<hostname>[^ ]+) \(\[(?P<ip>[0-9\.]{7,15})\]:(?P<port>\d{1,5})\).\r\n'
            )),
            dict(id='running', pattern=re.compile(
                r'debug1: Entering interactive session.\r\n'
            )),
            dict(id='not_known', pattern=re.compile(
                r'ssh: [^:]+: Name or service not known\r\n'
            )),
            dict(id='port_refused', pattern=re.compile(
                r'Warning: remote port forwarding failed for listen port (?P<port>\d{1,5})'
            )),
            dict(id='refused', pattern=re.compile(
                r'ssh: connect to host [^:]+: Connection refused\r\n'
            )),
            dict(id='control_refused', pattern=re.compile(
                r'connect_to (?P<hostname>[^ ]+) port (?P<port>\d{1,5}): failed\.\r\n'
            )),
            dict(id='denied', pattern=re.compile(
                r'Permission denied \(publickey,password\).\r\n'
            )),
            dict(id='closed', pattern=re.compile(
                r'Connection to (?P<hostname>[^ ]+) closed.\r\n'
            )),
        ]
        self.loop_ssh_tunnel = False
        self.process = None
        self.stdout_queue = None
        self.stdout_reader = None
        self.stderr_reader = None
        self.ssh_tunnel_state = {
            'ssh_user': 'skyreach',
            'ssh_port': 22,
            'control_port': 0,
            'maintenance_port': 0,
            'state': 'Not running',
            'command': '',
            'last_tunnel_info': ''
        }

    def establish_tunnel(self):
        public_key = None
        response = None
        logger.debug('Establishing new tunnel to %s', self.client.conf['SERVER_URL'])
        self._stop_reader()
        self._try_closing_process()
        self.update_ssh_state('state', 'prepare tunnel')
        try:
            logger.debug('Prepare tunnel')
            public_key = get_ssh_public_key()
            response = self.client.api_request('PREPARE_TUNNEL', data=dict(public_key=public_key))
        except Exception as e:
            self.update_ssh_state('state', 'prepare tunnel failed')
            self.update_ssh_state('control_port', 0)
            self.update_ssh_state('maintenance_port', 0)
            self.update_ssh_state('command', ['PREPARE_TUNNEL', self.client.conf['SERVER_URL']])
            logger.error('Cannot prepare ssh tunnel : %s', str(e))
            return
        ssh_user = response.get('ssh_user')
        if ssh_user and ssh_user != self.ssh_tunnel_state['ssh_user']:
            self.update_ssh_state('ssh_user', response['ssh_user'])
        ssh_port = response.get('ssh_port')
        if ssh_port and ssh_port != self.ssh_tunnel_state['ssh_port']:
            self.update_ssh_state('ssh_port', response['ssh_port'])
        maintenance_port = response.get('maintenance_port')
        if maintenance_port and maintenance_port != self.ssh_tunnel_state['maintenance_port']:
            self.update_ssh_state('maintenance_port', response['maintenance_port'])
        port = response.get('control_port') or response.get('port')
        if port is not None:
            self.update_ssh_state('control_port', port)
            host = self.client.conf['SERVER_URL'].split('://', 1)[-1]
            host = host.rsplit(':', 1)[0].rstrip('/')
            cmd = prepare_ssh_command(host, self.ssh_tunnel_state)
            self.update_ssh_state('command', cmd)
            logger.info('Starting SSH with command:\n    %s', ' '.join(cmd))
            if self.loop_ssh_tunnel:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid
                )
                self.stdout_queue = multiprocessing.Queue()
                self.stdout_reader = AsynchronousFileReader(self.process.stdout, self.stdout_queue)
                self.stdout_reader.start()
                self.stderr_reader = AsynchronousFileReader(self.process.stderr, self.stdout_queue)
                self.stderr_reader.start()
                return True
        else:
            logger.debug('No control port provided, not starting ssh tunnel')

    def update_ssh_state(self, key, value):
        if key == 'state' and self.ssh_tunnel_state.get('state') != value:
            logger.info('SSH state changed to %s', value)
        if self.ssh_tunnel_state.get(key) is not None:
            self.ssh_tunnel_state[key] = value
        else:
            logger.warning('Key %s not exists in ssh state dict', key)
        if self.status_callback:
            self.status_callback(self.ssh_tunnel_state)

    def close_tunnel(self, thread_event=None):
        logger.debug('Close ssh tunnel asked')
        self.loop_ssh_tunnel = False
        if thread_event:
            thread_event.set()
        self._stop_reader()
        self._try_closing_process()

    def _try_closing_process(self):
        if self.process:
            timeout = 5
            logger.debug('Waiting %ss for ssh process to terminate' % timeout)
            self.process.terminate()
            while self.process and self.process.poll() is None and timeout != 0:
                timeout -= 1
                time.sleep(1)
            if timeout == 0:
                logger.warning('SSH tunnel has not terminated, trying to kill it')
                pgrp = os.getpgid(self.process.pid)
                os.killpg(pgrp, signal.SIGINT)
                # self.process.kill()
                logger.warning('SSH tunnel killed')
            else:
                logger.info('SSH tunnel subprocess terminated')
            self.process = None

    def _stop_reader(self):
        if self.stdout_reader is not None and self.stdout_reader.pid is not None:
            logger.debug('Waiting for stdout_reader subprocess to terminate')
            try:
                os.kill(self.stdout_reader.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.stdout_reader = None
            logger.debug('SSH stdout_reader killed')

        if self.stderr_reader is not None and self.stderr_reader.pid is not None:
            logger.debug('Wait for stderr_reader subprocess to terminate')
            try:
                os.kill(self.stderr_reader.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.stderr_reader = None
            logger.debug('SSH stderr_reader killed')

        if self.stdout_queue:
            logger.debug('Waiting for ssh queue to close')
            self.stdout_queue.close()
            self.stdout_queue.cancel_join_thread()
            self.stdout_queue = None
            logger.debug('SSH queue closed')

    def tunnel_loop(self, thread_event=None):
        check_delay = 1
        self.loop_ssh_tunnel = True
        self.update_ssh_state('state', 'loading')
        self.update_ssh_state('control_port', 0)
        self.update_ssh_state('maintenance_port', 0)
        self.update_ssh_state('command', ['Load', self.client.conf['SERVER_URL']])
        while self.loop_ssh_tunnel:
            need_retry = False
            if self.process is not None:
                need_retry = self.read_ssh_stdout()
            else:
                need_retry = True
            if need_retry:
                try:
                    success = self.establish_tunnel()
                except Exception as e:
                    logger.error('error while establishing tunnel %s', e)
                if need_retry or not success:
                    self._wait(thread_event)
            else:
                self._wait(thread_event, check_delay)

    def _wait(self, thread_event=None, delay=10):
        if thread_event:
            # blocking unless thread_event.set() is called
            thread_event.wait(delay)
        else:
            # use a normal sleep if not running in a thread
            time.sleep(delay)

    def read_ssh_stdout(self):
        need_retry = False
        return_code = self.process.poll()
        if return_code is not None:
            logger.debug('SSH process has terminated')
            ssh_logs = ''
            try:
                while not self.stdout_queue.empty():
                    ssh_logs += self.stdout_queue.get_nowait()
            except OSError as e:
                ssh_logs = str(e)
            self.update_ssh_state('state', 'error')
            self.update_ssh_state('last_tunnel_info', ssh_logs)
            logger.error('SSH tunnel process has terminated with: %s', ssh_logs)
            need_retry = True
        else:
            # process is still alive
            try:
                while not self.stdout_queue.empty():
                    ssh_stdout = self.stdout_queue.get_nowait()
                    pattern_id_found = None
                    for pattern_dict in self.pattern_list:
                        if pattern_dict['pattern'].match(ssh_stdout):
                            pattern_id_found = pattern_dict['id']
                            self.update_ssh_state('state', pattern_id_found)
                            self.update_ssh_state('last_tunnel_info', ssh_stdout)
                            break
                    if not pattern_id_found:
                        if ssh_stdout.startswith('debug1:') or ssh_stdout.startswith('OpenSSH_'):
                            logger.debug('[SSH stdout] %s', ssh_stdout)
                        else:
                            logger.warning('[SSH stdout] %s', ssh_stdout)
                    elif pattern_id_found not in ['connecting', 'connected', 'authenticated', 'running']:
                        logger.error(
                            (
                                'Need to retry tunnel '
                                '(ssh port: %s, remote control port: %s, remote maintenance port: %s) '
                                'because ssh command failed in stdout %s'
                            ),
                            self.ssh_tunnel_state.get('ssh_port'),
                            self.ssh_tunnel_state.get('control_port'),
                            self.ssh_tunnel_state.get('maintenance_port'),
                            pattern_id_found
                        )
                        need_retry = True
                        break
            except OSError as e:
                logger.error(e)
                need_retry = True
        return need_retry


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
            time.sleep(.5)

    def eof(self):
        return not self.is_alive() and self._queue.empty()
