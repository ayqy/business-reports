"""Check the 13 inferred golden forms and run their reference acceptance vectors.

This small oracle is deliberately limited to deterministic cases. Passing it does
not establish what the 2019 server did or validate a future production engine.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


class VerificationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def merge(instances: list[dict], form: dict) -> dict:
    """Apply the explicitly marked reference triple transition, not server logic."""
    require(len(instances) == 3, "triple must consume exactly three instances")
    require(len({item["instance_id"] for item in instances}) == 3, "instance IDs must differ")
    require(
        all(item["normal_id"] == form["normal_id"] for item in instances),
        "mixed definitions cannot triple",
    )
    require(
        all(item["zone"] in {"board", "hand"} for item in instances),
        "combat instances cannot enter recruit triple",
    )
    require(
        all(item.get("origin") != "combat_token" for item in instances),
        "combat tokens cannot enter recruit triple",
    )
    require(all(not item.get("golden", False) for item in instances), "only normal copies triple")
    return {
        "consumed": [item["instance_id"] for item in instances],
        "board_slots_freed": sum(item["zone"] == "board" for item in instances),
        "zone": "hand",
        "origin": "shop_triple",
        "golden": True,
        "normal_id": form["normal_id"],
        "golden_client_id": form["golden_client_id"],
        "buff_attack": sum(item["buff_attack"] for item in instances),
        "buff_health": sum(item["buff_health"] for item in instances),
        "attack": form["base_attack"] + sum(item["buff_attack"] for item in instances),
        "health": form["base_health"] + sum(item["buff_health"] for item in instances),
        "keywords": list(form["keywords"]),
        "reward_count": 0,
        "reward_pending": True,
    }


def play_golden(merged: dict) -> dict:
    require(merged["zone"] == "hand" and merged["reward_pending"], "invalid golden play")
    return {**merged, "zone": "board", "reward_count": 1, "reward_pending": False}


def effect(case: dict, form: dict, row: dict) -> dict:
    """Evaluate only isolated, death-order-free reference effects."""
    op, data = case["op"], case["input"]
    if op == "shield_hit":
        shield = bool(data["shield"])
        damage = data["damage"]
        return {
            "health": data["health"] if shield and damage > 0 else max(0, data["health"] - damage),
            "shield": shield and damage <= 0,
        }
    if op == "taunt_target_pool":
        taunts = [x["id"] for x in data["candidates"] if x["taunt"]]
        return {"eligible_target_ids": taunts or [x["id"] for x in data["candidates"]]}
    if op == "self_damage_on_play":
        return {"hero_health": data["hero_health"] - (data["damage"] if data["event"] == "play" else 0)}
    if op == "tribe_match":
        race = row["client_race"]
        return {"matches": [race == "ALL" or race == tribe for tribe in data["tribes"]]}
    if op == "restore_shield_on_mech_summon":
        activated = data["event"] == "friendly_summon" and data["summoned_tribe"] == "MECHANICAL"
        return {"shield": bool(data["shield"]) or activated}
    if op == "cleave_no_death":
        before = data["enemy_health"]
        center = data["main_enemy_index"]
        require(0 <= center < len(before), f"{case['id']}: invalid center")
        after = [hp - form["base_attack"] if abs(i - center) <= 1 else hp for i, hp in enumerate(before)]
        require(all(hp > 0 for hp in after), f"{case['id']}: death ordering would be needed")
        return {"enemy_health": after, "counterattack_sources": [center]}
    if op == "grant_poisonous_on_play":
        units = {item["id"]: item["poisonous"] for item in data["friendly_murlocs"]}
        require(data["selected_id"] in units, f"{case['id']}: selected target is not a friendly murloc")
        if data["event"] == "play":
            units[data["selected_id"]] = True
        return {f"{unit_id}_poisonous": value for unit_id, value in units.items()}
    if op == "windfury_lowest_attack":
        require("windfury" in form["keywords"], f"{case['id']}: golden form lacks windfury")
        enemies = [dict(unit) for unit in data["enemies"]]
        targets = []
        for _ in range(2):
            living = [unit for unit in enemies if unit["health"] > 0]
            require(living, f"{case['id']}: no target for the next attack")
            lowest = min(unit["attack"] for unit in living)
            candidates = [unit for unit in living if unit["attack"] == lowest]
            require(len(candidates) == 1, f"{case['id']}: tied targeting is historically unknown")
            target = candidates[0]
            targets.append(target["id"])
            target["health"] -= form["base_attack"]
        return {"attack_targets": targets, "remaining_health": {unit["id"]: unit["health"] for unit in enemies}}
    if op == "poisonous_damage":
        require("poisonous" in form["keywords"], f"{case['id']}: golden form lacks poisonous")
        effective_damage = 0 if data["target_shield"] else form["base_attack"]
        return {
            "target_health": 0 if effective_damage > 0 else data["target_health"],
            "target_shield": False,
        }
    raise VerificationError(f"{case['id']}: unsupported operation {op}")


def main() -> None:
    vectors = load("historical-golden-acceptance.json")
    card_pool = load("historical-card-pool.json")
    rules = load("historical-rule-parameters.json")
    require(vectors["mode"] == rules["rule_set"] == "reference_2019_launch_week", "reference mode mismatch")
    require(vectors["build"] == int(card_pool["build"].split(".")[-1]) == rules["build"] == 35747, "build mismatch")
    require(vectors["historical_status"] == "reference_only_not_exact_replay", "historical label lost")
    unknown = vectors["exact_2019_unknown"]
    require(all(value == "unknown" for value in unknown.values()), "historical unknown was guessed")
    require(rules["dynamic_generation"]["exact_pool_membership"] == "unknown", "pool membership was guessed")
    require(rules["dynamic_generation"]["weights"] == "unknown", "pool weights were guessed")
    require(not rules["dynamic_generation"]["exact_replay_ready"], "exact replay must remain gated")

    missing = {row["normal_id"]: row for row in card_pool["rows"] if row["golden_id"] is None}
    forms = {form["normal_id"]: form for form in vectors["golden_forms"]}
    require(len(missing) == len(forms) == len(vectors["golden_forms"]) == 13, "expected exactly 13 unique missing forms")
    require(missing.keys() == forms.keys(), "golden forms must cover all and only the missing card IDs")
    for normal_id, form in forms.items():
        row = missing[normal_id]
        require(form["golden_client_id"] is None, f"{normal_id}: unverified client ID was assigned")
        require(row["golden_evidence"] == "inferred_from_triple_rule", f"{normal_id}: evidence grade drift")
        require(form["base_attack"] == row["golden_attack"] == 2 * row["normal_attack"], f"{normal_id}: attack mismatch")
        require(form["base_health"] == row["golden_health"] == 2 * row["normal_health"], f"{normal_id}: health mismatch")
        require("inferred" in form["grade"], f"{normal_id}: reference inference label missing")

    fixture = vectors["merge_fixture"]
    for normal_id, form in forms.items():
        instances = [{**item, "normal_id": normal_id} for item in fixture["instances"]]
        merged = merge(instances, form)
        expected = {
            "consumed": fixture["expected_consumed"],
            "board_slots_freed": fixture["expected_board_slots_freed"],
            "zone": fixture["expected_result_zone"],
            "origin": fixture["expected_result_origin"],
            "buff_attack": fixture["expected_buff_attack"],
            "buff_health": fixture["expected_buff_health"],
            "reward_count": fixture["expected_reward_count_after_merge"],
        }
        require(all(merged[key] == value for key, value in expected.items()), f"{normal_id}: triple state mismatch")
        require(merged["golden"] and merged["reward_pending"], f"{normal_id}: golden transition incomplete")
        require(merged["keywords"] == form["keywords"], f"{normal_id}: keywords were multiplied")
        require(merged["attack"] == missing[normal_id]["golden_attack"] + 3, f"{normal_id}: attack buff mismatch")
        require(merged["health"] == missing[normal_id]["golden_health"] + 3, f"{normal_id}: health buff mismatch")
        require(play_golden(merged)["reward_count"] == fixture["expected_reward_count_after_play"], f"{normal_id}: reward mismatch")

    cases = vectors["effect_cases"]
    require(len({case["id"] for case in cases}) == len(cases), "effect case IDs must be unique")
    require({case["normal_id"] for case in cases} == missing.keys(), "every missing golden form needs an effect case")
    for case in cases:
        actual = effect(case, forms[case["normal_id"]], missing[case["normal_id"]])
        require(actual == case["expected"], f"{case['id']} {case['normal_id']}: expected {case['expected']}, got {actual}")

    guards = vectors["identity_guards"]
    token = guards["golden_voidwalker_token"]
    require(forms["CS2_065"]["golden_client_id"] is None, "shop triple voidwalker identity was invented")
    require(guards["voidwalker_shop_triple_client_id"] is None, "shop triple identity guard failed")
    require(guards["voidwalker_shop_triple_form_key"] == "reference:CS2_065:golden", "reference identity drift")
    require(token["client_id"] == "TB_BaconUps_059t", "token identity drift")
    require(
        token["client_id"] not in {row["normal_id"] for row in card_pool["rows"]}
        and token["client_id"] not in {row["golden_id"] for row in card_pool["rows"]},
        "combat token was confused with a shop triple definition",
    )
    require(token["zone"] == "combat_board" and token["origin"] == "combat_token", "token origin drift")
    require(token["attack"] == 2 and token["health"] == 6 and token["premium"], "client token card face drift")
    require(token["source_parent_id"] == "TB_BaconUps_059" and "inferred" in token["source_parent_grade"], "parent-chain inference was upgraded")
    require(guards["mixed_triple_must_reject"] and guards["combat_token_must_not_enter_recruit_merge"], "negative guards missing")
    require(guards["exact_2019_requires_verified_pool_and_event_order"], "exact-mode gate missing")
    a = [{**item, "normal_id": "CS2_065"} for item in fixture["instances"]]
    for altered in ([{**a[0], "normal_id": "ICC_038"}, *a[1:]], [{**item, "origin": "combat_token"} for item in a]):
        try:
            merge(altered, forms["CS2_065"])
        except VerificationError:
            pass
        else:
            raise VerificationError("a mixed or combat-origin triple was accepted")

    print(f"PASS: {len(forms)} inferred golden merge forms, {len(cases)} deterministic effect vectors, identity and unknown-history guards; reference only")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
