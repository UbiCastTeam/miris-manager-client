![PyPI - Python Version](https://img.shields.io/pypi/pyversions/miris-manager-client.svg)
![PyPI](https://img.shields.io/pypi/v/miris-manager-client.svg)

# UbiCast Miris Manager client

A Python3 client to use UbiCast Miris Manager remote control API.

This client is intended to act as a system in Miris Manager so it allows you to integrate a device in order to control it using Miris Manager.


## Requirements

* python >= 3.11 (download the latest stable release from https://www.python.org/downloads/)
* python3-requests >= 2.30


## Important

For production use, it is recommended to use the branch named "stable". The "main" branch is used for development.


## Client class instantiation

The client class (`mm_client`.`client`.`MirisManagerClient`) takes two arguments:
* `local_conf`: This argument can be either a dict or a path (`str` object). The default value is `None`, which means no configuration.
* `setup_logging`: This argument must be a boolean. If set to `True`, the logging to console will be configured. The default value is `True`.


## Configuration

You can see available parameters in the default configuration file :
[Default configuration](/mm_client/conf.py)

The local configuration should be a json file.


## Notes about older client

If you are using the first version of this client (commit `33b554991303b573254d59fb757f601d1e84d132` and previous commits), here are the steps to update your client:

* Install the new client using the setup.py.
* Replace the import path of `MirisManagerClient` (see example).
* Replace the class variable `MirisManagerClient`.`LOCAL_CONF` with the class instance argument `MirisManagerClient`.`local_conf`.
* Check the value of `MirisManagerClient`.`DEFAULT_CONF` because it is now `None` by default.
* Replace all occurences of `URL` by `SERVER_URL` in all configuration.
* Replace all occurences of `CHECK_SSL` by `VERIFY_SSL` in all configuration.


## Examples

### Ping the server

``` python
from mm_client.client import MirisManagerClient
mmc = MirisManagerClient(local_conf='your-conf.json')

response = mmc.api_request('PING')
print(response)
```


### Recorder system

This example is the use case of a recorder system that can be controlled through the long polling.

[Link to the file](/examples/recorder_controller.py)


### Wake on LAN requests

This example is the use case of a client that forwards wake on LAN requests received through the long polling to its network.

[Link to the file](/examples/wol_relay.py)


### Other examples

There are more examples in the [examples](/examples) directory.


## Actions

Here is the list of actions that can be sent to the client depending on its supported capabilities:

**Basic actions**

* `SHUTDOWN`: capability: shutdown, description: Shutdown system
* `REBOOT`: capability: reboot, description: Reboot system
* `UPGRADE`: capability: upgrade, description: Upgrade system software

**Recording**

* `START_RECORDING`: capability: record, description: Start recording
* `STOP_RECORDING`: capability: record, description: Stop recording
* `LIST_PROFILES`: capability: record, description: Refresh profiles list

**Publishing**

* `START_PUBLISHING`: capability: publish, description: Start publishing non published media
* `STOP_PUBLISHING`: capability: publish, description: Stop publishing

**Wake on lan**

* `WAKE_ON_LAN_SEND`: capability: send_wake_on_lan, description: Send a wake on LAN network package from this system to wake another system
