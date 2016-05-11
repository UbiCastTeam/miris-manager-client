# campus-manager-client

A Python3 client to use UbiCast Campus Manager remote control.

This client allows you to integrate a device in Campus Manager and to control it from Campus Manager.

Here is the list of actions that can be send to the client depending on client's supported capabilities:

    # Basic actions, not related to any capabilities
    SHUTDOWN: capability: none, description: Shutdown system
    REBOOT: capability: none, description: Reboot system
    # SSH remote maintenance
    LAUNCH_MAINTENANCE: capability: ssh_maintenance, description: Run maintenance
    LAUNCH_BG_MAINTENANCE: capability: ssh_maintenance, description: Run background maintenance
    STOP_BG_MAINTENANCE: capability: ssh_maintenance, description: Stop background maintenance
    # Wake on lan
    WAKE_ON_LAN: capability: wol, description: Broadcast WOL package to wake this system
    WAKE_ON_LAN_SEND: capability: wol_relay, description: Send a WOL package from this system
    # Player
    PLAY_STREAM: capability: player, description: Play stream
    # Graphical control
    GET_SCREENSHOT: capability: gcontrol, description: Get screenshot
    SIMULATE_CLICK: capability: gcontrol, description: Simulate click
    SEND_TEXT: capability: gcontrol, description: Send text to the system
    # EasyCast
    START_PUBLISHING: capability: easycast, description: Start publishing videos
    STOP_PUBLISHING: capability: easycast, description: Stop publishing videos
    RESTART_EASYCAST: capability: easycast, description: Restart EasyCast software
    KILL_EASYCAST: capability: easycast, description: Kill EasyCast process
    UPGRADE: capability: easycast, description: Upgrade
    GET_LOGS: capability: easycast, description: Get system logs
    GET_SYSTEM_STATS: capability: easycast, description: Get system stats
    # Recording
    START_RECORDING: capability: recording, description: Start recording
    STOP_RECORDING: capability: recording, description: Stop recording
    LIST_PROFILES: capability: recording, description: Refresh profiles list

Take a look at the example file to learn how to create your client.
