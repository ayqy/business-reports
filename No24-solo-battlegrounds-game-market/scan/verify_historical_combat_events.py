"""Run bounded strike events and bridge terminal survivors into lifecycle settlement."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import verify_historical_combat_lifecycle as lifecycle


ROOT = Path(__file__).resolve().parent
SIDES = ("left", "right")
KEYWORDS = {"taunt", "divine_shield", "poisonous", "cleave", "windfury", "stealth"}


class Rejected(Exception):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Rejected(code)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


RULES = load("historical-combat-events.json")
ROWS = {row["normal_id"]: row for row in load("historical-card-pool.json")["rows"]}
ADAPT = load("historical-random-reference.json")
ADAPT_DEFS = ADAPT["adapt_option_defs"]
ADAPT_KEYWORDS = {"TAUNT": "taunt", "WINDFURY": "windfury",
                  "DIVINE_SHIELD": "divine_shield", "POISONOUS": "poisonous",
                  "STEALTH": "stealth"}
ADAPT_PLANT = {"id": "UNG_999t2t1", "attack": 1, "health": 1,
               "keywords": [], "premium": False, "race": "NONE"}
ADAPT_SPORE_NODE = {"destination": "friendly",
                    "tokens": {"normal": ADAPT_PLANT, "golden": ADAPT_PLANT}}
FIXED = {node["normal_id"]: node
         for node in load("historical-fixed-token-nodes.json")["nodes"]}
TOKEN_FORMS = {form["id"]: form for node in FIXED.values()
               for form in node["tokens"].values()}
RANDOM_DEATH = {node["normal_id"]
                for node in load("historical-random-effect-shells.json")["nodes"]
                if node["trigger"] == "source_died"}
RANDOM_COST_RULES = load(RULES["random_cost_nodes_file"])
RANDOM_COST_NODES = {node["normal_id"]: node for node in RANDOM_COST_RULES["nodes"]}
COST_CANDIDATES = load(RULES["random_cost_candidates_file"])
RANDOM_LEGENDARY_RULES = load(RULES["legendary_nodes_file"])
RANDOM_LEGENDARY_NODES = {node["normal_id"]: node for node in RANDOM_LEGENDARY_RULES["nodes"]}
LEGENDARY_CANDIDATES = load(RULES["legendary_candidates_file"])
RANDOM_DEATHRATTLE_RULES = load(RULES["random_deathrattle_nodes_file"])
RANDOM_DEATHRATTLE_NODES = {node["normal_id"]: node
                            for node in RANDOM_DEATHRATTLE_RULES["nodes"]}
DEATHRATTLE_CANDIDATES = load(RULES["random_deathrattle_candidates_file"])
RANDOM_SUMMON_NODES = (RANDOM_COST_NODES | RANDOM_LEGENDARY_NODES |
                       RANDOM_DEATHRATTLE_NODES)
COMMUNITY_POOLS = load("historical-community-simulator-pools.json")
RANDOM_DEATH -= set(RANDOM_SUMMON_NODES)
COMPOSITE = load("historical-composite-nodes.json")["nodes"]
DEATH_BUFF_RULES = load(RULES["death_buff_nodes_file"])
DEATH_BUFFS = {node["normal_id"]: node for node in DEATH_BUFF_RULES["nodes"]}
KANGOR_RULES = load(RULES["kangor_nodes_file"])
KANGOR_NODES = {node["normal_id"]: node for node in KANGOR_RULES["nodes"]}
OTHER_DEATH = {node["normal_id"] for node in COMPOSITE
               if node["family"] in {"deathrattle_team_buff", "first_dead_mechs"}} - (
                   set(DEATH_BUFFS) | set(KANGOR_NODES))
UNCOMPILED_PASSIVES = set(RULES["uncompiled_combat_passives"])
ATTACK_RULES = load(RULES["attack_nodes_file"])
ATTACK_NODES = {node["normal_id"]: node for node in ATTACK_RULES["nodes"]}
OTHER_ATTACK = {node["normal_id"] for node in COMPOSITE
                if node["family"] in {"overkill_summon", "attack_kill_growth"}} - set(ATTACK_NODES)
LISTENER_RULES = load(RULES["listener_nodes_file"])
LISTENERS = {node["normal_id"]: node for node in LISTENER_RULES["nodes"]}
AURA_RULES = load(RULES["aura_nodes_file"])
AURAS = {node["normal_id"]: node for node in AURA_RULES["nodes"]
         if node["trigger"] == "while_alive"}
SHIELD_LISTENERS = {node["normal_id"]: node for node in AURA_RULES["nodes"]
                    if node["trigger"] == "friendly_shield_lost"}
RACE_TAGS = {"BEAST": "beast", "MECHANICAL": "mech",
             "DEMON": "demon", "MURLOC": "murloc"}


def checked_adapt_effects(item: dict) -> list[dict]:
    effects = item.get("adapt_effects", [])
    require(type(effects) is list, "invalid_adapt_effects")
    if effects:
        require(item.get("card_id") in ROWS and
                item.get("adapt_grade") == "reference_injected" and
                ROWS[item["card_id"]]["client_race"] in {"MURLOC", "ALL"},
                "ungraded_adapt_effects")
    else:
        require("adapt_grade" not in item, "invalid_adapt_grade")
    for entry in effects:
        require(type(entry) is dict and set(entry) == {"option_id", "effect"} and
                entry["option_id"] in ADAPT_DEFS and
                entry["effect"] == ADAPT_DEFS[entry["option_id"]]["effect"],
                "invalid_adapt_effects")
    return effects


def adapt_keywords(effects: list[dict]) -> set[str]:
    result: set[str] = set()
    for entry in effects:
        effect = entry["effect"]
        if effect["kind"] in {"grant_keyword", "grant_keyword_until_next_turn"}:
            result.add(ADAPT_KEYWORDS[effect["keyword"]])
    return result


def unit_from_snapshot(item: dict, trait: dict) -> dict:
    card_id = item["card_id"]
    keywords = trait["keywords"]
    require(type(keywords) is list and len(set(keywords)) == len(keywords) and
            set(keywords) <= KEYWORDS, "unsupported_keyword")
    anchor = RULES["keyword_anchors"].get(card_id)
    adapted = "adapt_effects" in item
    effects = checked_adapt_effects(item) if adapted else []
    if adapted:
        require(item.get("origin") != "recruit_token" and
                set(keywords) == set(anchor or []) | adapt_keywords(effects) and
                trait.get("grade") == "reference_injected",
                "adapt_keyword_mismatch")
    elif anchor is not None and item.get("origin") != "recruit_token":
        require("adapt_grade" not in item, "invalid_adapt_grade")
        require(set(keywords) == set(anchor) and trait.get("grade") == "client_35747",
                "keyword_anchor_mismatch")
    else:
        require("adapt_grade" not in item, "invalid_adapt_grade")
        require(trait.get("grade") == "reference_injected", "ungraded_keywords")
    if item.get("origin") == "recruit_token":
        require(card_id in TOKEN_FORMS, "unknown_recruit_token")
        form = TOKEN_FORMS[card_id]
        attack, health = form["attack"], form["health"]
        require(item.get("tier_grade") == "reference_injected" and
                type(item.get("damage_tier")) is int and
                0 <= item["damage_tier"] <= 6, "ungraded_token_tier")
        origin = "recruit_token"
        race = form["race"]
    else:
        require(card_id in ROWS, "unknown_card")
        row = ROWS[card_id]
        golden = item.get("golden", False)
        require(type(golden) is bool, "invalid_golden_flag")
        attack = row["golden_attack"] if golden else row["normal_attack"]
        health = row["golden_health"] if golden else row["normal_health"]
        origin = "board"
        race = row["client_race"]
    attack += item.get("buff_attack", 0)
    health += item.get("buff_health", 0)
    require(type(attack) is int and attack >= 0 and type(health) is int and health > 0,
            "invalid_combat_stats")
    result = {"instance_id": item["instance_id"], "card_id": card_id,
              "attack": attack, "health": health, "max_health": health,
              "keywords": keywords.copy(),
              "golden": item.get("golden", False), "origin": origin, "race": race,
              "aura_attack": 0, "aura_health": 0}
    if adapted:
        result["adapt_effects"] = copy.deepcopy(effects)
        result["adapt_grade"] = "reference_injected"
        result["untargetable_by_spell_or_hero_power"] = any(
            entry["effect"]["kind"] == "untargetable_by_spell_or_hero_power"
            for entry in effects)
    if origin == "recruit_token":
        result["damage_tier"] = item["damage_tier"]
        result["tier_grade"] = item["tier_grade"]
    return result


def from_snapshot(snapshot: dict, traits: dict, first_side: str) -> dict:
    require(first_side in SIDES, "invalid_first_side")
    boards: dict[str, list[dict]] = {}
    ids: list[str] = []
    for side in SIDES:
        board = snapshot[side]["board"]
        require(len(board) <= 7, "board_overflow")
        boards[side] = []
        for item in board:
            item_id = item["instance_id"]
            require(item_id in traits, "missing_keyword_input")
            boards[side].append(unit_from_snapshot(item, traits[item_id]))
            ids.append(item_id)
    require(len(set(ids)) == len(ids), "duplicate_instance_id")
    state = {"phase": "terminal" if not boards["left"] or not boards["right"] else "combat",
            "boards": boards, "turn": first_side, "cursor": {"left": 0, "right": 0},
            "pending_extra_attack": None,
            "generated": {"left": [], "right": []}, "initial_ids": ids,
            "mech_death_history": {"left": [], "right": []}, "death_batch_serial": 0,
            "serial": 1, "event_log": []}
    recompute_auras(state, [], initial=True)
    return state


def validate_state(state: dict) -> None:
    require(state["phase"] in {"combat", "terminal"}, "invalid_phase")
    require(state["turn"] in SIDES, "invalid_turn")
    require(type(state["serial"]) is int and state["serial"] >= 1, "invalid_serial")
    require(type(state["initial_ids"]) is list and
            len(set(state["initial_ids"])) == len(state["initial_ids"]),
            "invalid_initial_ids")
    require(type(state["death_batch_serial"]) is int and
            state["death_batch_serial"] >= 0, "invalid_death_batch_serial")
    require(set(state["mech_death_history"]) == set(SIDES), "invalid_mech_history")
    for side in SIDES:
        history = state["mech_death_history"][side]
        require(type(history) is list and len(history) <= 100 and
                all(type(entry["batch_id"]) is int and
                    1 <= entry["batch_id"] <= state["death_batch_serial"] and
                    entry["race"] in {"MECHANICAL", "ALL"}
                    for entry in history), "invalid_mech_history")
    pending = state["pending_extra_attack"]
    if pending is not None:
        require(type(pending) is dict and
                set(pending) == {"side", "attacker_id", "remaining"} and
                pending["side"] == state["turn"] and pending["side"] in SIDES and
                type(pending["attacker_id"]) is str and
                type(pending["remaining"]) is int and pending["remaining"] == 1 and
                state["phase"] == "combat", "invalid_extra_attack")
    ids: list[str] = []
    for side in SIDES:
        board = state["boards"][side]
        require(type(board) is list and len(board) <= 7, "board_overflow")
        require(type(state["cursor"][side]) is int and state["cursor"][side] >= 0,
                "invalid_cursor")
        for unit in board:
            item_id = unit["instance_id"]
            require(type(item_id) is str and item_id, "invalid_instance_id")
            require(type(unit["attack"]) is int and unit["attack"] >= 0 and
                    type(unit["health"]) is int and unit["health"] > 0 and
                    type(unit["max_health"]) is int and
                    unit["max_health"] >= unit["health"], "invalid_combat_stats")
            require(type(unit["aura_attack"]) is int and unit["aura_attack"] >= 0 and
                    type(unit["aura_health"]) is int and unit["aura_health"] >= 0,
                    "invalid_aura_stats")
            require(set(unit["keywords"]) <= KEYWORDS, "unsupported_keyword")
            if "adapt_effects" in unit:
                checked_adapt_effects(unit)
                require(type(unit.get("untargetable_by_spell_or_hero_power")) is bool,
                        "invalid_adapt_targeting_flag")
            require(type(unit["race"]) is str and bool(unit["race"]), "invalid_race")
            ids.append(item_id)
    require(len(set(ids)) == len(ids), "duplicate_instance_id")
    if state["phase"] == "terminal":
        require(not state["boards"]["left"] or not state["boards"]["right"],
                "premature_terminal")
    if pending is not None:
        _, unit = find(state["boards"][pending["side"]], pending["attacker_id"],
                       "invalid_extra_attack")
        require(((unit["card_id"] in ATTACK_NODES and
                  ATTACK_NODES[unit["card_id"]]["family"] == "windfury_lowest_attack") or
                 "windfury" in unit["keywords"]) and
                unit["attack"] > 0,
                "invalid_extra_attack")


def find(board: list[dict], item_id: str, code: str) -> tuple[int, dict]:
    for index, unit in enumerate(board):
        if unit["instance_id"] == item_id:
            return index, unit
    raise Rejected(code)


def next_attacker(state: dict, side: str) -> dict:
    board = state["boards"][side]
    require(bool(board), "empty_attack_board")
    pending = state["pending_extra_attack"]
    if pending is not None:
        require(pending["side"] == side, "invalid_extra_attack")
        _, unit = find(board, pending["attacker_id"], "invalid_extra_attack")
        return unit
    start = state["cursor"][side] % len(board)
    for offset in range(len(board)):
        unit = board[(start + offset) % len(board)]
        if unit["attack"] > 0:
            return unit
    raise Rejected("no_attackable_minion")


def validate_attack_target(attacker: dict, enemy_board: list[dict],
                           target: dict, action: dict, events: list[dict]) -> None:
    visible = [unit for unit in enemy_board if "stealth" not in unit["keywords"]]
    require(bool(visible), "unknown_all_enemy_stealthed")
    require(target in visible, "stealth_target_forbidden")
    node = ATTACK_NODES.get(attacker["card_id"])
    if node is None or node["family"] != "windfury_lowest_attack":
        require("target_choice_grade" not in action, "unused_target_choice_grade")
        if any("taunt" in unit["keywords"] for unit in visible):
            require("taunt" in target["keywords"], "taunt_target_required")
        return
    require(node["target_selector"] == "enemy_lowest_current_attack",
            "unsupported_attack_selector")
    lowest = min(unit["attack"] for unit in visible)
    candidates = [unit for unit in visible if unit["attack"] == lowest]
    # The client card face does not settle the exception to Taunt. Keep the
    # reference transition inside positions where both rules agree.
    if any("taunt" in unit["keywords"] for unit in visible):
        require(all("taunt" in unit["keywords"] for unit in candidates),
                "zapp_taunt_conflict_unverified")
    require(any(unit["instance_id"] == target["instance_id"] for unit in candidates),
            "zapp_lowest_attack_required")
    if len(candidates) > 1:
        require(action.get("target_choice_grade") == "reference_injected",
                "zapp_tie_choice_ungraded")
        events.append({"type": "reference_target_choice",
                       "target": target["instance_id"],
                       "candidates": [unit["instance_id"] for unit in candidates]})
    else:
        require("target_choice_grade" not in action, "unused_target_choice_grade")


def aura_applies(selector: str, source: dict, target: dict,
                 source_index: int, target_index: int) -> bool:
    if selector == "friendly_adjacent":
        return abs(source_index - target_index) == 1
    if selector == "friendly_other_murloc":
        return source is not target and target["race"] in {"MURLOC", "ALL"}
    if selector == "friendly_taunt":
        return "taunt" in target["keywords"]
    if selector == "friendly_other_demon":
        return source is not target and target["race"] in {"DEMON", "ALL"}
    raise Rejected("unknown_aura_selector")


def recompute_auras(state: dict, events: list[dict], initial: bool = False) -> None:
    for side in SIDES:
        board = state["boards"][side]
        contributions = {unit["instance_id"]: [0, 0] for unit in board}
        # All sources are read from one pre-recompute board snapshot. If removing
        # health later kills a source, the next death batch repeats this pass.
        for source_index, source in enumerate(board):
            if source["health"] <= 0 or source["card_id"] not in AURAS:
                continue
            node = AURAS[source["card_id"]]
            values = params(source, node)
            for target_index, target in enumerate(board):
                if target["health"] > 0 and aura_applies(
                        node["target"], source, target, source_index, target_index):
                    contribution = contributions[target["instance_id"]]
                    contribution[0] += values["attack"]
                    contribution[1] += values["health"]
        for unit in board:
            if unit["health"] <= 0:
                continue
            attack, health = contributions[unit["instance_id"]]
            delta_attack = attack - unit["aura_attack"]
            delta_health = health - unit["aura_health"]
            unit["attack"] += delta_attack
            unit["health"] += delta_health
            unit["max_health"] += delta_health
            unit["aura_attack"], unit["aura_health"] = attack, health
            if (delta_attack or delta_health) and not initial:
                events.append({"type": "aura_change", "target": unit["instance_id"],
                               "attack": delta_attack, "health": delta_health})
                if unit["health"] <= 0:
                    events.append({"type": "aura_collapse", "target": unit["instance_id"]})


def notify_shield_lost(state: dict, side: str, target: dict,
                       events: list[dict]) -> None:
    for listener in state["boards"][side]:
        node = SHIELD_LISTENERS.get(listener["card_id"])
        if node is None or listener["health"] <= 0:
            continue
        values = params(listener, node)
        listener["attack"] += values["attack"]
        events.append({"type": "shield_listener_growth",
                       "listener": listener["instance_id"],
                       "shield_target": target["instance_id"],
                       "attack": values["attack"]})


def hit(state: dict, target_side: str, source: dict, target: dict,
        amount: int, events: list[dict],
        poison_enabled: bool = True) -> int:
    if amount == 0:
        return 0
    if "divine_shield" in target["keywords"]:
        target["keywords"].remove("divine_shield")
        events.append({"type": "shield_lost", "target": target["instance_id"]})
        notify_shield_lost(state, target_side, target, events)
        return 0
    target["health"] -= amount
    events.append({"type": "damage", "source": source["instance_id"],
                   "target": target["instance_id"], "amount": amount})
    if poison_enabled and "poisonous" in source["keywords"]:
        target["health"] = min(0, target["health"])
        events.append({"type": "poison_kill", "target": target["instance_id"]})
    return amount


def generated_id(state: dict) -> str:
    used = set(state["initial_ids"])
    used |= {unit["instance_id"] for side in SIDES for unit in state["boards"][side]}
    used |= {unit["instance_id"] for side in SIDES for unit in state["generated"][side]}
    while f"combat-{state['serial']}" in used:
        state["serial"] += 1
    item_id = f"combat-{state['serial']}"
    state["serial"] += 1
    return item_id


def live_listeners(state: dict, side: str, trigger: str) -> list[tuple[dict, dict]]:
    return [(unit, LISTENERS[unit["card_id"]])
            for unit in state["boards"][side]
            if unit["health"] > 0 and unit["card_id"] in LISTENERS and
            LISTENERS[unit["card_id"]]["trigger"] == trigger]


def live_race_listeners(state: dict, side: str, race: str,
                        event: str) -> list[tuple[dict, dict]]:
    tags = set(RACE_TAGS.values()) if race == "ALL" else {RACE_TAGS.get(race, "")}
    triggers = {"friendly_" + tag + "_" + event for tag in tags if tag}
    return [(unit, LISTENERS[unit["card_id"]])
            for unit in state["boards"][side]
            if unit["health"] > 0 and unit["card_id"] in LISTENERS and
            LISTENERS[unit["card_id"]]["trigger"] in triggers]


def params(unit: dict, node: dict) -> dict:
    return node["golden" if unit["golden"] else "normal"]


def validate_multipliers(state: dict) -> None:
    for side in SIDES:
        barons = live_listeners(state, side, "friendly_deathrattle")
        khadgars = live_listeners(state, side, "friendly_card_summon")
        require(len(barons) <= 1 and len(khadgars) <= 1,
                "multiple_multiplier_sources_unverified")
        require(not (barons and khadgars), "combined_multiplier_order_unverified")


def notify_summon(state: dict, destination: str, summoned: dict,
                  events: list[dict]) -> None:
    for listener, node in live_race_listeners(state, destination,
                                              summoned["race"], "summoned"):
        values = params(listener, node)
        operation = node["operation"]
        if operation == "grow_self":
            listener["attack"] += values["attack"]
            listener["health"] += values["health"]
            listener["max_health"] += values["health"]
            events.append({"type": "listener_growth", "listener": listener["instance_id"],
                           "trigger": "summon", "attack": values["attack"],
                           "health": values["health"]})
        elif operation == "buff_summoned":
            summoned["attack"] += values["attack"]
            summoned["health"] += values["health"]
            summoned["max_health"] += values["health"]
            events.append({"type": "summon_buff", "listener": listener["instance_id"],
                           "target": summoned["instance_id"], "attack": values["attack"],
                           "health": values["health"]})
        elif operation == "restore_self_shield":
            if "divine_shield" not in listener["keywords"]:
                listener["keywords"].append("divine_shield")
                events.append({"type": "shield_restored",
                               "listener": listener["instance_id"]})
        else:
            raise Rejected("unresolved_summon_listener")


def notify_death(state: dict, dead_side: str, dead: dict, action: dict,
                 context: dict, events: list[dict]) -> None:
    opposite = "right" if dead_side == "left" else "left"
    for listener, node in live_race_listeners(state, dead_side,
                                              dead["race"], "died"):
        values = params(listener, node)
        if node["operation"] == "grow_self":
            listener["attack"] += values["attack"]
            listener["health"] += values["health"]
            listener["max_health"] += values["health"]
            events.append({"type": "listener_growth", "listener": listener["instance_id"],
                           "trigger": "death", "attack": values["attack"],
                           "health": values["health"]})
        elif node["operation"] == "damage_injected_enemy":
            living = [unit for unit in state["boards"][opposite] if unit["health"] > 0]
            if not living:
                continue
            targets = action.get("listener_targets", [])
            require(type(targets) is list and context["target_index"] < len(targets),
                    "listener_target_missing")
            chosen = targets[context["target_index"]]
            context["target_index"] += 1
            require(type(chosen) is dict and
                    chosen.get("grade") == "reference_injected",
                    "ungraded_listener_target")
            target = next((unit for unit in living
                           if unit["instance_id"] == chosen.get("target_id")), None)
            require(target is not None, "invalid_listener_target")
            events.append({"type": "listener_damage", "listener": listener["instance_id"],
                           "target": target["instance_id"], "amount": values["damage"]})
            hit(state, opposite, listener, target, values["damage"],
                events, poison_enabled=False)
        else:
            raise Rejected("unresolved_death_listener")


def summon(state: dict, source: dict, source_side: str, node: dict, count: int,
           action: dict, insert_at: int, events: list[dict]) -> None:
    destination = source_side if node["destination"] == "friendly" else (
        "right" if source_side == "left" else "left")
    form = node["tokens"]["golden" if source["golden"] else "normal"]
    board = state["boards"][destination]
    khadgars = live_listeners(state, source_side, "friendly_card_summon")
    if khadgars:
        require(destination == source_side, "cross_side_multiplier_unverified")
        factor = params(*khadgars[0])["factor"]
        events.append({"type": "summon_multiplier",
                       "listener": khadgars[0][0]["instance_id"], "factor": factor})
        count *= factor
    require(count <= 100, "summon_count_limit")
    for _ in range(min(count, 100)):
        if len(board) >= 7:
            events.append({"type": "summon_dropped", "card_id": form["id"]})
            continue
        tier = action.get("token_tiers", {}).get(form["id"])
        require(type(tier) is int and 0 <= tier <= 6, "token_tier_missing")
        item_id = generated_id(state)
        unit = {"instance_id": item_id, "card_id": form["id"],
                "attack": form["attack"], "health": form["health"],
                "max_health": form["health"],
                "keywords": form["keywords"].copy(), "golden": bool(form["premium"]),
                "race": form["race"], "aura_attack": 0, "aura_health": 0,
                "origin": "combat_token", "source_instance_id": source["instance_id"],
                "source_side": source_side, "damage_tier": tier,
                "tier_grade": "reference_injected"}
        position = min(insert_at, len(board))
        board.insert(position, unit)
        insert_at = position + 1
        state["generated"][destination].append({
            key: unit[key] for key in ("instance_id", "card_id", "origin",
                                   "source_instance_id", "source_side",
                                   "damage_tier", "tier_grade")})
        events.append({"type": "summon", "instance_id": item_id,
                       "card_id": form["id"], "side": destination})
        recompute_auras(state, events)
        notify_summon(state, destination, unit, events)


def apply_death_buff(state: dict, dead_side: str, dead: dict,
                     node: dict, events: list[dict]) -> None:
    barons = live_listeners(state, dead_side, "friendly_deathrattle")
    times = params(*barons[0])["times"] if barons else 1
    if barons:
        events.append({"type": "deathrattle_repeat",
                       "listener": barons[0][0]["instance_id"], "times": times})
    values = params(dead, node)
    for repetition in range(1, times + 1):
        events.append({"type": "team_buff_trigger", "source": dead["instance_id"],
                       "repetition": repetition})
        for target in state["boards"][dead_side]:
            if target["health"] <= 0 or (node["target"] == "friendly_surviving_beasts" and
                                          target["race"] not in {"BEAST", "ALL"}):
                continue
            target["attack"] += values["attack"]
            target["health"] += values["health"]
            target["max_health"] += values["health"]
            events.append({"type": "team_buff", "source": dead["instance_id"],
                           "target": target["instance_id"], "repetition": repetition,
                           "attack": values["attack"], "health": values["health"]})


def resolve_random_summon(state: dict, side: str, index: int, dead: dict,
                          node: dict, action: dict, context: dict,
                          events: list[dict]) -> None:
    require(dead["instance_id"] in state["initial_ids"],
            "unknown_generated_random_source_chain")
    require(not live_listeners(state, side, "friendly_card_summon"),
            "unknown_random_khadgar_order")
    kind = {"summon_original_cost": "cost",
            "summon_legendary": "legendary",
            "summon_deathrattle": "deathrattle"}[node["family"]]
    candidates = {"cost": COST_CANDIDATES,
                  "legendary": LEGENDARY_CANDIDATES,
                  "deathrattle": DEATHRATTLE_CANDIDATES}[kind]
    pool = candidates["pools"][node["candidate_source"]]
    barons = live_listeners(state, side, "friendly_deathrattle")
    times = params(*barons[0])["times"] if barons else 1
    if barons:
        events.append({"type": "deathrattle_repeat",
                       "listener": barons[0][0]["instance_id"], "times": times})
    attempts = params(dead, node)["attempts"]
    insert_at = index
    for repetition in range(1, times + 1):
        events.append({"type": f"random_{kind}_trigger",
                       "source": dead["instance_id"], "repetition": repetition,
                       "requests": attempts, "pool": node["candidate_source"]})
        for request in range(1, attempts + 1):
            board = state["boards"][side]
            if len(board) >= 7:
                events.append({"type": f"random_{kind}_dropped",
                               "source": dead["instance_id"],
                               "repetition": repetition, "request": request})
                continue
            draws = action.get("random_draw_indexes", [])
            cursor = context["random_draw_index"]
            require(cursor < len(draws), "random_draw_missing")
            draw_index = draws[cursor]
            require(type(draw_index) is int and 0 <= draw_index < len(pool),
                    "random_draw_out_of_range")
            context["random_draw_index"] += 1
            candidate = pool[draw_index]
            card_id = candidate["id"]
            require(card_id in node["reference_supported_ids"],
                    "random_candidate_outside_bounded_subset")
            item_id = generated_id(state)
            unit = {"instance_id": item_id, "card_id": card_id,
                    "attack": candidate["attack"], "health": candidate["health"],
                    "max_health": candidate["health"], "keywords": [],
                    "golden": False, "race": candidate["race"],
                    "origin": "combat_generated_minion",
                    "source_instance_id": dead["instance_id"],
                    "source_side": side, "aura_attack": 0, "aura_health": 0}
            manifest = {"instance_id": item_id, "card_id": card_id,
                        "origin": "combat_generated_minion",
                        "source_instance_id": dead["instance_id"],
                        "source_side": side, "pool_grade": "reference_injected",
                        "candidate_grade": node["candidate_grade"],
                        "draw_grade": "reference_injected"}
            if kind == "cost":
                manifest["original_mana_cost"] = node["original_mana_cost"]
            elif kind == "legendary":
                manifest["client_rarity"] = candidate["client_rarity"]
            else:
                manifest["client_deathrattle_tag"] = candidate["client_deathrattle_tag"]
            position = min(insert_at, len(board))
            board.insert(position, unit)
            insert_at = position + 1
            state["generated"][side].append(manifest)
            require(len(state["generated"][side]) <= 100, "generated_limit")
            events.append({"type": f"random_{kind}_summon",
                           "instance_id": item_id, "card_id": card_id,
                           "source": dead["instance_id"], "side": side,
                           "pool_index": draw_index, "repetition": repetition,
                           "request": request})
            recompute_auras(state, events)
            notify_summon(state, side, unit, events)


def record_mech_deaths(state: dict, deaths: list[tuple[str, int, dict]]) -> None:
    state["death_batch_serial"] += 1
    batch_id = state["death_batch_serial"]
    for side, _, dead in deaths:
        if dead["race"] not in {"MECHANICAL", "ALL"}:
            continue
        attack = dead["attack"] - dead["aura_attack"]
        health = dead["max_health"] - dead["aura_health"]
        copy_state = ({"attack": attack, "health": health,
                       "keywords": dead["keywords"].copy()}
                      if attack >= 0 and health > 0 else None)
        entry = {"instance_id": dead["instance_id"],
                 "root_instance_id": dead.get("root_instance_id", dead["instance_id"]),
                 "card_id": dead["card_id"], "golden": dead["golden"],
                 "race": dead["race"], "origin": dead["origin"],
                 "batch_id": batch_id, "copy_state": copy_state}
        if "damage_tier" in dead:
            entry["damage_tier"] = dead["damage_tier"]
            entry["tier_grade"] = dead["tier_grade"]
        state["mech_death_history"][side].append(entry)
        require(len(state["mech_death_history"][side]) <= 100,
                "mech_death_history_limit")


def resolve_kangor(state: dict, side: str, index: int, dead: dict,
                   node: dict, events: list[dict]) -> None:
    history = state["mech_death_history"][side]
    require(not any(entry["batch_id"] == state["death_batch_serial"]
                    for entry in history), "unknown_mech_same_batch_with_kangor")
    require(len({entry["batch_id"] for entry in history}) == len(history),
            "unknown_mech_death_history_order")
    require(len({entry["root_instance_id"] for entry in history}) == len(history),
            "unknown_repeat_death_identity")
    require(not live_listeners(state, side, "friendly_card_summon"),
            "unknown_kangor_khadgar_order")
    require(dead["instance_id"] in state["initial_ids"],
            "unknown_generated_kangor_source")
    selected = history[:params(dead, node)["first_count"]]
    barons = live_listeners(state, side, "friendly_deathrattle")
    times = params(*barons[0])["times"] if barons else 1
    if barons:
        events.append({"type": "deathrattle_repeat",
                       "listener": barons[0][0]["instance_id"], "times": times})
    insert_at = index
    for repetition in range(1, times + 1):
        events.append({"type": "kangor_trigger", "source": dead["instance_id"],
                       "repetition": repetition,
                       "selected": [entry["instance_id"] for entry in selected]})
        for entry in selected:
            board = state["boards"][side]
            if len(board) >= 7:
                events.append({"type": "resummon_dropped",
                               "from": entry["instance_id"],
                               "repetition": repetition})
                continue
            source_state = entry["copy_state"]
            require(source_state is not None, "unknown_mech_resummon_state")
            item_id = generated_id(state)
            token = entry["card_id"] in TOKEN_FORMS
            origin = "combat_token" if token else "combat_generated_minion"
            unit = {"instance_id": item_id, "card_id": entry["card_id"],
                    "attack": source_state["attack"],
                    "health": source_state["health"],
                    "max_health": source_state["health"],
                    "keywords": source_state["keywords"].copy(),
                    "golden": entry["golden"], "race": entry["race"],
                    "origin": origin, "aura_attack": 0, "aura_health": 0,
                    "root_instance_id": entry["root_instance_id"],
                    "resummoned_from": entry["instance_id"]}
            manifest = {"instance_id": item_id, "card_id": entry["card_id"],
                        "origin": origin, "source_instance_id": dead["instance_id"],
                        "source_side": side, "resummoned_from": entry["instance_id"],
                        "golden": entry["golden"]}
            if token:
                require(entry.get("tier_grade") == "reference_injected" and
                        type(entry.get("damage_tier")) is int,
                        "ungraded_resummoned_token_tier")
                unit["damage_tier"] = manifest["damage_tier"] = entry["damage_tier"]
                unit["tier_grade"] = manifest["tier_grade"] = entry["tier_grade"]
            else:
                manifest["pool_grade"] = "reference_injected"
            position = min(insert_at, len(board))
            board.insert(position, unit)
            insert_at = position + 1
            state["generated"][side].append(manifest)
            require(len(state["generated"][side]) <= 100, "generated_limit")
            events.append({"type": "resummon", "instance_id": item_id,
                           "from": entry["instance_id"], "card_id": entry["card_id"],
                           "side": side, "repetition": repetition})
            recompute_auras(state, events)
            notify_summon(state, side, unit, events)


def resolve_adapt_spores(state: dict, side: str, index: int, dead: dict,
                         action: dict, events: list[dict]) -> None:
    grants = [entry for entry in dead.get("adapt_effects", [])
              if entry["option_id"] == "UNG_999t2"]
    if not grants:
        return
    require(not (FIXED.get(dead["card_id"], {}).get("trigger") == "deathrattle" or
                 dead["card_id"] in DEATH_BUFFS | KANGOR_NODES | RANDOM_SUMMON_NODES),
            "unknown_native_adapt_deathrattle_order")
    barons = live_listeners(state, side, "friendly_deathrattle")
    times = params(*barons[0])["times"] if barons else 1
    if barons:
        events.append({"type": "deathrattle_repeat",
                       "listener": barons[0][0]["instance_id"], "times": times})
    insert_at = index
    for grant_number, _ in enumerate(grants, start=1):
        for repetition in range(1, times + 1):
            events.append({"type": "adapt_spore_trigger",
                           "source": dead["instance_id"],
                           "grant_number": grant_number,
                           "repetition": repetition, "requests": 2})
            before = len(state["boards"][side])
            summon(state, dead, side, ADAPT_SPORE_NODE, 2, action,
                   insert_at, events)
            insert_at += len(state["boards"][side]) - before


def resolve_deaths(state: dict, action: dict, context: dict,
                   events: list[dict]) -> None:
    for _ in range(100):
        deaths = [(dead_side, index, copy.deepcopy(unit))
                  for dead_side in SIDES
                  for index, unit in enumerate(state["boards"][dead_side])
                  if unit["health"] <= 0]
        if not deaths:
            return
        for _, _, unit in deaths:
            require(unit["card_id"] not in RANDOM_DEATH | OTHER_DEATH,
                    "unresolved_death_effect")
            require(not ("resummoned_from" in unit and
                         FIXED.get(unit["card_id"], {}).get("trigger") == "deathrattle"),
                    "unknown_resummoned_deathrattle_chain")
        require(sum(unit["card_id"] in RANDOM_SUMMON_NODES for _, _, unit in deaths) <= 1,
                "unknown_random_sources_same_batch")
        require(sum(any(entry["option_id"] == "UNG_999t2"
                        for entry in unit.get("adapt_effects", []))
                    for _, _, unit in deaths) <= 1,
                "unknown_adapt_spores_same_batch_order")
        record_mech_deaths(state, deaths)
        for dead_side in SIDES:
            state["boards"][dead_side] = [unit for unit in state["boards"][dead_side]
                                           if unit["health"] > 0]
        recompute_auras(state, events)
        for dead_side, index, unit in deaths:
            events.append({"type": "death", "instance_id": unit["instance_id"],
                           "side": dead_side})
            node = FIXED.get(unit["card_id"])
            if node and node["trigger"] == "deathrattle":
                count = (node["count"]["value"] if node["count"]["kind"] == "fixed"
                         else max(0, unit["attack"]))
                barons = live_listeners(state, dead_side, "friendly_deathrattle")
                if barons:
                    times = params(*barons[0])["times"]
                    events.append({"type": "deathrattle_repeat",
                                   "listener": barons[0][0]["instance_id"], "times": times})
                    count *= times
                position = index if node["destination"] == "friendly" else len(
                    state["boards"]["right" if dead_side == "left" else "left"])
                summon(state, unit, dead_side, node, count, action, position, events)
            buff_node = DEATH_BUFFS.get(unit["card_id"])
            if buff_node:
                apply_death_buff(state, dead_side, unit, buff_node, events)
            kangor_node = KANGOR_NODES.get(unit["card_id"])
            if kangor_node:
                resolve_kangor(state, dead_side, index, unit, kangor_node, events)
            random_node = RANDOM_SUMMON_NODES.get(unit["card_id"])
            if random_node:
                resolve_random_summon(state, dead_side, index, unit,
                                      random_node, action, context, events)
            resolve_adapt_spores(state, dead_side, index, unit, action, events)
            notify_death(state, dead_side, unit, action, context, events)
    raise Rejected("death_chain_limit")


def resolve_attack_effect(state: dict, side: str, attacker: dict, target: dict,
                          primary_damage: int, target_health_before: int,
                          primary_killed: bool, action: dict,
                          events: list[dict]) -> None:
    node = ATTACK_NODES.get(attacker["card_id"])
    if node is None or node["family"] == "windfury_lowest_attack":
        return
    overkill = (node["family"] == "overkill_summon" and
                primary_damage > target_health_before)
    kill_growth = (node["family"] == "attack_kill_growth" and primary_killed)
    if not (overkill or kill_growth):
        return
    board = state["boards"][side]
    source = next((unit for unit in board
                   if unit["instance_id"] == attacker["instance_id"]), None)
    require(source is not None,
            "unknown_dying_overkill_source_order" if overkill else
            "unknown_dying_attacker_growth_order")
    if overkill:
        events.append({"type": "overkill", "attacker": attacker["instance_id"],
                       "target": target["instance_id"],
                       "excess": primary_damage - target_health_before})
        index, _ = find(board, attacker["instance_id"], "attacker_missing")
        summon(state, source, side, node, params(source, node)["count"],
               action, index + 1, events)
    else:
        values = params(source, node)
        source["attack"] += values["attack"]
        source["health"] += values["health"]
        source["max_health"] += values["health"]
        events.append({"type": "attack_kill_growth",
                       "attacker": attacker["instance_id"],
                       "target": target["instance_id"],
                       "attack": values["attack"], "health": values["health"]})


def run_action(original: dict, action: dict) -> tuple[dict, list[dict], str | None]:
    state = copy.deepcopy(original)
    events: list[dict] = []
    try:
        validate_state(state)
        require(action.get("mode", "reference") == "reference", "exact_mode_unverified")
        require(action.get("op") == "attack", "unknown_op")
        require(state["phase"] == "combat", "battle_terminal")
        require(not any(unit["card_id"] in UNCOMPILED_PASSIVES
                        for side in SIDES for unit in state["boards"][side]),
                "unresolved_board_effect")
        validate_multipliers(state)
        random_draws = action.get("random_draw_indexes", [])
        require(type(random_draws) is list and len(random_draws) <= 100,
                "invalid_random_draws")
        require((action.get("random_draw_grade") == "reference_injected")
                if random_draws else ("random_draw_grade" not in action),
                "random_draw_grade_missing")
        context = {"target_index": 0, "random_draw_index": 0}
        side = state["turn"]
        opposite = "right" if side == "left" else "left"
        require(action.get("attacker_id") == next_attacker(state, side)["instance_id"],
                "wrong_attacker")
        own_board = state["boards"][side]
        enemy_board = state["boards"][opposite]
        attacker_index, attacker = find(own_board, action["attacker_id"], "attacker_missing")
        require(attacker["card_id"] not in OTHER_ATTACK, "unresolved_attack_effect")
        attack_node = ATTACK_NODES.get(attacker["card_id"])
        if attack_node and attack_node["family"] in {"overkill_summon", "attack_kill_growth"}:
            require("cleave" not in attacker["keywords"],
                    "composite_cleave_attack_unverified")
        target_index, target = find(enemy_board, action.get("target_id"), "target_missing")
        validate_attack_target(attacker, enemy_board, target, action, events)
        target_health_before = target["health"]
        pending_before = state["pending_extra_attack"]
        attack_source = copy.deepcopy(attacker)
        counter_source = copy.deepcopy(target)
        target_ids = [target["instance_id"]]
        if "cleave" in attacker["keywords"]:
            if target_index > 0:
                target_ids.append(enemy_board[target_index - 1]["instance_id"])
            if target_index + 1 < len(enemy_board):
                target_ids.append(enemy_board[target_index + 1]["instance_id"])
        if "stealth" in attacker["keywords"]:
            attacker["keywords"].remove("stealth")
            events.append({"type": "stealth_revealed",
                           "instance_id": attacker["instance_id"]})
        events.append({"type": "attack", "attacker": attacker["instance_id"],
                       "target": target["instance_id"], "cleave_targets": target_ids[1:]})
        damaged: list[tuple[str, str]] = []
        primary_damage = 0
        for item_id in target_ids:
            _, victim = find(enemy_board, item_id, "target_missing")
            effective = hit(state, opposite, attack_source, victim,
                            attack_source["attack"], events)
            if item_id == target["instance_id"]:
                primary_damage = effective
            if effective > 0:
                damaged.append((opposite, item_id))
        primary_killed = primary_damage > 0 and target["health"] <= 0
        if hit(state, side, counter_source, attacker,
               counter_source["attack"], events) > 0:
            damaged.append((side, attacker["instance_id"]))

        for damaged_side, item_id in damaged:
            _, unit = find(state["boards"][damaged_side], item_id, "damaged_unit_missing")
            node = FIXED.get(unit["card_id"])
            if unit["health"] > 0 and node and node["trigger"] == "on_source_damaged":
                index, _ = find(state["boards"][damaged_side], item_id, "damaged_unit_missing")
                summon(state, unit, damaged_side, node, node["count"]["value"],
                       action, index + 1, events)

        resolve_deaths(state, action, context, events)
        resolve_attack_effect(state, side, attacker, target, primary_damage,
                              target_health_before, primary_killed, action, events)
        resolve_deaths(state, action, context, events)
        targets = action.get("listener_targets", [])
        require(type(targets) is list and context["target_index"] == len(targets),
                "unused_listener_target")
        require(context["random_draw_index"] == len(random_draws),
                "unused_random_draws")

        if not state["boards"]["left"] or not state["boards"]["right"]:
            state["phase"] = "terminal"
            state["pending_extra_attack"] = None
            events.append({"type": "terminal"})
        else:
            current = state["boards"][side]
            attacker_alive = any(unit["instance_id"] == attacker["instance_id"] and
                                 unit["attack"] > 0 for unit in current)
            zapp_windfury = (attacker["card_id"] in ATTACK_NODES and
                             ATTACK_NODES[attacker["card_id"]]["family"] ==
                             "windfury_lowest_attack")
            if pending_before is None and attacker_alive and (
                    zapp_windfury or "windfury" in attacker["keywords"]):
                strikes = (params(attacker, ATTACK_NODES[attacker["card_id"]])[
                    "strikes_per_turn"] if zapp_windfury else 2)
                require(strikes == 2, "unsupported_extra_attack_count")
                state["pending_extra_attack"] = {
                    "side": side, "attacker_id": attacker["instance_id"], "remaining": 1}
                events.append({"type": "extra_attack_ready",
                               "attacker": attacker["instance_id"], "remaining": 1})
            else:
                if pending_before is not None:
                    state["pending_extra_attack"] = None
                    events.append({"type": "extra_attack_used",
                                   "attacker": attacker["instance_id"]})
                state["turn"] = opposite
            if current:
                alive_ids = [unit["instance_id"] for unit in current]
                if state["pending_extra_attack"] is None:
                    if attacker["instance_id"] in alive_ids:
                        state["cursor"][side] = (alive_ids.index(attacker["instance_id"]) + 1) % len(current)
                    else:
                        state["cursor"][side] = attacker_index % len(current)
        state["event_log"] += events
        require(len(state["event_log"]) <= 2000, "event_limit")
        validate_state(state)
        return state, events, None
    except (Rejected, KeyError, TypeError, AttributeError) as exc:
        return original, [], str(exc) if isinstance(exc, Rejected) else "invalid_action"


def to_lifecycle_result(state: dict, pair_id: str) -> dict:
    validate_state(state)
    require(state["phase"] == "terminal", "battle_not_terminal")
    return {"pair_id": pair_id,
            "left_survivors": [unit["instance_id"] for unit in state["boards"]["left"]],
            "right_survivors": [unit["instance_id"] for unit in state["boards"]["right"]],
            "generated": copy.deepcopy(state["generated"])}


def project(state: dict) -> dict:
    return {"phase": state["phase"], "turn": state["turn"],
            "pending_extra_attack": state["pending_extra_attack"],
            "left_ids": [unit["instance_id"] for unit in state["boards"]["left"]],
            "right_ids": [unit["instance_id"] for unit in state["boards"]["right"]],
            "left_units": state["boards"]["left"], "right_units": state["boards"]["right"],
            "generated": state["generated"], "serial": state["serial"],
            "mech_death_history": state["mech_death_history"],
            "death_batch_serial": state["death_batch_serial"]}


def matches(actual: object, expected: object) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and matches(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            matches(a, e) for a, e in zip(actual, expected))
    return actual == expected


def verify_case(case: dict, vectors: dict) -> None:
    fixture = vectors["fixtures"][case["fixture"]]
    snapshot = copy.deepcopy(fixture["snapshot"])
    golden_ids = case.get("golden_instances", [])
    assert type(golden_ids) is list and len(set(golden_ids)) == len(golden_ids), case["id"]
    seen_gold = set()
    for side in SIDES:
        for item in snapshot[side]["board"]:
            if item["instance_id"] in golden_ids:
                item["golden"] = True
                seen_gold.add(item["instance_id"])
    assert seen_gold == set(golden_ids), case["id"]
    state = from_snapshot(snapshot, fixture["traits"], fixture["first_side"])
    for setup in case.get("setup", []):
        state, _, error = run_action(state, setup)
        assert error is None, (case["id"], "setup", error)
    action = copy.deepcopy(case["action"])
    before = copy.deepcopy(state)
    after, events, error = run_action(state, action)
    replay_after, replay_events, replay_error = run_action(before, action)
    assert (after, events, error) == (replay_after, replay_events, replay_error), case["id"]
    assert action == case["action"], case["id"]
    assert error == case.get("error"), (case["id"], error)
    if error:
        assert after == before and events == [], case["id"]
    else:
        assert matches(project(after), case["expect_state"]), (case["id"], project(after))
        assert [event["type"] for event in events] == case["expect_events"], case["id"]
        assert matches(events, case.get("expect_event_details", events)), case["id"]
        if case.get("expect_result"):
            assert matches(to_lifecycle_result(after, "p1"), case["expect_result"]), case["id"]


def verify_bridge(case: dict, vectors: dict) -> None:
    seats = copy.deepcopy(case["seats"])
    match = lifecycle.initial_state(seats)
    recruit_event_types: list[str] = []
    for action in case.get("recruit_actions", []):
        match, recruit_events, error = lifecycle.run_action(match, action)
        assert error is None, (case["id"], "recruit", error)
        recruit_event_types += [event["type"] for event in recruit_events]
    assert recruit_event_types == case.get("expect_recruit_events", []), case["id"]
    for seat in seats:
        match, _, error = lifecycle.run_action(match, {"op": "end_recruit",
                                                    "seat_id": seat["seat_id"]})
        assert error is None, (case["id"], error)
    match, _, error = lifecycle.run_action(match, {"op": "begin_combat", "pairings": [
        {"pair_id": "p1", "left": seats[0]["seat_id"], "right": seats[1]["seat_id"]}]})
    assert error is None, (case["id"], error)
    battle = from_snapshot(match["snapshots"]["p1"], case["traits"], case["first_side"])
    combat_event_types: list[str] = []
    for action in case["actions"]:
        battle, combat_events, error = run_action(battle, action)
        assert error is None, (case["id"], error)
        combat_event_types += [event["type"] for event in combat_events]
    if "expect_combat_events" in case:
        assert combat_event_types == case["expect_combat_events"], case["id"]
    result = to_lifecycle_result(battle, "p1")
    match, _, error = lifecycle.run_action(match, {"op": "settle_combat", "results": [result]})
    assert error is None, (case["id"], error)
    assert matches(lifecycle.project(match), case["expect_match"]), case["id"]
    assert matches(result, case["expect_result"]), case["id"]


def main() -> None:
    packs = [load(RULES["vectors_file"]), load(RULES["listener_vectors_file"]),
             load(RULES["aura_vectors_file"]), load(RULES["attack_vectors_file"]),
             load(RULES["composite_attack_vectors_file"]),
             load(RULES["death_buff_vectors_file"]),
             load(RULES["kangor_vectors_file"]),
             load(RULES["random_cost_vectors_file"]),
             load(RULES["legendary_vectors_file"]),
             load(RULES["random_deathrattle_vectors_file"])]
    assert RULES["mode"] == LISTENER_RULES["mode"] == "reference_2019_launch_week"
    assert RULES["build"] == LISTENER_RULES["build"] == 35747
    assert AURA_RULES["mode"] == RULES["mode"] and AURA_RULES["build"] == RULES["build"]
    assert ATTACK_RULES["mode"] == RULES["mode"] and ATTACK_RULES["build"] == RULES["build"]
    assert DEATH_BUFF_RULES["mode"] == RULES["mode"] and DEATH_BUFF_RULES["build"] == RULES["build"]
    assert KANGOR_RULES["mode"] == RULES["mode"] and KANGOR_RULES["build"] == RULES["build"]
    assert RANDOM_COST_RULES["mode"] == RULES["mode"] and RANDOM_COST_RULES["build"] == RULES["build"]
    assert RANDOM_LEGENDARY_RULES["mode"] == RULES["mode"]
    assert RANDOM_LEGENDARY_RULES["build"] == RULES["build"]
    assert RANDOM_DEATHRATTLE_RULES["mode"] == RULES["mode"]
    assert RANDOM_DEATHRATTLE_RULES["build"] == RULES["build"]
    assert all(value == "unknown" for value in RULES["historical_unknown"].values())
    assert all(value == "unknown" for value in LISTENER_RULES["historical_unknown"].values())
    assert all(value == "unknown" for value in AURA_RULES["historical_unknown"].values())
    assert all(value == "unknown" for value in ATTACK_RULES["historical_unknown"].values())
    assert all(value == "unknown" for value in DEATH_BUFF_RULES["historical_unknown"].values())
    assert all(value == "unknown" for value in KANGOR_RULES["historical_unknown"].values())
    assert all(value == "unknown" for value in RANDOM_COST_RULES["historical_unknown"].values())
    assert all(value == "unknown" for value in COST_CANDIDATES["historical_unknown"].values())
    assert all(value == "unknown" for value in RANDOM_LEGENDARY_RULES["historical_unknown"].values())
    assert all(value == "unknown" for value in LEGENDARY_CANDIDATES["historical_unknown"].values())
    assert all(value == "unknown" for value in RANDOM_DEATHRATTLE_RULES["historical_unknown"].values())
    assert all(value == "unknown" for value in DEATHRATTLE_CANDIDATES["historical_unknown"].values())
    assert COST_CANDIDATES["build"] == RULES["build"]
    assert COST_CANDIDATES["simulator_minion_info_sha256"] == (
        COMMUNITY_POOLS["simulator_minion_info_sha256"])
    assert COMMUNITY_POOLS["simulator_commit"] in COST_CANDIDATES["candidate_source"]
    assert LEGENDARY_CANDIDATES["build"] == RULES["build"]
    assert LEGENDARY_CANDIDATES["simulator_minion_info_sha256"] == (
        COMMUNITY_POOLS["simulator_minion_info_sha256"])
    assert COMMUNITY_POOLS["simulator_commit"] in LEGENDARY_CANDIDATES["candidate_source"]
    assert DEATHRATTLE_CANDIDATES["build"] == RULES["build"]
    assert DEATHRATTLE_CANDIDATES["simulator_minion_info_sha256"] == (
        COMMUNITY_POOLS["simulator_minion_info_sha256"])
    assert COMMUNITY_POOLS["simulator_commit"] in DEATHRATTLE_CANDIDATES["candidate_source"]
    shells = {node["normal_id"]: node for node in
              load("historical-random-effect-shells.json")["nodes"]}
    assert set(RANDOM_COST_NODES) == {"BGS_025", "BGS_023", "BGS_024"}
    for card_id, node in RANDOM_COST_NODES.items():
        row = ROWS[card_id]
        shell = shells[card_id]
        pool = COST_CANDIDATES["pools"][node["candidate_source"]]
        community = COMMUNITY_POOLS["pools"][node["candidate_source"]]
        assert [entry["id"] for entry in pool] == [entry["id"] for entry in community]
        assert node["golden_id"] == row["golden_id"] == shell["golden_id"]
        assert row["golden_evidence"] == "client_35747"
        assert node["tier"] == row["tier"]
        assert node["candidate_source"] == shell["target_filter"].replace(
            "original_mana_cost", "original_cost")
        assert node["cardface_grade"] == "H04_client_direct"
        assert node["candidate_grade"] == "H09_community_reference_only"
        assert node["execution_grade"] == "reference_only"
        for form in ("normal", "golden"):
            assert node[form]["attempts"] == shell["forms"][form]["attempts"]
        for candidate in pool:
            candidate_row = ROWS[candidate["id"]]
            assert candidate["original_mana_cost"] == node["original_mana_cost"]
            assert (candidate["attack"], candidate["health"],
                    candidate["race"]) == (
                candidate_row["normal_attack"], candidate_row["normal_health"],
                candidate_row["client_race"])
        assert set(node["reference_supported_ids"]) <= {c["id"] for c in pool}
        for candidate in pool:
            if candidate["id"] in node["reference_supported_ids"]:
                assert set(candidate["client_mechanics"]) <= {
                    "BATTLECRY", "TRIGGER_VISUAL"}
    assert set(RANDOM_LEGENDARY_NODES) == {"BGS_006"}
    sneed = RANDOM_LEGENDARY_NODES["BGS_006"]
    sneed_row = ROWS["BGS_006"]
    sneed_shell = shells["BGS_006"]
    legendary_pool = LEGENDARY_CANDIDATES["pools"]["legendary_candidates"]
    assert len(legendary_pool) == 12
    assert COMMUNITY_POOLS["legendary_count_independent_crosscheck"][
        "author_description_claim_count"] == 12
    assert [c["id"] for c in legendary_pool] == [
        c["id"] for c in COMMUNITY_POOLS["pools"]["legendary_candidates"]]
    assert sneed["golden_id"] == sneed_row["golden_id"] == sneed_shell["golden_id"]
    assert sneed_row["golden_evidence"] == "client_35747"
    assert sneed["tier"] == sneed_row["tier"] == 6
    assert sneed["family"] == "summon_legendary"
    assert sneed["candidate_source"] == "legendary_candidates"
    assert sneed_shell["target_filter"] == "legendary_minion"
    assert sneed["cardface_grade"] == "H04_client_direct"
    assert sneed["candidate_grade"] == "H09_community_reference_only"
    assert sneed["execution_grade"] == "reference_only"
    for form in ("normal", "golden"):
        assert sneed[form]["attempts"] == sneed_shell["forms"][form]["attempts"]
    for candidate in legendary_pool:
        candidate_row = ROWS[candidate["id"]]
        assert candidate["client_rarity"] == "LEGENDARY"
        assert (candidate["attack"], candidate["health"], candidate["race"],
                candidate["shop_tier"]) == (
                    candidate_row["normal_attack"], candidate_row["normal_health"],
                    candidate_row["client_race"], candidate_row["tier"])
    assert set(sneed["reference_supported_ids"]) == {"BGS_029", "LOE_077"}
    assert not (set(sneed["reference_supported_ids"]) &
                (set(AURAS) | set(LISTENERS) | set(ATTACK_NODES) |
                 set(DEATH_BUFFS) | set(RANDOM_COST_NODES) |
                 set(RANDOM_LEGENDARY_NODES)))
    assert "手牌" in ROWS["BGS_029"]["normal_effect_summary"]
    assert "战吼" in ROWS["LOE_077"]["normal_effect_summary"]
    assert set(RANDOM_DEATHRATTLE_NODES) == {"BGS_008"}
    coiler = RANDOM_DEATHRATTLE_NODES["BGS_008"]
    coiler_row = ROWS["BGS_008"]
    coiler_shell = shells["BGS_008"]
    deathrattle_pool = DEATHRATTLE_CANDIDATES["pools"]["deathrattle_candidates"]
    assert len(deathrattle_pool) == 22
    assert DEATHRATTLE_CANDIDATES["client_shop_tag_count"] == 22
    assert COMMUNITY_POOLS["differences_from_client_tag_subset"][
        "deathrattle_candidates"]["simulator_count"] == 22
    assert [c["id"] for c in deathrattle_pool] == [
        c["id"] for c in COMMUNITY_POOLS["pools"]["deathrattle_candidates"]]
    assert coiler["golden_id"] == coiler_row["golden_id"] == coiler_shell["golden_id"]
    assert coiler_row["golden_evidence"] == "client_35747"
    assert coiler["tier"] == coiler_row["tier"] == 6
    assert coiler["family"] == "summon_deathrattle"
    assert coiler["candidate_source"] == "deathrattle_candidates"
    assert coiler_shell["target_filter"] == "deathrattle_minion"
    assert coiler["cardface_grade"] == "H04_client_direct"
    assert coiler["candidate_grade"] == "H09_community_reference_only"
    assert coiler["execution_grade"] == "reference_only"
    for form in ("normal", "golden"):
        assert coiler[form]["attempts"] == coiler_shell["forms"][form]["attempts"]
    for candidate in deathrattle_pool:
        candidate_row = ROWS[candidate["id"]]
        assert candidate["client_deathrattle_tag"] is True
        assert "DEATHRATTLE" in candidate["client_mechanics"]
        assert (candidate["attack"], candidate["health"], candidate["race"],
                candidate["shop_tier"]) == (
                    candidate_row["normal_attack"], candidate_row["normal_health"],
                    candidate_row["client_race"], candidate_row["tier"])
    assert set(coiler["reference_supported_ids"]) == {"OG_256", "BGS_018"}
    assert set(coiler["reference_supported_ids"]) <= set(DEATH_BUFFS)
    assert all(set(c["client_mechanics"]) == {"DEATHRATTLE"}
               for c in deathrattle_pool if c["id"] in coiler["reference_supported_ids"])
    assert len(ATTACK_NODES) == len(ATTACK_RULES["nodes"]) == 3
    zapp = ATTACK_NODES["BGS_022"]
    zapp_row = ROWS["BGS_022"]
    assert zapp["target_selector"] == "enemy_lowest_current_attack"
    assert zapp["family"] == "windfury_lowest_attack"
    assert zapp["taunt_conflict_policy"] == "reject_unverified"
    assert zapp["equal_lowest_policy"] == "require_reference_injected_choice"
    assert zapp["normal"] == zapp["golden"] == {"strikes_per_turn": 2}
    assert zapp["normal_cardface_grade"] == "H04_client_direct"
    assert zapp["golden_cardface_grade"] == "H04_stats_triple_inferred_H16_windfury_retrospective"
    assert zapp["execution_grade"] == "reference_only"
    assert zapp_row["normal_attack"] == 7 and zapp_row["normal_health"] == 10
    assert zapp_row["golden_attack"] == 14 and zapp_row["golden_health"] == 20
    assert zapp_row["golden_id"] is None and zapp_row["golden_evidence"] == "inferred_from_triple_rule"
    assert "风怒" in zapp_row["normal_effect_summary"] and "最低攻击力" in zapp_row["normal_effect_summary"]
    assert not (set(ATTACK_NODES) & UNCOMPILED_PASSIVES)
    composite_by_id = {node["normal_id"]: node for node in COMPOSITE}
    assert set(KANGOR_NODES) == {"BGS_012"} and not OTHER_DEATH
    kangor = KANGOR_NODES["BGS_012"]
    kangor_source = composite_by_id["BGS_012"]
    kangor_row = ROWS["BGS_012"]
    assert kangor["family"] == kangor_source["family"] == "first_dead_mechs"
    assert kangor["trigger"] == "source_died"
    assert kangor["golden_id"] == kangor_source["golden_id"] == kangor_row["golden_id"]
    assert kangor_row["golden_evidence"] == "client_35747"
    assert kangor["cardface_grade"] == "H04_client_direct"
    assert kangor["execution_grade"] == "reference_only"
    assert kangor["copy_policy"] == "reference_death_snapshot"
    for form in ("normal", "golden"):
        assert kangor[form]["first_count"] == kangor_source["parameters"][form]["first_count"]
    assert set(DEATH_BUFFS) == {"OG_256", "BGS_018"}
    for card_id, selector in (("OG_256", "friendly_survivors"),
                              ("BGS_018", "friendly_surviving_beasts")):
        node = DEATH_BUFFS[card_id]
        source = composite_by_id[card_id]
        row = ROWS[card_id]
        assert node["family"] == source["family"] == "deathrattle_team_buff"
        assert node["trigger"] == "source_died" and node["target"] == selector
        assert source["target_race"] == ("ANY" if card_id == "OG_256" else "BEAST")
        assert node["normal_id"] == row["normal_id"] and node["golden_id"] == row["golden_id"]
        assert row["golden_evidence"] == "client_35747"
        assert node["cardface_grade"] == "H04_client_direct"
        assert node["execution_grade"] == "reference_only"
        for form in ("normal", "golden"):
            stat = source["parameters"][form]["each_stat"]
            assert node[form] == {"attack": stat, "health": stat}
    assert not OTHER_ATTACK
    for card_id, family in (("TRL_232", "overkill_summon"),
                            ("OG_300", "attack_kill_growth")):
        node = ATTACK_NODES[card_id]
        source = composite_by_id[card_id]
        row = ROWS[card_id]
        expected_stats = {"TRL_232": (7, 7, 14, 14),
                          "OG_300": (6, 7, 12, 14)}[card_id]
        assert (row["normal_attack"], row["normal_health"],
                row["golden_attack"], row["golden_health"]) == expected_stats
        assert node["family"] == source["family"] == family
        assert node["trigger"] == ("self_attack_effective_damage_gt_primary_target_health_before"
                                   if family == "overkill_summon" else
                                   "self_attack_killed_primary_target")
        assert row["golden_id"] == source["golden_id"]
        assert row["golden_evidence"] == "client_35747"
        assert node["cardface_grade"] == "H04_client_direct"
        assert node["execution_grade"] == "reference_only"
        assert node["dying_attacker_policy"] == "reject_unknown"
        for form in ("normal", "golden"):
            parameter = source["parameters"][form]
            if family == "overkill_summon":
                token = node["tokens"][form]
                assert node["destination"] == "friendly"
                assert node[form] == {"count": 1}
                assert (token["id"], token["attack"], token["health"],
                        token["race"], token["keywords"], token["premium"]) == (
                            parameter["token_id"], parameter["attack"],
                            parameter["health"], parameter["race"], [],
                            form == "golden")
                assert node["token_link_grade"] == "inference_from_client_name_stats_id"
            else:
                assert node[form] == {"attack": parameter["each_stat"],
                                      "health": parameter["each_stat"]}
    assert len(LISTENERS) == len(LISTENER_RULES["nodes"]) == 9
    assert len(AURAS) == 5 and len(SHIELD_LISTENERS) == 1
    assert len(AURAS | SHIELD_LISTENERS) == len(AURA_RULES["nodes"]) == 6
    assert set(AURAS | SHIELD_LISTENERS) <= set(ROWS)
    assert not (set(AURAS | SHIELD_LISTENERS) & UNCOMPILED_PASSIVES)
    effects = {node["normal_id"]: node
               for node in load("historical-effect-nodes.json")["nodes"]}
    composite = {node["normal_id"]: node for node in COMPOSITE}
    selectors = {"EX1_162": "friendly_adjacent",
                 "EX1_507": "friendly_other_murloc",
                 "ULD_179": "friendly_taunt",
                 "EX1_185": "friendly_other_demon",
                 "GVG_021": "friendly_other_demon"}
    client_targets = {
        "friendly_adjacent": {"scope": "adjacent", "tribe": None, "keyword": None},
        "friendly_other_murloc": {"scope": "all_other", "tribe": "MURLOC",
                                  "keyword": None},
        "friendly_taunt": {"scope": "all", "tribe": None, "keyword": "taunt"},
        "friendly_other_demon": {"scope": "all_other", "tribe": "DEMON",
                                 "keyword": None},
        "living_friendly_shield_listener": {"scope": "self", "tribe": None,
                                            "keyword": None},
    }
    for node in AURA_RULES["nodes"]:
        card_id = node["normal_id"]
        assert node["cardface_grade"] == "H04_client_direct"
        assert node["execution_grade"] == "reference_only"
        assert all(type(node[form]["attack"]) is int and
                   node[form]["attack"] >= 0 and
                   type(node[form].get("health", 0)) is int and
                   node[form].get("health", 0) >= 0
                   for form in ("normal", "golden"))
        if card_id == "GVG_021":
            assert composite[card_id]["family"] == "demon_hero_aura"
            for form in ("normal", "golden"):
                stat = composite[card_id]["parameters"][form]["each_stat"]
                assert node[form] == {"attack": stat, "health": stat}
        else:
            expected = effects[card_id]
            assert expected["evidence"]["numeric_and_target"] == (
                "H04_client_cardface_direct")
            for form in ("normal", "golden"):
                assert node[form] == {key: expected[form + "_effect"][key]
                                      for key in ("attack", "health")}
            assert expected["target"] == client_targets[node["target"]]
            assert set(RULES["keyword_anchors"].get(card_id, [])) == set(
                expected["static_keywords"])
        if card_id in AURAS:
            assert node["trigger"] == "while_alive" and node["operation"] == (
                "modify_current_stats") and node["target"] == selectors[card_id]
        else:
            assert card_id == "ICC_858" and node["trigger"] == (
                "friendly_shield_lost") and node["operation"] == "grow_self"
    assert set(LISTENERS) <= set(ROWS) and not (set(LISTENERS) & UNCOMPILED_PASSIVES)
    for card_id, node in LISTENERS.items():
        expected_grade = ("H04_client_direct" if ROWS[card_id]["golden_evidence"] ==
                          "client_35747" else
                          "H04_normal_client_direct_golden_triple_inferred")
        assert node["cardface_grade"] == expected_grade, card_id
    seen: set[str] = set()
    for vectors in packs:
        assert vectors["mode"] == RULES["mode"] and vectors["build"] == RULES["build"]
        for case in vectors["cases"]:
            assert case["id"] not in seen and case["grade"] == "reference_only", case["id"]
            seen.add(case["id"])
            verify_case(case, vectors)
        for case in vectors["bridge_cases"]:
            assert case["id"] not in seen and case["grade"] == "reference_only", case["id"]
            seen.add(case["id"])
            verify_bridge(case, vectors)
    print(f"combat event reference vectors: {len(seen)} passed; "
          "terminal result bridge validated; original same-tick order unknown")


if __name__ == "__main__":
    main()
