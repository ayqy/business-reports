"""Check 13 composite card nodes against build 35747 and bounded reference vectors.

Passing means that the reference specification is internally executable. It does
not establish the original server's event order, token emission, or replay state.
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


class VerificationError(Exception):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise VerificationError(message)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def plain(value: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", value))


def execute(node: dict, form: str, data: dict) -> dict:
    family = node["family"]
    value = node["parameters"][form]
    if data.get("simultaneous_deaths", False):
        raise VerificationError("unknown_simultaneous_death_order")
    if "free_slots" in data:
        require(0 <= data["free_slots"] <= 7, "free slots outside seven-slot board")
    if family == "deathrattle_team_buff":
        bonus = value["each_stat"] if data["event"] == "source_died" else 0
        return {"buffs": {
            item["id"]: [bonus, bonus]
            for item in data["survivors"]
            if bonus and (node["target_race"] == "ANY" or item["race"] == node["target_race"])
        }}
    if family == "card_summon_multiplier":
        if data["other_multipliers_present"]:
            raise VerificationError("unknown_multi_multiplier_order")
        factor = value["factor"] if data.get("source_present", True) and data["owner"] == "friendly" and data["origin"] == "card" else 1
        return {"summoned_count": min(data["base_count"] * factor, data["free_slots"])}
    if family == "ability_repeat":
        if data["other_repeat_sources_present"]:
            raise VerificationError("unknown_multi_repeat_order")
        active = data.get("source_present", True) and data["owner"] == "friendly" and data["ability"] == node["ability"]
        return {"trigger_count": value["times"] if active else 1}
    if family == "murloc_attack_aura":
        count = data["other_friendly_murlocs"] + data["other_enemy_murlocs"]
        return {"attack_bonus": count * value["attack_per_other_murloc"], "keywords": ["charge"]}
    if family == "pogo_growth":
        if data["history_ambiguous"]:
            raise VerificationError("unknown_pogo_history_identity")
        count = data["previous_pogo_plays"] if data["event"] == "played_from_hand" else 0
        delta = count * value["each_stat_per_previous"]
        return {"stat_bonus": [delta, delta]}
    if family == "hero_damage_health":
        if data["hero_healed_since_start"]:
            raise VerificationError("unknown_healed_hero_damage_metric")
        bonus = data["unhealed_hero_damage"] * value["health_per_damage"] if data["event"] == "played_from_hand" else 0
        return {"health_bonus": bonus}
    if family == "magnetic_merge":
        keywords = sorted({"divine_shield", "taunt"} | set(data["left_neighbor_keywords"]))
        if data["left_neighbor_race"] == "MECHANICAL":
            return {"result": "fused", "attack": data["left_neighbor_attack"] + value["attack"],
                    "health": data["left_neighbor_health"] + value["health"], "keywords": keywords}
        require(data["free_slots"] > 0, "magnetic standalone fixture has no free slot")
        return {"result": "standalone", "attack": value["attack"], "health": value["health"],
                "keywords": ["divine_shield", "taunt"]}
    if family == "overkill_summon":
        if not data["attacker_survives"]:
            raise VerificationError("unknown_dying_overkill_source_order")
        active = data["event"] == "attack_resolved" and data["effective_damage"] > data["target_health_before"]
        return {"summoned_count": int(active and data["free_slots"] > 0),
                "candidate_token_id": value["token_id"] if active and data["free_slots"] > 0 else None,
                "token_stats": [value["attack"], value["health"]] if active and data["free_slots"] > 0 else None,
                "token_race": value["race"] if active and data["free_slots"] > 0 else None}
    if family == "demon_hero_aura":
        active = data["source_present"]
        delta = value["each_stat"]
        return {"buffs": {item["id"]: [delta, delta] for item in data["other_friendlies"]
                          if active and item["race"] == "DEMON"}, "hero_immune": active}
    if family == "attack_kill_growth":
        if not data["attacker_survives"]:
            raise VerificationError("unknown_dying_attacker_growth_order")
        active = data["event"] == "attack_resolved" and data["self_attacked"] and data["target_killed"]
        delta = value["each_stat"] if active else 0
        return {"stat_bonus": [delta, delta]}
    if family == "first_dead_mechs":
        if not data["history_complete"] or data["same_event_tie"]:
            raise VerificationError("unknown_mech_death_history_order")
        if len({item["instance_id"] for item in data["death_history"]}) != len(data["death_history"]):
            raise VerificationError("unknown_repeat_death_identity")
        eligible = [item for item in data["death_history"]
                    if item["owner"] == "friendly" and item["race"] == "MECHANICAL"]
        selected = eligible[:min(value["first_count"], data["free_slots"])]
        return {"summoned_from": [{"instance_id": item["instance_id"], "definition_id": item["definition_id"]}
                                  for item in selected], "copy_policy": "reference_death_snapshot"}
    raise VerificationError(f"unsupported family: {family}")


def check_face(node: dict, form: str) -> None:
    text = plain(node["client_text_zh"][form])
    value = node["parameters"][form]
    family = node["family"]
    if family == "deathrattle_team_buff":
        require("亡语" in text and f"+{value['each_stat']}/+{value['each_stat']}" in text, "deathrattle face drift")
        require(("野兽" in text) == (node["target_race"] == "BEAST"), "deathrattle target drift")
    elif family == "card_summon_multiplier":
        require("召唤" in text and ("翻倍" if value["factor"] == 2 else "三倍") in text, "Khadgar face drift")
    elif family == "ability_repeat":
        require(node["ability"] in text and ("两次" if value["times"] == 2 else "三次") in text, "repeat face drift")
    elif family == "murloc_attack_aura":
        require("冲锋" in text and "其他鱼人" in text and f"+{value['attack_per_other_murloc']}攻击力" in text, "Murk-Eye face drift")
    elif family == "pogo_growth":
        amount = value["each_stat_per_previous"]
        require("战吼" in text and "蹦蹦兔" in text and f"+{amount}/+{amount}" in text, "Pogo face drift")
    elif family == "hero_damage_health":
        require("战吼" in text and "英雄每受到一点伤害" in text and f"+{value['health_per_damage']}生命值" in text, "Battlemaster face drift")
    elif family == "magnetic_merge":
        require(all(word in text for word in ("磁力", "圣盾", "嘲讽")), "magnetic face drift")
    elif family == "overkill_summon":
        require("超杀" in text and f"{value['attack']}/{value['health']}" in text, "overkill face drift")
    elif family == "demon_hero_aura":
        amount = value["each_stat"]
        require("其他恶魔" in text and "免疫" in text and f"+{amount}/+{amount}" in text, "Mal'Ganis face drift")
    elif family == "attack_kill_growth":
        amount = value["each_stat"]
        require("攻击并消灭" in text and f"+{amount}/+{amount}" in text, "Boogeymonster face drift")
    elif family == "first_dead_mechs":
        require("亡语" in text and "最先死亡" in text and "友方机械" in text
                and ("两个" if value["first_count"] == 2 else "四个") in text, "Kangor face drift")


def verify_xml(path: Path, data: dict, nodes: list[dict], rows: dict) -> None:
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == data["client_source"]["sha256"], "pinned XML hash mismatch")
    entities = {item.get("CardID"): item for item in ET.fromstring(raw)}
    for node in nodes:
        row = rows[node["normal_id"]]
        for form, cid in (("normal", node["normal_id"]), ("golden", node["golden_id"])):
            require(cid in entities, f"{cid}: missing parent entity")
            tags = {tag.get("name"): tag for tag in entities[cid].findall("Tag")}
            require(tags["CARDTEXT"].findtext("zhCN") == node["client_text_zh"][form], f"{cid}: card text drift")
            require(tags["CARDNAME"].findtext("zhCN") == node["name_zh"], f"{cid}: card name drift")
            require(int(tags["ATK"].get("value")) == row[f"{form}_attack"], f"{cid}: attack drift")
            require(int(tags["HEALTH"].get("value")) == row[f"{form}_health"], f"{cid}: health drift")
            check_face(node, form)
        if node["family"] == "overkill_summon":
            for value in node["parameters"].values():
                tid = value["token_id"]
                require(tid in entities, f"{tid}: candidate token absent")
                tags = {tag.get("name"): tag for tag in entities[tid].findall("Tag")}
                require(tags["CARDNAME"].findtext("zhCN") == "铁皮小恐龙", f"{tid}: token name drift")
                require(int(tags["ATK"].get("value")) == value["attack"]
                        and int(tags["HEALTH"].get("value")) == value["health"], f"{tid}: token stats drift")
                require(tags["CARDRACE"].get("value") == "20" and value["race"] == "BEAST",
                        f"{tid}: token race drift")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carddefs", type=Path, help="local build-35747 CardDefs.xml")
    args = parser.parse_args()
    data = load("historical-composite-nodes.json")
    effects = load("historical-effect-nodes.json")
    cards = load("historical-card-pool.json")
    rules = load("historical-rule-parameters.json")
    require(data["mode"] == effects["mode"] == rules["rule_set"] == "reference_2019_launch_week", "reference mode drift")
    require(data["build"] == effects["build"] == rules["build"] == 35747, "build drift")
    require(data["client_source"] == effects["client_source"], "client source drift")
    require(rules["dynamic_generation"]["exact_pool_membership"] == "unknown", "dynamic pool was guessed")
    require(set(data["historical_unknown"]) == {
        "dynamic_pool_eligibility", "simultaneous_death_event_order",
        "historical_summon_insert_position", "multiple_multiplier_resolution",
        "hero_damage_after_healing_metric", "kangor_resummoned_state",
    }, "historical gap inventory drift")
    require(all(value == "unknown" for value in data["historical_unknown"].values()), "historical gap was filled without evidence")
    require(data["reference_scope"]["board_limit"] == 7
            and data["reference_scope"]["single_effect_event_only"]
            and data["reference_scope"]["combat_changes_revert_to_recruit_snapshot"], "reference scope drift")
    nodes = data["nodes"]
    by_id = {node["normal_id"]: node for node in nodes}
    expected_ids = set(effects["typed_elsewhere"]["composite_lifecycle"])
    require(len(nodes) == len(by_id) == len(expected_ids) == data["coverage"]["composite_parent_rows"] == 13, "composite coverage drift")
    require(by_id.keys() == expected_ids, "composite IDs differ from coverage partition")
    require(data["coverage"]["parent_forms"] == 26, "parent form count drift")
    rows = {row["normal_id"]: row for row in cards["rows"]}
    for cid, node in by_id.items():
        row = rows[cid]
        require(row["golden_id"] == node["golden_id"] and row["golden_evidence"] == "client_35747", f"{cid}: golden identity drift")
        require(row["normal_name_zh"] == node["name_zh"], f"{cid}: parent name drift")
        require(node["evidence"]["card_face"] == "H04_client_direct", f"{cid}: card face grade drift")
        require(node["evidence"]["execution"] == "bounded_reference", f"{cid}: execution grade drift")
        require(set(node["parameters"]) == set(node["client_text_zh"]) == {"normal", "golden"}, f"{cid}: form mismatch")
        if node["family"] == "magnetic_merge":
            for form in ("normal", "golden"):
                require(node["parameters"][form] == {
                    "attack": row[f"{form}_attack"], "health": row[f"{form}_health"]}, f"{cid}: magnetic stats drift")
        if node["family"] == "overkill_summon":
            require(node["evidence"]["effect_to_token_id"] == "inference_from_client_name_stats_id",
                    f"{cid}: token mapping overclaimed")
        for form in ("normal", "golden"):
            check_face(node, form)
    cases = data["vectors"]
    require(len(cases) == len({case["id"] for case in cases}), "duplicate vector ID")
    require(len(cases) * 2 == data["coverage"]["form_vectors"] == 84, "form vector count drift")
    require({case["normal_id"] for case in cases if case["id"].endswith("-BASE")} == expected_ids, "baseline vector missing")
    require(all(sum(case["normal_id"] == cid for case in cases) >= 2 for cid in expected_ids),
            "a composite card lacks a boundary vector")
    for case in cases:
        require(case["normal_id"] in by_id, f"{case['id']}: unknown card")
        for form in ("normal", "golden"):
            try:
                actual = execute(by_id[case["normal_id"]], form, case["input"])
            except VerificationError as exc:
                require(case.get("expected_error") == str(exc), f"{case['id']} {form}: unexpected error {exc}")
            else:
                require("expected_error" not in case, f"{case['id']} {form}: unknown guard did not fire")
                require(actual == case["expected_by_form"][form], f"{case['id']} {form}: expected {case['expected_by_form'][form]}, got {actual}")
    if args.carddefs:
        verify_xml(args.carddefs, data, nodes, rows)
    print(f"PASS: {len(nodes)} composite cards, {len(cases) * 2} form vectors; "
          + ("pinned client XML verified" if args.carddefs else "stored client faces verified")
          + "; historical edge cases remain unknown")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, KeyError, TypeError, ValueError, ET.ParseError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
