'''
Miris Manager client library
This module is not intended to be used directly, only the client class should be used.
'''
import json
import logging
import re
from pathlib import Path

from ..conf import BASE_CONF

logger = logging.getLogger('mm_client.lib.configuration')


def load_conf(default_conf=None, local_conf=None):
    # copy default configuration
    conf = BASE_CONF.copy()
    # update with default and local configuration
    for index, conf_override in enumerate((default_conf, local_conf)):
        if not conf_override:
            continue
        if isinstance(conf_override, str):
            conf_override = Path(conf_override)
        if isinstance(conf_override, dict):
            for key, val in conf_override.items():
                if not key.startswith('_'):
                    conf[key] = val
        elif isinstance(conf_override, Path):
            if conf_override.exists():
                content = conf_override.read_text()
                content = re.sub(r'\n\s*//.*', '\n', content)  # remove comments
                conf_mod = json.loads(content) if content else None
                if not conf_mod:
                    logger.debug('Config file "%s" is empty.', conf_override)
                else:
                    logger.debug('Config file "%s" loaded.', conf_override)
                    if not isinstance(conf_mod, dict):
                        raise ValueError(f'The configuration in "{conf_override}" is not a dict.')
                    conf.update(conf_mod)
            else:
                logger.debug('Config file does not exists, using default config.')
        else:
            raise ValueError('Unsupported type for configuration.')
    if conf['SERVER_URL'].endswith('/'):
        conf['SERVER_URL'] = conf['SERVER_URL'].rstrip('/')
    return conf


def update_conf(local_conf, key, value):
    if not local_conf:
        logger.debug('Cannot update configuration, "local_conf" is not set.')
        return False
    if isinstance(local_conf, str):
        local_conf = Path(local_conf)
    elif not isinstance(local_conf, Path):
        logger.debug('Cannot update configuration, "local_conf" is not a path.')
        return False

    if local_conf.is_file():
        content = local_conf.read_text().strip()
    else:
        content = ''
    data = json.loads(content) if content else {}
    data[key] = value
    new_content = json.dumps(data, sort_keys=True, indent=4)
    local_conf.write_text(new_content)
    logger.debug('Configuration file "%s" updated: "%s" set to "%s".', local_conf, key, value)
    return True


def check_conf(conf):
    # check that mandatory configuration values are set
    if not conf.get('SERVER_URL') or conf['SERVER_URL'] == 'https://mirismanager':
        raise ValueError('The value of "SERVER_URL" is not set. Please configure it.')
    conf['SERVER_URL'] = conf['SERVER_URL'].strip('/')
