#!/usr/bin/env python3
"""Collect reproducible public evidence for the mobile ad-skip market report.

Only public GitHub APIs, raw READMEs, and official Google Play detail pages are
queried. The generated files are structured extracts, not revenue estimates.
"""

from __future__ import annotations

import csv
import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESEARCH_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = RESEARCH_DIR / "data"
USER_AGENT = "FF-0177-market-research/1.0 (+public-evidence-only)"
PLAY_BASE = "https://play.google.com/store/apps/details"

PLAY_TARGETS = [
    {
        "package_id": "li.songe.gkd",
        "segment": "rule_engine",
        "relevance": "closest_chinese_splash_ad_rule_engine",
    },
    {
        "package_id": "net.airplanez.android.adskip",
        "segment": "accessibility_skip_and_mute",
        "relevance": "current_free_ad_supported_comparator",
    },
    {
        "package_id": "com.candlelight.adskipper",
        "segment": "accessibility_skip_and_mute",
        "relevance": "current_small_comparator",
    },
    {
        "package_id": "com.evolvarc.adskipper",
        "segment": "accessibility_skip",
        "relevance": "recent_small_comparator",
    },
    {
        "package_id": "com.mavenkalabs.adskipper",
        "segment": "accessibility_skip_and_mute",
        "relevance": "current_free_large_comparator",
    },
    {
        "package_id": "decemberpei.gmail.adskipper",
        "segment": "accessibility_skip",
        "relevance": "current_mid_size_comparator",
    },
    {
        "package_id": "com.kw.skipify",
        "segment": "freemium_lifetime_unlock",
        "relevance": "only_observed_explicit_paid_anchor",
    },
    {
        "package_id": "com.rhaon.ad_skip",
        "segment": "ad_supported_skip",
        "relevance": "stale_ad_supported_comparator",
    },
    {
        "package_id": "skip.ads.pro",
        "segment": "ad_supported_skip_and_mute",
        "relevance": "stale_ad_supported_comparator",
    },
    {
        "package_id": "bluepie.ad_silence",
        "segment": "open_source_mute",
        "relevance": "adjacent_audio_ad_comparator",
    },
]


def fetch(url: str, *, attempts: int = 3) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json,text/html;q=0.9,*/*;q=0.8",
        },
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def fetch_json(url: str) -> Any:
    return json.loads(fetch(url).decode("utf-8"))


def fetch_text(url: str) -> str:
    return fetch(url).decode("utf-8", errors="replace")


def first_match(pattern: str, text: str, flags: int = 0) -> str | None:
    match = re.search(pattern, text, flags)
    return html.unescape(match.group(1)).strip() if match else None


def collect_github(snapshot_at: str) -> dict[str, Any]:
    repo_url = "https://api.github.com/repos/gkd-kit/gkd"
    release_url = "https://api.github.com/repos/gkd-kit/gkd/releases?per_page=100"
    topic_url = (
        "https://api.github.com/search/repositories"
        "?q=topic%3Agkd-subscription&per_page=100"
    )
    head_repo_url = "https://api.github.com/repos/AIsouler/GKD_subscription"
    successor_repo_url = "https://api.github.com/repos/Lin-arm/GKD_subscription"

    repo = fetch_json(repo_url)
    releases = fetch_json(release_url)
    topic_search = fetch_json(topic_url)
    head_repo = fetch_json(head_repo_url)
    successor_repo = fetch_json(successor_repo_url)
    gkd_readme = fetch_text(
        "https://raw.githubusercontent.com/gkd-kit/gkd/main/README.md"
    )
    head_readme = fetch_text(
        "https://raw.githubusercontent.com/AIsouler/GKD_subscription/main/README.md"
    )
    successor_readme = fetch_text(
        "https://raw.githubusercontent.com/Lin-arm/GKD_subscription/main/README.md"
    )

    release_rows: list[dict[str, Any]] = []
    for release in releases:
        release_rows.append(
            {
                "tag_name": release.get("tag_name"),
                "published_at": release.get("published_at"),
                "html_url": release.get("html_url"),
                "assets": [
                    {
                        "name": asset.get("name"),
                        "download_count": asset.get("download_count"),
                        "size": asset.get("size"),
                        "browser_download_url": asset.get("browser_download_url"),
                    }
                    for asset in release.get("assets", [])
                ],
            }
        )

    apk_downloads = sum(
        asset["download_count"] or 0
        for release in release_rows
        for asset in release["assets"]
        if (asset["name"] or "").endswith(".apk")
    )
    all_asset_downloads = sum(
        asset["download_count"] or 0
        for release in release_rows
        for asset in release["assets"]
    )

    topic_items = [
        {
            "full_name": item["full_name"],
            "html_url": item["html_url"],
            "description": item.get("description"),
            "stargazers_count": item["stargazers_count"],
            "forks_count": item["forks_count"],
            "archived": item["archived"],
            "created_at": item["created_at"],
            "updated_at": item["updated_at"],
            "pushed_at": item["pushed_at"],
        }
        for item in topic_search.get("items", [])
    ]
    stars = [item["stargazers_count"] for item in topic_items]
    stars_total = sum(stars)
    stars_top3 = sum(sorted(stars, reverse=True)[:3])

    head_counts = re.search(
        r"已适配\s*(\d+)\s*个应用，共有\s*(\d+)\s*应用规则组",
        head_readme,
    )
    successor_apps = first_match(r"已适配应用-(\d+)-", successor_readme)
    successor_groups = first_match(r"应用规则组-(\d+)-", successor_readme)

    return {
        "snapshot_at": snapshot_at,
        "sources": {
            "repository": repo_url,
            "releases": release_url,
            "topic_search": topic_url,
            "gkd_readme": "https://github.com/gkd-kit/gkd",
            "head_rule_repo": "https://github.com/AIsouler/GKD_subscription",
            "successor_rule_repo": "https://github.com/Lin-arm/GKD_subscription",
        },
        "gkd_repository": {
            "full_name": repo["full_name"],
            "html_url": repo["html_url"],
            "description": repo.get("description"),
            "stargazers_count": repo["stargazers_count"],
            "forks_count": repo["forks_count"],
            "subscribers_count": repo["subscribers_count"],
            "open_issues_count": repo["open_issues_count"],
            "created_at": repo["created_at"],
            "updated_at": repo["updated_at"],
            "pushed_at": repo["pushed_at"],
            "license": (repo.get("license") or {}).get("spdx_id"),
            "default_branch": repo["default_branch"],
            "readme_facts": {
                "default_rules_included": (
                    False if "GKD **默认不提供规则**" in gkd_readme else None
                ),
                "has_subscription_model": "订阅规则" in gkd_readme,
                "has_snapshot_inspection": "快照审查" in gkd_readme,
                "has_sponsor_link": "github.com/lisonge/sponsor" in gkd_readme,
            },
        },
        "releases": {
            "release_count": len(release_rows),
            "apk_downloads": apk_downloads,
            "all_asset_downloads": all_asset_downloads,
            "latest": release_rows[0] if release_rows else None,
            "items": release_rows,
        },
        "subscription_topic": {
            "reported_total_count": topic_search.get("total_count"),
            "returned_count": len(topic_items),
            "stars_total": stars_total,
            "stars_top3": stars_top3,
            "stars_top3_share_percent": (
                stars_top3 / stars_total * 100 if stars_total else None
            ),
            "repositories_with_stars_lte_10": sum(value <= 10 for value in stars),
            "repositories_with_stars_lte_100": sum(value <= 100 for value in stars),
            "repositories_with_stars_lte_1000": sum(value <= 1000 for value in stars),
            "zero_star_repositories": sum(value == 0 for value in stars),
            "archived_repositories": sum(item["archived"] for item in topic_items),
            "items": topic_items,
        },
        "head_rule_repository": {
            "full_name": head_repo["full_name"],
            "html_url": head_repo["html_url"],
            "stargazers_count": head_repo["stargazers_count"],
            "forks_count": head_repo["forks_count"],
            "archived": head_repo["archived"],
            "created_at": head_repo["created_at"],
            "pushed_at": head_repo["pushed_at"],
            "stopped_maintenance_date": first_match(
                r"本仓库已停止维护.*?>\s*(\d{4}\.\d{2}\.\d{2})",
                head_readme,
                re.S,
            ),
            "adapted_apps": int(head_counts.group(1)) if head_counts else None,
            "app_rule_groups": int(head_counts.group(2)) if head_counts else None,
            "maintenance_reason_present": "热情终究会耗尽" in head_readme,
            "domestic_distribution_prohibited_by_maintainer": (
                "禁止在国内平台传播" in head_readme
            ),
        },
        "successor_rule_repository": {
            "full_name": successor_repo["full_name"],
            "html_url": successor_repo["html_url"],
            "stargazers_count": successor_repo["stargazers_count"],
            "forks_count": successor_repo["forks_count"],
            "archived": successor_repo["archived"],
            "created_at": successor_repo["created_at"],
            "pushed_at": successor_repo["pushed_at"],
            "adapted_apps": int(successor_apps) if successor_apps else None,
            "app_rule_groups": int(successor_groups) if successor_groups else None,
            "describes_itself_as_successor_fork": "社区续更的Fork版"
            in successor_readme,
        },
    }


def collect_play(snapshot_at: str) -> dict[str, Any]:
    apps: list[dict[str, Any]] = []
    for target in PLAY_TARGETS:
        package_id = target["package_id"]
        url = f"{PLAY_BASE}?id={package_id}&hl=en&gl=US"
        page = fetch_text(url)
        title = first_match(r'property="og:title" content="([^"]+)', page)
        description = first_match(
            r'property="og:description" content="([^"]*)',
            page,
        )
        installs = first_match(
            r'class="ClM7O">([^<]+)</div><div class="g1rdde">Downloads',
            page,
        )
        rating = first_match(
            r'aria-label="Rated ([0-9.]+) stars out of five stars"',
            page,
        )
        reviews = first_match(
            r'<div class="g1rdde">([0-9.,]+[KMB]?) reviews</div>',
            page,
        )
        updated_on = first_match(
            r'<div class="lXlx5">Updated on</div><div class="xg1aie">([^<]+)',
            page,
        )
        info_badge_index = page.find('<div class="JU1wdd">')
        primary_header = page[:info_badge_index] if info_badge_index > 0 else page
        contains_ads = ">Contains ads<" in primary_header
        has_in_app_purchases = ">In-app purchases<" in primary_header
        purchase_prices = (
            sorted(
                {
                    html.unescape(value)
                    for value in re.findall(
                        r'(\$[0-9]+\.[0-9]{2} per item)',
                        page,
                    )
                }
            )
            if has_in_app_purchases
            else []
        )
        apps.append(
            {
                **target,
                "source_url": url,
                "name": (title or "").replace(" - Apps on Google Play", ""),
                "short_description": description,
                "installs_display": installs,
                "rating_display": rating,
                "reviews_display": reviews,
                "updated_on": updated_on,
                "contains_ads": contains_ads,
                "has_in_app_purchases": has_in_app_purchases,
                "purchase_prices_observed": purchase_prices,
                "page_marker_found": bool(title and installs),
            }
        )
        time.sleep(0.2)

    return {
        "snapshot_at": snapshot_at,
        "locale": "en",
        "region": "US",
        "sampling_note": (
            "Purposive comparator set discovered through the current Google Play "
            "search surface; it is not a census and does not reveal revenue or MAU."
        ),
        "apps": apps,
    }


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    github = collect_github(snapshot_at)
    play = collect_play(snapshot_at)

    write_json(DATA_DIR / "github_snapshot.json", github)
    write_json(DATA_DIR / "google_play_snapshot.json", play)

    csv_path = DATA_DIR / "google_play_snapshot.csv"
    fields = [
        "package_id",
        "name",
        "segment",
        "relevance",
        "installs_display",
        "rating_display",
        "reviews_display",
        "contains_ads",
        "has_in_app_purchases",
        "updated_on",
        "short_description",
        "source_url",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for app in play["apps"]:
            writer.writerow({field: app.get(field) for field in fields})

    print(
        json.dumps(
            {
                "snapshot_at": snapshot_at,
                "github_output": str(DATA_DIR / "github_snapshot.json"),
                "play_output": str(DATA_DIR / "google_play_snapshot.json"),
                "play_csv_output": str(csv_path),
                "play_apps": len(play["apps"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
