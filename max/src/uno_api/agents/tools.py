from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_SERVER = "http://127.0.0.1:8000"
COLORS = {"red", "yellow", "green", "blue"}


class GameApiError(RuntimeError):
    """Raised when the UNO API rejects or cannot complete a tool call."""


class UnoGameTools:
    """Named API tools that agents can call to interact with the UNO game."""

    def __init__(self, server: str = DEFAULT_SERVER) -> None:
        self.server = server.rstrip("/")

    def health(self) -> dict[str, Any]:
        return self._get("/api/health")

    def get_rules(self) -> dict[str, Any]:
        return self._get("/api/rules")

    def get_base_rules(self) -> dict[str, Any]:
        return self._get("/api/rules/base")

    def get_mutable_rules(self) -> dict[str, Any]:
        return self._get("/api/rules/mutable")

    def add_mutable_rule(self, player_id: str, rule: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/rules/mutable", {"player_id": player_id, "rule": rule})

    def modify_mutable_rule(self, player_id: str, rule_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/api/rules/mutable/{rule_id}", {"player_id": player_id, "updates": updates})

    def remove_mutable_rule(self, player_id: str, rule_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/api/rules/mutable/{rule_id}", {"player_id": player_id})

    def create_game(self, player_name: str) -> dict[str, Any]:
        return self._post("/api/games", {"player_name": player_name})

    def join_game(self, player_name: str) -> dict[str, Any]:
        return self._post("/api/games/join", {"player_name": player_name})

    def reset_game(self, player_name: str) -> dict[str, Any]:
        return self._post("/api/games/reset", {"player_name": player_name})

    def get_public_state(self) -> dict[str, Any]:
        return self._get("/api/games/state")

    def get_observer_state(self) -> dict[str, Any]:
        return self._get("/api/games/observer")

    def get_player_state(self, player_id: str) -> dict[str, Any]:
        query = urlencode({"player_id": player_id})
        return self._get(f"/api/games/state?{query}")

    def play_card(
        self,
        player_id: str,
        card_index: int,
        chosen_color: str | None = None,
        declare_uno: bool = True,
    ) -> dict[str, Any]:
        if chosen_color is not None and chosen_color not in COLORS:
            raise GameApiError("chosen_color must be red, yellow, green, or blue.")
        return self._post(
            "/api/games/actions",
            {
                "player_id": player_id,
                "action": "play",
                "card_index": card_index,
                "chosen_color": chosen_color,
                "declare_uno": declare_uno,
            },
        )

    def draw_card(self, player_id: str) -> dict[str, Any]:
        return self._post("/api/games/actions", {"player_id": player_id, "action": "draw"})

    def pass_turn(self, player_id: str) -> dict[str, Any]:
        return self._post("/api/games/actions", {"player_id": player_id, "action": "pass"})

    def submit_action(self, player_id: str, action: dict[str, Any]) -> dict[str, Any]:
        payload = {"player_id": player_id, **action}
        return self._post("/api/games/actions", payload)

    def _get(self, path: str) -> dict[str, Any]:
        try:
            with urlopen(f"{self.server}{path}") as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise GameApiError(_error_message(exc)) from exc

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, payload)

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.server}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise GameApiError(_error_message(exc)) from exc


def create_game(server: str, player_name: str) -> dict[str, Any]:
    return UnoGameTools(server).create_game(player_name)


def join_game(server: str, player_name: str) -> dict[str, Any]:
    return UnoGameTools(server).join_game(player_name)


def reset_game(server: str, player_name: str) -> dict[str, Any]:
    return UnoGameTools(server).reset_game(player_name)


def get_public_state(server: str) -> dict[str, Any]:
    return UnoGameTools(server).get_public_state()


def get_base_rules(server: str) -> dict[str, Any]:
    return UnoGameTools(server).get_base_rules()


def get_mutable_rules(server: str) -> dict[str, Any]:
    return UnoGameTools(server).get_mutable_rules()


def add_mutable_rule(server: str, player_id: str, rule: dict[str, Any]) -> dict[str, Any]:
    return UnoGameTools(server).add_mutable_rule(player_id, rule)


def modify_mutable_rule(server: str, player_id: str, rule_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    return UnoGameTools(server).modify_mutable_rule(player_id, rule_id, updates)


def remove_mutable_rule(server: str, player_id: str, rule_id: str) -> dict[str, Any]:
    return UnoGameTools(server).remove_mutable_rule(player_id, rule_id)


def get_observer_state(server: str) -> dict[str, Any]:
    return UnoGameTools(server).get_observer_state()


def get_player_state(server: str, player_id: str) -> dict[str, Any]:
    return UnoGameTools(server).get_player_state(player_id)


def play_card(
    server: str,
    player_id: str,
    card_index: int,
    chosen_color: str | None = None,
    declare_uno: bool = True,
) -> dict[str, Any]:
    return UnoGameTools(server).play_card(player_id, card_index, chosen_color, declare_uno)


def draw_card(server: str, player_id: str) -> dict[str, Any]:
    return UnoGameTools(server).draw_card(player_id)


def pass_turn(server: str, player_id: str) -> dict[str, Any]:
    return UnoGameTools(server).pass_turn(player_id)


def _error_message(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        return payload.get("detail", str(exc))
    except Exception:
        return str(exc)
