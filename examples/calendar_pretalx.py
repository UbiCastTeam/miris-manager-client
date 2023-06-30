#!/usr/bin/env python3
import os
import requests
import json
from datetime import datetime, timedelta

url = "https://pretalx_host/event/schedule/export/schedule.json"

d = requests.get(url).json()

for day in d["schedule"]["conference"]["days"]:
    for conf in day["rooms"]["Amphitheater"]:
        start = datetime.fromisoformat(
            conf["date"]
        )  # 2022-07-06T15:15:00+02:00 --> YYYY-MM-DD HH:MM:SS
        start_date = start.strftime("%Y-%m-%d %H:%M:%S")
        duration = conf["duration"]  # 00:20
        d = datetime.strptime(duration, "%H:%M")
        end = start + timedelta(hours=d.hour, minutes=d.minute)
        end_date = end.strftime("%Y-%m-%d %H:%M:%S")

        parameters = {
            "title": conf["title"],
            "speaker": conf["persons"][0]["public_name"],
            "description": conf["abstract"],
        }

        headers = {
            "api-key": os.environ["MM_API_KEY"],
            "system": "ubi-box-54b2038312316",
        }

        data = {
            "start_date": start_date,
            "end_date": end_date,
            "time_zone": "Europe/Paris",
            "command": "record",
            "parameters": json.dumps(parameters),
        }

        print(headers, data)
        p = requests.post(
            f'https://{os.environ["MM_URL"]}/api/v3/fleet/calendars/add-event/',
            headers=headers,
            data=data,
        )
        print(p.content)
