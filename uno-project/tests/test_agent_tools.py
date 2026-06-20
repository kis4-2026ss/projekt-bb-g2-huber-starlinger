import pytest

from uno_api.agents.tools import GameApiError, UnoGameTools


class FakeTools(UnoGameTools):
    def __init__(self):
        super().__init__("http://testserver")
        self.calls = []

    def _get(self, path):
        self.calls.append(("GET", path, None))
        return {"path": path}

    def _post(self, path, payload):
        self.calls.append(("POST", path, payload))
        return {"path": path, "payload": payload}

    def _request(self, method, path, payload):
        self.calls.append((method, path, payload))
        return {"path": path, "payload": payload}


def test_get_player_state_uses_player_query_parameter():
    tools = FakeTools()

    result = tools.get_player_state("player 1")

    assert result["path"] == "/api/games/state?player_id=player+1"


def test_get_observer_state_uses_observer_endpoint():
    tools = FakeTools()

    result = tools.get_observer_state()

    assert result["path"] == "/api/games/observer"


def test_add_mutable_rule_builds_payload():
    tools = FakeTools()

    result = tools.add_mutable_rule("p1", {"title": "Rule", "description": "Desc"})

    assert result["path"] == "/api/rules/mutable"
    assert result["payload"] == {
        "player_id": "p1",
        "rule": {"title": "Rule", "description": "Desc"},
    }


def test_modify_mutable_rule_uses_patch():
    tools = FakeTools()

    tools.modify_mutable_rule("p1", "rule_1", {"description": "New"})

    assert tools.calls == [("PATCH", "/api/rules/mutable/rule_1", {"player_id": "p1", "updates": {"description": "New"}})]


def test_consume_turn_for_rule_change_builds_action_payload():
    tools = FakeTools()

    result = tools.consume_turn_for_rule_change("p1")

    assert result["path"] == "/api/games/actions"
    assert result["payload"] == {"player_id": "p1", "action": "rule_change"}


def test_play_card_builds_action_payload():
    tools = FakeTools()

    result = tools.play_card("p1", 3, chosen_color="green", declare_uno=True)

    assert result["path"] == "/api/games/actions"
    assert result["payload"] == {
        "player_id": "p1",
        "action": "play",
        "card_index": 3,
        "chosen_color": "green",
        "declare_uno": True,
    }


def test_play_card_rejects_invalid_wild_color_before_api_call():
    tools = FakeTools()

    with pytest.raises(GameApiError):
        tools.play_card("p1", 3, chosen_color="purple")

    assert tools.calls == []
