"""Run count/identity/slot/snapshot vectors for 15 fixed-token card effects.

With --carddefs, verify the pinned build-35747 parent and token card faces.
These are reference transitions; client resources do not prove server emission IDs.
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
RACES = {"20": "BEAST", "17": "MECHANICAL", "14": "MURLOC", "15": "DEMON"}
COUNT_WORDS = {1: ("一个", "一头", "一只", "1个"), 2: ("两个", "两只"), 3: ("三个", "三台")}


class VerificationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def text_without_markup(value: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", value))


def check_card_faces(node: dict) -> None:
    count = node["count"]
    for form in ("normal", "golden"):
        text = text_without_markup(node["client_text_zh"][form])
        token = node["tokens"][form]
        require(f"{token['attack']}/{token['health']}" in text, f"{node['normal_id']} {form}: token stats absent from source text")
        if count["kind"] == "fixed":
            require(any(word in text for word in COUNT_WORDS[count["value"]]), f"{node['normal_id']} {form}: token count absent from source text")
        else:
            require("数量等同于该随从的攻击力" in text, f"{node['normal_id']} {form}: attack-count rule absent")
        trigger_marker = {"battlecry": "战吼", "deathrattle": "亡语", "on_source_damaged": "受到伤害"}[node["trigger"]]
        require(trigger_marker in text, f"{node['normal_id']} {form}: trigger absent from source text")
        if node["destination"] == "opponent":
            require("对手" in text, f"{node['normal_id']} {form}: opposing destination absent")
        for keyword, marker in (("magnetic", "磁力"), ("taunt", "嘲讽")):
            if keyword in node["parent_keywords"]:
                require(marker in text, f"{node['normal_id']} {form}: parent keyword absent")
        if "taunt" in token["keywords"]:
            require("嘲讽" in text, f"{node['normal_id']} {form}: token taunt absent")


def execute(node: dict, case: dict, board_limit: int) -> dict:
    data = case["input"]
    trigger = node["trigger"]
    phase = "recruit" if trigger == "battlecry" else "combat"
    event = {"battlecry": "play_from_hand", "deathrattle": "source_died", "on_source_damaged": "source_damaged"}[trigger]
    require(data["phase"] == phase and data["event"] == event, f"{case['id']}: wrong event fixture")
    friend, opponent = data["friendly_board_count_before"], data["opponent_board_count_before"]
    require(1 <= friend <= board_limit and 0 <= opponent <= board_limit, f"{case['id']}: board count invalid")
    if data["other_deaths_same_event"]:
        raise VerificationError("unverified_simultaneous_death_order")
    if trigger == "on_source_damaged" and not data["source_survives_hit"]:
        raise VerificationError("unverified_lethal_damage_order")
    if trigger == "on_source_damaged" and data["effective_damage_taken"] <= 0:
        requested = 0
    elif node["count"]["kind"] == "fixed":
        requested = node["count"]["value"]
    else:
        requested = max(0, data["source_attack_at_death"])
    recipient = node["destination"]
    own_after_source = friend - 1 if trigger == "deathrattle" else friend
    recipient_before_summon = own_after_source if recipient == "friendly" else opponent
    summoned = min(requested, board_limit - recipient_before_summon)
    token = node["tokens"][case["form"]]
    token_instances = [
        {
            "definition_id": token["id"],
            "attack": token["attack"],
            "health": token["health"],
            "race": token["race"],
            "keywords": token["keywords"],
            "premium": token["premium"],
            "origin": "recruit_token" if phase == "recruit" else "combat_token",
        }
        for _ in range(summoned)
    ]
    friend_after = own_after_source + (summoned if recipient == "friendly" else 0)
    opponent_after = opponent + (summoned if recipient == "opponent" else 0)
    return {
        "requested_count": requested,
        "summoned_count": summoned,
        "summon_owner": recipient,
        "token_instances": token_instances,
        "friendly_board_count_after_event": friend_after,
        "opponent_board_count_after_event": opponent_after,
        "recruit_friendly_count_after_resolution": friend_after if phase == "recruit" else data["recruit_snapshot_friendly_count"],
        "recruit_opponent_count_after_resolution": data["recruit_snapshot_opponent_count"],
    }


def verify_xml(path: Path, source: dict, nodes: list[dict]) -> None:
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == source["sha256"], "CardDefs XML does not match pinned build hash")
    entities = {entity.get("CardID"): entity for entity in ET.fromstring(raw)}
    for node in nodes:
        for form, parent_id in (("normal", node["normal_id"]), ("golden", node["golden_id"])):
            require(parent_id in entities, f"{parent_id}: parent absent from XML")
            parent_tags = {tag.get("name"): tag for tag in entities[parent_id].findall("Tag")}
            require(parent_tags["CARDTEXT"].findtext("zhCN") == node["client_text_zh"][form], f"{parent_id}: parent card face drift")
            token = node["tokens"][form]
            token_id = token["id"]
            require(token_id in entities, f"{token_id}: token absent from XML")
            tags = {tag.get("name"): tag for tag in entities[token_id].findall("Tag")}
            require(tags["CARDNAME"].findtext("zhCN") == token["name_zh"], f"{token_id}: token name drift")
            require(int(tags["ATK"].get("value")) == token["attack"], f"{token_id}: token attack drift")
            require(int(tags["HEALTH"].get("value")) == token["health"], f"{token_id}: token health drift")
            race_value = tags["CARDRACE"].get("value") if "CARDRACE" in tags else None
            require(RACES.get(race_value, "NONE") == token["race"], f"{token_id}: token race drift")
            premium = tags.get("PREMIUM").get("value") == "1" if "PREMIUM" in tags else False
            require(premium == token["premium"], f"{token_id}: token premium drift")
            card_text = tags["CARDTEXT"].findtext("zhCN") if "CARDTEXT" in tags else ""
            require(("taunt" in token["keywords"]) == ("嘲讽" in card_text), f"{token_id}: token taunt drift")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carddefs", type=Path, help="local copy of pinned build-35747 CardDefs.xml")
    args = parser.parse_args()
    data = load("historical-fixed-token-nodes.json")
    cards = load("historical-card-pool.json")
    earlier = load("historical-effect-nodes.json")
    rules = load("historical-rule-parameters.json")
    require(data["mode"] == rules["rule_set"] == "reference_2019_launch_week", "rule set mismatch")
    require(data["build"] == rules["build"] == int(cards["build"].split(".")[-1]) == 35747, "build mismatch")
    require(rules["dynamic_generation"]["exact_pool_membership"] == "unknown", "historical generation pool was guessed")
    require(data["reference_rules"]["same_event_death_order"] == "unknown", "historical death order was guessed")
    require(data["reference_rules"]["historical_summon_insert_position"] == "unknown", "historical insertion position was guessed")
    require(data["reference_rules"]["deathrattle_source_frees_own_slot_first"], "reference deathrattle slot rule drift")
    require(data["reference_rules"]["combat_summons_do_not_persist_to_recruit_snapshot"], "combat snapshot guard absent")
    board_limit = data["reference_rules"]["board_limit"]
    require(board_limit == 7, "unexpected board limit")
    rows = {row["normal_id"]: row for row in cards["rows"]}
    nodes = data["nodes"]
    by_id = {node["normal_id"]: node for node in nodes}
    expected_group = set(earlier["typed_elsewhere"]["fixed_token_or_capacity"])
    require(len(nodes) == len(by_id) == len(expected_group) == data["coverage"]["fixed_token_group"] == 15, "fixed-token coverage drift")
    require(by_id.keys() == expected_group, "fixed-token card IDs differ from prior coverage audit")
    require(data["coverage"]["parent_forms"] == 30, "parent form count drift")
    require(data["coverage"]["token_definition_ids"] == len({token["id"] for node in nodes for token in node["tokens"].values()}) == 29, "token ID count drift")
    require(data["coverage"]["historical_generation_chain_directly_verified"] == 0, "unproven generation chain was upgraded")
    require(by_id["EX1_577"]["tokens"]["normal"]["id"] == by_id["EX1_577"]["tokens"]["golden"]["id"] == "EX1_finkle", "Finkle identity drift")
    require(by_id["LOOT_368"]["tokens"]["normal"]["id"] == "CS2_065" and "CS2_065" in rows, "shared Voidwalker definition drift")
    require("ambiguous" in by_id["EX1_556"]["token_identity_grade"], "Damaged Golem alias caveat lost")
    require("needs_generation_chain" in by_id["UNG_010"]["token_identity_grade"], "Murloc token caveat lost")
    ledger = (ROOT / "historical-token-pool.md").read_text(encoding="utf-8")
    for cid, node in by_id.items():
        row = rows[cid]
        require(row["golden_id"] == node["golden_id"] and row["golden_evidence"] == "client_35747", f"{cid}: parent golden identity drift")
        require(row["normal_name_zh"] == node["name_zh"], f"{cid}: parent name drift")
        require(node["count"]["kind"] in ("fixed", "source_attack_at_death"), f"{cid}: unsupported count rule")
        if node["count"]["kind"] == "fixed":
            require(node["count"]["value"] in COUNT_WORDS, f"{cid}: invalid fixed count")
        else:
            require(node["count"]["value"] is None, f"{cid}: attack-count rule has fixed value")
        require(node["destination"] in ("friendly", "opponent"), f"{cid}: invalid destination")
        require(node["token_identity_grade"] != "server_generation_direct", f"{cid}: token identity overclaimed")
        require(node["evidence"]["effect_to_token_id_chain"] == "inference_from_client_name_stats_id", f"{cid}: token link grade drift")
        check_card_faces(node)
        ledger_line = next((line for line in ledger.splitlines() if f"`{cid}`" in line and line.startswith("|")), "")
        require(ledger_line and all(token["id"] in ledger_line for token in node["tokens"].values()), f"{cid}: token pool cross-reference drift")

    cases = data["vectors"]
    require(len({case["id"] for case in cases}) == len(cases), "duplicate vector ID")
    require({(case["normal_id"], case["form"]) for case in cases if case["id"].endswith("BASE")} == {(cid, form) for cid in by_id for form in ("normal", "golden")}, "a parent form lacks baseline vector")
    for case in cases:
        require(case["normal_id"] in by_id and case["form"] in ("normal", "golden"), f"{case['id']}: invalid parent identity")
        try:
            actual = execute(by_id[case["normal_id"]], case, board_limit)
        except VerificationError as exc:
            require(case.get("expected_error") == str(exc), f"{case['id']}: unexpected error {exc}")
        else:
            require("expected_error" not in case, f"{case['id']}: expected unknown guard did not fire")
            require(actual == case["expected"], f"{case['id']}: expected {case['expected']}, got {actual}")

    if args.carddefs:
        verify_xml(args.carddefs, data["client_source"], nodes)
    print(f"PASS: {len(nodes)} parent cards, {len(cases)} fixed-token vectors, 29 client token IDs; "
          + ("pinned XML verified" if args.carddefs else "stored card faces verified")
          + "; generation-chain IDs remain inferred")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, KeyError, TypeError, ValueError, ET.ParseError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
