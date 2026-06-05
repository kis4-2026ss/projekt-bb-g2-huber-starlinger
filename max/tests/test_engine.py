import pytest

from uno_api.engine import UnoError, apply_action, join_game, new_game


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
