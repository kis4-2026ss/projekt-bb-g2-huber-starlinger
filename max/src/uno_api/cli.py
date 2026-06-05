from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DEFAULT_SERVER = "http://127.0.0.1:8000"
COLORS = {"red", "yellow", "green", "blue"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Two-player UNO CLI client.")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="UNO API base URL.")
    parser.add_argument("--name", required=True, help="Player name.")
    parser.add_argument("--join", action="store_true", help="Join the waiting game instead of creating one.")
    args = parser.parse_args()

    try:
        state = join_game(args.server, args.name) if args.join else create_game(args.server, args.name)
    except RuntimeError as exc:
        print(exc)
        return 1

    player_id = state["you"]["id"]
    print(f"Connected as {state['you']['name']}. Keep this player id private: {player_id}")
    print("Commands: play <index> [color], draw, pass, refresh, quit")

    while True:
        state = get_state(args.server, player_id)
        render_state(state)
        if state["status"] == "finished":
            return 0

        if not state["you"]["is_current_turn"]:
            time.sleep(2)
            continue

        command = input("uno> ").strip()
        if command in {"quit", "exit"}:
            return 0
        if command == "refresh":
            continue
        try:
            handle_command(args.server, player_id, command)
        except RuntimeError as exc:
            print(f"Error: {exc}")


def create_game(server: str, name: str) -> dict[str, Any]:
    return post_json(server, "/api/games", {"player_name": name})


def join_game(server: str, name: str) -> dict[str, Any]:
    return post_json(server, "/api/games/join", {"player_name": name})


def get_state(server: str, player_id: str) -> dict[str, Any]:
    return get_json(server, f"/api/games/state?player_id={player_id}")


def handle_command(server: str, player_id: str, command: str) -> None:
    parts = command.split()
    if not parts:
        return
    action = parts[0]
    if action == "draw":
        post_json(server, "/api/games/actions", {"player_id": player_id, "action": "draw"})
        return
    if action == "pass":
        post_json(server, "/api/games/actions", {"player_id": player_id, "action": "pass"})
        return
    if action == "play" and len(parts) >= 2:
        card_index = int(parts[1])
        chosen_color = parts[2] if len(parts) >= 3 else None
        if chosen_color and chosen_color not in COLORS:
            raise RuntimeError("Color must be red, yellow, green, or blue.")
        post_json(
            server,
            "/api/games/actions",
            {
                "player_id": player_id,
                "action": "play",
                "card_index": card_index,
                "chosen_color": chosen_color,
                "declare_uno": True,
            },
        )
        return
    raise RuntimeError("Unknown command.")


def render_state(state: dict[str, Any]) -> None:
    print("\n" + "=" * 72)
    print(f"Status: {state['status']} | Turn: {state['turn']} | {state['message']}")
    if state["top_card"]:
        print(f"Top card: {label(state['top_card'])} | Draw pile: {state['draw_pile_count']}")
    print("Players:")
    for player in state["players"]:
        marker = "*" if player["id"] == state["current_player_id"] else " "
        print(f" {marker} {player['name']}: {player['cards_in_hand']} cards")
    print("Your hand:")
    for index, card in enumerate(state["you"]["hand"]):
        playable = " playable" if index in state["playable_indexes"] else ""
        print(f"  [{index}] {label(card)}{playable}")


def label(card: dict[str, Any]) -> str:
    color = card.get("chosen_color") or card.get("color")
    return f"{color} {card['value']}" if color else card["value"]


def get_json(server: str, path: str) -> dict[str, Any]:
    try:
        with urlopen(f"{server}{path}") as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(_error_message(exc)) from exc


def post_json(server: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = Request(f"{server}{path}", data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(_error_message(exc)) from exc


def _error_message(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        return payload.get("detail", str(exc))
    except Exception:
        return str(exc)


if __name__ == "__main__":
    sys.exit(main())
