from uno_api import storage
from uno_api.engine import new_game
from uno_api.rule_manager import add_mutable_rule, default_mutable_rules


def test_save_new_game_resets_mutable_rules_and_old_player_contexts(tmp_path, monkeypatch):
    shared_dir = tmp_path / "shared"
    private_state_path = tmp_path / "runtime" / "game_state.json"
    monkeypatch.setattr(storage, "SHARED_DIR", shared_dir)
    monkeypatch.setattr(storage, "PRIVATE_STATE_PATH", private_state_path)
    monkeypatch.setattr(storage, "RULES_PATH", shared_dir / "rules.json")
    monkeypatch.setattr(storage, "BASE_RULES_PATH", shared_dir / "base_rules.json")
    monkeypatch.setattr(storage, "MUTABLE_RULES_PATH", shared_dir / "mutable_rules.json")
    monkeypatch.setattr(storage, "PUBLIC_STATE_PATH", shared_dir / "public_state.json")
    monkeypatch.setattr(storage, "EVENT_LOG_PATH", shared_dir / "events.jsonl")

    old_rules = add_mutable_rule(
        default_mutable_rules(),
        "old-player",
        {
            "id": "old-rule",
            "title": "Old rule",
            "description": "An old rule that must not affect the next game.",
            "type": "turn_modifier",
            "condition": {"scope": "all"},
            "effect": {"max_plays_per_turn": 2},
        },
    )
    storage.save_mutable_rules(old_rules)
    shared_dir.mkdir(parents=True, exist_ok=True)
    (shared_dir / "player_old-player.json").write_text("old private view", encoding="utf-8")

    new_state = new_game("New player")
    storage.save_new_game(new_state)

    assert storage.load_state() == new_state
    assert storage.load_mutable_rules() == default_mutable_rules()
    assert not (shared_dir / "player_old-player.json").exists()
    assert (shared_dir / f"player_{new_state['players'][0]['id']}.json").exists()
