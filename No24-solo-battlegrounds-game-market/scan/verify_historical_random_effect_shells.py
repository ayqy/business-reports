"""Verify the 16 unresolved random cards' bounded trigger and quantity shells.

The output is an effect intent, never a selected card, target, option, or RNG
result. Exact historical resolution must fail closed until independent evidence
establishes candidate eligibility, weighting, and event order.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
SUMMON_KINDS = {"summon_original_cost", "summon_deathrattle", "summon_legendary"}
TRIBE_NAMES = {"BEAST": "野兽", "DRAGON": "龙", "MURLOC": "鱼人",
               "MECHANICAL": "机械", "DEMON": "恶魔"}
KNOWN_KINDS = {
    "grant_divine_shield", "summon_original_cost", "damage_enemy",
    "buff_each_tribe", "transform_in_hand", "buff_one_friendly",
    "buff_other_mech", "discover_murloc", "adapt_all_friendly_murlocs",
    "summon_deathrattle", "summon_legendary",
}
EXPECTED_FILTERS = {
    "OG_221": "other_friendly_minion",
    "BGS_025": "original_mana_cost_1",
    "BOT_606": "enemy_minion",
    "KAR_095": "one_each_friendly_BEAST_DRAGON_MURLOC",
    "BGS_023": "original_mana_cost_2",
    "BGS_029": "minion_card",
    "BGS_002": "enemy_minion",
    "UNG_037": "other_friendly_minion",
    "GVG_027": "other_friendly_mech",
    "KAR_702": "one_each_friendly_BEAST_DRAGON_MURLOC",
    "BGS_024": "original_mana_cost_4",
    "BGS_020": "murloc_card",
    "BGS_009": "one_each_friendly_MECHANICAL_MURLOC_DEMON_BEAST",
    "BGS_031": "all_friendly_murlocs",
    "BGS_008": "deathrattle_minion",
    "BGS_006": "legendary_minion",
}
UNKNOWN_FIELDS = {
    "dynamic_pool_eligibility", "dynamic_pool_weights", "board_target_selection",
    "multi_tribe_overlap_resolution", "repeated_damage_target_reselection",
    "discover_options", "adapt_options", "zerus_transform_pool_and_tick_phase",
    "simultaneous_death_event_order",
}


class VerificationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def plain(value: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", value))


def check_cardface(node: dict, form: str) -> None:
    face = plain(node["client_text_zh"][form])
    kind = node["kind"]
    count = node["forms"][form]["attempts"]
    number = node["forms"][form]["number"]
    require(("随机" in face) == node["random_word_in_face"], f"{node['normal_id']} {form}: random wording drift")
    trigger = node["trigger"]
    marker = {
        "source_died": "亡语",
        "friendly_demon_died": "友方恶魔死亡",
        "played_from_hand": "战吼",
        "own_turn_end": "回合结束",
        "held_round_tick": "每个回合",
    }[trigger]
    require(marker in face, f"{node['normal_id']} {form}: trigger wording drift")
    if kind == "grant_divine_shield":
        require("圣盾" in face and ("一个" if count == 1 else "两个") in face, "divine shield count drift")
    elif kind == "summon_original_cost":
        require(f"法力值消耗为（{number}）点" in face
                and ("一个" if count == 1 else "两个") in face, "original cost summon face drift")
        require(node["target_filter"] == f"original_mana_cost_{number}", "cost filter drift")
    elif kind == "damage_enemy":
        require(f"造成{number}点伤害" in face and "敌方随从" in face, "damage face drift")
        if node["normal_id"] == "BOT_606":
            require((count == 2) == ("重复一次" in face), "Bombot repeat count drift")
        else:
            require(count == 1, "Soul Juggler single-event count drift")
    elif kind == "buff_each_tribe":
        require(f"+{number}/+{number}" in face and count == len(node["tribes"]), "tribe buff amount drift")
        require(all(TRIBE_NAMES[tribe] in face for tribe in node["tribes"]), "tribe fan-out drift")
    elif kind == "transform_in_hand":
        require("在你的手牌中" in face and "变成一张随从牌" in face and count == 1, "Zerus face drift")
    elif kind == "buff_one_friendly":
        require(f"+{number}/+{number}" in face and "一个友方随从" in face and count == 1, "single buff face drift")
    elif kind == "buff_other_mech":
        require(f"+{number}/+{number}" in face and "另一个友方机械" in face and count == 1, "Iron Sensei face drift")
    elif kind == "discover_murloc":
        require("如果你控制其他任何鱼人" in face and "发现" in face
                and ("一张" if count == 1 else "两张") in face, "Murloc discover face drift")
    elif kind == "adapt_all_friendly_murlocs":
        require("进化你所有的鱼人" in face and (count == 2) == ("两次" in face), "Megasaur adapt count drift")
    elif kind == "summon_deathrattle":
        require("亡语随从" in face and ("两个" if count == 2 else "四个") in face, "Ghastcoiler count drift")
    elif kind == "summon_legendary":
        require("传说随从" in face and ("一个" if count == 1 else "两个") in face, "Sneed count drift")
    else:
        raise VerificationError(f"unsupported kind: {kind}")


def exact_error(kind: str) -> str:
    if kind in SUMMON_KINDS:
        return "unknown_pool_eligibility"
    if kind == "discover_murloc":
        return "unknown_discover_options"
    if kind == "adapt_all_friendly_murlocs":
        return "unknown_adapt_options"
    if kind == "transform_in_hand":
        return "unknown_transform_pool_and_tick_phase"
    return "unknown_board_target_selection"


def execute(node: dict, form: str, event: dict) -> dict:
    if event.get("simultaneous_deaths", False):
        raise VerificationError("unknown_simultaneous_death_event_order")
    if "free_slots" in event:
        require(0 <= event["free_slots"] <= 7, "free slots outside seven-slot board")
    active = event["event"] == node["trigger"]
    if node["trigger"] in {"friendly_demon_died", "own_turn_end", "played_from_hand"}:
        active = active and event.get("source_present", True)
    if node["kind"] == "transform_in_hand":
        active = active and event.get("zone") == "hand"
    if node["kind"] == "discover_murloc":
        active = active and event.get("other_friendly_murloc_present", False)
    if not active:
        return {"attempts": 0, "number": None, "capacity_bound": None,
                "target_count": None, "selection_resolved": False}
    if event.get("exact_mode", False):
        raise VerificationError(exact_error(node["kind"]))
    params = node["forms"][form]
    capacity = min(params["attempts"], event["free_slots"]) if node["kind"] in SUMMON_KINDS else None
    targets = event["friendly_murloc_count"] if node["kind"] == "adapt_all_friendly_murlocs" else None
    if targets is not None:
        require(0 <= targets <= 7, "murloc count outside seven-slot board")
    return {"attempts": params["attempts"], "number": params["number"],
            "capacity_bound": capacity, "target_count": targets,
            "selection_resolved": False}


def verify_xml(path: Path, data: dict, nodes: list[dict], rows: dict) -> None:
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == data["client_source"]["sha256"], "pinned XML hash mismatch")
    entities = {entity.get("CardID"): entity for entity in ET.fromstring(raw)}
    for node in nodes:
        row = rows[node["normal_id"]]
        for form, cid in (("normal", node["normal_id"]), ("golden", node["golden_id"])):
            require(cid in entities, f"{cid}: parent absent from XML")
            tags = {tag.get("name"): tag for tag in entities[cid].findall("Tag")}
            require(tags["CARDTEXT"].findtext("zhCN") == node["client_text_zh"][form], f"{cid}: card text drift")
            require(tags["CARDNAME"].findtext("zhCN") == node["name_zh"], f"{cid}: card name drift")
            require(int(tags["ATK"].get("value")) == row[f"{form}_attack"], f"{cid}: attack drift")
            require(int(tags["HEALTH"].get("value")) == row[f"{form}_health"], f"{cid}: health drift")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carddefs", type=Path, help="local build-35747 CardDefs.xml")
    args = parser.parse_args()
    data = load("historical-random-effect-shells.json")
    effects = load("historical-effect-nodes.json")
    cards = load("historical-card-pool.json")
    rules = load("historical-rule-parameters.json")
    require(data["mode"] == effects["mode"] == rules["rule_set"] == "reference_2019_launch_week", "mode drift")
    require(data["build"] == effects["build"] == rules["build"] == 35747, "build drift")
    require(data["client_source"] == effects["client_source"], "source hash drift")
    require(set(data["historical_unknown"]) == UNKNOWN_FIELDS
            and all(value == "unknown" for value in data["historical_unknown"].values()), "unknown-history guard drift")
    require(rules["dynamic_generation"]["exact_pool_membership"] == "unknown"
            and rules["dynamic_generation"]["weights"] == "unknown", "dynamic pool was upgraded without evidence")
    nodes = data["nodes"]
    by_id = {node["normal_id"]: node for node in nodes}
    expected_ids = set(effects["deferred"]["random_or_discover"])
    require(len(nodes) == len(by_id) == len(expected_ids) == data["coverage"]["parent_rows"] == 16, "16-card coverage drift")
    require(by_id.keys() == expected_ids and data["coverage"]["parent_forms"] == 32, "random card partition drift")
    require(by_id.keys() == EXPECTED_FILTERS.keys(), "filter review inventory drift")
    require(data["coverage"]["status"] == "typed_intent_only", "partial shell was marked fully resolved")
    require(data["reference_scope"] == {
        "attempts_are_requests_not_successful_results": True,
        "original_mana_cost_interpretation": "inference_from_mana_cost_wording_and_client_tags",
        "exact_2019_selection": "fail_closed",
    }, "intent-only reference boundary drift")
    rows = {row["normal_id"]: row for row in cards["rows"]}
    require(effects["partial_shells"]["random_or_discover_file"] == "historical-random-effect-shells.json",
            "partial shell reference drift")
    for cid, node in by_id.items():
        row = rows[cid]
        require(node["golden_id"] == row["golden_id"] and row["golden_evidence"] == "client_35747",
                f"{cid}: golden identity drift")
        require(node["name_zh"] == row["normal_name_zh"], f"{cid}: name drift")
        require(node["kind"] in KNOWN_KINDS, f"{cid}: unsupported kind")
        require(node["target_filter"] == EXPECTED_FILTERS[cid], f"{cid}: target or pool filter drift")
        require(node["evidence"] == {"card_face": "H04_client_direct", "resolution": "intent_only"},
                f"{cid}: source grade drift")
        require(set(node["forms"]) == set(node["client_text_zh"]) == {"normal", "golden"},
                f"{cid}: form mismatch")
        for form in ("normal", "golden"):
            params = node["forms"][form]
            require(isinstance(params["attempts"], int) and params["attempts"] >= 1,
                    f"{cid}: invalid attempt count")
            require(params["number"] is None or isinstance(params["number"], int) and params["number"] >= 1,
                    f"{cid}: invalid face number")
            check_cardface(node, form)
    require(by_id["GVG_027"]["random_word_in_face"] is False
            and "随机" not in plain(by_id["GVG_027"]["client_text_zh"]["normal"]),
            "Iron Sensei's unstated random selector was promoted to direct evidence")
    vectors = data["vectors"]
    require(len(vectors) == len({case["id"] for case in vectors}), "duplicate vector ID")
    require(len(vectors) * 2 == data["coverage"]["form_vectors"] == 66, "form vector count drift")
    require({case["normal_id"] for case in vectors if case["id"].endswith("-BASE")} == expected_ids,
            "a random card lacks a baseline vector")
    for case in vectors:
        require(case["normal_id"] in by_id, f"{case['id']}: card absent from partition")
        for form in ("normal", "golden"):
            try:
                actual = execute(by_id[case["normal_id"]], form, case["input"])
            except VerificationError as exc:
                require(case.get("expected_error") == str(exc),
                        f"{case['id']} {form}: unexpected error {exc}")
            else:
                require("expected_error" not in case, f"{case['id']} {form}: unknown gate failed")
                if case.get("expected_inactive"):
                    require(actual["attempts"] == 0 and not actual["selection_resolved"],
                            f"{case['id']} {form}: should be inactive")
                else:
                    expected = case["expected_by_form"][form]
                    require(all(actual[key] == value for key, value in expected.items()),
                            f"{case['id']} {form}: expected {expected}, got {actual}")
                    require(actual["selection_resolved"] is False,
                            f"{case['id']} {form}: unknown selection was resolved")
    if args.carddefs:
        verify_xml(args.carddefs, data, nodes, rows)
    print(f"PASS: {len(nodes)} random/discover card shells, {len(vectors) * 2} form vectors; "
          + ("pinned client XML verified" if args.carddefs else "stored faces verified")
          + "; candidate and target resolution remain unknown")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, KeyError, TypeError, ValueError, ET.ParseError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
