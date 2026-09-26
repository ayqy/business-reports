#!/usr/bin/env python3
"""Capture official Apple China lookup responses for scan references."""

import json
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


APPS = {"hearthstone": 841140063, "night_of_full_moon": 1278845241}
RAW = Path(__file__).with_name("raw") / "store-detail.json"
EXTRACT = Path(__file__).with_name("store-extract.json")


def fetch(app_id):
    url = f"https://itunes.apple.com/lookup?id={app_id}&country=cn"
    req = urllib.request.Request(url, headers={"User-Agent": "FF-0810 scan/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    if payload.get("resultCount") != 1:
        raise RuntimeError(f"Unexpected Apple resultCount for app id {app_id}")
    return {"url": url, "payload": payload}


def main():
    observed = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    raw = {"observed_at_beijing": observed,
           "apps": {name: fetch(app_id) for name, app_id in APPS.items()}}
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ("trackId", "trackName", "artistName", "primaryGenreName",
              "releaseDate", "currentVersionReleaseDate", "version", "price",
              "formattedPrice", "userRatingCount", "averageUserRating",
              "trackContentRating", "description", "releaseNotes", "trackViewUrl",
              "artistViewUrl", "screenshotUrls", "ipadScreenshotUrls",
              "supportedDevices", "languageCodesISO2A")
    extract = {"observed_at_beijing": observed,
               "apps": {name: {field: entry["payload"]["results"][0].get(field)
                               for field in fields} for name, entry in raw["apps"].items()}}
    EXTRACT.write_text(json.dumps(extract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, value in extract["apps"].items():
        print(name, value["trackId"], value["version"], value["userRatingCount"],
              len(value["screenshotUrls"] or []), len(value["ipadScreenshotUrls"] or []))


if __name__ == "__main__":
    main()
