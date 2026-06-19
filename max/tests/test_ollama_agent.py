import pytest

from uno_api.agents.ollama_agent import (
    OllamaAgentError,
    OllamaUnoAgent,
    execute_rule_action,
    normalize_action,
    normalize_decision,
    normalize_rule_action,
    parse_json_object,
    should_attempt_rule_action,
)


def private_state(hand, playable_indexes, has_drawn=False, turn=0):
    return {
        "status": "active",
        "turn": turn,
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


class GameActionClient:
    def chat_json(self, messages):
        return {"kind": "game_action", "game_action": {"action": "draw"}}


class FakeTools:
    def __init__(self):
        self.calls = []

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

    def get_mutable_rules(self):
        return {"version": 1, "rules": []}

    def add_mutable_rule(self, player_id, rule):
        self.calls.append(("add", player_id, rule))
        return {"rules": [rule]}

    def modify_mutable_rule(self, player_id, rule_id, updates):
        self.calls.append(("modify", player_id, rule_id, updates))
        return {"rules": [{"id": rule_id, **updates}]}

    def remove_mutable_rule(self, player_id, rule_id):
        self.calls.append(("remove", player_id, rule_id))
        return {"rules": []}

    def consume_turn_for_rule_change(self, player_id):
        self.calls.append(("consume_rule_turn", player_id))
        return {"message": "rule turn consumed"}


def test_ollama_agent_falls_back_to_deterministic_action_when_model_fails():
    agent = OllamaUnoAgent("Ollama Agent", FakeTools(), BadClient(), player_id="p1", rule_change_interval=0)

    result = agent.take_turn()

    assert result["submitted"] == {
        "action": "play",
        "card_index": 0,
        "chosen_color": None,
        "declare_uno": True,
    }


def test_normalize_decision_wraps_legacy_game_action():
    state = private_state([{"color": "red", "value": "7", "type": "number"}], [0])

    assert normalize_decision({"action": "draw"}, state) == {
        "kind": "game_action",
        "game_action": {"action": "draw"},
    }


def test_normalize_decision_accepts_rule_add_action():
    decision = normalize_decision(
        {
            "kind": "rule_action",
            "rule_action": {
                "operation": "add",
                "rule": {
                    "id": "two_cards",
                    "title": "Two Cards",
                    "description": "Play two cards.",
                    "type": "turn_modifier",
                    "condition": {"scope": "all"},
                    "effect": {"max_plays_per_turn": 2},
                },
            },
        },
        private_state([], []),
        {"rules": []},
    )

    assert decision["kind"] == "rule_action"
    assert decision["rule_action"]["operation"] == "add"


def test_should_attempt_rule_action_when_no_mutable_rules():
    assert should_attempt_rule_action(private_state([], []), {"rules": []}, 4) is True


def test_should_attempt_rule_action_on_interval():
    assert should_attempt_rule_action(private_state([], [], turn=8), {"rules": [{"id": "r1"}]}, 4) is True
    assert should_attempt_rule_action(private_state([], [], turn=9), {"rules": [{"id": "r1"}]}, 4) is False


def test_ollama_agent_forces_rule_action_when_model_plays_on_rule_turn():
    agent = OllamaUnoAgent("Ollama Agent", FakeTools(), GameActionClient(), player_id="p1", rule_change_interval=4)

    decision = agent.decide_action(private_state([{"color": "red", "value": "7", "type": "number"}], [0]))

    assert decision["kind"] == "rule_action"
    assert decision["rule_action"]["operation"] == "add"
    assert decision["rule_action"]["rule"]["effect"] == {"max_plays_per_turn": 2}


def test_normalize_rule_action_rejects_duplicate_add():
    with pytest.raises(OllamaAgentError):
        normalize_rule_action(
            {
                "operation": "add",
                "rule": {
                    "id": "two_cards",
                    "title": "Two Cards",
                    "description": "Play two cards.",
                    "effect": {"max_plays_per_turn": 2},
                },
            },
            {"rules": [{"id": "two_cards"}]},
        )


def test_execute_rule_action_calls_tool_wrapper():
    tools = FakeTools()
    rule = {
        "id": "two_cards",
        "title": "Two Cards",
        "description": "Play two cards.",
        "effect": {"max_plays_per_turn": 2},
    }

    execute_rule_action(tools, "p1", {"operation": "add", "rule": rule})

    assert tools.calls == [("add", "p1", rule)]
