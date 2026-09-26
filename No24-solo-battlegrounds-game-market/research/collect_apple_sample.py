#!/usr/bin/env python3
"""Snapshot Apple China search results; ratings are never treated as sales."""

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


TERMS = ("卡牌自走棋", "酒馆战棋", "背包乱斗", "自走棋 单机")
OUT = Path(__file__).with_name("apple-cn-search-snapshot.json")


def query(term):
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": term, "country": "cn", "entity": "software", "limit": 200}
    )
    request = urllib.request.Request(url, headers={"User-Agent": "FF-0810 research/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    fields = (
        "trackId", "trackName", "artistName", "primaryGenreName", "genres",
        "userRatingCount", "averageUserRating", "price", "currency",
        "releaseDate", "currentVersionReleaseDate", "version", "trackViewUrl",
    )
    return {"url": url, "resultCount": payload["resultCount"],
            "results": [{key: result.get(key) for key in fields} for result in payload["results"]]}


def main():
    payload = {"collected_at_utc": datetime.now(timezone.utc).isoformat(),
               "method": "Apple iTunes Search API, China storefront, software, first 200 per query",
               "queries": {term: query(term) for term in TERMS}}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for term, result in payload["queries"].items():
        games = [row for row in result["results"] if row["primaryGenreName"] == "Games"]
        counts = sorted((row["userRatingCount"] or 0) for row in games)
        print(term, "returned", result["resultCount"], "games", len(games),
              "<=100 ratings", sum(value <= 100 for value in counts),
              "median ratings", counts[len(counts) // 2] if counts else None)


if __name__ == "__main__":
    main()
