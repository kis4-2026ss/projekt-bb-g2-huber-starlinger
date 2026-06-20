import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DANIEL_AGENT_DIR = PROJECT_ROOT / "Daniel" / "competitive_agent"
if str(DANIEL_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(DANIEL_AGENT_DIR))

from daniel_uno_client import (  # noqa: E402
    build_game_context,
    choose_turn_action,
    execute_rule_proposal,
    execute_rule_turn,
)


class FakeTools:
    def __init__(self):
        self.calls = []

    def add_mutable_rule(self, player_id, rule):
        self.calls.append(("add", player_id, rule))
        return {"operation": "add", "rule": rule}

    def modify_mutable_rule(self, player_id, rule_id, updates):
        self.calls.append(("modify", player_id, rule_id, updates))
        return {"operation": "modify", "rule_id": rule_id, "updates": updates}

    def remove_mutable_rule(self, player_id, rule_id):
        self.calls.append(("remove", player_id, rule_id))
        return {"operation": "remove", "rule_id": rule_id}

    def consume_turn_for_rule_change(self, player_id):
        self.calls.append(("consume_rule_turn", player_id))
        return {"turn": 7, "message": "Daniel-Agent changed the mutable rules."}


def player_state():
    return {
        "status": "active",
        "turn": 4,
        "message": "Daniel-Agent turn.",
        "top_card": {"color": "red", "value": "5", "type": "number"},
        "playable_indexes": [0],
        "players": [
            {"id": "p1", "name": "Daniel-Agent", "cards_in_hand": 2},
            {"id": "p2", "name": "Other Agent", "cards_in_hand": 3},
        ],
        "you": {
            "id": "p1",
            "name": "Daniel-Agent",
            "is_current_turn": True,
            "has_drawn_this_turn": False,
            "hand": [
                {"color": "red", "value": "7", "type": "number"},
                {"color": "blue", "value": "9", "type": "number"},
            ],
        },
    }


def test_build_game_context_accepts_combined_rules_shape():
    context = build_game_context(
        player_state(),
        {"base_rules": {"valid_colors": ["red", "green"]}, "mutable_rules": {"rules": []}},
    )

    assert context["current_turn"] is True
    assert context["playable_indexes"] == [0]
    assert context["opponent_cards_in_hand"] == 3
    assert context["allowed_actions"] == ["play", "draw"]
    assert context["valid_colors"] == ["red", "green"]


def test_execute_rule_proposal_supports_add_modify_remove():
    tools = FakeTools()

    execute_rule_proposal(tools, "p1", {"operation": "add", "rule": {"id": "r1"}})
    execute_rule_proposal(tools, "p1", {"operation": "modify", "rule_id": "r1", "updates": {"effect": {"draw_count": 2}}})
    execute_rule_proposal(tools, "p1", {"operation": "remove", "rule_id": "r1"})

    assert tools.calls == [
        ("add", "p1", {"id": "r1"}),
        ("modify", "p1", "r1", {"effect": {"draw_count": 2}}),
        ("remove", "p1", "r1"),
    ]


def test_execute_rule_turn_consumes_turn_after_rule_change():
    tools = FakeTools()

    result = execute_rule_turn(tools, "p1", {"operation": "add", "rule": {"id": "r1"}})

    assert result["turn_result"]["turn"] == 7
    assert tools.calls == [
        ("add", "p1", {"id": "r1"}),
        ("consume_rule_turn", "p1"),
    ]


def test_choose_turn_action_accepts_modify_rule_effects():
    assert (
        choose_turn_action(
            {"hand": [{}, {}, {}], "playable_indexes": [], "opponent_cards_in_hand": 5},
            {"operation": "modify", "rule_id": "r1", "updates": {"effect": {"max_plays_per_turn": 3}}},
        )
        == "rule"
    )
