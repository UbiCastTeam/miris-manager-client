#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Campus Manager client default configuration
This file should not be modified directly, put your modification in your local file.
'''

# Logging level
LOG_LEVEL = 'INFO'

# URL of Campus Manager server
URL = 'https://campusmanager'

# API key of this system in Campus Manager
# The API key is automatically set when empty and when Capus Manager discovery mode is enabled.
API_KEY = ''

# Secret key of this system in Campus Manager, used to sign messages
SECRET_KEY = ''

# Notify systemd watchdog after each long polling call
WATCHDOG = False

# Check server SSL certificate
CHECK_SSL = False

# API requests max duration in seconds
TIMEOUT = 10

# Proxies for API requests
# Example: {'http': 'http://10.10.1.10:3128', 'https': 'http://10.10.1.10:1080'}
PROXIES = None

# This list makes available or not actions buttons in Campus Manager
CAPABILITIES = {}

# List of Campus Manager urls (do not overwritte this)
API_CALLS = {
    'PING': {'method': 'get', 'url': '/api/', 'anonymous': True},
    'TIME': {'method': 'get', 'url': '/api/time/', 'anonymous': True},
    'INFO': {'method': 'get', 'url': '/api/info/', 'anonymous': True},
    'LONG_POLLING': {'method': 'get', 'url': '/remote-event/v3'},
    'SET_COMMAND_STATUS': {'method': 'post', 'url': '/api/v3/fleet/control/set-command-status/'},
    'GET_INFO': {'method': 'get', 'url': '/api/v3/fleet/systems/get-info/'},
    'SET_INFO': {'method': 'post', 'url': '/api/v3/fleet/systems/set-info/'},
    'SET_STATUS': {'method': 'post', 'url': '/api/v3/fleet/systems/set-status/'},
    'SET_SCREENSHOT': {'method': 'post', 'url': '/api/v3/fleet/systems/set-screenshot/'},
    'REGISTER_SYSTEM': {'method': 'post', 'url': '/api/v3/fleet/systems/register/'},
}
