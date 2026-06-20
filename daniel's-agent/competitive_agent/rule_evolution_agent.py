import json
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"


SUPPORTED_EFFECTS = {
    "max_plays_per_turn",
    "draw_count",
    "draw_two_penalty",
    "wild_draw_four_penalty",
    "skip_penalty_cards",
    "reverse_penalty_cards",
    "allow_same_type_match",
    "allow_number_on_number",
    "allow_action_on_action",
    "win_hand_count",
}


def write_log(log_file: Path, title: str, content: str) -> None:
    with log_file.open("a", encoding="utf-8") as file:
        file.write(f"\n\n===== {title} =====\n")
        file.write(content)
        file.write("\n")


def propose_mutable_rule(rule_context: dict[str, Any], log_file: Path) -> dict[str, Any]:
    """Build a server-compatible mutable-rule proposal.

    This is deliberately deterministic. The server only accepts a small set of
    mechanical effects, so hard-validating our best rule templates is stronger
    than asking the LLM to invent free-form rules.
    """

    write_log(log_file, "RULE CONTEXT", json.dumps(rule_context, indent=2, ensure_ascii=False))

    existing_ids = {
        rule.get("id")
        for rule in rule_context.get("mutable_rules", {}).get("rules", [])
    }
    hand = rule_context.get("hand", [])
    top_card = rule_context.get("top_card") or {}
    player_name = rule_context.get("player_name", "Daniel-Agent")
    my_cards = len(hand)
    opponent_cards = rule_context.get("opponent_cards_in_hand")
    playable_indexes = rule_context.get("playable_indexes", [])

    candidates = [
        _finish_rule(player_name, my_cards),
        _combo_rule(player_name, my_cards),
        _number_freedom_rule(player_name, my_cards, top_card, hand),
        _action_freedom_rule(player_name, top_card, hand),
        _opponent_pressure_rule(opponent_cards),
        _draw_two_pressure_rule(player_name, hand, playable_indexes),
        _skip_reverse_pressure_rule(player_name, hand, playable_indexes),
    ]

    for candidate in candidates:
        if not candidate:
            continue
        if candidate["id"] in existing_ids:
            continue
        _validate_rule_shape(candidate)
        write_log(log_file, "MUTABLE RULE PROPOSAL", json.dumps(candidate, indent=2, ensure_ascii=False))
        return {
            "operation": "add",
            "rule": candidate,
            "visible_reason": _rule_reason(candidate),
        }

    proposal = {
        "operation": "none",
        "rule": None,
        "visible_reason": "No useful non-duplicate mutable rule available.",
    }
    write_log(log_file, "MUTABLE RULE PROPOSAL", json.dumps(proposal, indent=2, ensure_ascii=False))
    return proposal


def _finish_rule(player_name: str, my_cards: int) -> dict[str, Any] | None:
    if my_cards > 3:
        return None
    return {
        "id": "daniel_finish_at_three",
        "title": "Daniel Finish Window",
        "description": "When Daniel-Agent has three or fewer cards, playing a card can finish the game.",
        "type": "turn_modifier",
        "condition": {
            "scope": "current_player",
            "player_name": player_name,
            "current_player": {"hand_count": {"lte": 3}},
        },
        "effect": {"win_hand_count": 3},
    }


def _combo_rule(player_name: str, my_cards: int) -> dict[str, Any] | None:
    if my_cards > 5:
        return None
    return {
        "id": "daniel_low_hand_combo",
        "title": "Daniel Low Hand Combo",
        "description": "When Daniel-Agent is close to winning, Daniel-Agent may play up to four cards in one turn.",
        "type": "turn_modifier",
        "condition": {
            "scope": "current_player",
            "player_name": player_name,
            "current_player": {"hand_count": {"lte": 5}},
        },
        "effect": {"max_plays_per_turn": 4},
    }


def _number_freedom_rule(player_name: str, my_cards: int, top_card: dict[str, Any], hand: list[dict[str, Any]]) -> dict[str, Any] | None:
    if my_cards > 5:
        return None
    if top_card.get("type") != "number":
        return None
    if not any(card.get("type") == "number" for card in hand):
        return None
    return {
        "id": "daniel_number_freedom",
        "title": "Daniel Number Freedom",
        "description": "When Daniel-Agent is close to winning, Daniel-Agent may play any number card on any number card.",
        "type": "turn_modifier",
        "condition": {
            "scope": "current_player",
            "player_name": player_name,
            "current_player": {"hand_count": {"lte": 5}},
        },
        "effect": {"allow_number_on_number": True},
    }


def _action_freedom_rule(player_name: str, top_card: dict[str, Any], hand: list[dict[str, Any]]) -> dict[str, Any] | None:
    if top_card.get("type") != "action":
        return None
    if not any(card.get("type") == "action" for card in hand):
        return None
    return {
        "id": "daniel_action_freedom",
        "title": "Daniel Action Freedom",
        "description": "Daniel-Agent may play any action card on another action card.",
        "type": "turn_modifier",
        "condition": {
            "scope": "current_player",
            "player_name": player_name,
        },
        "effect": {"allow_action_on_action": True},
    }


def _opponent_pressure_rule(opponent_cards: int | None) -> dict[str, Any] | None:
    if opponent_cards is None or opponent_cards > 2:
        return None
    return {
        "id": "max_low_hand_draw_pressure",
        "title": "Max Low Hand Draw Pressure",
        "description": "When the opponent is close to winning, normal draws become heavier.",
        "type": "draw_modifier",
        "condition": {
            "opponent": {"hand_count": {"lte": 2}},
        },
        "effect": {"draw_count": 2},
    }


def _draw_two_pressure_rule(player_name: str, hand: list[dict[str, Any]], playable_indexes: list[int]) -> dict[str, Any] | None:
    if not any(hand[index].get("value") == "draw_two" for index in playable_indexes):
        return None
    return {
        "id": "daniel_draw_two_pressure",
        "title": "Daniel Draw Two Pressure",
        "description": "Draw Two becomes more punishing while Daniel-Agent can use it.",
        "type": "draw_modifier",
        "condition": {
            "scope": "current_player",
            "player_name": player_name,
        },
        "effect": {"draw_two_penalty": 6},
    }


def _skip_reverse_pressure_rule(player_name: str, hand: list[dict[str, Any]], playable_indexes: list[int]) -> dict[str, Any] | None:
    values = {hand[index].get("value") for index in playable_indexes}
    if "skip" in values:
        return {
            "id": "daniel_skip_pressure",
            "title": "Daniel Skip Pressure",
            "description": "Skip also makes the opponent draw cards while Daniel-Agent can use it.",
            "type": "draw_modifier",
            "condition": {
                "scope": "current_player",
                "player_name": player_name,
            },
            "effect": {"skip_penalty_cards": 3},
        }
    if "reverse" in values:
        return {
            "id": "daniel_reverse_pressure",
            "title": "Daniel Reverse Pressure",
            "description": "Reverse also makes the opponent draw cards while Daniel-Agent can use it.",
            "type": "draw_modifier",
            "condition": {
                "scope": "current_player",
                "player_name": player_name,
            },
            "effect": {"reverse_penalty_cards": 3},
        }
    return None


def _validate_rule_shape(rule: dict[str, Any]) -> None:
    required = {"id", "title", "description", "type", "condition", "effect"}
    missing = required - set(rule)
    if missing:
        raise ValueError(f"Rule missing required fields: {sorted(missing)}")
    if not isinstance(rule["condition"], dict):
        raise ValueError("Rule condition must be a dict")
    if not isinstance(rule["effect"], dict):
        raise ValueError("Rule effect must be a dict")
    if not SUPPORTED_EFFECTS.intersection(rule["effect"]):
        raise ValueError("Rule effect does not contain a supported server mechanic")


def _rule_reason(rule: dict[str, Any]) -> str:
    effect_keys = ", ".join(rule["effect"].keys())
    return f"Adding {rule['id']} because it uses supported effect(s): {effect_keys}."


def main() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = LOG_DIR / f"rule-evolution-run-{timestamp}.txt"

    example_context = {
        "hand": [
            {"color": "red", "value": "3", "type": "number"},
            {"color": "blue", "value": "skip", "type": "action"},
            {"color": "yellow", "value": "8", "type": "number"},
        ],
        "top_card": {"color": "green", "value": "5", "type": "number"},
        "playable_indexes": [],
        "opponent_cards_in_hand": 2,
        "mutable_rules": {"rules": []},
    }

    proposal = propose_mutable_rule(example_context, log_file)
    print(json.dumps(proposal, indent=2, ensure_ascii=False))
    print(f"Log-Datei: {log_file}")


if __name__ == "__main__":
    main()
