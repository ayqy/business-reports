#!/usr/bin/env python3
"""Freeze official App Store search and lookup evidence for iOS comparators.

The script queries Apple's public Search/Lookup API only.  It records store
metadata and seller-authored descriptions; it does not treat those descriptions
as independent proof of blocking effectiveness, installs, revenue, or profit.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESEARCH_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = RESEARCH_DIR / "data"
USER_AGENT = "FF-0177-ios-competitor-research/1.0 (+official-app-store-only)"
SEARCH_ENDPOINT = "https://itunes.apple.com/search"
LOOKUP_ENDPOINT = "https://itunes.apple.com/lookup"
API_DOCUMENTATION = (
    "https://developer.apple.com/library/archive/documentation/AudioVideo/"
    "Conceptual/iTuneSearchAPI/index.html"
)

SEARCH_QUERIES = [
    {"country": "cn", "term": "自动跳过广告"},
    {"country": "cn", "term": "开屏广告"},
    {"country": "cn", "term": "李跳跳"},
    {"country": "cn", "term": "防误触跳转"},
    {"country": "us", "term": "skip ads"},
    {"country": "us", "term": "ad skipper"},
    {"country": "us", "term": "system wide ad blocker"},
    {"country": "us", "term": "ad blocker"},
]

TARGETS = [
    {
        "country": "cn",
        "bundle_id": "com.twostones.adblocker",
        "segment": "deep_link_launch_bypass",
        "relevance": "closest_splash_and_shake_launch_path_substitute",
    },
    {
        "country": "cn",
        "bundle_id": "com.app.nojump",
        "segment": "shortcuts_post_jump_return",
        "relevance": "closest_configured_mistouch_recovery_substitute",
    },
    {
        "country": "cn",
        "bundle_id": "com.appstudio.Jinx",
        "segment": "dns_vpn_https_filter",
        "relevance": "china_system_wide_network_filter_claim",
    },
    {
        "country": "us",
        "bundle_id": "com.adguard.AdguardExtension",
        "segment": "safari_and_dns_filter",
        "relevance": "mature_safari_and_system_dns_comparator",
    },
    {
        "country": "us",
        "bundle_id": "com.adguard.AdguardPro",
        "segment": "safari_and_dns_filter_paid_sku",
        "relevance": "upfront_price_anchor_for_adguard_family",
    },
    {
        "country": "us",
        "bundle_id": "com.khanov.BlockerX",
        "segment": "safari_content_blocker",
        "relevance": "mature_safari_comparator",
    },
    {
        "country": "us",
        "bundle_id": "com.confirmed.lockdown",
        "segment": "local_firewall_and_vpn",
        "relevance": "all_app_domain_firewall_comparator",
    },
    {
        "country": "us",
        "bundle_id": "net.blocka.app",
        "segment": "dns_filter_and_vpn",
        "relevance": "all_app_dns_comparator",
    },
    {
        "country": "us",
        "bundle_id": "io.nextdns.NextDNS",
        "segment": "encrypted_dns_filter",
        "relevance": "system_wide_domain_filter_comparator",
    },
    {
        "country": "us",
        "bundle_id": "site.kaylees.Wipr2",
        "segment": "safari_and_network_filter",
        "relevance": "indie_upfront_paid_comparator",
    },
    {
        "country": "us",
        "bundle_id": "com.futuremind.adblock",
        "segment": "local_dns_proxy_and_safari",
        "relevance": "legacy_upfront_paid_comparator",
    },
    {
        "country": "us",
        "bundle_id": "com.samuellaska.AdBuster",
        "segment": "safari_content_blocker",
        "relevance": "large_rating_count_safari_comparator",
    },
]


def fetch_json(url: str, *, attempts: int = 3) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def endpoint_url(endpoint: str, parameters: dict[str, Any]) -> str:
    return f"{endpoint}?{urllib.parse.urlencode(parameters)}"


def compact_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "track_name": item.get("trackName"),
        "bundle_id": item.get("bundleId"),
        "track_id": item.get("trackId"),
        "artist_name": item.get("artistName"),
        "formatted_price": item.get("formattedPrice"),
        "average_user_rating": item.get("averageUserRating"),
        "user_rating_count": item.get("userRatingCount"),
        "track_view_url": item.get("trackViewUrl"),
    }


def selected_result(
    item: dict[str, Any], target: dict[str, str]
) -> dict[str, Any]:
    return {
        "country": target["country"],
        "segment": target["segment"],
        "relevance": target["relevance"],
        "track_name": item.get("trackName"),
        "bundle_id": item.get("bundleId"),
        "track_id": item.get("trackId"),
        "artist_name": item.get("artistName"),
        "artist_view_url": item.get("artistViewUrl"),
        "track_view_url": item.get("trackViewUrl"),
        "seller_url": item.get("sellerUrl"),
        "price": item.get("price"),
        "currency": item.get("currency"),
        "formatted_price": item.get("formattedPrice"),
        "average_user_rating": item.get("averageUserRating"),
        "user_rating_count": item.get("userRatingCount"),
        "version": item.get("version"),
        "current_version_release_date": item.get("currentVersionReleaseDate"),
        "minimum_os_version": item.get("minimumOsVersion"),
        "genres": item.get("genres") or [],
        "description": item.get("description"),
        "release_notes": item.get("releaseNotes"),
        "screenshot_urls": item.get("screenshotUrls") or [],
    }


def collect() -> dict[str, Any]:
    snapshot_at = datetime.now(timezone.utc).isoformat()
    queries: list[dict[str, Any]] = []
    for query in SEARCH_QUERIES:
        url = endpoint_url(
            SEARCH_ENDPOINT,
            {
                "term": query["term"],
                "country": query["country"],
                "entity": "software",
                "limit": 200,
            },
        )
        payload = fetch_json(url)
        queries.append(
            {
                **query,
                "source_url": url,
                "result_count": payload.get("resultCount", 0),
                "results": [
                    compact_result(item) for item in payload.get("results", [])
                ],
            }
        )

    selected_apps: list[dict[str, Any]] = []
    for target in TARGETS:
        url = endpoint_url(
            LOOKUP_ENDPOINT,
            {"bundleId": target["bundle_id"], "country": target["country"]},
        )
        payload = fetch_json(url)
        results = payload.get("results", [])
        if len(results) != 1:
            raise RuntimeError(
                f"expected one lookup result for {target['bundle_id']}, got {len(results)}"
            )
        selected_apps.append(
            {**selected_result(results[0], target), "lookup_source_url": url}
        )

    return {
        "snapshot_at": snapshot_at,
        "methodology": {
            "api_documentation": API_DOCUMENTATION,
            "search_endpoint": SEARCH_ENDPOINT,
            "lookup_endpoint": LOOKUP_ENDPOINT,
            "query_limit": 200,
            "query_count": len(SEARCH_QUERIES),
            "selected_app_count": len(TARGETS),
            "limitations": [
                "Search ranking is keyword- and storefront-dependent, so this is not an exhaustive App Store census.",
                "Apple returns ratings and review-count signals here, not installs, MAU, purchases, revenue, or profit.",
                "Descriptions and screenshots are seller-authored claims; platform capability and real-app success require separate validation.",
            ],
        },
        "queries": queries,
        "selected_apps": selected_apps,
    }


def write_csv(snapshot: dict[str, Any], path: Path) -> None:
    fieldnames = [
        "snapshot_at",
        "country",
        "segment",
        "relevance",
        "track_name",
        "bundle_id",
        "track_id",
        "artist_name",
        "formatted_price",
        "average_user_rating",
        "user_rating_count",
        "version",
        "current_version_release_date",
        "minimum_os_version",
        "track_view_url",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for app in snapshot["selected_apps"]:
            writer.writerow(
                {"snapshot_at": snapshot["snapshot_at"]}
                | {field: app.get(field) for field in fieldnames if field != "snapshot_at"}
            )


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = collect()
    json_path = DATA_DIR / "ios_app_store_snapshot.json"
    csv_path = DATA_DIR / "ios_app_store_snapshot.csv"
    json_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(snapshot, csv_path)
    print(
        json.dumps(
            {
                "status": "collected",
                "queries": len(snapshot["queries"]),
                "selected_apps": len(snapshot["selected_apps"]),
                "json": str(json_path),
                "csv": str(csv_path),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
