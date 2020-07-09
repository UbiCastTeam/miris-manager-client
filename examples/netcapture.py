#!/usr/bin/env python3
import requests
import os
import time
import sys

URL = 'https://mirismanager.ubicast.eu'
headers = {'api-key': os.environ.get('MEDIACODER_MIRISMANAGER_API_KEY')}
PROFILE = 'showroom'


def get_status(session):
    status_dict = s.get(URL + '/api/v3/fleet/systems/get-status/', headers=headers, params={'profile': PROFILE}).json()
    '''
    status dict: {'last_status_update': '20200227112959', 'last_status_update_display': '2020-02-27 11:29:59', 'last_connection': '2020-02-27 11:29:57', 'profile': 'ndi', 'status': 'RUNNING', 'status_info': {'status_message': 'Recording in progress', 'audio': {'master': {'volume': 1.0, 'muted': False}}, 'video': [{'type': 'ndivsource', 'name': 'source-f41f', 'device': 'v4l-HDMI-1-pci-0000:01:00.0', 'capture': '1280x720@25', 'signal': 'fake'}], 'playlist': '/hls/944d/adaptive.m3u8', 'time_in_sec': 2, 'timecode': '0:00:02', 'record_folder': '/home/ubicast/mediacoder/media/20200227-112957-09bd'}, 'status_display': 'Recording in progress (profile: ndi)', 'remaining_space': 911891, 'remaining_time': 0, 'online': True, 'auto_refresh': False, 'screenshot_name': 'screenshots/ubi-box-e0d55ec52008_2020-02-27_10-30-00.jpg', 'screenshot_date': '2020-02-27 11:30:00', 'screenshot_outdated': False, 'messages_info': 20, 'messages_warning': 2, 'messages_error': 17, 'last_error_message': None, 'last_error_date': None}

    status_dict["status"] can contain:
    "READY": idle
    "RUNNING": system is recording
    "UNAVAILABLE": system not found or profile does not exist
    "INITIALIZING": loading
    '''
    return status_dict.get('status')


with requests.Session() as s:
    params = {
        'profile': PROFILE,
        'async': 'no',
        'action': 'START_RECORDING',
        'speaker_email': 'user@domain.com',
    }
    # list of mediaserver supported parameters here: https://sandbox.ubicast.tv/static/mediaserver/docs/api/api.html#api-v2-medias-add

    print('Start recording')
    response = s.post(URL + '/api/v3/fleet/control/run-command/', headers=headers, data=params).json()
    #{'uid': '89b15583-7528-4c0c-a18e-28155be08d21', 'status': 'DONE', 'message': 'Recording started'}

    if response.get('error'):
        # {'error': 'No system is available to record.'}
        print(response['error'])
        sys.exit(1)
    else:
        print(response.get('message'))
        # can be UNAVAILABLE, READY, INITIALIZING, RUNNING
        # https://mirismanager.ubicast.eu/static/docs/api/values.html
        while not get_status(s) == 'RUNNING':
            time.sleep(1)
            if get_status(s) == 'UNAVAILABLE':
                print('Profile does not exist or no system is online')
                sys.exit(1)
        print('System is recording, stopping now')

        print('Stop recording')
        params['action'] = 'STOP_RECORDING'
        s.post(URL + '/api/v3/fleet/control/run-command/', headers=headers, data=params)
