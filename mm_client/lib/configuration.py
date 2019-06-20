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
from ..conf import BASE_CONF

logger = logging.getLogger('mm_client.lib.configuration')


def load_conf(default_conf=None, local_conf=None):
    # copy default configuration
    conf = BASE_CONF.copy()
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
    if conf['SERVER_URL'].endswith('/'):
        conf['SERVER_URL'] = conf['SERVER_URL'].rstrip('/')
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


def check_conf(conf):
    # check that mandatory configuration values are set
    if not conf.get('SERVER_URL') or conf['SERVER_URL'] == 'https://mirismanager':
        raise ValueError('The value of "SERVER_URL" is not set. Please configure it.')
    conf['SERVER_URL'] = conf['SERVER_URL'].strip('/')
