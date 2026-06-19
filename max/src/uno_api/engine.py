from __future__ import annotations

import random
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

COLORS = ["red", "yellow", "green", "blue"]
NUMBER_VALUES = [str(value) for value in range(10)]
ACTION_VALUES = ["skip", "reverse", "draw_two"]
WILD_VALUES = ["wild", "wild_draw_four"]


class UnoError(ValueError):
    """Raised when a requested UNO action is invalid."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_game(player_name: str) -> dict[str, Any]:
    player = _new_player(player_name)
    return {
        "game_id": str(uuid.uuid4()),
        "status": "waiting",
        "players": [player],
        "draw_pile": [],
        "discard_pile": [],
        "current_player_index": 0,
        "direction": 1,
        "drawn_this_turn_player_id": None,
        "plays_this_turn_player_id": None,
        "plays_this_turn_count": 0,
        "winner_id": None,
        "turn": 0,
        "message": f"Waiting for a second player. {player_name} created the game.",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }


def join_game(state: dict[str, Any], player_name: str) -> dict[str, Any]:
    state = deepcopy(state)
    if state["status"] != "waiting":
        raise UnoError("A running game cannot be joined.")
    if len(state["players"]) >= 2:
        raise UnoError("This first version supports exactly two players.")

    state["players"].append(_new_player(player_name))
    _start_game(state)
    return state


def reset_game(player_name: str) -> dict[str, Any]:
    return new_game(player_name)


def apply_action(
    state: dict[str, Any],
    player_id: str,
    action: dict[str, Any],
    mechanics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = deepcopy(state)
    mechanics = _mechanics_or_default(mechanics)
    _ensure_turn_tracking(state)
    if state["status"] != "active":
        raise UnoError("The game is not active.")

    player_index = _player_index(state, player_id)
    if player_index != state["current_player_index"]:
        raise UnoError("It is not your turn.")

    player = state["players"][player_index]
    action_type = action["action"]

    if action_type == "draw":
        if state.get("drawn_this_turn_player_id") == player_id:
            raise UnoError("You have already drawn this turn.")
        drawn = _draw_cards(state, mechanics["draw_count"])
        player["hand"].extend(drawn)
        state["drawn_this_turn_player_id"] = player_id
        if any(_is_playable(card, _top_card(state), mechanics) for card in drawn):
            state["message"] = f"{player['name']} drew {len(drawn)} card(s), including a playable card."
        else:
            state["message"] = f"{player['name']} drew {len(drawn)} card(s) and may pass."
    elif action_type == "pass":
        has_played = state.get("plays_this_turn_player_id") == player_id and state.get("plays_this_turn_count", 0) > 0
        if not has_played and state.get("drawn_this_turn_player_id") != player_id and _has_playable_card(player["hand"], _top_card(state), mechanics):
            raise UnoError("You have a playable card and cannot pass.")
        state["message"] = f"{player['name']} passed."
        state["drawn_this_turn_player_id"] = None
        _advance_turn(state)
    elif action_type == "play":
        _play_card(state, player_index, action, mechanics)
    elif action_type == "rule_change":
        state["message"] = f"{player['name']} changed the mutable rules."
        _advance_turn(state)
    else:
        raise UnoError("Unsupported action.")

    state["turn"] += 1
    state["updated_at"] = utc_now()
    return state


def public_view(state: dict[str, Any], mechanics: dict[str, Any] | None = None) -> dict[str, Any]:
    mechanics = _mechanics_or_default(mechanics)
    _ensure_turn_tracking(state)
    return {
        "game_id": state["game_id"],
        "status": state["status"],
        "players": [
            {
                "id": player["id"],
                "name": player["name"],
                "cards_in_hand": len(player["hand"]),
                "uno_declared": player.get("uno_declared", False),
            }
            for player in state["players"]
        ],
        "top_card": _top_card(state) if state["discard_pile"] else None,
        "draw_pile_count": len(state["draw_pile"]),
        "discard_pile_count": len(state["discard_pile"]),
        "current_player_id": _current_player(state)["id"] if state["players"] else None,
        "current_player_name": _current_player(state)["name"] if state["players"] else None,
        "direction": state["direction"],
        "winner_id": state["winner_id"],
        "drawn_this_turn_player_id": state.get("drawn_this_turn_player_id"),
        "plays_this_turn_player_id": state.get("plays_this_turn_player_id"),
        "plays_this_turn_count": state.get("plays_this_turn_count", 0),
        "active_rule_mechanics": mechanics,
        "turn": state["turn"],
        "message": state["message"],
        "updated_at": state["updated_at"],
    }


def observer_view(state: dict[str, Any], mechanics: dict[str, Any] | None = None) -> dict[str, Any]:
    mechanics = _mechanics_or_default(mechanics)
    view = public_view(state, mechanics)
    top_card = _top_card(state) if state["discard_pile"] else None
    view["players"] = [
        {
            "id": player["id"],
            "name": player["name"],
            "cards_in_hand": len(player["hand"]),
            "hand": player["hand"],
            "uno_declared": player.get("uno_declared", False),
            "is_current_turn": index == state["current_player_index"] and state["status"] == "active",
            "playable_indexes": _playable_indexes(player["hand"], top_card, mechanics) if top_card else [],
        }
        for index, player in enumerate(state["players"])
    ]
    return view


def player_view(state: dict[str, Any], player_id: str, mechanics: dict[str, Any] | None = None) -> dict[str, Any]:
    mechanics = _mechanics_or_default(mechanics)
    _ensure_turn_tracking(state)
    player_index = _player_index(state, player_id)
    player = state["players"][player_index]
    view = public_view(state, mechanics)
    view["you"] = {
        "id": player["id"],
        "name": player["name"],
        "hand": player["hand"],
        "is_current_turn": player_index == state["current_player_index"] and state["status"] == "active",
        "has_drawn_this_turn": state.get("drawn_this_turn_player_id") == player_id,
        "plays_this_turn_count": state.get("plays_this_turn_count", 0) if state.get("plays_this_turn_player_id") == player_id else 0,
        "remaining_plays_this_turn": _remaining_plays_this_turn(state, player_id, mechanics),
    }
    view["playable_indexes"] = _playable_indexes(player["hand"], _top_card(state), mechanics) if state["discard_pile"] else []
    return view


def default_rules() -> dict[str, Any]:
    return {
        "game": "UNO",
        "version": 1,
        "player_count": 2,
        "starting_hand_size": 7,
        "valid_colors": COLORS,
        "card_types": {
            "number": NUMBER_VALUES,
            "action": ACTION_VALUES,
            "wild": WILD_VALUES,
        },
        "matching": [
            "A non-wild card may be played when its color or value matches the top discard card.",
            "A wild card may be played on any top discard card.",
        ],
        "actions": {
            "skip": "Skips the opponent. In a two-player game, the same player gets the next turn.",
            "reverse": "Acts like skip in this two-player implementation.",
            "draw_two": "Opponent draws two cards and loses their turn.",
            "wild": "Player chooses the next active color.",
            "wild_draw_four": "Opponent draws four cards and loses their turn; player chooses the next active color.",
        },
        "turn_actions": ["play", "draw", "pass"],
        "win_condition": "A player wins immediately after playing their final card.",
    }


def _new_player(name: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "hand": [],
        "uno_declared": False,
    }


def _start_game(state: dict[str, Any]) -> None:
    deck = _build_deck()
    random.shuffle(deck)
    for player in state["players"]:
        player["hand"] = [_draw_from(deck) for _ in range(7)]

    first_discard = _draw_from(deck)
    while first_discard["type"] == "wild":
        deck.insert(0, first_discard)
        random.shuffle(deck)
        first_discard = _draw_from(deck)

    state["draw_pile"] = deck
    state["discard_pile"] = [first_discard]
    state["status"] = "active"
    state["current_player_index"] = 0
    state["direction"] = 1
    state["drawn_this_turn_player_id"] = None
    state["plays_this_turn_player_id"] = None
    state["plays_this_turn_count"] = 0
    state["message"] = f"{state['players'][0]['name']} starts. Top card is {_card_label(first_discard)}."
    state["updated_at"] = utc_now()


def _build_deck() -> list[dict[str, Any]]:
    deck = []
    for color in COLORS:
        deck.append({"color": color, "value": "0", "type": "number"})
        for value in NUMBER_VALUES[1:]:
            deck.extend([{"color": color, "value": value, "type": "number"} for _ in range(2)])
        for value in ACTION_VALUES:
            deck.extend([{"color": color, "value": value, "type": "action"} for _ in range(2)])

    for value in WILD_VALUES:
        deck.extend([{"color": None, "value": value, "type": "wild", "chosen_color": None} for _ in range(4)])
    return deck


def _draw_from(deck: list[dict[str, Any]]) -> dict[str, Any]:
    if not deck:
        raise UnoError("No cards are available to draw.")
    return deck.pop()


def _draw_cards(state: dict[str, Any], amount: int) -> list[dict[str, Any]]:
    drawn = []
    for _ in range(amount):
        if not state["draw_pile"]:
            _reshuffle_discard_into_draw(state)
        drawn.append(_draw_from(state["draw_pile"]))
    return drawn


def _reshuffle_discard_into_draw(state: dict[str, Any]) -> None:
    if len(state["discard_pile"]) <= 1:
        raise UnoError("No cards are available to draw.")
    top = state["discard_pile"].pop()
    cards = state["discard_pile"]
    for card in cards:
        if card["type"] == "wild":
            card["chosen_color"] = None
    random.shuffle(cards)
    state["draw_pile"] = cards
    state["discard_pile"] = [top]


def _play_card(state: dict[str, Any], player_index: int, action: dict[str, Any], mechanics: dict[str, Any]) -> None:
    player = state["players"][player_index]
    card_index = action.get("card_index")
    if card_index is None or card_index >= len(player["hand"]):
        raise UnoError("A valid card_index is required for play actions.")

    card = player["hand"][card_index]
    top_card = _top_card(state)
    if not _is_playable(card, top_card, mechanics):
        raise UnoError(f"{_card_label(card)} cannot be played on {_card_label(top_card)}.")

    chosen_color = action.get("chosen_color")
    played = player["hand"].pop(card_index)
    if played["type"] == "wild":
        if chosen_color not in COLORS:
            raise UnoError("Wild cards require chosen_color: red, yellow, green, or blue.")
        played["chosen_color"] = chosen_color

    player["uno_declared"] = bool(action.get("declare_uno")) and len(player["hand"]) == 1
    state["discard_pile"].append(played)
    _record_play_for_turn(state, player["id"])

    if len(player["hand"]) <= mechanics["win_hand_count"] or not player["hand"]:
        state["status"] = "finished"
        state["winner_id"] = player["id"]
        state["drawn_this_turn_player_id"] = None
        state["plays_this_turn_player_id"] = None
        state["plays_this_turn_count"] = 0
        state["message"] = f"{player['name']} played {_card_label(played)} and won the game."
        return

    state["drawn_this_turn_player_id"] = None
    _apply_card_effect(state, player, played, mechanics)
    if state["status"] == "active":
        suffix = " and declared UNO." if player["uno_declared"] else "."
        extra = ""
        if state["current_player_index"] == player_index and _remaining_plays_this_turn(state, player["id"], mechanics) > 0:
            extra = " They may play again."
        state["message"] = f"{player['name']} played {_card_label(played)}{suffix}{extra}"


def _apply_card_effect(state: dict[str, Any], player: dict[str, Any], card: dict[str, Any], mechanics: dict[str, Any]) -> None:
    if card["value"] == "skip":
        if mechanics["skip_penalty_cards"]:
            _next_player(state)["hand"].extend(_draw_cards(state, mechanics["skip_penalty_cards"]))
        _advance_turn(state, steps=2)
    elif card["value"] == "reverse":
        if mechanics["reverse_penalty_cards"]:
            _next_player(state)["hand"].extend(_draw_cards(state, mechanics["reverse_penalty_cards"]))
        _advance_turn(state, steps=2)
    elif card["value"] == "draw_two":
        victim = _next_player(state)
        victim["hand"].extend(_draw_cards(state, mechanics["draw_two_penalty"]))
        _advance_turn(state, steps=2)
    elif card["value"] == "wild_draw_four":
        victim = _next_player(state)
        victim["hand"].extend(_draw_cards(state, mechanics["wild_draw_four_penalty"]))
        _advance_turn(state, steps=2)
    else:
        if not _can_continue_playing(state, player["id"], mechanics):
            _advance_turn(state)


def _advance_turn(state: dict[str, Any], steps: int = 1) -> None:
    state["current_player_index"] = (state["current_player_index"] + state["direction"] * steps) % len(state["players"])
    state["drawn_this_turn_player_id"] = None
    state["plays_this_turn_player_id"] = None
    state["plays_this_turn_count"] = 0


def _player_index(state: dict[str, Any], player_id: str) -> int:
    for index, player in enumerate(state["players"]):
        if player["id"] == player_id:
            return index
    raise UnoError("Unknown player_id.")


def _current_player(state: dict[str, Any]) -> dict[str, Any]:
    return state["players"][state["current_player_index"]]


def _next_player(state: dict[str, Any]) -> dict[str, Any]:
    next_index = (state["current_player_index"] + state["direction"]) % len(state["players"])
    return state["players"][next_index]


def _top_card(state: dict[str, Any]) -> dict[str, Any]:
    return state["discard_pile"][-1]


def _effective_color(card: dict[str, Any]) -> str | None:
    return card.get("chosen_color") or card.get("color")


def _is_playable(card: dict[str, Any], top_card: dict[str, Any], mechanics: dict[str, Any] | None = None) -> bool:
    mechanics = _mechanics_or_default(mechanics)
    if card["type"] == "wild":
        return True
    if card["color"] == _effective_color(top_card) or card["value"] == top_card["value"]:
        return True
    if mechanics["allow_same_type_match"] and card["type"] == top_card["type"]:
        return True
    if mechanics["allow_number_on_number"] and card["type"] == "number" and top_card["type"] == "number":
        return True
    if mechanics["allow_action_on_action"] and card["type"] == "action" and top_card["type"] == "action":
        return True
    return False


def _has_playable_card(hand: list[dict[str, Any]], top_card: dict[str, Any], mechanics: dict[str, Any] | None = None) -> bool:
    return any(_is_playable(card, top_card, mechanics) for card in hand)


def _playable_indexes(hand: list[dict[str, Any]], top_card: dict[str, Any], mechanics: dict[str, Any] | None = None) -> list[int]:
    return [index for index, card in enumerate(hand) if _is_playable(card, top_card, mechanics)]


def _card_label(card: dict[str, Any]) -> str:
    color = _effective_color(card)
    if color:
        return f"{color} {card['value']}"
    return card["value"]


def _mechanics_or_default(mechanics: dict[str, Any] | None) -> dict[str, Any]:
    default = {
        "max_plays_per_turn": 1,
        "draw_count": 1,
        "draw_two_penalty": 2,
        "wild_draw_four_penalty": 4,
        "skip_penalty_cards": 0,
        "reverse_penalty_cards": 0,
        "allow_same_type_match": False,
        "allow_number_on_number": False,
        "allow_action_on_action": False,
        "win_hand_count": 0,
        "active_rule_ids": [],
    }
    if mechanics:
        default.update(mechanics)
    return default


def _ensure_turn_tracking(state: dict[str, Any]) -> None:
    state.setdefault("plays_this_turn_player_id", None)
    state.setdefault("plays_this_turn_count", 0)


def _record_play_for_turn(state: dict[str, Any], player_id: str) -> None:
    if state.get("plays_this_turn_player_id") != player_id:
        state["plays_this_turn_player_id"] = player_id
        state["plays_this_turn_count"] = 0
    state["plays_this_turn_count"] += 1


def _remaining_plays_this_turn(state: dict[str, Any], player_id: str, mechanics: dict[str, Any]) -> int:
    if state.get("plays_this_turn_player_id") == player_id:
        used = state.get("plays_this_turn_count", 0)
    else:
        used = 0
    return max(0, mechanics["max_plays_per_turn"] - used)


def _can_continue_playing(state: dict[str, Any], player_id: str, mechanics: dict[str, Any]) -> bool:
    if _remaining_plays_this_turn(state, player_id, mechanics) <= 0:
        return False
    player = state["players"][_player_index(state, player_id)]
    return _has_playable_card(player["hand"], _top_card(state), mechanics)
