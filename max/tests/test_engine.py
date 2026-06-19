import pytest

from uno_api.engine import UnoError, apply_action, join_game, new_game, observer_view


def active_game():
    state = new_game("Alice")
    return join_game(state, "Bob")


def test_join_starts_two_player_game():
    state = active_game()

    assert state["status"] == "active"
    assert len(state["players"]) == 2
    assert len(state["players"][0]["hand"]) == 7
    assert len(state["players"][1]["hand"]) == 7
    assert len(state["discard_pile"]) == 1


def test_player_cannot_act_out_of_turn():
    state = active_game()
    bob = state["players"][1]

    with pytest.raises(UnoError):
        apply_action(state, bob["id"], {"action": "draw"})


def test_matching_color_card_can_be_played():
    state = active_game()
    alice = state["players"][0]
    top = state["discard_pile"][-1]
    alice["hand"] = [{"color": top["color"], "value": "9", "type": "number"}]

    result = apply_action(
        state,
        alice["id"],
        {"action": "play", "card_index": 0, "declare_uno": False},
    )

    assert result["status"] == "finished"
    assert result["winner_id"] == alice["id"]


def test_wild_requires_chosen_color():
    state = active_game()
    alice = state["players"][0]
    alice["hand"] = [{"color": None, "value": "wild", "type": "wild", "chosen_color": None}]

    with pytest.raises(UnoError):
        apply_action(state, alice["id"], {"action": "play", "card_index": 0})


def test_observer_view_contains_both_visible_hands():
    state = active_game()

    view = observer_view(state)

    assert len(view["players"]) == 2
    assert len(view["players"][0]["hand"]) == 7
    assert len(view["players"][1]["hand"]) == 7
    assert "playable_indexes" in view["players"][0]


def test_mutable_rule_mechanics_can_allow_two_normal_plays_in_one_turn():
    state = active_game()
    alice = state["players"][0]
    state["discard_pile"] = [{"color": "red", "value": "3", "type": "number"}]
    alice["hand"] = [
        {"color": "red", "value": "5", "type": "number"},
        {"color": "red", "value": "8", "type": "number"},
    ]

    result = apply_action(
        state,
        alice["id"],
        {"action": "play", "card_index": 0},
        {"max_plays_per_turn": 2, "draw_count": 1, "draw_two_penalty": 2, "wild_draw_four_penalty": 4},
    )

    assert result["current_player_index"] == 0
    assert result["plays_this_turn_count"] == 1
    assert "may play again" in result["message"]


def test_turn_advances_after_reaching_mutable_play_limit():
    state = active_game()
    alice = state["players"][0]
    state["discard_pile"] = [{"color": "red", "value": "3", "type": "number"}]
    state["plays_this_turn_player_id"] = alice["id"]
    state["plays_this_turn_count"] = 1
    alice["hand"] = [
        {"color": "red", "value": "5", "type": "number"},
        {"color": "red", "value": "8", "type": "number"},
    ]

    result = apply_action(
        state,
        alice["id"],
        {"action": "play", "card_index": 0},
        {"max_plays_per_turn": 2, "draw_count": 1, "draw_two_penalty": 2, "wild_draw_four_penalty": 4},
    )

    assert result["current_player_index"] == 1
    assert result["plays_this_turn_count"] == 0
