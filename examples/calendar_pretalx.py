#!/usr/bin/env python3
"""
Script to import a pretalx schedule in the calendar of a Miris Manager system.
"""

import argparse
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import pprint
import tempfile

import requests


def get_cache_path(pretalx_url):
    digest = hashlib.sha256(pretalx_url.encode()).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f'pretalx-schedule-{digest}.json'


def get_schedule(pretalx_url, use_cache=True):
    cache_path = get_cache_path(pretalx_url)
    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text())
    schedule = requests.get(pretalx_url).json()
    cache_path.write_text(json.dumps(schedule))
    return schedule


def get_rooms(schedule):
    rooms = set()
    for day in schedule['schedule']['conference']['days']:
        rooms.update(day['rooms'].keys())
    return sorted(rooms)


def import_pretalx_events(args, schedule):
    for day in schedule['schedule']['conference']['days']:
        for conf in day['rooms'].get(args.room_name, []):
            start = datetime.fromisoformat(conf['date'])  # 2022-07-06T15:15:00+02:00 --> YYYY-MM-DD HH:MM:SS
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

            print(f'about to post: {pprint.pformat(data)}')
            if not args.dry_run:
                p = requests.post(
                    f'{args.url}/api/v3/fleet/calendars/add-event/',
                    headers=headers,
                    data=data,
                )
                print(p.content)


if __name__ == '__main__':
    # Minimal parser holding only what the pre-parsing needs to fetch the
    # schedule; "add_help=False" so it does not print usage before the
    # "--room-name" argument (and its room choices) is added. It is reused as a
    # parent of the final parser, which lists the rooms in usage.
    early_parser = argparse.ArgumentParser(add_help=False)
    early_parser.add_argument(
        '--pretalx-url',
        default='https://pretalx_host/event/schedule/export/schedule.json',
        help='The URL of the pretalx schedule.',
        required=False,
        type=str,
    )
    early_parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Ignore the on-disk schedule cache and download a fresh copy.',
    )

    # Fetch the schedule first so the room name can be validated against the
    # rooms actually present in it (offered as argparse choices).
    pre_args, _ = early_parser.parse_known_args()
    schedule = get_schedule(pre_args.pretalx_url, use_cache=not pre_args.no_cache)
    rooms = get_rooms(schedule)

    # Build the final parser from the early parser; "add_help" defaults to True
    # here, so help is available and now lists the rooms below.
    parser = argparse.ArgumentParser(
        description=__doc__ and __doc__.strip(),
        parents=[early_parser],
    )
    parser.add_argument(
        '--url',
        default='https://mirismanager.ubicast.eu',
        help='The Miris Manager server URL.',
        required=False,
        type=str,
    )
    parser.add_argument(
        '--api-key',
        help='The Miris Manager API key to use.',
        required=True,
        type=str,
    )
    parser.add_argument(
        '--serial',
        default='showroom',
        help='The system serial number (for example: "ubi-box-1234").',
        required=False,
        type=str,
    )
    parser.add_argument(
        '-n',
        '--dry-run',
        action='store_true',
        help='dry run (simulation)',
    )
    # Not "required=True": argparse's missing-argument error is generic and
    # would not list the rooms. Validate below so the error lists the choices.
    parser.add_argument(
        '-r',
        '--room-name',
        choices=rooms,
        help='room name (one of the rooms found in the pretalx schedule)',
    )
    args = parser.parse_args()
    if args.room_name is None:
        parser.error(f'the following argument is required: -r/--room-name; choose one of: {", ".join(rooms)}')

    import_pretalx_events(args, schedule)
