"""Bridge bounded Megasaur recruitment effects into reference combat and settlement."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import verify_historical_recruitment_transitions as recruit
import verify_historical_combat_events as combat
import verify_historical_combat_lifecycle as lifecycle


ROOT = Path(__file__).resolve().parent
VECTORS = json.loads((ROOT / "historical-combat-adapt-vectors.json").read_text())


def battle_item(item: dict) -> dict:
    fields = ("instance_id", "golden", "buff_attack", "buff_health",
              "adapt_effects", "adapt_grade")
    result = {key: copy.deepcopy(item[key]) for key in fields if key in item}
    result["card_id"] = item["normal_id"]
    return result


def left_traits(board: list[dict]) -> dict:
    traits = {}
    for item in board:
        anchor = combat.RULES["keyword_anchors"].get(item["card_id"])
        if "adapt_effects" in item:
            keywords = set(anchor or []) | combat.adapt_keywords(item["adapt_effects"])
            grade = "reference_injected"
        else:
            keywords = set(anchor or [])
            grade = "client_35747" if anchor is not None else "reference_injected"
        traits[item["instance_id"]] = {"keywords": sorted(keywords), "grade": grade}
    return traits


def verify_case(case: dict) -> None:
    assert case["grade"] == "reference_only", case["id"]
    recruited = {**recruit.initial_state(), **copy.deepcopy(case["initial"])}
    for item in recruited["hand"]:
        item.setdefault("golden", False)
    recruit_events = []
    recruit_details = []
    for action in case["recruit_actions"]:
        recruited, events, error = recruit.run_action(recruited, copy.deepcopy(action))
        assert error is None, (case["id"], "recruit", error)
        recruit_events.extend(event["type"] for event in events)
        recruit_details.extend(events)
    assert recruit_events == case["expect_recruit_events"], case["id"]
    if "expect_recruit_details" in case:
        assert recruit.matches(recruit_details, case["expect_recruit_details"]), case["id"]
    assert recruit.matches(recruit.project(recruited), case["expect_recruit"]), case["id"]
    if "enemy_board" not in case:
        return

    left_board = [battle_item(item) for item in recruited["board"]]
    seats = [
        {"seat_id": "A", "health": 40, "tier": recruited["tier"],
         "alive": True, "ready": False, "board": left_board},
        {"seat_id": "B", "health": case.get("enemy_health", 20),
         "tier": case.get("enemy_tier", 1), "alive": True,
         "ready": False, "board": copy.deepcopy(case["enemy_board"])}]
    match = lifecycle.initial_state(seats)
    for seat_id in ("A", "B"):
        match, _, error = lifecycle.run_action(
            match, {"op": "end_recruit", "seat_id": seat_id})
        assert error is None, (case["id"], "end_recruit", error)
    match, _, error = lifecycle.run_action(match, {"op": "begin_combat",
        "pairings": [{"pair_id": "p1", "left": "A", "right": "B"}]})
    assert error is None, (case["id"], "begin_combat", error)
    snapshot = match["snapshots"]["p1"]
    traits = {**left_traits(left_board), **copy.deepcopy(case["enemy_traits"])}
    for item_id, override in case.get("override_traits", {}).items():
        traits[item_id] = override
    try:
        battle = combat.from_snapshot(snapshot, traits, case.get("first_side", "left"))
    except combat.Rejected as exc:
        assert str(exc) == case.get("start_error"), (case["id"], str(exc))
        return
    assert "start_error" not in case, case["id"]
    assert combat.matches(combat.project(battle), case["expect_start"]), case["id"]
    for step in case["steps"]:
        before = copy.deepcopy(battle)
        action = copy.deepcopy(step["action"])
        after, events, error = combat.run_action(battle, action)
        assert action == step["action"], case["id"]
        assert error == step.get("error"), (case["id"], error)
        if error:
            assert after == before and not events, case["id"]
        else:
            assert [event["type"] for event in events] == step["events"], (
                case["id"], [event["type"] for event in events])
            assert combat.matches(combat.project(after), step["expect"]), (
                case["id"], combat.project(after))
            battle = after
    if "expect_result" in case:
        result = combat.to_lifecycle_result(battle, "p1")
        assert combat.matches(result, case["expect_result"]), case["id"]
        match, _, error = lifecycle.run_action(
            match, {"op": "settle_combat", "results": [result]})
        assert error is None, (case["id"], "settle_combat", error)
        assert lifecycle.matches(lifecycle.project(match), case["expect_match"]), (
            case["id"], lifecycle.project(match))
        # The battle is a snapshot: no temporary damage or shield loss writes
        # back to the recruited board after settlement.
        assert match["seats"][0]["board"] == left_board, case["id"]


def main() -> None:
    assert VECTORS["build"] == combat.RULES["build"] == recruit.RULES["build"] == 35747
    assert VECTORS["mode"] == combat.RULES["mode"] == recruit.RULES["mode"]
    assert len(VECTORS["cases"]) == len({case["id"] for case in VECTORS["cases"]})
    assert all(value == "unknown" for value in
               VECTORS["historical_unknown"].values())
    for case in VECTORS["cases"]:
        verify_case(case)
    print(f"adapt recruit/combat/lifecycle reference vectors: "
          f"{len(VECTORS['cases'])} passed; original order and weights unknown")


if __name__ == "__main__":
    main()
