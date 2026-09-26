#!/usr/bin/env python3
"""Explicit scenario arithmetic. Inputs are hypotheses, not measured industry rates."""

import json
import math
from pathlib import Path


OUT = Path(__file__).with_name("model-results.json")


def pass_model(price=68, months=4, commission=0.15, refund=0.03,
               monthly_fixed_cost=3000, owner_pre_tax_target=10000,
               payer_share=0.02, renewal=0.40):
    net_per_pass = price * (1 - commission) * (1 - refund)
    needed_active_payers = math.ceil((monthly_fixed_cost + owner_pre_tax_target)
                                     * months / net_per_pass)
    needed_mau = math.ceil(needed_active_payers / payer_share)
    new_payers_per_month = needed_active_payers * (1 - renewal) / months
    return {
        "inputs": {"price": price, "months": months, "commission": commission,
                   "refund": refund, "monthly_fixed_cost": monthly_fixed_cost,
                   "owner_pre_tax_target": owner_pre_tax_target,
                   "payer_share": payer_share, "renewal": renewal},
        "net_per_season_pass_yuan": round(net_per_pass, 3),
        "monthly_net_per_active_payer_yuan": round(net_per_pass / months, 3),
        "active_season_payers_for_target": needed_active_payers,
        "mau_for_target": needed_mau,
        "monthly_new_payers_at_renewal": math.ceil(new_payers_per_month),
        "monthly_new_installs_at_same_conversion": math.ceil(new_payers_per_month / payer_share),
        "lifetime_net_receipts_per_payer_at_renewal": round(net_per_pass / (1 - renewal), 3),
        "break_even_acquisition_cost_per_install": round(
            payer_share * net_per_pass / (1 - renewal), 3),
    }


def profit(mau, payer_share, price=68, months=4, commission=0.15,
           refund=0.03, monthly_fixed_cost=3000):
    gross = mau * payer_share * price / months
    developer_receipts = gross * (1 - commission) * (1 - refund)
    return {"mau": mau, "payer_share": payer_share,
            "gross_sales_per_month_yuan": round(gross, 2),
            "developer_receipts_per_month_yuan": round(developer_receipts, 2),
            "owner_profit_pre_tax_per_month_yuan": round(developer_receipts - monthly_fixed_cost, 2)}


def forecast(base, annual_rate, years):
    return round(base * (1 + annual_rate) ** years, 2)


def main():
    result = {
        "units": "CNY unless stated; forecast market units are 亿元",
        "warning": "All prices, conversion, refunds, renewal, fixed cost and growth rates are declared scenarios, not observed averages.",
        "pass_base": pass_model(),
        "pass_sensitivity": [pass_model(payer_share=share, commission=fee)
                             for share in (0.01, 0.02, 0.05)
                             for fee in (0.15, 0.30)],
        "monthly_profit_examples": [profit(mau, share)
                                    for mau, share in ((5000, .01), (10000, .02),
                                                       (20000, .02), (50000, .02),
                                                       (20000, .05))],
        "paid_indie_price_examples": [
            {"storefront_price_yuan": price,
             "net_per_sale_after_assumed_15pct_fee_and_3pct_refunds_yuan": round(price * .85 * .97, 4),
             "monthly_sales_for_13000_yuan_receipts": math.ceil(13000 / (price * .85 * .97))}
            for price in (15, 18)
        ],
        "mobile_market_forecast_from_2025_2570_76_yi": {
            str(rate): {"2029": forecast(2570.76, rate, 4),
                        "2031": forecast(2570.76, rate, 6)}
            for rate in (-0.02, 0.03, 0.08)
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("base", {key: value for key, value in result["pass_base"].items() if key != "inputs"})
    print("profit", result["monthly_profit_examples"])
    print("forecast", result["mobile_market_forecast_from_2025_2570_76_yi"])


if __name__ == "__main__":
    main()
