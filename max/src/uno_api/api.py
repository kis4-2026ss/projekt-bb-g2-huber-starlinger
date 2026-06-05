from __future__ import annotations

from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .engine import UnoError, apply_action, join_game, new_game, player_view, public_view
from .models import ApiMessage, CreateGameRequest, JoinGameRequest, PlayerActionRequest
from .storage import ensure_storage, load_rules, load_state, save_state

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATE_LOCK = Lock()

app = FastAPI(
    title="UNO Local Network API",
    description="A two-player UNO implementation playable by REST API calls, CLI, or browser.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup() -> None:
    ensure_storage()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health", response_model=ApiMessage)
def health() -> ApiMessage:
    return ApiMessage(message="UNO API is running.")


@app.get("/api/rules")
def get_rules() -> dict:
    return load_rules()


@app.post("/api/games")
def create_game(request: CreateGameRequest) -> dict:
    with STATE_LOCK:
        state = new_game(request.player_name)
        save_state(
            state,
            event={"type": "game_created", "player_name": request.player_name, "game_id": state["game_id"]},
        )
        return player_view(state, state["players"][0]["id"])


@app.post("/api/games/join")
def join(request: JoinGameRequest) -> dict:
    with STATE_LOCK:
        state = load_state()
        try:
            state = join_game(state, request.player_name)
        except UnoError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        save_state(
            state,
            event={"type": "player_joined", "player_name": request.player_name, "game_id": state["game_id"]},
        )
        return player_view(state, state["players"][-1]["id"])


@app.get("/api/games/state")
def get_state(player_id: str | None = None) -> dict:
    state = load_state()
    if not player_id:
        return public_view(state)
    try:
        return player_view(state, player_id)
    except UnoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/games/actions")
def action(request: PlayerActionRequest) -> dict:
    with STATE_LOCK:
        state = load_state()
        try:
            request_payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            state = apply_action(state, request.player_id, request_payload)
        except UnoError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        save_state(
            state,
            event={
                "type": "player_action",
                "player_id": request.player_id,
                "action": request.action,
                "card_index": request.card_index,
                "chosen_color": request.chosen_color,
                "turn": state["turn"],
            },
        )
        return player_view(state, request.player_id)


@app.post("/api/games/reset")
def reset(request: CreateGameRequest) -> dict:
    with STATE_LOCK:
        state = new_game(request.player_name)
        save_state(
            state,
            event={"type": "game_reset", "player_name": request.player_name, "game_id": state["game_id"]},
        )
        return player_view(state, state["players"][0]["id"])
