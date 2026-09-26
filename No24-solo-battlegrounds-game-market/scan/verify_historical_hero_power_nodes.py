"""Verify 24 inferred-launch hero powers as bounded, non-historical reference intents."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
DEFERRED = {"battle_start", "next_battlecry_this_round"}


class VerificationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def matches(minion: dict, tribe: str) -> bool:
    return minion.get("race") in {tribe, "ALL"}


class Draws:
    def __init__(self, indexes: list[int]):
        self.indexes = indexes
        self.used = 0

    def pick(self, entries: list):
        require(bool(entries), "draw_from_empty_candidates")
        require(self.used < len(self.indexes), "draw_index_missing")
        index = self.indexes[self.used]
        require(type(index) is int and 0 <= index < len(entries), "draw_index_out_of_bounds")
        self.used += 1
        return entries[index]

    def pick_distinct(self, entries: list, count: int) -> list:
        remaining = entries.copy()
        selected = []
        for _ in range(min(count, len(remaining))):
            choice = self.pick(remaining)
            remaining.remove(choice)
            selected.append(choice)
        return selected


def empty() -> dict:
    return {"active": False, "coin_payment": 0, "hero_damage": 0,
            "scheduled": None, "actions": []}


def has_button_target(node: dict, event: dict) -> bool:
    scope = node["target_filter"]
    friendly = event.get("friendly", [])
    shop = event.get("shop", [])
    if scope == "selected_friendly_minion":
        return event.get("selected_id") in {m["id"] for m in friendly}
    if scope == "one_friendly_minion_random":
        return bool(friendly)
    if scope == "one_shop_minion_random":
        return bool(shop)
    return True


def actions_for(node: dict, event: dict, draws: Draws) -> list[dict]:
    kind = node["kind"]
    scope = node["target_filter"]
    params = node["params"]
    friendly = event.get("friendly", [])
    enemy = event.get("enemy", [])
    shop = event.get("shop", [])

    if kind == "grant_card":
        hand_slots = event.get("hand_slots", 10)
        require(type(hand_slots) is int and 0 <= hand_slots <= 10, "invalid_hand_slots")
        return [{"kind": kind, "card_id": params["card_id"],
                 "requested": params["count"], "acquired": min(params["count"], hand_slots)}]
    if scope == "two_distinct_enemy_random":
        targets = [m["id"] for m in draws.pick_distinct(enemy, params["count"])]
        return [{"kind": "damage", "targets": targets, "amount_each": params["amount"]}] if targets else []
    if scope == "one_each_friendly_tribe_random":
        result = []
        for tribe in params["tribes"]:
            candidates = [m for m in friendly if matches(m, tribe)]
            if candidates:
                target = draws.pick(candidates)
                result.append({"kind": "buff_one", "target": target["id"],
                               "tribe_step": tribe, "attack": params["attack"],
                               "health": params["health"]})
        return result
    if scope == "selected_friendly_minion":
        return [{"kind": kind, "target": event["selected_id"], "keyword": params["keyword"]}]
    if kind == "buff_matching_purchased":
        bought = event.get("bought")
        if not bought:
            return []
        if "active_tribe" not in event:
            require(type(event.get("round")) is int and event["round"] >= 1, "invalid_round")
        tribe = event.get("active_tribe") or params["tribe_cycle"][(event["round"] - 1) % 4]
        require(tribe in params["tribe_cycle"], "invalid_active_tribe")
        return ([{"kind": "buff_one", "target": bought["id"], "attack": params["attack"],
                  "health": params["health"], "active_tribe": tribe}]
                if matches(bought, tribe) else [])
    if kind == "afk_skip_then_reward":
        round_number = event["round"]
        if round_number in params["skip_rounds"]:
            return [{"kind": "suppress_recruitment", "round": round_number}]
        if round_number == params["reward_round"]:
            return [{"kind": "unresolved_minion_request", "count": params["reward_count"],
                     "candidate_tiers": params["candidate_tiers"], "eligibility": "unknown"}]
        return []
    if scope in {"shop_mechanical", "friendly_demon"}:
        board = shop if scope == "shop_mechanical" else friendly
        tribe = "MECHANICAL" if scope == "shop_mechanical" else "DEMON"
        targets = [m["id"] for m in board if matches(m, tribe)]
        return [{"kind": "buff_all", "targets": targets, "attack": params["attack"],
                 "health": params["health"]}] if targets else []
    if scope == "all_friendly_minions":
        targets = [m["id"] for m in friendly]
        return [{"kind": kind, "targets": targets, "deathrattle_entity": params["deathrattle_entity"],
                 "summon_tribe": params["summon_tribe"], "summon_attack": params["summon_attack"],
                 "summon_health": params["summon_health"]}] if targets else []
    if scope in {"leftmost_friendly_minion", "rightmost_friendly_minion"}:
        if not friendly:
            return []
        target = friendly[0] if scope.startswith("leftmost") else friendly[-1]
        if kind == "buff_one":
            return [{"kind": kind, "target": target["id"], "attack": params["attack"],
                     "health": params["health"]}]
        return [{"kind": kind, "target": target["id"], "keyword": params["keyword"]}]
    if kind == "discover_request":
        return [{"kind": kind, "offer_type": params["offer_type"], "count": params["count"],
                 "placement": params["placement"], "candidate_eligibility": "unknown"}]
    if kind == "double_next_battlecry":
        return [{"kind": kind, "trigger_count": params["trigger_count"]}]
    if kind == "reroll_shop_request":
        tier = event["tavern_tier"]
        require(type(tier) is int and 1 <= tier <= 6, "invalid_tavern_tier")
        return [{"kind": kind, "last_slot_tier": min(tier + params["tier_delta"], params["tier_cap"]),
                 "candidate_eligibility": "unknown"}]
    if scope == "all_enemy_minions":
        targets = [m["id"] for m in enemy]
        return [{"kind": "damage", "targets": targets, "amount_each": params["amount"]}] if targets else []
    if kind == "upgrade_discount":
        return [{"kind": kind, "amount": params["discount"]}]
    if kind == "summon_starting_token":
        require(len(friendly) <= 7, "board_exceeds_seven_slots")
        return [{"kind": kind, "card_id": params["card_id"], "requested": params["count"],
                 "placed": min(params["count"], 7 - len(friendly)), "attack": params["attack"],
                 "health": params["health"], "race": params["race"]}]
    if kind == "set_starting_health":
        return [{"kind": kind, "health": params["health"]}]
    if scope == "one_shop_minion_random":
        return [{"kind": kind, "target": draws.pick(shop)["id"],
                 "attack": params["attack"], "health": params["health"]}]
    if scope == "two_distinct_shop_minions_random":
        targets = [m["id"] for m in draws.pick_distinct(shop, params["count"])]
        return [{"kind": kind, "targets": targets, "attack": params["attack"],
                 "health": params["health"]}] if targets else []
    if scope == "one_friendly_minion_random":
        return [{"kind": kind, "target": draws.pick(friendly)["id"],
                 "attack": params["attack"], "health": params["health"]}]
    raise VerificationError(f"{node['hero_id']}: unsupported effect")


def resolve(node: dict, event: dict) -> dict:
    if event.get("simultaneous_deaths"):
        raise VerificationError("unknown_simultaneous_death_order")
    if event.get("exact_mode"):
        raise VerificationError("unknown_hero_server_behavior")
    for side in ("friendly", "enemy", "shop"):
        require(len(event.get(side, [])) <= 7, f"{side}_exceeds_seven_slots")
    draws = Draws(event.get("draws", []))
    trigger = event["event"]
    if node["hero_id"] == "TB_BaconShop_HERO_12" and trigger == "round_start":
        require(type(event.get("round")) is int and event["round"] >= 1, "invalid_round")
        tribe = node["params"]["tribe_cycle"][(event["round"] - 1) % 4]
        return {"active": True, "coin_payment": 0, "hero_damage": 0,
                "scheduled": None, "actions": [{"kind": "set_active_tribe", "tribe": tribe}]}
    deferred_resolution = (node["activation"] == "button" and
                           node["resolution_trigger"] in DEFERRED and
                           trigger == node["resolution_trigger"] and event.get("armed") is True)
    if trigger != node["trigger"] and not deferred_resolution:
        return empty()
    if deferred_resolution and node["resolution_trigger"] == "next_battlecry_this_round":
        require(type(event.get("round")) is int and type(event.get("armed_round")) is int,
                "battlecry_round_missing")
        if event["round"] != event["armed_round"]:
            return empty()
    if node["activation"] == "button" and not deferred_resolution:
        coins = event.get("coins")
        require(type(coins) is int and coins >= 0, "invalid_coin_balance")
        if coins < node["coin_cost"] or not has_button_target(node, event):
            return empty()
        if node["resolution_trigger"] in DEFERRED:
            return {"active": True, "coin_payment": node["coin_cost"],
                    "hero_damage": node["health_damage"],
                    "scheduled": node["resolution_trigger"], "actions": []}
    actions = actions_for(node, event, draws)
    require(draws.used == len(draws.indexes), "unused_draw_indexes")
    return {"active": True,
            "coin_payment": node["coin_cost"] if node["activation"] == "button" and not deferred_resolution else 0,
            "hero_damage": node["health_damage"] if node["activation"] == "button" and not deferred_resolution else 0,
            "scheduled": None, "actions": actions}


def verify_client(path: Path, data: dict, nodes: list[dict], heroes: dict[str, dict]) -> None:
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == data["source"]["carddefs_sha256"],
            "CardDefs build hash drift")
    entities = {entity.get("CardID"): entity for entity in ET.fromstring(raw)}
    for node in nodes:
        hero_id, power_id = node["hero_id"], node["power_id"]
        hero, power = entities[hero_id], entities[power_id]
        hero_tags = {tag.get("name"): tag for tag in hero.findall("Tag")}
        tags = {tag.get("name"): tag for tag in power.findall("Tag")}
        require(hero_tags["HERO_POWER"].get("value") == power.get("ID"),
                f"{hero_id}: hero-power link drift")
        require(hero_tags["CARDNAME"].findtext("zhCN") == heroes[hero_id]["hero_name_zh"],
                f"{hero_id}: hero name drift")
        client_cost = int(tags["COST"].get("value")) if "COST" in tags else None
        expected_cost = node["coin_cost"] if heroes[hero_id]["power_cost"] is not None else None
        require(client_cost == expected_cost, f"{power_id}: coin cost drift")
        face = tags["CARDTEXT"].findtext("zhCN").replace("\n", "")
        require(all(marker in face for marker in node["face_markers"]),
                f"{power_id}: effect marker absent from client text")
        require(("被动英雄技能" in face) == (node["activation"] == "passive")
                or hero_id == "TB_BaconShop_HERO_38", f"{power_id}: passive/active label drift")
    for cid in ["TB_BaconShop_HP_008a", "TB_BaconShop_HP_017e", "TB_BaconShop_HP_033t",
                "TB_BaconShop_HP_038t", "TB_BaconShop_HP_041b", "TB_BaconShop_HP_041c",
                "TB_BaconShop_HP_041d", "TB_BaconShop_HP_041e"]:
        require(cid in entities, f"{cid}: auxiliary entity absent")
    aux_markers = {
        "TB_BaconShop_HP_008a": ("本回合", "1枚铸币"),
        "TB_BaconShop_HP_017e": ("亡语", "1/1的鱼人"),
        "TB_BaconShop_HP_033t": ("机械", "恶魔", "鱼人", "野兽"),
        "TB_BaconShop_HP_038t": ("友方野兽", "+1/+1"),
        "TB_BaconShop_HP_041e": ("+1/+2",),
    }
    for cid, markers in aux_markers.items():
        tags = {tag.get("name"): tag for tag in entities[cid].findall("Tag")}
        face = tags["CARDTEXT"].findtext("zhCN")
        require(all(marker in face for marker in markers), f"{cid}: auxiliary text drift")
    variant_tribes = {"TB_BaconShop_HP_041a": "野兽", "TB_BaconShop_HP_041b": "机械",
                      "TB_BaconShop_HP_041c": "鱼人", "TB_BaconShop_HP_041d": "恶魔"}
    for cid, tribe_zh in variant_tribes.items():
        tags = {tag.get("name"): tag for tag in entities[cid].findall("Tag")}
        face = tags["CARDTEXT"].findtext("zhCN")
        require(tribe_zh in face and "+1/+2" in face and "每回合切换类型" in face,
                f"{cid}: Rat King variant drift")
    token_tags = {tag.get("name"): tag for tag in entities["TB_BaconShop_HP_033t"].findall("Tag")}
    require(int(token_tags["ATK"].get("value")) == int(token_tags["HEALTH"].get("value")) == 1,
            "Curator token body drift")
    all_tribe_tags = {tag.get("name"): tag for tag in entities["GIL_681"].findall("Tag")}
    require(token_tags["CARDRACE"].get("value") == all_tribe_tags["CARDRACE"].get("value"),
            "Curator token all-tribe tag drift")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carddefs", type=Path, help="local pinned build-35747 CardDefs.xml")
    args = parser.parse_args()
    data = load("historical-hero-power-nodes.json")
    index = load("historical-hero-candidates.json")
    require(data["build"] == index["build"] == 35747 and
            data["mode"] == "reference_2019_launch_week" and data["unverified"] is True,
            "hero reference boundary drift")
    require(all(value == "unknown" for value in data["historical_unknown"].values()),
            "historical unknown was promoted")
    require(set(data["auxiliary_effects"]) == {"TB_BaconShop_HP_008a", "TB_BaconShop_HP_017e",
            "TB_BaconShop_HP_033t", "TB_BaconShop_HP_038t", "TB_BaconShop_HP_041e"},
            "auxiliary effect inventory drift")
    heroes = {row["hero_id"]: row for row in index["rows"]}
    expected = {cid for cid, row in heroes.items() if row["launch_eligibility"] == "inferred_launch_24"}
    nodes = data["nodes"]
    by_id = {node["hero_id"]: node for node in nodes}
    require(len(nodes) == len(by_id) == len(expected) == 24 and by_id.keys() == expected,
            "24 inferred-launch hero inventory drift")
    for cid, node in by_id.items():
        row = heroes[cid]
        require(node["power_id"] == row["power_id"], f"{cid}: power identity drift")
        require(node["coin_cost"] == (row["power_cost"] or 0), f"{cid}: power cost drift")
        require(node["health_damage"] == (3 if cid == "TB_BaconShop_HERO_25" else 0),
                f"{cid}: health payment drift")
        require(node["activation"] in {"button", "passive"} and
                node["resolution_trigger"] in {"immediate", *DEFERRED},
                f"{cid}: invalid trigger definition")
    if args.carddefs:
        verify_client(args.carddefs, data, nodes, heroes)
    vectors = load(data["vectors_file"])["vectors"]
    require(len(vectors) == len({case["id"] for case in vectors}), "duplicate hero vector id")
    require({case["hero_id"] for case in vectors if case["id"].endswith("-BASE")} == expected,
            "missing hero baseline vector")
    for case in vectors:
        try:
            actual = resolve(by_id[case["hero_id"]], case["input"])
        except VerificationError as exc:
            require(case.get("expected_error") == str(exc),
                    f"{case['id']}: unexpected error {exc}")
        else:
            expected_result = case["expected"]
            require({"active", "actions"} <= expected_result.keys(), "incomplete hero expected result")
            require("expected_error" not in case and
                    all(actual.get(key) == value for key, value in expected_result.items()),
                    f"{case['id']}: expected {case.get('expected')}, got {actual}")
    print(f"PASS: {len(nodes)} inferred-launch hero power nodes, {len(vectors)} reference vectors; "
          "launch flags, target weights, secret and minion pools, event order remain unknown")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, KeyError, TypeError, ValueError, ET.ParseError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
