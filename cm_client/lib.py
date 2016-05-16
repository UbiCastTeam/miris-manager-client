#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Campus Manager remote control library
"""
import base64
import datetime
import hashlib
import hmac
import json
import logging
import os
import re
import requests
import subprocess

logger = logging.getLogger('cm_client.lib')

ALLOWED_STATUS = (
    'UNKNOWN',
    'OFFLINE',
    'HOME',
    'PROCESSING',
    'REVIEW_IDLE',
    'REVIEW_PROCESSING',
    'DETECTION',
    'LOADING',
    'RECORDER_IDLE',
    'RECORDING',
    'STREAMING',
    'RECORDER_ERROR',
)


def get_signature(client):
    if not client.CONF.get('SECRET_KEY') or not client.CONF.get('API_KEY'):
        return dict()
    utime = datetime.datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S_%f')
    to_sign = 'time=%s|api_key=%s|mac=%s' % (utime, client.CONF['API_KEY'], client.mac)
    hm = hmac.new(
        client.CONF['SECRET_KEY'].encode('utf-8'),
        msg=to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    hm = base64.b64encode(hm).decode('utf-8')
    # headers with "_" are ignored by Django
    return {'api-key': client.CONF['API_KEY'], 'time': utime, 'hmac': hm}


def check_signature(client, rdata):
    if not client.CONF.get('SECRET_KEY') or not client.CONF.get('API_KEY'):
        return None
    remote_time = rdata.get('time')
    remote_hmac = rdata.get('hmac')
    if not remote_time or not remote_hmac:
        return 'some mandatory data are missing.'
    try:
        rdate = datetime.datetime.strptime(remote_time, '%Y-%m-%d_%H-%M-%S_%f')
    except ValueError:
        return 'the received time is invalid.'
    try:
        rhmac = base64.b64decode(remote_hmac)
    except Exception:
        return 'the received hmac is invalid.'
    utcnow = datetime.datetime.utcnow()
    diff = utcnow - rdate if utcnow > rdate else rdate - utcnow
    if diff.seconds > 300:
        return 'the difference between the request time and the current time is too large.'
    to_sign = 'time=%s|api_key=%s|mac=%s' % (remote_time, client.CONF['API_KEY'], client.mac)
    hm = hmac.new(
        client.CONF['SECRET_KEY'].encode('utf-8'),
        msg=to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    if rhmac != hm:
        return 'the received and computed HMAC values do not match.'
    return None


def _make_api_request(client, url_name, method='get', params=None, data=None, files=None):
    if not client.CONF.get('API_KEY'):
        raise Exception('No API key set.')
    signature = get_signature(client)
    req = requests.post(
        url=client.get_url(url_name),
        headers=signature,
        params=params,
        data=data,
        files=files,
        proxies=client.CONF.get('PROXIES'),
        verify=client.CONF['CHECK_SSL'],
        timeout=client.CONF['TIMEOUT']
    )
    response = req.text.strip()
    if req.status_code != 200:
        raise Exception('Request failed with status code %s.\n    %s.' % (req.status_code, response[:200]))
    if response:
        response = json.loads(response)
    return response


def set_command_status(client, command_uid, status='DONE', data=None):
    if not command_uid:
        return
    try:
        _make_api_request(client, 'COMMAND_STATUS', 'post', data=dict(
            uid=command_uid,
            status=status,
            data=data or '',
        ))
    except Exception as e:
        logger.error('Unable to communicate command status: %s %s', type(e), e)


def post_screenshot(client, path, file_name=None):
    with open(path, 'rb') as file_obj:
        return _make_api_request(client, 'POST_SCREENSHOT', 'post', files=dict(
            screenshot=(file_name or os.path.basename(path), file_obj)
        ))


def post_status(client, status=None, status_info=None, remaining_space=None, remaining_time=None):
    data = dict()
    if status is not None:
        if status not in ALLOWED_STATUS:
            raise ValueError('Invalid status given. Allowed statuses are: %s.' % ','.join(ALLOWED_STATUS))
        data['status'] = status
    if status_info is not None:
        data['status_info'] = status_info
    if remaining_space == 'auto':
        # Return remaining space in /home
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
    if remaining_space is not None:
        data['remaining_space'] = remaining_space
    if remaining_time is not None:
        data['remaining_time'] = remaining_time
    if not data:
        raise ValueError('No data to update.')
    return _make_api_request(client, 'POST_STATUS', 'post', data=data)
