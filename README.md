# campus-manager-client

A Python3 client to use UbiCast Campus Manager remote control.

This client allows you to integrate a device in Campus Manager in order to control it.

Here is the list of actions that can be sent to the client depending on its supported capabilities:

    # Basic actions, not related to any capabilities
    SHUTDOWN: capability: none, description: Shutdown system
    REBOOT: capability: none, description: Reboot system
    # Recording
    START_RECORDING: capability: recording, description: Start recording
    STOP_RECORDING: capability: recording, description: Stop recording
    LIST_PROFILES: capability: recording, description: Refresh profiles list
    # Wake on lan
    WAKE_ON_LAN: capability: wol, description: Broadcast WOL package to wake this system
    WAKE_ON_LAN_SEND: capability: wol_relay, description: Send a WOL package from this system
    # Player
    PLAY_STREAM: capability: player, description: Play stream
    # Graphical control
    GET_SCREENSHOT: capability: gcontrol, description: Get screenshot
    SIMULATE_CLICK: capability: gcontrol, description: Simulate click
    SEND_TEXT: capability: gcontrol, description: Send text to the system

Take a look at the example file to learn how to create your client.
