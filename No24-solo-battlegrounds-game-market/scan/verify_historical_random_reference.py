"""Resolve 16 random/discover cards in an explicitly NON-historical reference profile.

The supplied draw indexes are the output of a caller-owned uniform-index RNG.
No inferred result from this module is evidence of Blizzard's 35747 server.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from verify_historical_random_effect_shells import VerificationError, execute as shell_execute


ROOT = Path(__file__).resolve().parent
SUMMON_POOLS = {
    "BGS_025": "original_cost_1", "BGS_023": "original_cost_2",
    "BGS_024": "original_cost_4", "BGS_008": "deathrattle_candidates",
    "BGS_006": "legendary_candidates",
}
BOARD_TARGETS = {
    "OG_221", "BOT_606", "KAR_095", "BGS_002", "UNG_037",
    "GVG_027", "KAR_702", "BGS_009",
}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise VerificationError(message)


def read(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def tribe_matches(minion: dict, tribe: str) -> bool:
    return minion.get("race") in {tribe, "ALL"}


class Draws:
    def __init__(self, indexes: list[int]):
        self.indexes = indexes
        self.used = 0

    def pick(self, values: list):
        require(bool(values), "draw_from_empty_set")
        require(self.used < len(self.indexes), "draw_index_missing")
        index = self.indexes[self.used]
        require(type(index) is int and 0 <= index < len(values), "draw_index_out_of_bounds")
        self.used += 1
        return values[index]


def reference_pools(profile: dict) -> dict[str, list[str]]:
    simulator = read("historical-community-simulator-pools.json")
    require(simulator["simulator_commit"] == profile["sources"]["simulator_commit"],
            "simulator provenance drift")
    require(simulator["simulator_minion_info_sha256"] == profile["sources"]["simulator_minion_info_sha256"],
            "simulator source hash drift")
    rows = read("historical-card-pool.json")["rows"]
    require(len(rows) == 81, "shop reference inventory drift")
    shop = {row["normal_id"]: row for row in rows}
    pools = {}
    for key, entries in simulator["pools"].items():
        ids = [entry["id"] for entry in entries]
        require(len(ids) == len(set(ids)) and set(ids) <= shop.keys(), f"{key}: bad reference candidates")
        pools[key] = ids
    require({key: len(value) for key, value in pools.items()} == {
        "original_cost_1": 9, "original_cost_2": 10, "original_cost_4": 14,
        "deathrattle_candidates": 22, "legendary_candidates": 12,
    }, "simulator reference pool count drift")
    pools["zerus_transform"] = [row["normal_id"] for row in rows if row["normal_id"] != "BGS_029"]
    pools["discover_murloc"] = [row["normal_id"] for row in rows if row["client_race"] in {"MURLOC", "ALL"}]
    pools["adapt"] = profile["adapt_option_ids"]
    require(len(pools["zerus_transform"]) == 80 and len(pools["discover_murloc"]) == 9,
            "derived reference pool drift")
    require(len(pools["adapt"]) == len(set(pools["adapt"])) == 10,
            "adapt option list drift")
    return pools


def verify_adapt_entities(path: Path, profile: dict) -> None:
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == profile["sources"]["carddefs_sha256"],
            "pinned CardDefs hash drift")
    entities = {entity.get("CardID"): entity for entity in ET.fromstring(raw)}
    text_markers = {
        "UNG_999t2": ("亡语", "两个1/1"), "UNG_999t3": ("+3攻击力",),
        "UNG_999t4": ("+3生命值",), "UNG_999t5": ("无法成为法术或英雄技能",),
        "UNG_999t6": ("嘲讽",), "UNG_999t7": ("风怒",),
        "UNG_999t8": ("圣盾",), "UNG_999t10": ("潜行", "下个回合"),
        "UNG_999t13": ("剧毒",), "UNG_999t14": ("+1/+1",),
    }
    require(set(profile["adapt_option_ids"]) == set(text_markers) == set(profile["adapt_option_defs"]),
            "adapt option inventory drift")
    for cid, markers in text_markers.items():
        entity = entities[cid]
        tags = {tag.get("name"): tag for tag in entity.findall("Tag")}
        require(tags["CARDNAME"].findtext("zhCN") == profile["adapt_option_defs"][cid]["name_zh"],
                f"{cid}: option name drift")
        face = tags["CARDTEXT"].findtext("zhCN")
        require(all(marker in face for marker in markers), f"{cid}: option text drift")
    plant = {tag.get("name"): tag for tag in entities["UNG_999t2t1"].findall("Tag")}
    require(int(plant["ATK"].get("value")) == int(plant["HEALTH"].get("value")) == 1,
            "living spores token drift")


def offer(pool: list[str], draws: Draws, count: int = 3) -> list[str]:
    remaining = pool.copy()
    selected = []
    for _ in range(min(count, len(remaining))):
        choice = draws.pick(remaining)
        remaining.remove(choice)
        selected.append(choice)
    return selected


def resolve(node: dict, form: str, event: dict, profile: dict, pools: dict[str, list[str]]) -> dict:
    """Resolve one isolated event; simultaneous death batches remain unsupported."""
    require(form in {"normal", "golden"}, "invalid form")
    cid = node["normal_id"]
    friendly = copy.deepcopy(event.get("friendly", []))
    enemy = copy.deepcopy(event.get("enemy", []))
    require(len(friendly) <= 7 and len(enemy) <= 7, "board_exceeds_seven_slots")
    ids = [m["id"] for m in friendly + enemy]
    require(len(ids) == len(set(ids)), "duplicate_instance_id")
    adapted = dict(event)
    adapted["free_slots"] = 7 - len(friendly)
    adapted["friendly_murloc_count"] = sum(tribe_matches(m, "MURLOC") for m in friendly)
    if node["normal_id"] == "BGS_020":
        adapted["other_friendly_murloc_present"] = any(
            m["id"] != event.get("source_id") and tribe_matches(m, "MURLOC") for m in friendly)
    shell = shell_execute(node, form, adapted)  # Exact mode still fails closed here.
    if not shell["attempts"]:
        return {"active": False, "requests": 0, "draws_used": 0, "actions": []}
    draws = Draws(event.get("draws", []))
    if "candidate_overrides" in event:
        pools = dict(pools)
        for key, ids in event["candidate_overrides"].items():
            require(key in pools and len(ids) == len(set(ids)) and set(ids) <= set(pools[key]),
                    "invalid_reference_candidate_override")
            pools[key] = ids
    actions = []
    attempts = shell["attempts"]
    number = shell["number"]

    if cid in SUMMON_POOLS:
        pool = pools[SUMMON_POOLS[cid]]
        for _ in range(attempts):
            if len(friendly) == 7 or not pool:
                break
            card = draws.pick(pool)  # Independent draws with replacement; no shop stock decrement.
            serial = len(actions) + 1
            while f"generated-{serial}" in ids:
                serial += 1
            instance_id = f"generated-{serial}"
            ids.append(instance_id)
            actions.append({"op": "summon", "card_id": card, "instance_id": instance_id})
            friendly.append({"id": actions[-1]["instance_id"]})
    elif cid == "BGS_029":
        pool = pools["zerus_transform"]
        if pool:
            actions.append({"op": "transform_in_hand", "card_id": draws.pick(pool), "form": form})
    elif cid == "BGS_020":
        pool = pools["discover_murloc"]
        choices = event.get("choices", [])
        hand_slots = event.get("hand_slots", 10)
        require(type(hand_slots) is int and 0 <= hand_slots <= 10, "invalid_hand_slots")
        for round_index in range(attempts):
            options = offer(pool, draws)
            if not options:
                break
            require(round_index < len(choices), "discover_choice_missing")
            choice = choices[round_index]
            require(type(choice) is int and 0 <= choice < len(options), "invalid_discover_choice")
            acquired = hand_slots > 0
            hand_slots -= int(acquired)
            actions.append({"op": "discover", "options": options,
                            "chosen": options[choice], "acquired": acquired})
    elif cid == "BGS_031":
        targets = [m["id"] for m in friendly if tribe_matches(m, "MURLOC")]
        choices = event.get("choices", [])
        if targets:
            for round_index in range(attempts):
                options = offer(pools["adapt"], draws)
                require(round_index < len(choices), "adapt_choice_missing")
                choice = choices[round_index]
                require(type(choice) is int and 0 <= choice < len(options), "invalid_adapt_choice")
                actions.append({"op": "adapt_all", "options": options,
                                "chosen": options[choice], "targets": targets})
    elif cid in BOARD_TARGETS:
        for tribe in node.get("tribes", [None] * attempts):
            if cid in {"BOT_606", "BGS_002"}:
                eligible = enemy
            elif cid == "GVG_027":
                eligible = [m for m in friendly if m["id"] != event.get("source_id")
                            and tribe_matches(m, "MECHANICAL")]
            elif cid == "OG_221":
                eligible = [m for m in friendly if m["id"] != event.get("source_id")
                            and not m.get("divine_shield", False)]
            elif cid == "UNG_037":
                eligible = [m for m in friendly if m["id"] != event.get("source_id")]
            else:
                eligible = [m for m in friendly if tribe_matches(m, tribe)]
            if not eligible:
                continue
            target = eligible[0] if cid == "GVG_027" else draws.pick(eligible)
            if cid in {"BOT_606", "BGS_002"}:
                require(type(target.get("health")) is int and target["health"] > 0,
                        "invalid_enemy_health")
                shielded = target.get("divine_shield", False)
                if shielded:
                    target["divine_shield"] = False
                else:
                    target["health"] -= number
                died = not shielded and target["health"] <= 0
                actions.append({"op": "damage", "target": target["id"], "amount": number,
                                "absorbed_by_shield": shielded, "died": died})
                if died:
                    enemy.remove(target)
            elif cid == "OG_221":
                target["divine_shield"] = True
                actions.append({"op": "grant_divine_shield", "target": target["id"]})
            else:
                actions.append({"op": "buff", "target": target["id"],
                                "attack": number, "health": number,
                                "tribe_step": tribe})
    else:
        raise VerificationError(f"{cid}: unhandled card")

    require(draws.used == len(draws.indexes), "unused_draw_indexes")
    return {"active": True, "requests": attempts, "draws_used": draws.used, "actions": actions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carddefs", type=Path, help="pinned build-35747 CardDefs.xml")
    args = parser.parse_args()
    profile = read("historical-random-reference.json")
    shells = read("historical-random-effect-shells.json")
    require(profile["mode"] == "reference_2019_launch_week" and profile["build"] == 35747,
            "profile version drift")
    require(profile["unverified"] is True and profile["evidence_grade"] ==
            "reference_design_not_original_server_behavior", "reference label drift")
    require(profile["historical_unknown"] == shells["historical_unknown"],
            "historical unknown fields were promoted")
    require(set(profile["adapt_option_ids"]) == set(profile["adapt_option_defs"])
            and len(profile["adapt_option_ids"]) == 10, "adapt option list drift")
    if args.carddefs:
        verify_adapt_entities(args.carddefs, profile)
    by_id = {node["normal_id"]: node for node in shells["nodes"]}
    require(set(profile["node_policies"]) == set(by_id) and len(by_id) == 16,
            "16-card reference inventory drift")
    pools = reference_pools(profile)
    for cid, policy in profile["node_policies"].items():
        kind = by_id[cid]["kind"]
        expected_source = (SUMMON_POOLS.get(cid) or {
            "transform_in_hand": "zerus_transform", "discover_murloc": "discover_murloc",
            "adapt_all_friendly_murlocs": "adapt", "damage_enemy": "enemy_board",
        }.get(kind, "friendly_board"))
        expected_selector = ("leftmost" if cid == "GVG_027" else
                             "uniform_index_each_tribe" if kind == "buff_each_tribe" else
                             "three_distinct_options_per_offer" if kind in
                             {"discover_murloc", "adapt_all_friendly_murlocs"} else "uniform_index")
        require(policy == {"kind": kind, "candidate_source": expected_source,
                           "selector": expected_selector}, f"{cid}: reference policy drift")
    vector_doc = read(profile["vectors_file"])
    require(vector_doc["evidence_grade"] == "reference_design_acceptance_only_not_original_2019_replay",
            "vector evidence label drift")
    vectors = vector_doc["vectors"]
    require(len(vectors) == len({v["id"] for v in vectors}) == 33, "reference vector count or ID drift")
    require({v["normal_id"] for v in vectors if v["id"].endswith("-BASE")} == set(by_id),
            "missing baseline reference vector")
    checked = 0
    for vector in vectors:
        node = by_id[vector["normal_id"]]
        for form in ("normal", "golden"):
            event = {**vector["input"], **vector.get("input_by_form", {}).get(form, {})}
            try:
                actual = resolve(node, form, event, profile, pools)
            except VerificationError as exc:
                require(vector.get("expected_error") == str(exc),
                        f"{vector['id']} {form}: unexpected error {exc}")
            else:
                require("expected_error" not in vector, f"{vector['id']} {form}: exact gate bypassed")
                expected = vector["expected_by_form"][form]
                require({"active", "requests", "actions"} <= expected.keys(), "incomplete reference expected result")
                require(all(actual.get(key) == value for key, value in expected.items()),
                        f"{vector['id']} {form}: expected {expected}, got {actual}")
            checked += 1
    print(f"PASS: 16 reference-resolved cards, {checked} normal/golden acceptance vectors; "
          "historical candidate eligibility, weight, and event order remain unknown")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, KeyError, TypeError, ValueError, ET.ParseError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
