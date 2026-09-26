"""Execute bounded recruitment reference transitions, not a 2019 server replay."""

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


RULES = load("historical-recruitment-transitions.json")
ZERUS = load("historical-recruitment-zerus-candidates.json")
MURLOC = load("historical-recruitment-murloc-candidates.json")
ADAPT = load("historical-random-reference.json")
PARAMETERS = load("historical-rule-parameters.json")
ROWS = {row["normal_id"]: row for row in load("historical-card-pool.json")["rows"]}
ZERUS_POOL = ZERUS["candidate_ids"]
MURLOC_POOL = MURLOC["candidate_ids"]
ADAPT_POOL = ADAPT["adapt_option_ids"]
ADAPT_DEFS = ADAPT["adapt_option_defs"]
SLOTS = {int(k): v for k, v in PARAMETERS["tavern"]["offer_slots_by_tier"].items()}
BASE_COSTS = {int(k): v for k, v in PARAMETERS["tavern"]["base_upgrade_cost_by_target_tier"].items()}


def initial_state() -> dict:
    return {
        "phase": "recruit", "round": 1, "coins": 3, "tier": 1,
        "skipped_rounds": 0, "upgraded_this_round": False, "hero_discount": 0,
        "hand": [], "board": [], "shop": [], "pending_rewards": [], "serial": 1,
    }


def instances(state: dict) -> list[dict]:
    return state["hand"] + state["board"] + state["shop"]


def normalize_shop_slots(state: dict) -> None:
    for index, offer in enumerate(state["shop"]):
        offer.setdefault("slot", index)


def validate_state(state: dict) -> None:
    require(state["phase"] == "recruit", "wrong_phase")
    require(type(state["round"]) is int and state["round"] >= 1, "invalid_round")
    require(type(state["tier"]) is int and 1 <= state["tier"] <= 6, "invalid_tier")
    require(type(state["coins"]) is int and 0 <= state["coins"] <= 10, "invalid_coins")
    require(type(state["skipped_rounds"]) is int and state["skipped_rounds"] >= 0,
            "invalid_skipped_rounds")
    require(type(state["hero_discount"]) is int and state["hero_discount"] >= 0,
            "invalid_hero_discount")
    require(type(state["upgraded_this_round"]) is bool, "invalid_upgrade_flag")
    require(type(state["serial"]) is int and state["serial"] >= 1, "invalid_serial")
    require(len(state["hand"]) <= 10, "hand_full")
    require(len(state["board"]) <= 7, "board_full")
    require(len(state["shop"]) <= SLOTS[state["tier"]], "shop_overflow")
    ids = [item["instance_id"] for item in instances(state)]
    require(all(type(item_id) is str and item_id for item_id in ids), "invalid_instance_id")
    require(len(set(ids)) == len(ids), "duplicate_instance_id")
    for zone in ("hand", "board"):
        for item in state[zone]:
            require(item["normal_id"] in ROWS, "unknown_card")
            require(type(item.get("golden", False)) is bool, "invalid_golden_flag")
            if "adapt_effects" in item:
                require(ROWS[item["normal_id"]]["client_race"] in {"MURLOC", "ALL"} and
                        item.get("adapt_grade") == "reference_injected" and
                        type(item["adapt_effects"]) is list and all(
                            type(entry) is dict and
                            set(entry) == {"option_id", "effect"} and
                            entry["option_id"] in ADAPT_DEFS and
                            entry["effect"] == ADAPT_DEFS[entry["option_id"]]["effect"]
                            for entry in item["adapt_effects"]),
                        "invalid_adapt_effects")
            else:
                require("adapt_grade" not in item, "invalid_adapt_grade")
            if "zerus_origin" in item:
                origin = item["zerus_origin"]
                require(type(origin) is dict and set(origin) ==
                        {"normal_id", "golden", "ticks", "active"}, "invalid_zerus_origin")
                require(origin["normal_id"] == "BGS_029" and
                        type(origin["golden"]) is bool and
                        origin["golden"] == item.get("golden", False) and
                        type(origin["ticks"]) is int and origin["ticks"] >= 1 and
                        type(origin["active"]) is bool and
                        origin["active"] == (zone == "hand") and
                        item["normal_id"] != "BGS_029" and
                        (not origin["golden"] or
                         (ROWS[item["normal_id"]]["golden_id"] is not None and
                          item.get("golden_form_key") ==
                          ROWS[item["normal_id"]]["golden_id"])),
                        "invalid_zerus_origin")
    for offer in state["shop"]:
        require(offer["card_id"] in ROWS, "unknown_card")
        require(ROWS[offer["card_id"]]["tier"] <= state["tier"], "offer_above_tier")
        require(type(offer["frozen"]) is bool, "invalid_frozen_flag")
        require(type(offer["slot"]) is int and 0 <= offer["slot"] < SLOTS[state["tier"]],
                "invalid_shop_slot")
    require(len({offer["slot"] for offer in state["shop"]}) == len(state["shop"]),
            "duplicate_shop_slot")
    for reward in state["pending_rewards"]:
        require(type(reward["target_tier"]) is int and 1 <= reward["target_tier"] <= 6,
                "invalid_reward_tier")


def find(zone: list[dict], item_id: str, code: str) -> tuple[int, dict]:
    for index, item in enumerate(zone):
        if item["instance_id"] == item_id:
            return index, item
    raise Rejected(code)


def validate_offers(state: dict, offers: list[dict], expected_count: int) -> None:
    require(type(offers) is list and len(offers) == expected_count, "wrong_offer_count")
    occupied = {item["instance_id"] for item in instances(state)}
    new_ids: set[str] = set()
    for offer in offers:
        require(type(offer) is dict, "invalid_offer")
        item_id, card_id = offer.get("instance_id"), offer.get("card_id")
        require(type(item_id) is str and item_id, "invalid_instance_id")
        require(item_id not in occupied and item_id not in new_ids, "duplicate_instance_id")
        require(card_id in ROWS, "unknown_card")
        require(ROWS[card_id]["tier"] <= state["tier"], "offer_above_tier")
        require(set(offer) == {"instance_id", "card_id"}, "invalid_offer")
        new_ids.add(item_id)


def fill_shop(state: dict, offers: list[dict]) -> None:
    slots = [slot for slot in range(SLOTS[state["tier"]])
             if slot not in {offer["slot"] for offer in state["shop"]}]
    validate_offers(state, offers, len(slots))
    state["shop"] += [{**offer, "slot": slot, "frozen": False}
                      for slot, offer in zip(slots, offers)]
    state["shop"].sort(key=lambda offer: offer["slot"])


def next_id(state: dict) -> str:
    item_id = f"ref-{state['serial']}"
    require(item_id not in {item["instance_id"] for item in instances(state)},
            "duplicate_instance_id")
    state["serial"] += 1
    return item_id


def resolve_triple(state: dict, card_id: str, events: list[dict]) -> None:
    # Board then hand is solely a deterministic reference choice.
    matches = [item for item in state["board"] + state["hand"]
               if item["normal_id"] == card_id and not item.get("golden", False)]
    require(len(matches) >= 3, "triple_missing_copies")
    used = matches[:3]
    require(not any(item.get("adapt_effects") for item in used),
            "unknown_adapt_triple_merge")
    require(not any(item.get("zerus_origin", {}).get("active", False) for item in matches),
            "unknown_zerus_triple_timing")
    used_ids = {item["instance_id"] for item in used}
    require(len(state["hand"]) - sum(item["instance_id"] in used_ids
                                     for item in state["hand"]) < 10, "hand_full")
    state["board"] = [item for item in state["board"] if item["instance_id"] not in used_ids]
    state["hand"] = [item for item in state["hand"] if item["instance_id"] not in used_ids]
    row = ROWS[card_id]
    buff_attack = sum(item.get("buff_attack", 0) for item in used)
    buff_health = sum(item.get("buff_health", 0) for item in used)
    attachments = [attachment for item in used for attachment in item.get("attachments", [])]
    golden = {
        "instance_id": next_id(state), "normal_id": card_id, "golden": True,
        "golden_form_key": row["golden_id"] or f"reference:{card_id}:golden",
        "golden_evidence": row["golden_evidence"], "origin": "shop_triple",
        "attack": row["golden_attack"] + buff_attack,
        "health": row["golden_health"] + buff_health,
        "buff_attack": buff_attack, "buff_health": buff_health,
        "attachments": attachments, "reward_pending": True,
    }
    state["hand"].append(golden)
    events.append({"type": "triple", "consumed": [item["instance_id"] for item in used],
                   "created": golden["instance_id"], "form": golden["golden_form_key"]})


def maybe_triple(state: dict, card_id: str, events: list[dict]) -> None:
    copies = sum(item["normal_id"] == card_id and not item.get("golden", False)
                 for item in state["board"] + state["hand"])
    if copies >= 3:
        resolve_triple(state, card_id, events)


def transform_held_zerus(state: dict, action: dict, events: list[dict]) -> None:
    """Reference-only next-recruit tick; every held source needs one injected index."""
    held = [item for item in state["hand"] if item["normal_id"] == "BGS_029" or
            item.get("zerus_origin", {}).get("active", False)]
    require(type(action.get("exact_mode", False)) is bool, "invalid_exact_mode")
    if held and action.get("exact_mode", False):
        raise Rejected("unknown_zerus_transform_pool_and_tick_phase")
    draws = action.get("zerus_draws", {})
    require(type(draws) is dict, "invalid_zerus_draws")
    require(set(draws) == {item["instance_id"] for item in held}, "zerus_draws_mismatch")
    for item in held:
        draw = draws[item["instance_id"]]
        require(type(draw) is dict and set(draw) == {"index", "grade"},
                "invalid_zerus_draw")
        require(draw["grade"] == "reference_injected", "ungraded_zerus_draw")
        index = draw["index"]
        require(type(index) is int and 0 <= index < len(ZERUS_POOL),
                "invalid_zerus_candidate_index")
        target_id = ZERUS_POOL[index]
        target = ROWS[target_id]
        golden = item.get("golden", False)
        current = ROWS[item["normal_id"]]
        require(item.get("attack", current["golden_attack" if golden else "normal_attack"]) ==
                current["golden_attack" if golden else "normal_attack"] and
                item.get("health", current["golden_health" if golden else "normal_health"]) ==
                current["golden_health" if golden else "normal_health"],
                "ambiguous_zerus_enchantments")
        require(not item.get("buff_attack", 0) and not item.get("buff_health", 0) and
                not item.get("attachments", []), "ambiguous_zerus_enchantments")
        require(not item.get("reward_pending", False) or golden,
                "invalid_zerus_reward")
        if golden:
            require(target["golden_id"] is not None, "unresolved_zerus_golden_form")
        else:
            others = [other for other in state["hand"] + state["board"]
                      if other["instance_id"] != item["instance_id"] and
                      other["normal_id"] == target_id and not other.get("golden", False)]
            require(len(others) < 2, "unknown_zerus_triple_timing")
        old_id = item["normal_id"]
        origin = item.get("zerus_origin") or {"normal_id": "BGS_029", "golden": golden,
                                              "ticks": 0, "active": True}
        item["normal_id"] = target_id
        item["golden"] = golden
        item["attack"] = target["golden_attack" if golden else "normal_attack"]
        item["health"] = target["golden_health" if golden else "normal_health"]
        if golden:
            item["golden_form_key"] = target["golden_id"]
            item["golden_evidence"] = target["golden_evidence"]
        origin["ticks"] += 1
        item["zerus_origin"] = origin
        events.append({"type": "zerus_transform", "instance_id": item["instance_id"],
                       "from_card_id": old_id, "to_card_id": target_id,
                       "candidate_index": index, "form": "golden" if golden else "normal",
                       "form_key": target["golden_id"] if golden else target_id,
                       "tick_round": state["round"], "grade": draw["grade"]})


def discover_murlocs_on_play(state: dict, source: dict, action: dict,
                             events: list[dict]) -> None:
    """Resolve injected Lookout offers with at most one Brann repeat source."""
    offers = action.get("murloc_discovers", [])
    require(type(offers) is list, "invalid_murloc_discover_input")
    def has_other_fish() -> bool:
        return any(item["instance_id"] != source["instance_id"] and
                   ROWS[item["normal_id"]]["client_race"] in {"MURLOC", "ALL"}
                   for item in state["board"])

    other_fish = has_other_fish()
    if not other_fish:
        require(not offers, "unexpected_murloc_discover")
        return
    require(type(action.get("exact_mode", False)) is bool, "invalid_exact_mode")
    require(not action.get("exact_mode", False),
            "unknown_murloc_discover_candidates_and_order")
    branns = [item for item in state["board"] if item["normal_id"] == "LOE_077"]
    require(len(branns) <= 1, "unknown_multi_repeat_order")
    base_attempts = 2 if source.get("golden", False) else 1
    repeat_count = (3 if branns[0].get("golden", False) else 2) if branns else 1
    attempts = base_attempts * repeat_count
    require(len(offers) == attempts, "wrong_murloc_discover_count")
    for offer_number, offer in enumerate(offers, start=1):
        require(type(offer) is dict and
                set(offer) == {"option_indexes", "choice_index", "grade"},
                "invalid_murloc_discover_offer")
        require(offer["grade"] == "reference_injected", "ungraded_murloc_discover")
        indexes = offer["option_indexes"]
        require(type(indexes) is list and len(indexes) == 3 and
                all(type(index) is int and 0 <= index < len(MURLOC_POOL)
                    for index in indexes), "invalid_murloc_option_indexes")
        require(len(set(indexes)) == 3, "duplicate_murloc_options")
        choice = offer["choice_index"]
        require(type(choice) is int and 0 <= choice < 3, "invalid_murloc_choice")
        options = [MURLOC_POOL[index] for index in indexes]
        chosen = options[choice]
        acquired = len(state["hand"]) < 10
        if acquired:
            item_id = next_id(state)
            state["hand"].append({"instance_id": item_id, "normal_id": chosen,
                                  "golden": False, "origin": "murloc_discover"})
        events.append({"type": "murloc_discover", "source_instance_id": source["instance_id"],
                       "offer_number": offer_number, "option_indexes": indexes,
                       "options": options, "choice_index": choice, "chosen": chosen,
                       "acquired": acquired,
                       "battlecry_trigger": (offer_number - 1) // base_attempts + 1,
                       "discover_number_in_trigger": (offer_number - 1) % base_attempts + 1,
                       "repeat_source_instance_id": branns[0]["instance_id"] if branns else None,
                       "grade": offer["grade"]})
        if acquired:
            maybe_triple(state, chosen, events)
        if branns and offer_number < attempts:
            require(any(item["instance_id"] == source["instance_id"]
                        for item in state["board"]) and has_other_fish(),
                    "unknown_repeated_discover_board_state")


def adapt_murlocs_on_play(state: dict, source: dict, action: dict,
                          events: list[dict]) -> None:
    """Resolve injected choices after play, with at most one Brann repeat source."""
    offers = action.get("adapt_offers", [])
    require(type(offers) is list, "invalid_adapt_input")
    targets = [item for item in state["board"]
               if ROWS[item["normal_id"]]["client_race"] in {"MURLOC", "ALL"}]
    if not targets:
        require(not offers, "unexpected_adapt_offer")
        return
    require(type(action.get("exact_mode", False)) is bool, "invalid_exact_mode")
    require(not action.get("exact_mode", False), "unknown_adapt_options_and_order")
    branns = [item for item in state["board"] if item["normal_id"] == "LOE_077"]
    require(len(branns) <= 1, "unknown_multi_repeat_order")
    base_attempts = 2 if source.get("golden", False) else 1
    repeat_count = (3 if branns[0].get("golden", False) else 2) if branns else 1
    attempts = base_attempts * repeat_count
    require(len(offers) == attempts, "wrong_adapt_offer_count")
    target_ids = [item["instance_id"] for item in targets]
    for offer_number, offer in enumerate(offers, start=1):
        require(type(offer) is dict and
                set(offer) == {"option_indexes", "choice_index", "grade"},
                "invalid_adapt_offer")
        require(offer["grade"] == "reference_injected", "ungraded_adapt_offer")
        indexes = offer["option_indexes"]
        require(type(indexes) is list and len(indexes) == 3 and
                all(type(index) is int and 0 <= index < len(ADAPT_POOL)
                    for index in indexes), "invalid_adapt_option_indexes")
        require(len(set(indexes)) == 3, "duplicate_adapt_options")
        choice = offer["choice_index"]
        require(type(choice) is int and 0 <= choice < 3, "invalid_adapt_choice")
        options = [ADAPT_POOL[index] for index in indexes]
        chosen = options[choice]
        effect = ADAPT_DEFS[chosen]["effect"]
        for item in targets:
            item["adapt_grade"] = "reference_injected"
            item.setdefault("adapt_effects", []).append(
                {"option_id": chosen, "effect": copy.deepcopy(effect)})
            if effect["kind"] == "stat_buff":
                item["buff_attack"] = item.get("buff_attack", 0) + effect["attack"]
                item["buff_health"] = item.get("buff_health", 0) + effect["health"]
        events.append({"type": "adapt", "source_instance_id": source["instance_id"],
                       "offer_number": offer_number, "option_indexes": indexes,
                       "options": options, "choice_index": choice, "chosen": chosen,
                       "effect": copy.deepcopy(effect), "targets": target_ids,
                       "battlecry_trigger": (offer_number - 1) // base_attempts + 1,
                       "adapt_number_in_trigger": (offer_number - 1) % base_attempts + 1,
                       "repeat_source_instance_id": branns[0]["instance_id"] if branns else None,
                       "grade": offer["grade"]})


def coldlight_health_on_play(state: dict, source: dict, action: dict,
                             events: list[dict]) -> None:
    """Apply the printed other-Murloc health buff in a bounded play order."""
    require(type(action.get("exact_mode", False)) is bool, "invalid_exact_mode")
    targets = [item for item in state["board"]
               if item["instance_id"] != source["instance_id"] and
               ROWS[item["normal_id"]]["client_race"] in {"MURLOC", "ALL"}]
    if not targets:
        return
    require(not action.get("exact_mode", False), "unknown_coldlight_event_order")
    branns = [item for item in state["board"] if item["normal_id"] == "LOE_077"]
    require(len(branns) <= 1, "unknown_multi_repeat_order")
    repeats = (3 if branns[0].get("golden", False) else 2) if branns else 1
    health_delta = 4 if source.get("golden", False) else 2
    target_ids = [item["instance_id"] for item in targets]
    for trigger in range(1, repeats + 1):
        for item in targets:
            item["buff_health"] = item.get("buff_health", 0) + health_delta
        events.append({"type": "coldlight_health_buff",
                       "source_instance_id": source["instance_id"],
                       "battlecry_trigger": trigger,
                       "repeat_source_instance_id": branns[0]["instance_id"] if branns else None,
                       "health_delta": health_delta, "targets": target_ids,
                       "grade": "reference_rule"})


def rockpool_buff_on_play(state: dict, source: dict, action: dict,
                          events: list[dict]) -> None:
    """Resolve one injected other-Murloc target per bounded battlecry."""
    targets = action.get("rockpool_targets", [])
    require(type(targets) is list, "invalid_rockpool_targets")
    require(type(action.get("exact_mode", False)) is bool, "invalid_exact_mode")
    require(not action.get("exact_mode", False), "unknown_rockpool_target_timing")
    eligible = {item["instance_id"]: item for item in state["board"]
                if item["instance_id"] != source["instance_id"] and
                ROWS[item["normal_id"]]["client_race"] in {"MURLOC", "ALL"}}
    if not eligible:
        require(not targets, "unexpected_rockpool_target")
        return
    branns = [item for item in state["board"] if item["normal_id"] == "LOE_077"]
    require(len(branns) <= 1, "unknown_multi_repeat_order")
    repeats = (3 if branns[0].get("golden", False) else 2) if branns else 1
    require(len(targets) == repeats, "wrong_rockpool_target_count")
    amount = 2 if source.get("golden", False) else 1
    for trigger, target in enumerate(targets, start=1):
        require(type(target) is dict and set(target) == {"instance_id", "grade"},
                "invalid_rockpool_target_input")
        require(target["grade"] == "reference_injected", "ungraded_rockpool_target")
        target_id = target["instance_id"]
        require(type(target_id) is str, "invalid_rockpool_target")
        require(target_id != source["instance_id"], "unknown_rockpool_self_target")
        require(target_id in eligible, "invalid_rockpool_target")
        item = eligible[target_id]
        item["buff_attack"] = item.get("buff_attack", 0) + amount
        item["buff_health"] = item.get("buff_health", 0) + amount
        events.append({"type": "rockpool_buff", "source_instance_id": source["instance_id"],
                       "battlecry_trigger": trigger, "target_instance_id": target_id,
                       "repeat_source_instance_id": branns[0]["instance_id"] if branns else None,
                       "buff_attack": amount, "buff_health": amount,
                       "grade": "reference_injected"})


def run_action(original: dict, action: dict) -> tuple[dict, list[dict], str | None]:
    state = copy.deepcopy(original)
    events: list[dict] = []
    try:
        normalize_shop_slots(state)
        validate_state(state)
        op = action.get("op")
        require(op in {entry["op"] for entry in RULES["actions"]}, "unknown_op")
        if op == "buy":
            index, offer = find(state["shop"], action.get("instance_id"), "offer_missing")
            require(state["coins"] >= 3, "insufficient_coins")
            require(len(state["hand"]) < 10, "hand_full")
            state["coins"] -= 3
            state["shop"].pop(index)
            state["hand"].append({"instance_id": offer["instance_id"],
                                  "normal_id": offer["card_id"], "golden": False})
            events.append({"type": "buy", "instance_id": offer["instance_id"],
                           "card_id": offer["card_id"]})
            maybe_triple(state, offer["card_id"], events)
        elif op == "sell":
            index, item = find(state["board"], action.get("instance_id"), "board_item_missing")
            state["board"].pop(index)
            state["coins"] = min(10, state["coins"] + 1)
            events.append({"type": "sell", "instance_id": item["instance_id"]})
        elif op == "refresh":
            require(state["coins"] >= 1, "insufficient_coins")
            frozen = [offer for offer in state["shop"] if offer["frozen"]]
            retained_ids = [offer["instance_id"] for offer in frozen]
            state["shop"] = frozen
            fill_shop(state, action.get("offers"))
            state["coins"] -= 1
            events.append({"type": "refresh", "retained": retained_ids})
        elif op == "freeze":
            require(bool(state["shop"]), "empty_shop")
            frozen = any(not offer["frozen"] for offer in state["shop"])
            for offer in state["shop"]:
                offer["frozen"] = frozen
            events.append({"type": "freeze", "frozen": frozen})
        elif op == "upgrade":
            require(state["tier"] < 6, "tier_cap")
            target = state["tier"] + 1
            cost = max(0, BASE_COSTS[target] - state["skipped_rounds"]
                       - state["hero_discount"])
            require(state["coins"] >= cost, "insufficient_coins")
            state["coins"] -= cost
            state["tier"] = target
            state["skipped_rounds"] = 0
            state["hero_discount"] = 0
            state["upgraded_this_round"] = True
            events.append({"type": "upgrade", "target_tier": target, "paid": cost})
        elif op == "resolve_triple":
            require(action.get("card_id") in ROWS, "unknown_card")
            resolve_triple(state, action["card_id"], events)
        elif op == "play":
            index, item = find(state["hand"], action.get("instance_id"), "hand_item_missing")
            require(len(state["board"]) < 7, "board_full")
            position = action.get("position", len(state["board"]))
            require(type(position) is int and 0 <= position <= len(state["board"]),
                    "invalid_position")
            state["hand"].pop(index)
            if "zerus_origin" in item:
                item["zerus_origin"]["active"] = False
            state["board"].insert(position, item)
            events.append({"type": "play", "instance_id": item["instance_id"]})
            if item.get("golden") and item.get("reward_pending", False):
                target = min(6, state["tier"] + 1)
                item["reward_pending"] = False
                state["pending_rewards"].append({"source_instance_id": item["instance_id"],
                                                  "target_tier": target})
                events.append({"type": "queue_discover", "target_tier": target})
            if item["normal_id"] == "BGS_020":
                discover_murlocs_on_play(state, item, action, events)
            else:
                require("murloc_discovers" not in action, "unexpected_murloc_discover")
            if item["normal_id"] == "BGS_031":
                adapt_murlocs_on_play(state, item, action, events)
            else:
                require("adapt_offers" not in action, "unexpected_adapt_offer")
            if item["normal_id"] == "EX1_103":
                coldlight_health_on_play(state, item, action, events)
            if item["normal_id"] == "UNG_073":
                rockpool_buff_on_play(state, item, action, events)
            else:
                require("rockpool_targets" not in action, "unexpected_rockpool_target")
        elif op == "triple_discover":
            require(bool(state["pending_rewards"]), "reward_missing")
            require(len(state["hand"]) < 10, "hand_full")
            tier = state["pending_rewards"][0]["target_tier"]
            options = action.get("options")
            require(type(options) is list and len(options) == 3 and
                    len(set(options)) == 3, "invalid_discover_options")
            require(all(option in ROWS and ROWS[option]["tier"] == tier
                        for option in options), "invalid_discover_candidate")
            chosen = action.get("chosen")
            require(chosen in options, "choice_not_offered")
            item_id = next_id(state)
            state["pending_rewards"].pop(0)
            state["hand"].append({"instance_id": item_id, "normal_id": chosen,
                                  "golden": False})
            events.append({"type": "discover", "card_id": chosen, "target_tier": tier})
            maybe_triple(state, chosen, events)
        elif op == "advance_round":
            frozen = [offer for offer in state["shop"] if offer["frozen"]]
            retained_ids = [offer["instance_id"] for offer in frozen]
            state["shop"] = frozen
            fill_shop(state, action.get("offers"))
            for offer in frozen:
                offer["frozen"] = False
            if not state["upgraded_this_round"]:
                state["skipped_rounds"] += 1
            state["round"] += 1
            state["coins"] = min(10, state["round"] + 2)
            state["upgraded_this_round"] = False
            events.append({"type": "advance_round", "retained": retained_ids})
            for item in state["board"]:
                effects = item.get("adapt_effects", [])
                expired = [entry for entry in effects
                           if entry["option_id"] == "UNG_999t10"]
                if expired:
                    remaining = [entry for entry in effects
                                 if entry["option_id"] != "UNG_999t10"]
                    if remaining:
                        item["adapt_effects"] = remaining
                    else:
                        item.pop("adapt_effects")
                        item.pop("adapt_grade")
                    events.append({"type": "adapt_expired",
                                   "instance_id": item["instance_id"],
                                   "option_id": "UNG_999t10", "count": len(expired)})
            transform_held_zerus(state, action, events)
        validate_state(state)
        return state, events, None
    except (Rejected, KeyError, TypeError) as exc:
        return original, [], str(exc) if isinstance(exc, Rejected) else "invalid_action"


def project(state: dict) -> dict:
    return {
        "phase": state["phase"], "round": state["round"], "coins": state["coins"],
        "tier": state["tier"], "skipped_rounds": state["skipped_rounds"],
        "upgraded_this_round": state["upgraded_this_round"],
        "hero_discount": state["hero_discount"], "serial": state["serial"],
        "hand_ids": [item["instance_id"] for item in state["hand"]],
        "board_ids": [item["instance_id"] for item in state["board"]],
        "shop_ids": [item["instance_id"] for item in state["shop"]],
        "frozen_ids": [item["instance_id"] for item in state["shop"] if item["frozen"]],
        "pending_target_tiers": [item["target_tier"] for item in state["pending_rewards"]],
        "hand_cards": state["hand"], "board_cards": state["board"],
    }


def matches(actual: object, expected: object) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and matches(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            matches(a, e) for a, e in zip(actual, expected))
    return actual == expected


def main() -> None:
    vectors = load("historical-recruitment-vectors.json")
    zerus_vectors = load("historical-recruitment-zerus-vectors.json")
    murloc_vectors = load("historical-recruitment-murloc-vectors.json")
    adapt_vectors = load("historical-recruitment-adapt-vectors.json")
    coldlight_vectors = load("historical-recruitment-coldlight-vectors.json")
    rockpool_vectors = load("historical-recruitment-rockpool-vectors.json")
    assert RULES["mode"] == vectors["mode"] == PARAMETERS["rule_set"]
    assert zerus_vectors["mode"] == RULES["mode"]
    assert murloc_vectors["mode"] == RULES["mode"]
    assert adapt_vectors["mode"] == RULES["mode"]
    assert coldlight_vectors["mode"] == RULES["mode"]
    assert rockpool_vectors["mode"] == RULES["mode"]
    assert RULES["build"] == vectors["build"] == PARAMETERS["build"] == 35747
    assert zerus_vectors["build"] == 35747
    assert murloc_vectors["build"] == 35747
    assert adapt_vectors["build"] == 35747
    assert coldlight_vectors["build"] == 35747
    assert rockpool_vectors["build"] == 35747
    assert all(value == "unknown" for value in coldlight_vectors["historical_unknown"].values())
    assert all(value == "unknown" for value in rockpool_vectors["historical_unknown"].values())
    assert all(value == "unknown" for value in RULES["historical_unknown"].values())
    assert len(ROWS) == 81 and len([r for r in ROWS.values() if r["golden_id"] is None]) == 13
    assert (ROWS["EX1_103"]["normal_effect_summary"],
            ROWS["EX1_103"]["golden_id"],
            ROWS["EX1_103"]["golden_effect_summary"]) == (
                "打出时其他己方鱼人各增加2生命", "TB_BaconUps_064",
                "打出时其他己方鱼人各增加4生命")
    assert (ROWS["LOE_077"]["normal_effect_summary"],
            ROWS["LOE_077"]["golden_id"],
            ROWS["LOE_077"]["golden_effect_summary"]) == (
                "己方战吼结算2遍", "TB_BaconUps_045", "己方战吼结算3遍")
    assert (ROWS["UNG_073"]["normal_effect_summary"],
            ROWS["UNG_073"]["golden_id"],
            ROWS["UNG_073"]["golden_effect_summary"]) == (
                "打出时指定一名己方鱼人，使其增加1/1", "TB_BaconUps_061",
                "打出时指定一名己方鱼人，使其增加2/2")
    assert ZERUS["build"] == 35747 and ZERUS["candidate_grade"] == "reference_design_only"
    assert len(ZERUS_POOL) == len(set(ZERUS_POOL)) == 80
    assert ZERUS_POOL == [row["normal_id"] for row in
                          load("historical-card-pool.json")["rows"]
                          if row["normal_id"] != "BGS_029"]
    assert len([cid for cid in ZERUS_POOL if ROWS[cid]["golden_id"] is not None]) == 67
    assert ZERUS["golden_unresolved_ids"] == [cid for cid in ZERUS_POOL
                                               if ROWS[cid]["golden_id"] is None]
    assert all(value == "unknown" for value in ZERUS["historical_unknown"].values())
    assert MURLOC["build"] == 35747 and MURLOC["candidate_grade"] == "reference_design_only"
    assert len(MURLOC_POOL) == len(set(MURLOC_POOL)) == 9
    assert MURLOC_POOL == [row["normal_id"] for row in
                           load("historical-card-pool.json")["rows"]
                           if row["client_race"] in {"MURLOC", "ALL"}]
    assert all(value == "unknown" for value in MURLOC["historical_unknown"].values())
    assert ADAPT["build"] == 35747 and ADAPT["unverified"] is True
    assert len(ADAPT_POOL) == len(set(ADAPT_POOL)) == len(ADAPT_DEFS) == 10
    assert set(ADAPT_POOL) == set(ADAPT_DEFS)
    assert ADAPT["historical_unknown"]["adapt_options"] == "unknown"
    seen: set[str] = set()
    used_ops: set[str] = set()
    cases = (vectors["cases"] + zerus_vectors["cases"] + murloc_vectors["cases"] +
             adapt_vectors["cases"] + coldlight_vectors["cases"] + rockpool_vectors["cases"])
    for case in cases:
        assert case["id"] not in seen, case["id"]
        seen.add(case["id"])
        assert case["grade"] == "reference_only", case["id"]
        state = {**initial_state(), **copy.deepcopy(case.get("initial", {}))}
        assert ("actions" in case) != ("action" in case), case["id"]
        actions = copy.deepcopy(case["actions"] if "actions" in case else [case["action"]])
        assert actions and all(type(action) is dict for action in actions), case["id"]
        used_ops.update(action["op"] for action in actions)
        before = copy.deepcopy(state)
        actions_before = copy.deepcopy(actions)
        events = []
        error = None
        for action in actions:
            after, emitted, error = run_action(state, action)
            if error:
                assert len(actions) == 1, case["id"]
                break
            state = after
            events.extend(emitted)
        assert actions == actions_before, case["id"]
        assert error == case.get("error"), (case["id"], error)
        if error:
            assert after == before and not events, case["id"]
        else:
            assert matches(project(state), case["expect_state"]), (case["id"], project(state))
            assert [event["type"] for event in events] == case["expect_events"], case["id"]
            assert matches(events, case.get("expect_event_details", events)), case["id"]
    assert {"buy", "sell", "refresh", "freeze", "upgrade", "resolve_triple",
            "play", "triple_discover", "advance_round"}.issubset(used_ops)
    missing = {normal_id for normal_id, row in ROWS.items() if row["golden_id"] is None}
    assert set(vectors["missing_golden_form_ids"]) == missing
    for normal_id in missing:
        state = initial_state()
        state["hand"] = [{"instance_id": item_id, "normal_id": normal_id}
                         for item_id in ("a", "b", "c")]
        after, events, error = run_action(state, {"op": "resolve_triple", "card_id": normal_id})
        assert error is None and [event["type"] for event in events] == ["triple"], normal_id
        golden = after["hand"][0]
        row = ROWS[normal_id]
        assert golden["golden_form_key"] == f"reference:{normal_id}:golden", normal_id
        assert (golden["attack"], golden["health"]) == (
            row["golden_attack"], row["golden_health"]), normal_id
        assert golden["golden_evidence"] == "inferred_from_triple_rule", normal_id
        assert golden["reward_pending"] and not after["pending_rewards"], normal_id
    print(f"recruitment reference vectors: {len(seen)} passed; "
          f"{len(missing)} missing-golden forms guarded; historical unknowns preserved")


if __name__ == "__main__":
    main()
