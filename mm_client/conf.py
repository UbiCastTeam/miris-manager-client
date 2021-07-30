# Miris Manager client base configuration
# This file should not be modified directly, put your modification in another json file and give the path to the client.

BASE_CONF = {
    # Logging level
    'LOG_LEVEL': 'INFO',

    # Server URL of Miris Manager
    'SERVER_URL': 'https://mirismanager',

    # API key of this system in Miris Manager
    # The API key is automatically set when empty and when Capus Manager discovery mode is enabled.
    'API_KEY': '',

    # Secret key of this system in Miris Manager, used to sign messages
    'SECRET_KEY': '',

    # Try to register this system if no API_KEY is defined
    'AUTO_REGISTRATION': True,

    # Notify systemd watchdog after each long polling call
    'WATCHDOG': False,

    # Verify server SSL certificate
    'VERIFY_SSL': False,

    # API requests max duration in seconds
    'TIMEOUT': 10,

    # Proxies for API requests
    # To use system proxies: None (proxies should be set in environment)
    # To disable proxies: {'http': '', 'https': ''}
    # To use a proxy: {'http': 'http://10.10.1.10:3128', 'https': 'http://10.10.1.10:1080'}
    'PROXIES': None,

    # This list makes available or not actions buttons in Miris Manager
    'CAPABILITIES': {},

    # List of Miris Manager urls (do not overwritte this)
    'API_CALLS': {
        'PING': {'method': 'get', 'url': '/api/', 'anonymous': True},
        'TIME': {'method': 'get', 'url': '/api/time/', 'anonymous': True},
        'INFO': {'method': 'get', 'url': '/api/info/', 'anonymous': True},
        'LONG_POLLING': {'method': 'get', 'url': '/remote-event/v3'},
        'SET_COMMAND_STATUS': {'method': 'post', 'url': '/api/v3/fleet/control/set-command-status/'},
        'GET_INFO': {'method': 'get', 'url': '/api/v3/fleet/systems/get-info/'},
        'SET_INFO': {'method': 'post', 'url': '/api/v3/fleet/systems/set-info/'},
        'GET_STATUS': {'method': 'get', 'url': '/api/v3/fleet/systems/get-status/'},
        'SET_STATUS': {'method': 'post', 'url': '/api/v3/fleet/systems/set-status/'},
        'SET_SCREENSHOT': {'method': 'post', 'url': '/api/v3/fleet/systems/set-screenshot/'},
        'REGISTER_SYSTEM': {'method': 'post', 'url': '/api/v3/fleet/systems/register/'},
        'GET_MESSAGE': {'method': 'get', 'url': '/api/v3/fleet/messages/get/'},
        'ADD_MESSAGE': {'method': 'post', 'url': '/api/v3/fleet/messages/add/'},
        'ARCHIVE_MESSAGE': {'method': 'post', 'url': '/api/v3/fleet/messages/archive/'},
        'DELETE_MESSAGE': {'method': 'post', 'url': '/api/v3/fleet/messages/delete/'},
        'PREPARE_TUNNEL': {'method': 'post', 'url': '/api/v3/fleet/proxy/prepare-tunnel/'},
        'SET_PROFILES': {'method': 'post', 'url': '/api/v3/fleet/profiles/set/'},
        'CHECK_TOKEN': {'method': 'post', 'url': '/api/v3/users/check-token/'},
        'GET_RELEASE': {'method': 'get', 'url': '/api/v3/packaging/check-for-update/'}
    }
}
