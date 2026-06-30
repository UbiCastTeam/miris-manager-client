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
                'enabled': 'yes' if args.enable_event else 'no',
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
    early_parser = argparse.ArgumentParser(add_help=False)
    # Keep this NOT required here even though we want it required overall: a
    # "required=True" makes "parse_known_args" below run argparse's required
    # check and exit before "-h/--help" can reach the final parser, so a bare
    # "--help" would never work. We flip it to required on the final parser
    # below (after the pre-parse), where "-h/--help" fires first and still works.
    pretalx_url_action = early_parser.add_argument(
        '--pretalx-url',
        help='The URL of the pretalx schedule. (Ex: https://pretalx_host/event/schedule/export/schedule.json)',
        type=str,
    )
    early_parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Ignore the on-disk schedule cache and download a fresh copy.',
    )

    # Fetch the schedule first so the room name can be validated against the
    # rooms actually present in it (offered as argparse choices). Skip the fetch
    # when no URL was given (e.g. a bare "--help") and tolerate a failed fetch,
    # so the final parser still prints a valid help, just without room choices.
    pre_args, _ = early_parser.parse_known_args()
    schedule = None
    rooms = []
    if pre_args.pretalx_url:
        try:
            schedule = get_schedule(pre_args.pretalx_url, use_cache=not pre_args.no_cache)
            rooms = get_rooms(schedule)
        except requests.RequestException:
            pass

    # Build the final parser from the early parser; "add_help" defaults to True
    # here, so help is available and now lists the rooms below.
    parser = argparse.ArgumentParser(
        description=__doc__ and __doc__.strip(),
        parents=[early_parser],
    )
    # Now require the URL: this shared Action is enforced by the final parser's
    # "parse_args", which handles "-h/--help" first, so help still works while a
    # real run without "--pretalx-url" errors as required.
    pretalx_url_action.required = True
    parser.add_argument(
        '-e', '--enable-event', action='store_true', help='enable the event'
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
        choices=rooms or None,
        help='room name (one of the rooms found in the pretalx schedule)',
    )
    args = parser.parse_args()
    if schedule is None:
        parser.error(f'could not fetch the pretalx schedule from {pre_args.pretalx_url!r}; check --pretalx-url')
    if args.room_name is None:
        parser.error(f'the following argument is required: -r/--room-name; choose one of: {", ".join(rooms)}')

    import_pretalx_events(args, schedule)
