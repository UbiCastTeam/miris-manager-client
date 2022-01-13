#!/usr/bin/env python3
import requests
import json
import os

MM_URL = os.environ['MIRISMANAGER_URL']
SYSTEM = 'ubi-box-1234'

headers = {
    'api-key': os.environ['MIRISMANAGER_API_KEY'],
    'system': SYSTEM,
}

user_info = {
    'speaker_name': 'Joh Does',
    'speaker_id': 'jdoe',
    'speaker_email': 'john@doe.com',
}

# GENERATE ONE TIME TOKEN
url = MM_URL + '/api/v3/users/create-token/'
data = {
    'purpose': 'control',
    'system': SYSTEM,
    'data': json.dumps(user_info),  # will be passed to the recorder and also prevents another user from accessing the system if a recording is already in progress
}
r = requests.post(url, headers=headers, data=data).json()
token = r['token']
#{'token': 'c8pse0v0gv312eg07m3vb29u6c78fcrlg5c1roo1', 'expires': '2022-01-14 02:56:13'}

# GENERATE FULL URL THE USER SHOULD BE 302ed to
params = {
    'profile': 'myprofile',
    'title': 'my title',
    'location': 'Room A',
    'live_title': 'my live title',
    'channel': 'mscspeaker',
    'logout_url': 'http://www.ubicast.eu',  # you should probably redirect to the custom login page
    'token': token,
}

querystring = requests.compat.urlencode(params)

UI_URL = MM_URL + f'/fleet/stations/{SYSTEM}/control/?' + querystring

print(f'Redirect the user to this url:\n{UI_URL}')
