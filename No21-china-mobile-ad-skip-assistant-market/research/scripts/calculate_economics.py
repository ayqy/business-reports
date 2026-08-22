#!/usr/bin/env python3
"""Generate the transparent unit-economics and 3–5 year scenario model."""

from __future__ import annotations

import csv
import json
import math
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


RESEARCH_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = RESEARCH_DIR / "data"
GITHUB_SNAPSHOT = DATA_DIR / "github_snapshot.json"


def d(value: str | int | float) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ceil_decimal(value: Decimal) -> int:
    return math.ceil(float(value))


def main() -> None:
    github = json.loads(GITHUB_SNAPSHOT.read_text(encoding="utf-8"))
    snapshot_date = datetime.fromisoformat(github["snapshot_at"]).date()

    target_profit_cny = d("10000")
    monthly_fixed_cash_cost_cny = d("1000")
    required_contribution_cny = target_profit_cny + monthly_fixed_cash_cost_cny
    refund_rate = d("0.03")
    usd_cny_scenario_rate = d("7.15")

    cn_price = d("29.9")
    cn_payment_fee = d("0.006")
    cn_contribution = cn_price * (d("1") - cn_payment_fee) * (
        d("1") - refund_rate
    )
    cn_buyers = ceil_decimal(required_contribution_cny / cn_contribution)

    play_buyout_usd = d("4.99")
    play_fee = d("0.15")
    play_buyout_contribution_usd = (
        play_buyout_usd * (d("1") - play_fee) * (d("1") - refund_rate)
    )
    play_buyout_contribution_cny = (
        play_buyout_contribution_usd * usd_cny_scenario_rate
    )
    play_buyers = ceil_decimal(
        required_contribution_cny / play_buyout_contribution_cny
    )

    play_subscription_usd = d("1.99")
    play_subscription_contribution_cny = (
        play_subscription_usd
        * (d("1") - play_fee)
        * (d("1") - refund_rate)
        * usd_cny_scenario_rate
    )
    play_subscription_users = ceil_decimal(
        required_contribution_cny / play_subscription_contribution_cny
    )

    conversion_rates = [d("0.02"), d("0.05")]
    cn_installs = {
        f"{int(rate * 100)}pct": ceil_decimal(d(cn_buyers) / rate)
        for rate in conversion_rates
    }
    play_installs = {
        f"{int(rate * 100)}pct": ceil_decimal(d(play_buyers) / rate)
        for rate in conversion_rates
    }

    ad_impressions_per_mau = d("10")
    ad_ecpm_range_usd = [d("1"), d("5")]
    ad_mau_required: dict[str, int] = {}
    for ecpm in ad_ecpm_range_usd:
        revenue_per_mau_cny = (
            ad_impressions_per_mau
            / d("1000")
            * ecpm
            * usd_cny_scenario_rate
        )
        ad_mau_required[f"ecpm_usd_{ecpm}"] = ceil_decimal(
            required_contribution_cny / revenue_per_mau_cny
        )

    latest = github["releases"]["latest"]
    latest_apk = next(
        asset for asset in latest["assets"] if asset["name"].endswith(".apk")
    )
    release_date = date.fromisoformat(latest["published_at"][:10])
    observed_days = (snapshot_date - release_date).days + 1
    monthly_days = d("365.25") / d("12")
    latest_apk_monthly_rate = (
        d(latest_apk["download_count"]) / d(observed_days) * monthly_days
    )

    forecast_rates = {
        "pessimistic": d("-0.15"),
        "base": d("-0.05"),
        "optimistic": d("0.03"),
    }
    forecast: dict[str, dict[str, Any]] = {}
    for name, annual_rate in forecast_rates.items():
        multiplier = d("1") + annual_rate
        forecast[name] = {
            "annual_change_percent": float(annual_rate * d("100")),
            "index_2026": 100.0,
            "index_2029": float((d("100") * multiplier**3).quantize(d("0.1"))),
            "index_2031": float((d("100") * multiplier**5).quantize(d("0.1"))),
        }

    output = {
        "model_date": snapshot_date.isoformat(),
        "evidence_boundary": {
            "direct_inputs": [
                "Google Play 15% service-fee tier",
                "Skipify public $4.99 lifetime unlock",
                "GKD release asset download counts and dates",
            ],
            "scenario_inputs_not_industry_facts": [
                "CNY 29.90 mainland buyout price",
                "3% refund rate",
                "0.6% mainland payment fee",
                "CNY 1,000 monthly fixed cash cost",
                "USD/CNY 7.15 conversion rate",
                "2% and 5% paid conversion rates",
                "USD 1–5 realized ad eCPM and 10 impressions per MAU",
                "forecast annual change rates",
            ],
        },
        "common_inputs": {
            "target_monthly_cash_profit_cny_before_personal_tax": float(
                target_profit_cny
            ),
            "monthly_fixed_cash_cost_cny": float(monthly_fixed_cash_cost_cny),
            "required_monthly_contribution_cny": float(required_contribution_cny),
            "refund_rate_percent": float(refund_rate * d("100")),
            "usd_cny_scenario_rate": float(usd_cny_scenario_rate),
        },
        "mainland_buyout": {
            "price_cny": float(cn_price),
            "payment_fee_percent": float(cn_payment_fee * d("100")),
            "contribution_per_order_cny": float(money(cn_contribution)),
            "orders_required_per_month": cn_buyers,
            "gross_sales_at_threshold_cny": float(
                money(d(cn_buyers) * cn_price)
            ),
            "monthly_contribution_at_threshold_cny": float(
                money(d(cn_buyers) * cn_contribution)
            ),
            "monthly_operating_profit_at_threshold_cny": float(
                money(
                    d(cn_buyers) * cn_contribution
                    - monthly_fixed_cash_cost_cny
                )
            ),
            "installs_required_at_2pct_conversion": cn_installs["2pct"],
            "installs_required_at_5pct_conversion": cn_installs["5pct"],
        },
        "google_play_buyout": {
            "price_usd": float(play_buyout_usd),
            "service_fee_percent": float(play_fee * d("100")),
            "contribution_per_order_usd": float(
                money(play_buyout_contribution_usd)
            ),
            "contribution_per_order_cny": float(
                money(play_buyout_contribution_cny)
            ),
            "orders_required_per_month": play_buyers,
            "gross_sales_at_threshold_usd": float(
                money(d(play_buyers) * play_buyout_usd)
            ),
            "gross_sales_at_threshold_cny": float(
                money(
                    d(play_buyers)
                    * play_buyout_usd
                    * usd_cny_scenario_rate
                )
            ),
            "monthly_contribution_at_threshold_cny": float(
                money(d(play_buyers) * play_buyout_contribution_cny)
            ),
            "monthly_operating_profit_at_threshold_cny": float(
                money(
                    d(play_buyers) * play_buyout_contribution_cny
                    - monthly_fixed_cash_cost_cny
                )
            ),
            "installs_required_at_2pct_conversion": play_installs["2pct"],
            "installs_required_at_5pct_conversion": play_installs["5pct"],
        },
        "google_play_subscription": {
            "price_usd_per_month": float(play_subscription_usd),
            "contribution_per_active_payer_cny": float(
                money(play_subscription_contribution_cny)
            ),
            "active_payers_required": play_subscription_users,
            "gross_sales_at_threshold_usd": float(
                money(d(play_subscription_users) * play_subscription_usd)
            ),
            "monthly_operating_profit_at_threshold_cny": float(
                money(
                    d(play_subscription_users)
                    * play_subscription_contribution_cny
                    - monthly_fixed_cash_cost_cny
                )
            ),
        },
        "ad_supported_sensitivity": {
            "impressions_per_mau_per_month_scenario": int(
                ad_impressions_per_mau
            ),
            "mau_required_at_realized_ecpm_usd_1": ad_mau_required[
                "ecpm_usd_1"
            ],
            "mau_required_at_realized_ecpm_usd_5": ad_mau_required[
                "ecpm_usd_5"
            ],
        },
        "gkd_head_proxy": {
            "latest_release": latest["tag_name"],
            "latest_release_published_at": latest["published_at"],
            "latest_apk_downloads": latest_apk["download_count"],
            "observed_days_inclusive": observed_days,
            "normalized_apk_downloads_per_30_4375_days": float(
                latest_apk_monthly_rate.quantize(d("0.1"))
            ),
            "mainland_2pct_required_installs_as_head_proxy_percent": float(
                (d(cn_installs["2pct"]) / latest_apk_monthly_rate * d("100")).quantize(
                    d("0.1")
                )
            ),
            "mainland_5pct_required_installs_as_head_proxy_percent": float(
                (d(cn_installs["5pct"]) / latest_apk_monthly_rate * d("100")).quantize(
                    d("0.1")
                )
            ),
            "warning": (
                "Release-asset downloads are not unique users or new installs; "
                "this is a directional head-product traffic proxy only."
            ),
        },
        "paid_tool_revenue_pool_scenario_index": forecast,
    }

    output_path = DATA_DIR / "economics.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    csv_rows = [
        ("mainland_buyout", "orders_required_per_month", cn_buyers, "orders"),
        (
            "mainland_buyout",
            "installs_required_at_2pct_conversion",
            cn_installs["2pct"],
            "installs",
        ),
        (
            "mainland_buyout",
            "installs_required_at_5pct_conversion",
            cn_installs["5pct"],
            "installs",
        ),
        ("play_buyout", "orders_required_per_month", play_buyers, "orders"),
        (
            "play_buyout",
            "installs_required_at_2pct_conversion",
            play_installs["2pct"],
            "installs",
        ),
        (
            "play_buyout",
            "installs_required_at_5pct_conversion",
            play_installs["5pct"],
            "installs",
        ),
        (
            "play_subscription",
            "active_payers_required",
            play_subscription_users,
            "active_payers",
        ),
        (
            "ad_supported",
            "mau_required_at_realized_ecpm_usd_1",
            ad_mau_required["ecpm_usd_1"],
            "MAU",
        ),
        (
            "ad_supported",
            "mau_required_at_realized_ecpm_usd_5",
            ad_mau_required["ecpm_usd_5"],
            "MAU",
        ),
    ]
    with (DATA_DIR / "economics.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["model", "metric", "value", "unit"])
        writer.writerows(csv_rows)

    with (DATA_DIR / "forecast_scenarios.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "scenario",
                "annual_change_percent",
                "index_2026",
                "index_2029",
                "index_2031",
            ]
        )
        for name, row in forecast.items():
            writer.writerow(
                [
                    name,
                    row["annual_change_percent"],
                    row["index_2026"],
                    row["index_2029"],
                    row["index_2031"],
                ]
            )

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
