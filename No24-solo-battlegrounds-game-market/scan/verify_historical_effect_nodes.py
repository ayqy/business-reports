"""Validate deterministic reference nodes against the 2019 card table and vectors.

Pass --carddefs with the pinned build-35747 XML to additionally compare every
captured normal/golden card face against its original client definition.
This interpreter is a specification oracle, not the original game engine.
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
TRIBE_ZH = {"BEAST": "野兽", "DEMON": "恶魔", "MECHANICAL": "机械", "MURLOC": "鱼人"}
FAMILIES = {
    "battlecry_target_buff": {"selected_one"},
    "battlecry_group_buff": {"all", "all_other", "adjacent"},
    "continuous_aura": {"all", "all_other", "adjacent"},
    "trigger_self_buff": {"self"},
    "trigger_summoned_buff": {"event_subject"},
}


class VerificationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", value))


def card_face_numbers(node: dict) -> None:
    for form in ("normal", "golden"):
        effect = node[f"{form}_effect"]
        text = clean_text(node["client_text_zh"][form])
        attack, health = effect["attack"], effect["health"]
        if attack and health:
            require(f"+{attack}/+{health}" in text, f"{node['normal_id']} {form}: buff value absent from client text")
        elif attack:
            require(f"+{attack}攻击力" in text, f"{node['normal_id']} {form}: attack value absent from client text")
        elif health:
            require(f"+{health}生命值" in text, f"{node['normal_id']} {form}: health value absent from client text")
        else:
            raise VerificationError(f"{node['normal_id']} {form}: empty effect")
        if effect["grant_taunt"]:
            require("嘲讽" in text, f"{node['normal_id']} {form}: taunt keyword absent")
        if effect["hero_damage"]:
            require(f"{effect['hero_damage']}点伤害" in text, f"{node['normal_id']} {form}: hero damage absent")
        for tribe in (node["target"]["tribe"], node["event_tribe"]):
            if tribe:
                require(TRIBE_ZH[tribe] in text, f"{node['normal_id']} {form}: tribe predicate absent")
        if node["target"]["keyword"]:
            require("嘲讽" in text, f"{node['normal_id']} {form}: target keyword absent")
        if node["family"].startswith("battlecry"):
            require("战吼" in text, f"{node['normal_id']} {form}: battlecry marker absent")
        for keyword, marker in (("taunt", "嘲讽"), ("divine_shield", "圣盾")):
            if keyword in node["static_keywords"]:
                require(marker in text, f"{node['normal_id']} {form}: intrinsic keyword absent")


def select_targets(node: dict, data: dict) -> list[str]:
    board = data["board"]
    by_id = {unit["id"]: unit for unit in board}
    require(len(by_id) == len(board) and "source" in by_id, "invalid board fixture")
    source_position = next(i for i, unit in enumerate(board) if unit["id"] == "source")
    scope = node["target"]["scope"]
    if scope == "selected_one":
        selected = data["selected_id"]
        require(selected in by_id and selected != "source", "invalid_target")
        selected_units = [by_id[selected]]
    elif scope == "adjacent":
        selected_units = [unit for i, unit in enumerate(board) if abs(i - source_position) == 1]
    elif scope == "all_other":
        selected_units = [unit for unit in board if unit["id"] != "source"]
    elif scope == "all":
        selected_units = board
    elif scope == "self":
        selected_units = [by_id["source"]]
    elif scope == "event_subject":
        subject = data["event_subject_id"]
        require(subject in by_id and subject != "source", "invalid_event_subject")
        selected_units = [by_id[subject]]
    else:
        raise VerificationError(f"unsupported target scope {scope}")
    tribe, keyword = node["target"]["tribe"], node["target"]["keyword"]
    filtered = [
        unit["id"] for unit in selected_units
        if (tribe is None or unit["tribe"] in (tribe, "ALL"))
        and (keyword is None or unit[keyword])
    ]
    if scope == "selected_one":
        require(len(filtered) == 1, "invalid_target")
    return filtered


def execute(node: dict, case: dict) -> dict:
    data = case["input"]
    source_keywords = node["static_keywords"] if data["source_present"] else []
    if not data["source_present"] or data["event"] != node["event"]:
        return {"buffs": {}, "hero_health": data["hero_health"], "source_keywords": source_keywords}
    if node["event_tribe"] and data["event_tribe"] != node["event_tribe"]:
        return {"buffs": {}, "hero_health": data["hero_health"], "source_keywords": source_keywords}
    effect = node[f"{case['form']}_effect"]
    targets = select_targets(node, data)
    return {
        "buffs": {
            target: {
                "attack": effect["attack"],
                "health": effect["health"],
                "grant_taunt": effect["grant_taunt"],
            }
            for target in targets
        },
        "hero_health": data["hero_health"] - effect["hero_damage"],
        "source_keywords": source_keywords,
    }


def verify_xml(path: Path, source: dict, nodes: list[dict]) -> None:
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == source["sha256"], "CardDefs XML does not match pinned build hash")
    entities = {entity.get("CardID"): entity for entity in ET.fromstring(raw)}
    for node in nodes:
        for form, card_id in (("normal", node["normal_id"]), ("golden", node["golden_id"])):
            require(card_id in entities, f"{card_id}: absent from pinned client XML")
            card_text = next((tag for tag in entities[card_id].findall("Tag") if tag.get("name") == "CARDTEXT"), None)
            require(card_text is not None, f"{card_id}: client text absent")
            require(
                card_text.findtext("zhCN") == node["client_text_zh"][form],
                f"{card_id}: stored client text differs from pinned XML",
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carddefs", type=Path, help="local copy of the fixed build-35747 CardDefs.xml")
    args = parser.parse_args()
    data = load("historical-effect-nodes.json")
    cards = load("historical-card-pool.json")
    rules = load("historical-rule-parameters.json")
    inferred = load("historical-golden-acceptance.json")
    require(data["mode"] == rules["rule_set"] == "reference_2019_launch_week", "mode mismatch")
    require(data["build"] == rules["build"] == int(cards["build"].split(".")[-1]) == 35747, "build mismatch")
    require(all(value == "unknown" for value in data["historical_unknown"].values()), "unknown historical field was guessed")
    require(rules["dynamic_generation"]["exact_pool_membership"] == "unknown", "historical pool was guessed")
    require(rules["dynamic_generation"]["weights"] == "unknown", "historical weights were guessed")
    require(inferred["exact_2019_unknown"]["simultaneous_death_event_order"] == "unknown", "historical event order was guessed")

    rows = {row["normal_id"]: row for row in cards["rows"]}
    direct = {cid for cid, row in rows.items() if row["golden_id"] is not None}
    nodes = data["nodes"]
    node_by_id = {node["normal_id"]: node for node in nodes}
    typed_elsewhere = data["typed_elsewhere"]
    fixed_ids = typed_elsewhere["fixed_token_or_capacity"]
    composite_ids = typed_elsewhere["composite_lifecycle"]
    deferred = data["deferred"]
    deferred_ids = [cid for group in deferred.values() for cid in group]
    require(data["partial_shells"] == {
        "random_or_discover_file": "historical-random-effect-shells.json",
        "status": "trigger_and_quantity_only",
    }, "random-effect shell boundary drift")
    require(len(cards["rows"]) == data["coverage"]["shop_rows"] == 81, "shop row count drift")
    require(len(direct) == data["coverage"]["direct_golden_rows"] == 68, "direct golden count drift")
    require(len(nodes) == len(node_by_id) == data["coverage"]["typed_direct_golden_rows"] == 24, "typed coverage drift")
    require(typed_elsewhere["file"] == "historical-fixed-token-nodes.json", "fixed-token artifact reference drift")
    require(typed_elsewhere["composite_file"] == "historical-composite-nodes.json", "composite artifact reference drift")
    require(len(fixed_ids) == len(set(fixed_ids)) == data["coverage"]["typed_fixed_token_elsewhere_rows"] == 15, "fixed-token coverage drift")
    require(len(composite_ids) == len(set(composite_ids)) == data["coverage"]["typed_composite_elsewhere_rows"] == 13, "composite coverage drift")
    require(len(deferred_ids) == len(set(deferred_ids)) == data["coverage"]["deferred_direct_golden_rows"] == 16, "deferred coverage drift")
    groups = [set(node_by_id), set(fixed_ids), set(composite_ids), set(deferred_ids)]
    require(direct == set().union(*groups), "68 direct-golden cards are not partitioned exactly")
    require(sum(map(len, groups)) == len(direct), "typed and deferred IDs overlap")
    require(len(rows) - len(direct) == data["coverage"]["separate_inferred_golden_rows"] == 13, "inferred golden count drift")
    require(len(data["vectors"]) == len({case["id"] for case in data["vectors"]}), "duplicate vector ID")

    for cid, node in node_by_id.items():
        row = rows[cid]
        require(node["golden_id"] == row["golden_id"] and row["golden_evidence"] == "client_35747", f"{cid}: golden identity drift")
        require(node["name_zh"] == row["normal_name_zh"], f"{cid}: name drift")
        require(node["target"]["scope"] in FAMILIES[node["family"]], f"{cid}: invalid family/target scope")
        require(set(node["static_keywords"]) <= {"taunt", "divine_shield"}, f"{cid}: unsupported intrinsic keyword")
        require(node["evidence"]["numeric_and_target"] == "H04_client_cardface_direct", f"{cid}: source grade drift")
        require(node["evidence"]["event_routing"] == "reference_rule", f"{cid}: routing grade drift")
        for form in ("normal", "golden"):
            effect = node[f"{form}_effect"]
            require(all(isinstance(effect[key], int) and effect[key] >= 0 for key in ("attack", "health", "hero_damage")), f"{cid}: invalid effect amount")
            require(isinstance(effect["grant_taunt"], bool), f"{cid}: invalid taunt marker")
        card_face_numbers(node)

    covered = {(case["normal_id"], case["form"]) for case in data["vectors"] if case["grade"] != "reference_negative_guard"}
    require(covered == {(cid, form) for cid in node_by_id for form in ("normal", "golden")}, "every form needs a positive vector")
    for case in data["vectors"]:
        require(case["normal_id"] in node_by_id and case["form"] in ("normal", "golden"), f"{case['id']}: invalid identity")
        try:
            actual = execute(node_by_id[case["normal_id"]], case)
        except VerificationError as exc:
            require(case.get("expected_error") == str(exc), f"{case['id']}: unexpected error {exc}")
        else:
            require("expected_error" not in case, f"{case['id']}: expected rejection but operation succeeded")
            require(actual == case["expected"], f"{case['id']}: expected {case['expected']}, got {actual}")

    if args.carddefs:
        verify_xml(args.carddefs, data["client_source"], nodes)
    print(
        f"PASS: {len(nodes)} direct-golden card nodes, {len(data['vectors'])} deterministic vectors, "
        f"{len(deferred_ids)} explicitly deferred rows; "
        + ("pinned client XML verified" if args.carddefs else "stored client text verified")
        + "; reference only"
    )


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, KeyError, ValueError, TypeError, ET.ParseError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
