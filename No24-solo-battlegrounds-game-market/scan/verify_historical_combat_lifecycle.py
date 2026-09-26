"""Validate a bounded 2019-style combat lifecycle, not original server combat."""

from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class Rejected(Exception):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Rejected(code)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


RULES = load("historical-combat-lifecycle.json")
ROWS = {row["normal_id"]: row for row in load("historical-card-pool.json")["rows"]}
FIXED = load("historical-fixed-token-nodes.json")
COMPOSITE = load("historical-composite-nodes.json")
IMMUNITY_RULES = load(RULES["hero_immunity_nodes_file"])
IMMUNITY_SOURCE = IMMUNITY_RULES["immunity_source"]["normal_id"]
RECRUIT_DAMAGE_SOURCE = IMMUNITY_RULES["recruit_damage_source"]["normal_id"]
TOKEN_IDS = {form["id"] for node in FIXED["nodes"] for form in node["tokens"].values()}
TOKEN_IDS |= {form["token_id"] for node in COMPOSITE["nodes"]
              for form in node.get("parameters", {}).values()
              if isinstance(form, dict) and "token_id" in form}
TOKEN_IDS.add("UNG_999t2t1")  # H04 entity; its Battlegrounds damage tier remains reference-injected.


def initial_state(seats: list[dict], graveyard: list[dict] | None = None) -> dict:
    return {"phase": "recruit", "round": 1, "seats": copy.deepcopy(seats),
            "graveyard": copy.deepcopy(graveyard or []), "pairings": [], "snapshots": {},
            "history": [], "winner_id": None}


def seat_map(state: dict) -> dict[str, dict]:
    return {seat["seat_id"]: seat for seat in state["seats"]}


def hero_immune(board: list[dict]) -> bool:
    return any(item["card_id"] == IMMUNITY_SOURCE for item in board)


def card_tier(item: dict) -> int:
    card_id = item["card_id"]
    if item.get("origin") == "combat_generated_minion":
        require(card_id in ROWS, "unsupported_generated_entity")
        require(item.get("pool_grade") == "reference_injected", "ungraded_generated_pool")
        require("damage_tier" not in item, "forged_card_tier")
        return ROWS[card_id]["tier"]
    if card_id in ROWS and item.get("origin") in {None, "recruit_minion"}:
        require("damage_tier" not in item, "forged_card_tier")
        return ROWS[card_id]["tier"]
    require(card_id in TOKEN_IDS, "unknown_token")
    require(item.get("origin") in {"recruit_token", "combat_token"}, "invalid_token_origin")
    tier = item.get("damage_tier")
    require(type(tier) is int and 0 <= tier <= 6, "invalid_token_tier")
    require(item.get("tier_grade") == "reference_injected", "ungraded_token_tier")
    return tier


def validate_board(board: list[dict]) -> None:
    require(type(board) is list and len(board) <= 7, "board_overflow")
    ids: list[str] = []
    for item in board:
        require(type(item) is dict, "invalid_board_item")
        require(item.get("origin") not in {"combat_token", "combat_generated_minion"},
                "combat_instance_persisted")
        item_id = item.get("instance_id")
        require(type(item_id) is str and item_id, "invalid_instance_id")
        ids.append(item_id)
        card_tier(item)
    require(len(set(ids)) == len(ids), "duplicate_instance_id")


def validate_state(state: dict) -> None:
    require(state["phase"] in {"recruit", "await_pairing", "combat", "post_combat",
                               "match_over"}, "invalid_phase")
    require(type(state["round"]) is int and state["round"] >= 1, "invalid_round")
    require(2 <= len(state["seats"]) <= 8, "invalid_seat_count")
    ids = [seat["seat_id"] for seat in state["seats"]]
    require(len(set(ids)) == len(ids), "duplicate_seat_id")
    all_instance_ids: list[str] = []
    for seat in state["seats"]:
        require(type(seat["seat_id"]) is str and seat["seat_id"], "invalid_seat_id")
        require(type(seat["health"]) is int, "invalid_health")
        require(type(seat["tier"]) is int and 1 <= seat["tier"] <= 6,
                "invalid_tavern_tier")
        require(type(seat["alive"]) is bool and seat["alive"] == (seat["health"] > 0),
                "invalid_alive_flag")
        require(type(seat["ready"]) is bool, "invalid_ready_flag")
        require(type(seat.get("pending_rewards", 0)) is int and
                seat.get("pending_rewards", 0) >= 0, "invalid_pending_rewards")
        validate_board(seat["board"])
        all_instance_ids += [item["instance_id"] for item in seat["board"]]
    require(len(set(all_instance_ids)) == len(all_instance_ids), "duplicate_instance_id")
    grave_ids = [entry["seat_id"] for entry in state["graveyard"]]
    require(len(set(grave_ids)) == len(grave_ids), "duplicate_graveyard_seat")
    for entry in state["graveyard"]:
        require(entry["seat_id"] in ids and not seat_map(state)[entry["seat_id"]]["alive"],
                "invalid_graveyard_seat")
        require(type(entry["tier"]) is int and 1 <= entry["tier"] <= 6,
                "invalid_ghost_tier")
        validate_board(entry["board"])
    if state["phase"] == "await_pairing":
        require(all(seat["ready"] for seat in state["seats"] if seat["alive"]),
                "unready_seat")
    if state["phase"] == "combat":
        require(bool(state["pairings"]) and
                {pair["pair_id"] for pair in state["pairings"]} == set(state["snapshots"]),
                "missing_combat_snapshot")
    if state["phase"] == "match_over":
        living = [seat["seat_id"] for seat in state["seats"] if seat["alive"]]
        require(living == [state["winner_id"]], "invalid_winner")


def pairings_for(state: dict, pairings: list[dict]) -> dict[str, dict]:
    require(type(pairings) is list, "invalid_pairings")
    living = {seat["seat_id"] for seat in state["seats"] if seat["alive"]}
    require(len(pairings) == (len(living) + 1) // 2, "wrong_pair_count")
    seats = seat_map(state)
    ghosts = {entry["seat_id"]: entry for entry in state["graveyard"]}
    assigned: list[str] = []
    ghost_count = 0
    snapshots: dict[str, dict] = {}
    for pair in pairings:
        require(type(pair) is dict and set(pair) == {"pair_id", "left", "right"},
                "invalid_pairing")
        pair_id, left, right = pair["pair_id"], pair["left"], pair["right"]
        require(type(pair_id) is str and pair_id and pair_id not in snapshots,
                "duplicate_pair_id")
        require(left in living, "invalid_pair_left")
        assigned.append(left)
        left_source = seats[left]
        if isinstance(right, str):
            require(right in living and right != left, "invalid_pair_right")
            assigned.append(right)
            right_source = seats[right]
            right_side = {"seat_id": right, "tier": right_source["tier"],
                          "board": copy.deepcopy(right_source["board"])}
        else:
            require(type(right) is dict and set(right) == {"ghost_of"},
                    "invalid_ghost_pairing")
            ghost_of = right["ghost_of"]
            require(ghost_of in ghosts, "ghost_snapshot_missing")
            ghost_count += 1
            source = ghosts[ghost_of]
            right_side = {"ghost_of": ghost_of, "tier": source["tier"],
                          "board": copy.deepcopy(source["board"])}
        snapshots[pair_id] = {
            "left": {"seat_id": left, "tier": left_source["tier"],
                     "board": copy.deepcopy(left_source["board"])},
            "right": right_side,
        }
    require(len(assigned) == len(living) and set(assigned) == living,
            "pairing_not_disjoint")
    require(ghost_count == len(living) % 2, "wrong_ghost_count")
    return snapshots


def side_survivors(snapshot: dict, generated: list[dict], survivors: list[str],
                   side: str, other_initial: set[str], other_ids: set[str]) -> list[dict]:
    require(type(generated) is list and len(generated) <= 100, "invalid_token_manifest")
    known = {item["instance_id"]: item for item in snapshot["board"]}
    require(not (set(known) & other_ids), "cross_side_instance_id")
    for token in generated:
        require(type(token) is dict and token.get("origin") in
                {"combat_token", "combat_generated_minion"},
                "invalid_token_manifest")
        item_id = token.get("instance_id")
        require(type(item_id) is str and item_id and item_id not in known and
                item_id not in other_ids, "duplicate_instance_id")
        source_side = token.get("source_side", side)
        require(source_side in {"left", "right"}, "invalid_token_source_side")
        sources = known if source_side == side else other_initial
        require(token.get("source_instance_id") in sources, "token_source_missing")
        card_tier(token)
        known[item_id] = token
    require(type(survivors) is list and len(survivors) <= 7 and
            all(type(item_id) is str for item_id in survivors), "invalid_survivors")
    require(len(set(survivors)) == len(survivors), "duplicate_survivor")
    require(all(item_id in known for item_id in survivors), "survivor_not_in_snapshot")
    return [known[item_id] for item_id in survivors]


def settle_pair(snapshot: dict, result: dict) -> dict:
    require(not any(key in result for key in (
        "hero_immune", "hero_immune_at_settlement", "damage_override")),
        "untrusted_immunity_override")
    generated = result.get("generated", {"left": [], "right": []})
    require(type(generated) is dict and set(generated) == {"left", "right"},
            "invalid_token_manifest")
    left_initial = {item["instance_id"] for item in snapshot["left"]["board"]}
    right_initial = {item["instance_id"] for item in snapshot["right"]["board"]}
    left_generated = {item.get("instance_id") for item in generated["left"]}
    right_generated = {item.get("instance_id") for item in generated["right"]}
    require(not ((left_initial | left_generated) & (right_initial | right_generated)),
            "cross_side_instance_id")
    left = side_survivors(snapshot["left"], generated["left"],
                          result.get("left_survivors"), "left", right_initial,
                          right_initial | right_generated)
    right = side_survivors(snapshot["right"], generated["right"],
                           result.get("right_survivors"), "right", left_initial,
                           left_initial | left_generated)
    require(not (left and right), "both_sides_survive")
    immunity = {"left": hero_immune(left), "right": hero_immune(right)}
    if not left and not right:
        return {"outcome": "draw", "damage": 0, "damaged_seat": None,
                "survivors": {"left": [], "right": []},
                "hero_immune_at_settlement": immunity}
    winning_side = "left" if left else "right"
    winner = snapshot[winning_side]
    loser = snapshot["right" if left else "left"]
    require(not immunity["right" if left else "left"],
            "immune_loser_with_survivors_unverified")
    surviving = left if left else right
    damage = winner["tier"] + sum(card_tier(item) for item in surviving)
    damaged_seat = loser.get("seat_id")
    return {"outcome": winning_side, "damage": damage,
            "damaged_seat": damaged_seat,
            "survivors": {"left": [item["instance_id"] for item in left],
                          "right": [item["instance_id"] for item in right]},
            "hero_immune_at_settlement": immunity}


def run_action(original: dict, action: dict) -> tuple[dict, list[dict], str | None]:
    state = copy.deepcopy(original)
    events: list[dict] = []
    try:
        validate_state(state)
        require(action.get("mode", "reference") == "reference", "exact_mode_unverified")
        op = action.get("op")
        require(op in {entry["op"] for entry in RULES["actions"]}, "unknown_op")
        if op == "end_recruit":
            require(state["phase"] == "recruit", "wrong_phase")
            seat = seat_map(state).get(action.get("seat_id"))
            require(seat is not None and seat["alive"], "seat_not_alive")
            require(not seat["ready"], "already_ready")
            require(seat.get("pending_rewards", 0) == 0, "reward_pending")
            seat["ready"] = True
            events.append({"type": "recruit_locked", "seat_id": seat["seat_id"]})
            if all(item["ready"] for item in state["seats"] if item["alive"]):
                state["phase"] = "await_pairing"
                events.append({"type": "all_recruit_locked"})
        elif op == "apply_recruit_hero_damage":
            require(state["phase"] == "recruit", "wrong_phase")
            require(action.get("trigger") == "friendly_demon_played" and
                    action.get("trigger_grade") == "reference_injected",
                    "unverified_hero_damage_trigger")
            require(not any(key in action for key in ("amount", "hero_immune")),
                    "untrusted_damage_override")
            seat = seat_map(state).get(action.get("seat_id"))
            require(seat is not None and seat["alive"], "seat_not_alive")
            source_id = action.get("source_instance_id")
            source = next((item for item in seat["board"]
                           if item["instance_id"] == source_id), None)
            require(source is not None and source["card_id"] == RECRUIT_DAMAGE_SOURCE,
                    "unsupported_hero_damage_source")
            amount = IMMUNITY_RULES["recruit_damage_source"]["amount"]
            if hero_immune(seat["board"]):
                events.append({"type": "hero_damage_prevented", "seat_id": seat["seat_id"],
                               "source_instance_id": source_id, "amount": amount})
            else:
                seat["health"] -= amount
                events.append({"type": "hero_damage", "seat_id": seat["seat_id"],
                               "source_instance_id": source_id, "amount": amount})
                if seat["health"] <= 0:
                    seat["alive"] = False
                    state["graveyard"].append({"seat_id": seat["seat_id"],
                                               "tier": seat["tier"],
                                               "board": copy.deepcopy(seat["board"]),
                                               "eliminated_round": state["round"],
                                               "placement": "unknown"})
                    events.append({"type": "eliminated", "seat_id": seat["seat_id"]})
                    living = [item["seat_id"] for item in state["seats"] if item["alive"]]
                    require(bool(living), "no_survivor")
                    if len(living) == 1:
                        state["phase"] = "match_over"
                        state["winner_id"] = living[0]
                        events.append({"type": "match_over", "winner_id": living[0]})
        elif op == "begin_combat":
            require(state["phase"] == "await_pairing", "wrong_phase")
            pairings = action.get("pairings")
            snapshots = pairings_for(state, pairings)
            state["pairings"] = copy.deepcopy(pairings)
            state["snapshots"] = snapshots
            state["phase"] = "combat"
            events.append({"type": "combat_snapshots_created",
                           "pair_ids": list(snapshots)})
        elif op == "settle_combat":
            require(state["phase"] == "combat", "wrong_phase")
            results = action.get("results")
            require(type(results) is list and len(results) == len(state["pairings"]),
                    "wrong_result_count")
            result_map = {item.get("pair_id"): item for item in results if isinstance(item, dict)}
            require(len(result_map) == len(results) and
                    set(result_map) == set(state["snapshots"]), "invalid_result_ids")
            damages: dict[str, int] = {}
            outcomes = []
            for pair in state["pairings"]:
                pair_id = pair["pair_id"]
                outcome = settle_pair(state["snapshots"][pair_id], result_map[pair_id])
                outcomes.append({"pair_id": pair_id, **outcome})
                if outcome["damaged_seat"] is not None:
                    seat_id = outcome["damaged_seat"]
                    damages[seat_id] = damages.get(seat_id, 0) + outcome["damage"]
            for seat_id, damage in damages.items():
                seat_map(state)[seat_id]["health"] -= damage
                events.append({"type": "hero_damage", "seat_id": seat_id,
                               "amount": damage})
            eliminated = []
            for seat in state["seats"]:
                if seat["alive"] and seat["health"] <= 0:
                    seat["alive"] = False
                    eliminated.append(seat["seat_id"])
                    state["graveyard"].append({"seat_id": seat["seat_id"],
                                               "tier": seat["tier"],
                                               "board": copy.deepcopy(seat["board"]),
                                               "eliminated_round": state["round"],
                                               "placement": "unknown"})
                    events.append({"type": "eliminated", "seat_id": seat["seat_id"]})
            living = [seat["seat_id"] for seat in state["seats"] if seat["alive"]]
            require(bool(living), "no_survivor")
            state["history"].append({"round": state["round"], "outcomes": outcomes,
                                     "eliminated": eliminated})
            if len(living) == 1:
                state["phase"] = "match_over"
                state["winner_id"] = living[0]
                events.append({"type": "match_over", "winner_id": living[0]})
            else:
                state["phase"] = "post_combat"
        elif op == "open_next_recruit":
            require(state["phase"] == "post_combat", "wrong_phase")
            state["round"] += 1
            state["phase"] = "recruit"
            state["pairings"] = []
            state["snapshots"] = {}
            for seat in state["seats"]:
                seat["ready"] = False
                if seat["alive"]:
                    events.append({"type": "advance_recruit", "seat_id": seat["seat_id"],
                                   "round": state["round"]})
        validate_state(state)
        return state, events, None
    except (Rejected, KeyError, TypeError, AttributeError) as exc:
        return original, [], str(exc) if isinstance(exc, Rejected) else "invalid_action"


def project(state: dict) -> dict:
    return {"phase": state["phase"], "round": state["round"],
            "health": {seat["seat_id"]: seat["health"] for seat in state["seats"]},
            "alive": {seat["seat_id"]: seat["alive"] for seat in state["seats"]},
            "ready": {seat["seat_id"]: seat["ready"] for seat in state["seats"]},
            "boards": {seat["seat_id"]: seat["board"] for seat in state["seats"]},
            "graveyard_ids": [entry["seat_id"] for entry in state["graveyard"]],
            "placements": {entry["seat_id"]: entry.get("placement")
                           for entry in state["graveyard"]},
            "pairings": state["pairings"], "snapshots": state["snapshots"],
            "history": state["history"], "winner_id": state["winner_id"]}


def matches(actual: object, expected: object) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and matches(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            matches(a, e) for a, e in zip(actual, expected))
    return actual == expected


def main() -> None:
    packs = [load(RULES["vectors_file"]), load(RULES["hero_immunity_vectors_file"])]
    assert RULES["mode"] == IMMUNITY_RULES["mode"] == "reference_2019_launch_week"
    assert RULES["build"] == IMMUNITY_RULES["build"] == 35747
    assert all(value == "unknown" for value in RULES["historical_unknown"].values())
    assert all(value == "unknown" for value in IMMUNITY_RULES["historical_unknown"].values())
    assert IMMUNITY_SOURCE == "GVG_021" and RECRUIT_DAMAGE_SOURCE == "BGS_004"
    source = next(node for node in COMPOSITE["nodes"]
                  if node["normal_id"] == IMMUNITY_SOURCE)
    damage = next(node for node in load("historical-effect-nodes.json")["nodes"]
                  if node["normal_id"] == RECRUIT_DAMAGE_SOURCE)
    assert source["family"] == "demon_hero_aura" and all(
        "免疫" in source["client_text_zh"][form] for form in ("normal", "golden"))
    assert damage["event"] == "friendly_demon_played" and all(
        damage[form + "_effect"]["hero_damage"] ==
        IMMUNITY_RULES["recruit_damage_source"]["amount"]
        for form in ("normal", "golden"))
    seen: set[str] = set()
    covered_ops: set[str] = set()
    for vectors in packs:
        assert RULES["mode"] == vectors["mode"] and RULES["build"] == vectors["build"]
        for case in vectors["cases"]:
            assert case["id"] not in seen and case["grade"] == "reference_only", case["id"]
            seen.add(case["id"])
            fixture = vectors["fixtures"][case["fixture"]]
            state = initial_state(fixture["seats"], fixture.get("graveyard"))
            setup_actions = vectors["setups"].get(case.get("setup_ref"), []) + case.get("setup", [])
            for setup in setup_actions:
                state, _, error = run_action(state, setup)
                assert error is None, (case["id"], "setup", error)
            action = copy.deepcopy(case["action"])
            before = copy.deepcopy(state)
            after, events, error = run_action(state, action)
            replay_after, replay_events, replay_error = run_action(before, action)
            assert (after, events, error) == (
                replay_after, replay_events, replay_error), case["id"]
            assert action == case["action"], case["id"]
            assert error == case.get("error"), (case["id"], error)
            if error:
                assert after == before and events == [], case["id"]
            else:
                assert matches(project(after), case["expect_state"]), (case["id"], project(after))
                assert [event["type"] for event in events] == case["expect_events"], case["id"]
                assert matches(events, case.get("expect_event_details", events)), case["id"]
            covered_ops.add(action["op"])
    assert covered_ops == {entry["op"] for entry in RULES["actions"]}
    print(f"combat lifecycle reference vectors: {len(seen)} passed; "
          "original pairing and event order remain unknown")


if __name__ == "__main__":
    main()
