import pytest

from uno_api.agents.ollama_agent import (
    OllamaAgentError,
    OllamaUnoAgent,
    normalize_action,
    parse_json_object,
)


def private_state(hand, playable_indexes, has_drawn=False):
    return {
        "status": "active",
        "top_card": {"color": "red", "value": "5", "type": "number"},
        "draw_pile_count": 40,
        "current_player_name": "Ollama Agent",
        "players": [
            {"id": "p1", "name": "Ollama Agent", "cards_in_hand": len(hand), "uno_declared": False},
            {"id": "p2", "name": "Other Agent", "cards_in_hand": 7, "uno_declared": False},
        ],
        "playable_indexes": playable_indexes,
        "you": {
            "id": "p1",
            "hand": hand,
            "is_current_turn": True,
            "has_drawn_this_turn": has_drawn,
        },
    }


def test_parse_json_object_accepts_plain_json():
    assert parse_json_object('{"action":"draw"}') == {"action": "draw"}


def test_parse_json_object_extracts_json_from_extra_text():
    assert parse_json_object('Decision: {"action":"pass"} done') == {"action": "pass"}


def test_normalize_action_accepts_playable_normal_card():
    state = private_state(
        [{"color": "red", "value": "7", "type": "number"}],
        [0],
    )

    assert normalize_action({"action": "play", "card_index": 0}, state) == {
        "action": "play",
        "card_index": 0,
        "chosen_color": None,
        "declare_uno": False,
    }


def test_normalize_action_requires_playable_index():
    state = private_state(
        [{"color": "blue", "value": "7", "type": "number"}],
        [],
    )

    with pytest.raises(OllamaAgentError):
        normalize_action({"action": "play", "card_index": 0}, state)


def test_normalize_action_accepts_wild_with_color():
    state = private_state(
        [{"color": None, "value": "wild", "type": "wild", "chosen_color": None}],
        [0],
    )

    assert normalize_action({"action": "play", "card_index": 0, "chosen_color": "green"}, state) == {
        "action": "play",
        "card_index": 0,
        "chosen_color": "green",
        "declare_uno": False,
    }


def test_normalize_action_converts_second_draw_to_pass():
    state = private_state(
        [{"color": "blue", "value": "7", "type": "number"}],
        [],
        has_drawn=True,
    )

    assert normalize_action({"action": "draw"}, state) == {"action": "pass"}


class BadClient:
    def chat_json(self, messages):
        raise RuntimeError("ollama unavailable")


class FakeTools:
    def get_player_state(self, player_id):
        return private_state(
            [
                {"color": "red", "value": "7", "type": "number"},
                {"color": "blue", "value": "9", "type": "number"},
            ],
            [0],
        )

    def submit_action(self, player_id, action):
        return {"player_id": player_id, "submitted": action}


def test_ollama_agent_falls_back_to_deterministic_action_when_model_fails():
    agent = OllamaUnoAgent("Ollama Agent", FakeTools(), BadClient(), player_id="p1")

    result = agent.take_turn()

    assert result["submitted"] == {
        "action": "play",
        "card_index": 0,
        "chosen_color": None,
        "declare_uno": True,
    }
