#!/usr/bin/env python3
"""
This scripts aims to convert an indico calendar to MirisManager calendar entries.

For this you have to download the JSON indico file, for instance if a calendar
is available at this address:
https://indico.freedesktop.org/event/5/timetable/?layout=room#all

You can get it at this address: https://indico.freedesktop.org/export/timetable/5.json

``curl https://indico.freedesktop.org/export/timetable/5.json -o calendar.json``

Once you have a calendar.json file you can view the events with:

``indico2mm.py calendar.json`` and before adding event to MM you'd better
choose a room and relaunch the script with it:

``indico2mm.py -r "Room 1" -m https://skyreach.ubicast.net -k API_KEY -s "mbm-dev" calendar.json``

Note: the script will also generate an `self-remove` script to delete added event at once.
"""

import argparse
import collections
import datetime
import json
import sys
import zoneinfo

import requests


def main(args):
    with open(args.jsonfile) as fh:
        data = json.load(fh)

    assert len(data["results"]) == 1
    # get the first and only dict value
    root = next(iter(data["results"].values()))

    mm_events = list()
    for date, sessions in root.items():
        for session in sessions.values():
            if session["entryType"] == "Session" and len(entries := session["entries"]):
                for entry in entries.values():
                    if entry["entryType"] == "Contribution":
                        room = entry.get("room") or session.get("title", "unknown")
                        if args.room != "all" and room != args.room:
                            continue

                        start = datetime.datetime.combine(
                            datetime.date.fromisoformat(entry["startDate"]["date"]),
                            datetime.time.fromisoformat(entry["startDate"]["time"]),
                            tzinfo=zoneinfo.ZoneInfo(entry["startDate"]["tz"]),
                        )
                        end = datetime.datetime.combine(
                            datetime.date.fromisoformat(entry["endDate"]["date"]),
                            datetime.time.fromisoformat(entry["endDate"]["time"]),
                            tzinfo=zoneinfo.ZoneInfo(entry["endDate"]["tz"]),
                        )
                        mm_events.append(
                            collections.OrderedDict(
                                (
                                    ("title", entry["title"]),
                                    (
                                        "speakers",
                                        ", ".join(
                                            [p["name"] for p in entry["presenters"]]
                                        ),
                                    ),
                                    ("start", start),
                                    ("end", end),
                                    ("room", room),
                                    ("description", entry["description"]),
                                )
                            )
                        )

    if not args.mm_url:
        for i, e in enumerate(sorted(mm_events, key=lambda x: x["start"])):
            print(
                f"{i}\ttitle: {e['title']}\n"
                f"\tspeakers: {e['speakers']}\n"
                f"\troom: {e['room']}\n"
                f"\ttime: {e['start']} -> {e['end']}\n"
            )

    # send it to MirisManager
    if args.mm_url and args.mm_api_key and args.system:
        created_uids = list()
        for event in mm_events:
            parameters = {
                "title": event["title"],
                "speaker": event["speakers"],
                "description": event["description"],
            }

            headers = {
                "api-key": args.mm_api_key,
                "system": args.system,
            }

            data = {
                "start_date": event["start"]
                .replace(tzinfo=None)
                .isoformat(sep=" ", timespec="seconds"),
                "end_date": event["end"]
                .replace(tzinfo=None)
                .isoformat(sep=" ", timespec="seconds"),
                "time_zone": event["start"].tzinfo.key,
                "command": "record",
                "parameters": json.dumps(parameters),
                "enabled": "yes" if args.enable_event else "no",
            }

            if not args.dry_run:
                print(f">> calling add-event with {headers} and {data}")
                p = requests.post(
                    f"{args.mm_url}/api/v3/fleet/calendars/add-event/",
                    headers=headers,
                    data=data,
                )
                p.raise_for_status()
                uid = p.json()["uid"]
                print(f"added uid {uid} for {p.content}")
                created_uids.append(uid)
                uid_filename = f"delete_events_{datetime.datetime.now().isoformat(timespec='seconds')}.sh"
            else:
                print(f"dry run: calling add-event with {headers} and {data}")

        if created_uids:
            cmd = f'curl -w "\\n" -H "api-key:{args.mm_api_key}" -H "system:{args.system}" -d "uid={{uid}}" https://skyreach.ubicast.net/api/v3/fleet/calendars/delete-event/'
            with open(uid_filename, "w") as fh:
                fh.write("set -e\n\n")
                fh.write(
                    "read -p 'Are you sure you want to clear these events ? [yN]: ' yn\n"
                )
                fh.write("[ x${yn}x != xyx ] && exit;\n\n")
                for uid in created_uids:
                    fh.write(cmd.format(uid=uid) + "\n")

                # delete the script
                fh.write('rm "$0"\n')

                print("*" * 50)
                print(f"delete script available with: `bash {uid_filename}`")


class RawDefaultFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=RawDefaultFormatter
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="dry run")
    parser.add_argument(
        "-m", "--mm-url", type=str, action="store", help="miris manager URL"
    )
    parser.add_argument(
        "-k", "--mm-api-key", type=str, action="store", help="miris manager API key"
    )
    parser.add_argument(
        "-s",
        "--system",
        type=str,
        action="store",
        help="system (=box) on which calendar will be set",
    )
    parser.add_argument(
        "-r",
        "--room",
        type=str,
        action="store",
        help="room name filtering",
        default="all",
    )
    parser.add_argument(
        "-e", "--enable-event", action="store_true", help="enable the event"
    )
    parser.add_argument("jsonfile", help="json file")
    args = parser.parse_args()

    if args.mm_url:
        failure = False
        if not args.mm_api_key:
            print("Missing api key")
            failure = True
        if not args.system:
            print("Missing system")
            failure = True

        if failure:
            parser.print_usage()
            sys.exit(1)

    main(args)
