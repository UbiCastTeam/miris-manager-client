#!/usr/bin/env python3
"""
Script to import a pretalx schedule in the calendar of a Miris Manager system.
"""
import argparse
import json
from datetime import datetime, timedelta

import requests


def import_pretalx_events(args):
    d = requests.get(args.pretalx_url).json()

    for day in d['schedule']['conference']['days']:
        for conf in day['rooms']['Amphitheater']:
            start = datetime.fromisoformat(
                conf['date']
            )  # 2022-07-06T15:15:00+02:00 --> YYYY-MM-DD HH:MM:SS
            start_date = start.strftime('%Y-%m-%d %H:%M:%S')
            duration = conf['duration']  # 00:20
            d = datetime.strptime(duration, '%H:%M')
            end = start + timedelta(hours=d.hour, minutes=d.minute)
            end_date = end.strftime('%Y-%m-%d %H:%M:%S')

            parameters = {
                'title': conf['title'],
                'speaker': conf['persons'][0]['public_name'],
                'description': conf['abstract'],
            }

            headers = {
                'api-key': args.api_key,
                'system': args.serial,
            }

            data = {
                'start_date': start_date,
                'end_date': end_date,
                'time_zone': 'Europe/Paris',
                'command': 'record',
                'parameters': json.dumps(parameters),
            }

            print(headers, data)
            p = requests.post(
                f'{args.url}/api/v3/fleet/calendars/add-event/',
                headers=headers,
                data=data,
            )
            print(p.content)


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
    parser.add_argument(
        '--pretalx-url',
        dest='pretalx_url',
        default='https://pretalx_host/event/schedule/export/schedule.json',
        help='The URL of the pretalx schedule.',
        required=False,
        type=str,
    )
    args = parser.parse_args()

    import_pretalx_events(args)
