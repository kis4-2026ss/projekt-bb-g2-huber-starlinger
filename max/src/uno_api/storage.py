from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .engine import default_rules, new_game, player_view, public_view, utc_now

PROJECT_DIR = Path(__file__).resolve().parents[2]
PRIVATE_STATE_PATH = Path(os.getenv("UNO_PRIVATE_STATE_PATH", PROJECT_DIR / "src" / "uno_api" / "runtime" / "game_state.json"))
SHARED_DIR = Path(os.getenv("UNO_SHARED_DIR", PROJECT_DIR / "shared"))
RULES_PATH = SHARED_DIR / "rules.json"
PUBLIC_STATE_PATH = SHARED_DIR / "public_state.json"
EVENT_LOG_PATH = SHARED_DIR / "events.jsonl"


def ensure_storage() -> None:
    PRIVATE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    if not RULES_PATH.exists():
        _write_json(RULES_PATH, default_rules())
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


def load_rules() -> dict[str, Any]:
    ensure_storage()
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def publish_shared_context(state: dict[str, Any]) -> None:
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(RULES_PATH, default_rules())
    _write_json(PUBLIC_STATE_PATH, public_view(state))
    for player in state["players"]:
        player_context_path = SHARED_DIR / f"player_{player['id']}.json"
        _write_json(player_context_path, player_view(state, player["id"]))


def append_event(event: dict[str, Any]) -> None:
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": utc_now(), **event}
    with EVENT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
