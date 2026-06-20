from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .engine import default_rules, new_game, player_view, public_view, utc_now
from .rule_manager import combined_rules, default_mutable_rules, rule_mechanics

PROJECT_DIR = Path(__file__).resolve().parents[2]
PRIVATE_STATE_PATH = Path(os.getenv("UNO_PRIVATE_STATE_PATH", PROJECT_DIR / "src" / "uno_api" / "runtime" / "game_state.json"))
SHARED_DIR = Path(os.getenv("UNO_SHARED_DIR", PROJECT_DIR / "shared"))
RULES_PATH = SHARED_DIR / "rules.json"
BASE_RULES_PATH = SHARED_DIR / "base_rules.json"
MUTABLE_RULES_PATH = SHARED_DIR / "mutable_rules.json"
PUBLIC_STATE_PATH = SHARED_DIR / "public_state.json"
EVENT_LOG_PATH = SHARED_DIR / "events.jsonl"


def ensure_storage() -> None:
    PRIVATE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    if not BASE_RULES_PATH.exists():
        _write_json(BASE_RULES_PATH, default_rules())
    if not MUTABLE_RULES_PATH.exists():
        _write_json(MUTABLE_RULES_PATH, default_mutable_rules())
    if not RULES_PATH.exists():
        _write_json(RULES_PATH, combined_rules(load_mutable_rules()))
    if not PRIVATE_STATE_PATH.exists():
        state = new_game("Player 1")
        save_state(state, event={"type": "bootstrap", "message": "Initial waiting game created."})


def load_state() -> dict[str, Any]:
    ensure_storage()
    return json.loads(PRIVATE_STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any], event: dict[str, Any] | None = None) -> dict[str, Any]:
    _write_json(PRIVATE_STATE_PATH, state)
    publish_shared_context(state)
    if event:
        append_event(event)
    return state


def save_new_game(state: dict[str, Any], event: dict[str, Any] | None = None) -> dict[str, Any]:
    """Persist a new game with no rules or private views carried over from a prior game."""
    fresh_mutable_rules = default_mutable_rules()
    _write_json(MUTABLE_RULES_PATH, fresh_mutable_rules)
    _write_json(RULES_PATH, combined_rules(fresh_mutable_rules))

    # Player-specific files contain private hands, so they must not survive a new game.
    for player_context_path in SHARED_DIR.glob("player_*.json"):
        player_context_path.unlink()

    return save_state(state, event)


def load_rules() -> dict[str, Any]:
    ensure_storage()
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def load_base_rules() -> dict[str, Any]:
    ensure_storage()
    return json.loads(BASE_RULES_PATH.read_text(encoding="utf-8"))


def load_mutable_rules() -> dict[str, Any]:
    if not MUTABLE_RULES_PATH.exists():
        _write_json(MUTABLE_RULES_PATH, default_mutable_rules())
    return json.loads(MUTABLE_RULES_PATH.read_text(encoding="utf-8"))


def save_mutable_rules(mutable_rules: dict[str, Any], event: dict[str, Any] | None = None) -> dict[str, Any]:
    _write_json(MUTABLE_RULES_PATH, mutable_rules)
    _write_json(RULES_PATH, combined_rules(mutable_rules))
    if PRIVATE_STATE_PATH.exists():
        publish_shared_context(json.loads(PRIVATE_STATE_PATH.read_text(encoding="utf-8")))
    if event:
        append_event(event)
    return mutable_rules


def publish_shared_context(state: dict[str, Any]) -> None:
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(BASE_RULES_PATH, default_rules())
    _write_json(RULES_PATH, combined_rules(load_mutable_rules()))
    _write_json(PUBLIC_STATE_PATH, public_view(state, _mechanics_for(state)))
    for player in state["players"]:
        player_context_path = SHARED_DIR / f"player_{player['id']}.json"
        _write_json(player_context_path, player_view(state, player["id"], _mechanics_for(state, player["id"])))


def append_event(event: dict[str, Any]) -> None:
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": utc_now(), **event}
    with EVENT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _mechanics_for(state: dict[str, Any], player_id: str | None = None) -> dict[str, Any]:
    if not state.get("players"):
        return rule_mechanics(load_mutable_rules())
    target_player_id = player_id
    if not target_player_id and state.get("current_player_index") is not None:
        target_player_id = state["players"][state["current_player_index"]]["id"]
    player = next((item for item in state["players"] if item["id"] == target_player_id), state["players"][0])
    opponent = next((item for item in state["players"] if item["id"] != player["id"]), None)
    top_card = state["discard_pile"][-1] if state.get("discard_pile") else {}
    return rule_mechanics(
        load_mutable_rules(),
        {
            "player_id": player["id"],
            "player_name": player["name"],
            "current_player_id": player["id"],
            "current_player_name": player["name"],
            "current_player_hand_count": len(player["hand"]),
            "opponent_id": opponent["id"] if opponent else None,
            "opponent_name": opponent["name"] if opponent else None,
            "opponent_hand_count": len(opponent["hand"]) if opponent else None,
            "top_color": top_card.get("chosen_color") or top_card.get("color"),
            "top_value": top_card.get("value"),
            "top_type": top_card.get("type"),
        },
    )
