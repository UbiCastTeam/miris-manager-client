# UbiCast Miris Manager client

A Python3 client to use UbiCast Miris Manager remote control API.

This client is intended to act as a system in Miris Manager so it allows you to integrate a device in order to control it using Miris Manager.

Here is the list of actions that can be sent to the client depending on its supported capabilities:

    # Basic actions
    SHUTDOWN: capability: shutdown, description: Shutdown system
    REBOOT: capability: reboot, description: Reboot system
    UPGRADE: capability: upgrade, description: Upgrade system software
    # Recording
    START_RECORDING: capability: record, description: Start recording
    STOP_RECORDING: capability: record, description: Stop recording
    LIST_PROFILES: capability: record, description: Refresh profiles list
    # Publishing
    START_PUBLISHING: capability: publish, description: Start publishing non published media
    STOP_PUBLISHING: capability: publish, description: Stop publishing
    # Wake on lan
    WAKE_ON_LAN_SEND: capability: send_wake_on_lan, description: Send a wake on LAN network package from this system to wake another system

Take a look at the example files to learn how to create your client.
