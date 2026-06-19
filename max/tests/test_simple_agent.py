from uno_api.agents.simple_agent import choose_wild_color, decide_action, register_agent


def private_state(hand, playable_indexes, has_drawn=False):
    return {
        "status": "active",
        "playable_indexes": playable_indexes,
        "you": {
            "hand": hand,
            "is_current_turn": True,
            "has_drawn_this_turn": has_drawn,
        },
    }


def test_decide_action_plays_first_playable_card():
    state = private_state(
        [
            {"color": "red", "value": "3", "type": "number"},
            {"color": "blue", "value": "8", "type": "number"},
        ],
        [1],
    )

    assert decide_action(state) == {
        "action": "play",
        "card_index": 1,
        "chosen_color": None,
        "declare_uno": True,
    }


def test_decide_action_draws_before_passing():
    state = private_state(
        [{"color": "red", "value": "3", "type": "number"}],
        [],
    )

    assert decide_action(state) == {"action": "draw"}


def test_decide_action_passes_after_drawing_without_playable_card():
    state = private_state(
        [{"color": "red", "value": "3", "type": "number"}],
        [],
        has_drawn=True,
    )

    assert decide_action(state) == {"action": "pass"}


def test_decide_action_chooses_color_for_wild_from_most_common_hand_color():
    state = private_state(
        [
            {"color": None, "value": "wild", "type": "wild"},
            {"color": "green", "value": "3", "type": "number"},
            {"color": "green", "value": "4", "type": "number"},
            {"color": "blue", "value": "7", "type": "number"},
        ],
        [0],
    )

    assert decide_action(state)["chosen_color"] == "green"


def test_choose_wild_color_defaults_to_red_without_colored_cards():
    assert choose_wild_color([{"color": None, "value": "wild", "type": "wild"}]) == "red"


class FakeTools:
    def __init__(self):
        self.calls = []

    def create_game(self, name):
        self.calls.append(("create_game", name))
        return {"you": {"id": "created-id"}}

    def reset_game(self, name):
        self.calls.append(("reset_game", name))
        return {"you": {"id": "reset-id"}}

    def join_game(self, name):
        self.calls.append(("join_game", name))
        return {"you": {"id": "joined-id"}}


def test_register_agent_can_create_game():
    tools = FakeTools()

    agent = register_agent(tools, "Agent A", "create")

    assert agent.player_id == "created-id"
    assert tools.calls == [("create_game", "Agent A")]


def test_register_agent_can_resume_existing_player_id_without_api_registration():
    tools = FakeTools()

    agent = register_agent(tools, "Agent A", "reset", player_id="known-id")

    assert agent.player_id == "known-id"
    assert tools.calls == []
