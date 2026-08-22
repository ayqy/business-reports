#!/usr/bin/env python3
"""Validate report structure, snapshots, calculations, and PRD trigger logic."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research"
DATA = RESEARCH / "data"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    required_files = [
        ROOT / "README.md",
        ROOT / "report.md",
        RESEARCH / "process.md",
        RESEARCH / "sources.md",
        RESEARCH / "calculations.md",
        RESEARCH / "scan" / "competitor-functional-matrix.md",
        RESEARCH / "scan" / "ios-feasibility-matrix.md",
        RESEARCH / "scan" / "ios-competitor-functional-matrix.md",
        DATA / "github_snapshot.json",
        DATA / "google_play_snapshot.json",
        DATA / "google_play_snapshot.csv",
        DATA / "ios_app_store_snapshot.json",
        DATA / "ios_app_store_snapshot.csv",
        DATA / "economics.json",
        DATA / "economics.csv",
        DATA / "forecast_scenarios.csv",
    ]
    for path in required_files:
        require(path.is_file() and path.stat().st_size > 0, f"missing: {path}")

    report = (ROOT / "report.md").read_text(encoding="utf-8")
    sources = (RESEARCH / "sources.md").read_text(encoding="utf-8")
    matrix = (RESEARCH / "scan" / "competitor-functional-matrix.md").read_text(
        encoding="utf-8"
    )
    ios_matrix = (RESEARCH / "scan" / "ios-feasibility-matrix.md").read_text(
        encoding="utf-8"
    )
    ios_competitor_matrix = (
        RESEARCH / "scan" / "ios-competitor-functional-matrix.md"
    ).read_text(encoding="utf-8")
    economics = json.loads((DATA / "economics.json").read_text(encoding="utf-8"))
    github = json.loads(
        (DATA / "github_snapshot.json").read_text(encoding="utf-8")
    )
    play = json.loads(
        (DATA / "google_play_snapshot.json").read_text(encoding="utf-8")
    )
    ios_store = json.loads(
        (DATA / "ios_app_store_snapshot.json").read_text(encoding="utf-8")
    )

    require(
        "一句话结论：不建议做，除非" in report[:1000]
        and "因为" in report[:1000],
        "opening decision sentence is missing or weak",
    )
    for marker in [
        "高置信判断",
        "你的关注点",
        "抽象后的研究问题",
        "目标用户的顾虑",
        "获客可行性",
        "信任门槛与切换成本",
        "结论置信度",
        "致命假设",
        "最终判断",
        "官方直接证据",
        "基于公开数据的测算",
        "仍存在不确定性",
    ]:
        require(marker in report, f"report marker missing: {marker}")

    for source_id in [f"S{index:02d}" for index in range(1, 50)]:
        require(source_id in sources, f"source ledger missing {source_id}")
    require(sources.count("https://") >= 49, "too few source links")

    for marker in [
        "iOS 原生自动跳过不可行",
        "iOS 26 URL Filter",
        "对知乎与豆瓣的直接回答",
        "关闭豆瓣 Motion & Fitness",
        "替代分发改变安装路径，不改变沙箱",
        "iOS 市场上有哪些类似产品",
        "开屏弃",
        "别跳",
        "没有检出可验证产品",
    ]:
        require(marker in report, f"iOS feasibility marker missing from report: {marker}")
    for marker in [
        "原生第三方 App 自动跳过：不可行",
        "路线能力矩阵",
        "知乎：熄屏后切回出现原生开屏广告",
        "豆瓣：轻微移动触发广告落地页",
        "直接证据",
        "推断",
        "待真机验证缺口",
    ]:
        require(marker in ios_matrix, f"iOS matrix marker missing: {marker}")
    for marker in [
        "有相邻产品，但没有普通 iOS 上等价于李跳跳的产品",
        "最接近李跳跳的中国区产品",
        "开屏弃：绕过启动路径，不点击广告",
        "别跳：误跳后的自动回退，不跳过广告",
        "Jinx：DNS/本地 VPN/HTTPS URL 过滤，不操作界面",
        "到底能自动跳过哪些广告",
        "对知乎与豆瓣的直接回答",
        "scan 三桶结论",
        "官方直接证据",
        "基于证据的推断",
        "待真机验证缺口",
    ]:
        require(marker in ios_competitor_matrix, f"iOS competitor marker missing: {marker}")

    require(
        economics["mainland_buyout"]["orders_required_per_month"] == 382,
        "mainland order threshold drifted",
    )
    require(
        economics["mainland_buyout"]["installs_required_at_2pct_conversion"]
        == 19100,
        "mainland 2% install threshold drifted",
    )
    require(
        economics["mainland_buyout"]["installs_required_at_5pct_conversion"]
        == 7640,
        "mainland 5% install threshold drifted",
    )
    require(
        economics["google_play_buyout"]["orders_required_per_month"] == 374,
        "Play order threshold drifted",
    )
    require(
        economics["google_play_subscription"]["active_payers_required"] == 938,
        "subscription threshold drifted",
    )

    for visible_number in [
        "382",
        "19,100",
        "7,640",
        "374",
        "18,700",
        "7,480",
        "938",
        f"{github['releases']['apk_downloads']:,}",
        f"{github['gkd_repository']['stargazers_count']:,}",
        f"{economics['mainland_buyout']['gross_sales_at_threshold_cny']:,.2f}",
        f"{economics['mainland_buyout']['monthly_operating_profit_at_threshold_cny']:,.2f}",
        f"{economics['google_play_buyout']['gross_sales_at_threshold_usd']:,.2f}",
        f"{economics['google_play_buyout']['monthly_operating_profit_at_threshold_cny']:,.2f}",
    ]:
        require(visible_number in report, f"key result absent from report: {visible_number}")

    require(
        github["subscription_topic"]["returned_count"] == 29,
        "topic sample count drifted",
    )
    require(
        github["subscription_topic"]["repositories_with_stars_lte_10"] == 15,
        "long-tail count drifted",
    )
    require(
        github["head_rule_repository"]["archived"] is True,
        "head rule repository archive state not captured",
    )
    require(len(play["apps"]) == 10, "Play comparator set is incomplete")
    require(
        all(app["page_marker_found"] for app in play["apps"]),
        "one or more Play pages failed extraction",
    )
    require(len(ios_store["queries"]) == 8, "iOS query set is incomplete")
    require(
        ios_store["methodology"]["query_limit"] == 200,
        "iOS query limit drifted",
    )
    require(
        len(ios_store["selected_apps"]) == 12,
        "iOS selected comparator set is incomplete",
    )
    ios_bundles = {app["bundle_id"] for app in ios_store["selected_apps"]}
    for bundle_id in [
        "com.twostones.adblocker",
        "com.app.nojump",
        "com.appstudio.Jinx",
        "com.adguard.AdguardExtension",
        "com.khanov.BlockerX",
        "com.confirmed.lockdown",
        "net.blocka.app",
        "io.nextdns.NextDNS",
        "site.kaylees.Wipr2",
    ]:
        require(bundle_id in ios_bundles, f"missing iOS comparator: {bundle_id}")
    require(
        all(app["track_view_url"] for app in ios_store["selected_apps"]),
        "one or more iOS comparators lack an official store URL",
    )
    require(
        "新增央视频、知乎、浙里办"
        in next(
            app["release_notes"]
            for app in ios_store["selected_apps"]
            if app["bundle_id"] == "com.twostones.adblocker"
        ),
        "JumpBlocker Zhihu release evidence is missing",
    )
    require(
        "不会屏蔽广告"
        in next(
            app["description"]
            for app in ios_store["selected_apps"]
            if app["bundle_id"] == "com.app.nojump"
        ),
        "NoJump scope disclaimer is missing",
    )

    require(
        "完整 PRD 条件未触发" in matrix,
        "scan trigger decision is not explicit",
    )
    require(
        not list(ROOT.glob("*requirements-specification*.md")),
        "a full PRD exists even though the feasibility trigger is negative",
    )

    result = {
        "status": "passed",
        "required_files": len(required_files),
        "play_comparators": len(play["apps"]),
        "ios_comparator_skus": len(ios_store["selected_apps"]),
        "ios_search_queries": len(ios_store["queries"]),
        "source_ledger_entries_checked": 49,
        "prd_trigger": "not_triggered",
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise
