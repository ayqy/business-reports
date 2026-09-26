#!/usr/bin/env python3
"""Capture a small, dated Apple China review sample for demand hypotheses."""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


IDS = {"月圆之夜": 1278845241, "炉石传说": 841140063}
OUT = Path(__file__).with_name("apple-cn-recent-reviews.json")


def get_reviews(app_id):
    url = f"https://itunes.apple.com/cn/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.load(response)
    entries = data["feed"].get("entry", [])
    reviews = []
    for entry in entries:
        if "im:rating" not in entry:
            continue
        reviews.append({"date": entry["updated"]["label"],
                        "rating": int(entry["im:rating"]["label"]),
                        "title": entry["title"]["label"],
                        "text": entry["content"]["label"]})
    return {"url": url, "returned": len(reviews), "reviews": reviews}


def main():
    result = {"collected_at_utc": datetime.now(timezone.utc).isoformat(),
              "method": "Apple China RSS, mostRecent, first page; not a random sample",
              "apps": {name: get_reviews(app_id) for name, app_id in IDS.items()}}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, item in result["apps"].items():
        print(name, "reviews", item["returned"],
              "single_player_keyword", sum("单机" in row["text"] for row in item["reviews"]))


if __name__ == "__main__":
    main()
