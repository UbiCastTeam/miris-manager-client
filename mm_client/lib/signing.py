'''
Miris Manager client signing functions
This module is not intended to be used directly, only the client class should be used.
'''
import base64
import datetime
import hashlib
import hmac
import logging

logger = logging.getLogger('mm_client.lib.signing')


def get_signature(conf):
    if not conf.get('SECRET_KEY') or not conf.get('API_KEY'):
        return {}
    utime = datetime.datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S_%f')
    to_sign = 'time=%s|api_key=%s' % (utime, conf['API_KEY'])
    hm = hmac.new(
        conf['SECRET_KEY'].encode('utf-8'),
        msg=to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    hm = base64.b64encode(hm).decode('utf-8')
    return {'time': utime, 'hmac': hm}


def check_signature(conf, rdata):
    if not conf.get('SECRET_KEY') or not conf.get('API_KEY'):
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
    to_sign = 'time=%s|api_key=%s' % (remote_time, conf['API_KEY'])
    hm = hmac.new(
        conf['SECRET_KEY'].encode('utf-8'),
        msg=to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    if rhmac != hm:
        return 'the received and computed HMAC values do not match.'
    return None
