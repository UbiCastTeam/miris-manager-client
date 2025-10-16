#!/usr/bin/env python3
"""
Script to get the URL of the web user interface of a recorder with a valid access token.
"""
import requests
import json
import argparse


def main(args):
    # GENERATE ONE TIME TOKEN
    # Data will be passed to the recorder and also prevents another user
    # from accessing the system if a recording is already in progress
    req = requests.post(
        f'{args.url}/api/v3/users/create-token/',
        headers={
            'api-key': args.api_key,
            'system': args.serial,
        },
        data={
            'purpose': 'control',
            'system': args.serial,
            'data': json.dumps({
                'speaker_name': 'Joh Does',
                'speaker_id': 'jdoe',
                'speaker_email': 'john@doe.com',
            }),
        }
    )
    response = req.json()
    token = response['token']
    #{'token': 'c8pse0v0gv312eg07m3vb29u6c78fcrlg5c1roo1', 'expires': '2022-01-14 02:56:13'}

    # GENERATE FULL URL THE USER SHOULD BE REDIRECTED TO
    querystring = requests.compat.urlencode({
        'profile': 'myprofile',
        'title': 'my title',
        'location': 'Room A',
        'live_title': 'my live title',
        'channel': 'mscspeaker',
        'logout_url': 'https://example.com',  # you should probably redirect to the custom login page
        'token': token,
    })
    ui_url = f'{args.url}/fleet/stations/{args.serial}/control/?' + querystring
    print(f'Redirect the user to this url:\n{ui_url}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument(
        '--url',
        dest='url',
        default='https://mirismanager.ubicast.eu',
        help='The Miris Manager server URL.',
        required=False,
        type=str,
    )
    parser.add_argument(
        '--api-key',
        dest='api_key',
        help='The Miris Manager API key to use.',
        required=True,
        type=str,
    )
    parser.add_argument(
        '--serial',
        dest='serial',
        default='showroom',
        help='The system serial number (for example: "ubi-box-1234").',
        required=False,
        type=str,
    )
    args = parser.parse_args()

    main(args)
