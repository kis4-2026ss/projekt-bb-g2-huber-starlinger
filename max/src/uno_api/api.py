from __future__ import annotations

from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .engine import UnoError, apply_action, join_game, new_game, observer_view, player_view, public_view
from .models import AddRuleRequest, ApiMessage, CreateGameRequest, JoinGameRequest, ModifyRuleRequest, PlayerActionRequest, RemoveRuleRequest
from .rule_manager import RuleChangeError, add_mutable_rule, modify_mutable_rule, remove_mutable_rule, rule_mechanics
from .storage import ensure_storage, load_base_rules, load_mutable_rules, load_rules, load_state, save_mutable_rules, save_state

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATE_LOCK = Lock()

app = FastAPI(
    title="UNO Agent API",
    description="A two-agent UNO environment with REST tools and a read-only observer dashboard.",
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


@app.get("/api/rules/base")
def get_base_rules() -> dict:
    return load_base_rules()


@app.get("/api/rules/mutable")
def get_mutable_rules() -> dict:
    return load_mutable_rules()


@app.post("/api/rules/mutable")
def add_rule(request: AddRuleRequest) -> dict:
    with STATE_LOCK:
        try:
            mutable_rules = add_mutable_rule(
                load_mutable_rules(),
                request.player_id,
                request.rule.model_dump() if hasattr(request.rule, "model_dump") else request.rule.dict(),
            )
        except RuleChangeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return save_mutable_rules(
            mutable_rules,
            event={"type": "rule_added", "player_id": request.player_id, "rule_count": len(mutable_rules["rules"])},
        )


@app.patch("/api/rules/mutable/{rule_id}")
def modify_rule(rule_id: str, request: ModifyRuleRequest) -> dict:
    with STATE_LOCK:
        try:
            mutable_rules = modify_mutable_rule(load_mutable_rules(), request.player_id, rule_id, request.updates)
        except RuleChangeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return save_mutable_rules(
            mutable_rules,
            event={"type": "rule_modified", "player_id": request.player_id, "rule_id": rule_id},
        )


@app.delete("/api/rules/mutable/{rule_id}")
def remove_rule(rule_id: str, request: RemoveRuleRequest) -> dict:
    with STATE_LOCK:
        try:
            mutable_rules = remove_mutable_rule(load_mutable_rules(), request.player_id, rule_id)
        except RuleChangeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return save_mutable_rules(
            mutable_rules,
            event={"type": "rule_removed", "player_id": request.player_id, "rule_id": rule_id},
        )


@app.post("/api/games")
def create_game(request: CreateGameRequest) -> dict:
    with STATE_LOCK:
        state = new_game(request.player_name)
        save_state(
            state,
            event={"type": "game_created", "player_name": request.player_name, "game_id": state["game_id"]},
        )
        return player_view(state, state["players"][0]["id"], _mechanics_for(state, state["players"][0]["id"]))


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
        return player_view(state, state["players"][-1]["id"], _mechanics_for(state, state["players"][-1]["id"]))


@app.get("/api/games/state")
def get_state(player_id: str | None = None) -> dict:
    state = load_state()
    if not player_id:
        return public_view(state, _mechanics_for(state))
    try:
        return player_view(state, player_id, _mechanics_for(state, player_id))
    except UnoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/games/observer")
def get_observer_state() -> dict:
    state = load_state()
    return observer_view(state, _mechanics_for(state))


@app.post("/api/games/actions")
def action(request: PlayerActionRequest) -> dict:
    with STATE_LOCK:
        state = load_state()
        try:
            request_payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            state = apply_action(state, request.player_id, request_payload, _mechanics_for(state, request.player_id))
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
        return player_view(state, request.player_id, _mechanics_for(state, request.player_id))


@app.post("/api/games/reset")
def reset(request: CreateGameRequest) -> dict:
    with STATE_LOCK:
        state = new_game(request.player_name)
        save_state(
            state,
            event={"type": "game_reset", "player_name": request.player_name, "game_id": state["game_id"]},
        )
        return player_view(state, state["players"][0]["id"], _mechanics_for(state, state["players"][0]["id"]))


def _mechanics_for(state: dict, player_id: str | None = None) -> dict:
    if not state.get("players"):
        return rule_mechanics(load_mutable_rules())
    target_player_id = player_id or state.get("current_player_id")
    player = next((item for item in state["players"] if item["id"] == target_player_id), state["players"][state["current_player_index"]])
    top_card = state["discard_pile"][-1] if state.get("discard_pile") else {}
    return rule_mechanics(
        load_mutable_rules(),
        {
            "player_id": player["id"],
            "player_name": player["name"],
            "top_color": top_card.get("chosen_color") or top_card.get("color"),
            "top_value": top_card.get("value"),
        },
    )
