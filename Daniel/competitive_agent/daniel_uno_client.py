import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parents[1]
MAX_SRC_DIR = PROJECT_DIR / "max" / "src"
LOG_DIR = BASE_DIR / "logs"

sys.path.insert(0, str(MAX_SRC_DIR))

from uno_api.agents.tools import DEFAULT_SERVER, GameApiError, UnoGameTools  # noqa: E402
from strategy_agent import analyze_context, decide, write_log  # noqa: E402


VALID_COLORS = ("red", "yellow", "green", "blue")


def build_game_context(player_state: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    opponent_cards = None
    own_player_id = player_state["you"]["id"]
    for player in player_state.get("players", []):
        if player["id"] != own_player_id:
            opponent_cards = player.get("cards_in_hand")
            break

    allowed_actions = ["play", "draw"]
    if player_state["you"].get("has_drawn_this_turn"):
        allowed_actions = ["play", "pass"]

    return {
        "agent_id": "daniel_agent",
        "current_turn": player_state["you"]["is_current_turn"],
        "top_card": player_state.get("top_card"),
        "hand": player_state["you"]["hand"],
        "playable_indexes": player_state.get("playable_indexes", []),
        "opponent_cards_in_hand": opponent_cards,
        "valid_colors": rules.get("valid_colors", list(VALID_COLORS)),
        "allowed_actions": allowed_actions,
        "status": player_state.get("status"),
        "turn": player_state.get("turn"),
        "message": player_state.get("message"),
        "has_drawn_this_turn": player_state["you"].get("has_drawn_this_turn", False),
    }


def to_api_action(decision: dict[str, Any]) -> dict[str, Any]:
    action = decision["action"]
    if action == "play":
        return {
            "action": "play",
            "card_index": decision["card_index"],
            "chosen_color": decision.get("chosen_color"),
            "declare_uno": bool(decision.get("declare_uno", False)),
        }
    if action == "draw":
        return {"action": "draw"}
    if action == "pass":
        return {"action": "pass"}
    raise ValueError(f"Unsupported action: {action}")


def fallback_decision(game_context: dict[str, Any]) -> dict[str, Any]:
    hand = game_context.get("hand", [])
    tactical_analysis = analyze_context(game_context)
    ranked_moves = tactical_analysis.get("ranked_playable_moves", [])

    if ranked_moves:
        card_index = ranked_moves[0]["card_index"]
        card = hand[card_index]
        return {
            "agent_id": "daniel_agent",
            "action": "play",
            "card_index": card_index,
            "chosen_color": choose_wild_color(hand) if card.get("type") == "wild" else None,
            "declare_uno": len(hand) == 2,
            "visible_reason": f"Fallback: best ranked legal card. Reasons: {', '.join(ranked_moves[0].get('reasons', []))}",
            "confidence": 0.5,
        }

    if game_context.get("has_drawn_this_turn"):
        return {
            "agent_id": "daniel_agent",
            "action": "pass",
            "card_index": None,
            "chosen_color": None,
            "declare_uno": False,
            "visible_reason": "Fallback: already drew this turn.",
            "confidence": 0.3,
        }

    return {
        "agent_id": "daniel_agent",
        "action": "draw",
        "card_index": None,
        "chosen_color": None,
        "declare_uno": False,
        "visible_reason": "Fallback: no playable card.",
        "confidence": 0.3,
    }


def choose_wild_color(hand: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for card in hand:
        color = card.get("color")
        if color in VALID_COLORS:
            counts[color] = counts.get(color, 0) + 1
    if not counts:
        return "red"
    return max(counts, key=counts.get)


def register(tools: UnoGameTools, mode: str, name: str, player_id: str | None) -> str:
    if mode == "resume":
        if not player_id:
            raise ValueError("--mode resume requires --player-id")
        return player_id

    if mode == "reset":
        state = tools.reset_game(name)
    elif mode == "create":
        state = tools.create_game(name)
    elif mode == "join":
        state = tools.join_game(name)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    return state["you"]["id"]


def run_client(
    server: str,
    mode: str,
    name: str,
    max_turns: int,
    delay_seconds: float,
    player_id: str | None,
) -> dict[str, Any]:
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = LOG_DIR / f"daniel-client-run-{timestamp}.txt"

    tools = UnoGameTools(server)
    tools.health()
    registered_player_id = register(tools, mode, name, player_id)

    print(f"{name} registered with player_id={registered_player_id}")
    print(f"Log-Datei: {log_file}")

    write_log(log_file, "CLIENT START", f"server={server}\nmode={mode}\nplayer_id={registered_player_id}")

    acted_turns = 0
    while acted_turns < max_turns:
        public_state = tools.get_public_state()
        if public_state["status"] == "finished":
            write_log(log_file, "FINAL STATE", json.dumps(public_state, indent=2, ensure_ascii=False))
            return public_state

        if public_state["status"] == "waiting":
            time.sleep(delay_seconds)
            continue

        if public_state["current_player_id"] != registered_player_id:
            time.sleep(delay_seconds)
            continue

        player_state = tools.get_player_state(registered_player_id)
        rules = tools.get_rules()
        game_context = build_game_context(player_state, rules)
        turn_log_file = log_file

        try:
            decision = decide(game_context, turn_log_file)
        except Exception as exc:
            write_log(turn_log_file, "DECISION FALLBACK", f"{type(exc).__name__}: {exc}")
            decision = fallback_decision(game_context)
            write_log(turn_log_file, "FALLBACK DECISION", json.dumps(decision, indent=2, ensure_ascii=False))

        api_action = to_api_action(decision)
        write_log(turn_log_file, "API ACTION", json.dumps(api_action, indent=2, ensure_ascii=False))

        result = tools.submit_action(registered_player_id, api_action)
        acted_turns += 1
        print(f"{name}: turn={result['turn']} {result['message']}")
        write_log(turn_log_file, "SERVER RESULT", json.dumps(result, indent=2, ensure_ascii=False))

        time.sleep(delay_seconds)

    final_state = tools.get_public_state()
    write_log(log_file, "STOPPED AFTER MAX TURNS", json.dumps(final_state, indent=2, ensure_ascii=False))
    return final_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Daniel-Agent as one UNO API client.")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="UNO API base URL.")
    parser.add_argument(
        "--mode",
        choices=("reset", "create", "join", "resume"),
        default="join",
        help="Register mode: reset/create first player, join second player, or resume by player id.",
    )
    parser.add_argument("--name", default="Daniel-Agent", help="Player name.")
    parser.add_argument("--player-id", help="Existing player id for --mode resume.")
    parser.add_argument("--max-turns", type=int, default=300, help="Stop after this many Daniel-Agent decisions.")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between polling/decisions.")
    args = parser.parse_args()

    try:
        final_state = run_client(args.server, args.mode, args.name, args.max_turns, args.delay, args.player_id)
    except GameApiError as exc:
        print(f"UNO API error: {exc}")
        return 1
    except OSError as exc:
        print(f"Server nicht erreichbar: {exc}")
        return 1
    except ValueError as exc:
        print(f"Konfigurationsfehler: {exc}")
        return 1

    print(f"status={final_state['status']} turn={final_state['turn']} message={final_state['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
