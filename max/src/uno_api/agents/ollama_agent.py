from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen

from .simple_agent import decide_action as fallback_decide_action
from .tools import COLORS, DEFAULT_SERVER, GameApiError, UnoGameTools

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:latest")


class OllamaAgentError(RuntimeError):
    """Raised when the Ollama agent cannot get a usable model response."""


@dataclass
class OllamaClient:
    base_url: str = DEFAULT_OLLAMA_URL
    model: str = DEFAULT_OLLAMA_MODEL
    temperature: float = 0.2
    timeout_seconds: int = 60

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
            },
        }
        request = Request(
            f"{self.base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data.get("message", {}).get("content", "")
        return parse_json_object(content)


@dataclass
class OllamaUnoAgent:
    name: str
    tools: UnoGameTools
    client: OllamaClient
    player_id: str | None = None

    def register_from_state(self, state: dict[str, Any]) -> None:
        self.player_id = state["you"]["id"]

    def take_turn(self) -> dict[str, Any] | None:
        if not self.player_id:
            raise RuntimeError(f"{self.name} has no player_id. Register the agent first.")

        state = self.tools.get_player_state(self.player_id)
        if state["status"] != "active" or not state["you"]["is_current_turn"]:
            return None

        action = self.decide_action(state)
        try:
            return self.tools.submit_action(self.player_id, action)
        except GameApiError:
            fallback = fallback_decide_action(state)
            if fallback == action:
                raise
            return self.tools.submit_action(self.player_id, fallback)

    def decide_action(self, state: dict[str, Any]) -> dict[str, Any]:
        messages = build_messages(self.name, state)
        try:
            raw_action = self.client.chat_json(messages)
            return normalize_action(raw_action, state)
        except Exception:
            return fallback_decide_action(state)


def register_agent(
    tools: UnoGameTools,
    client: OllamaClient,
    name: str,
    mode: str,
    player_id: str | None = None,
) -> OllamaUnoAgent:
    agent = OllamaUnoAgent(name, tools, client, player_id=player_id)
    if player_id:
        return agent
    if mode == "create":
        agent.register_from_state(tools.create_game(name))
    elif mode == "reset":
        agent.register_from_state(tools.reset_game(name))
    elif mode == "join":
        agent.register_from_state(tools.join_game(name))
    else:
        raise ValueError(f"Unsupported single-agent mode: {mode}")
    return agent


def build_messages(agent_name: str, state: dict[str, Any]) -> list[dict[str, str]]:
    prompt_state = {
        "agent_name": agent_name,
        "status": state["status"],
        "top_card": state["top_card"],
        "draw_pile_count": state["draw_pile_count"],
        "current_player_name": state["current_player_name"],
        "your_hand": state["you"]["hand"],
        "playable_indexes": state["playable_indexes"],
        "active_rule_mechanics": state.get("active_rule_mechanics", {}),
        "has_drawn_this_turn": state["you"].get("has_drawn_this_turn", False),
        "plays_this_turn_count": state["you"].get("plays_this_turn_count", 0),
        "remaining_plays_this_turn": state["you"].get("remaining_plays_this_turn", 1),
        "opponents": [
            {
                "name": player["name"],
                "cards_in_hand": player["cards_in_hand"],
                "uno_declared": player["uno_declared"],
            }
            for player in state["players"]
            if player["id"] != state["you"]["id"]
        ],
    }
    return [
        {
            "role": "system",
            "content": (
                "You are an autonomous UNO-playing agent. "
                "Choose exactly one legal action for the current turn. "
                "Return only JSON with this schema: "
                '{"action":"play|draw|pass","card_index":0,"chosen_color":"red|yellow|green|blue|null","declare_uno":true}. '
                "Use action=play only with an index from playable_indexes. "
                "Use chosen_color only for wild cards. "
                "Use action=draw if no card is playable and you have not drawn this turn. "
                "Use action=pass only after drawing this turn or when no card is playable."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(prompt_state, ensure_ascii=True),
        },
    ]


def normalize_action(raw_action: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_action, dict):
        raise OllamaAgentError("Model response must be a JSON object.")

    action = raw_action.get("action")
    if action not in {"play", "draw", "pass"}:
        raise OllamaAgentError("Action must be play, draw, or pass.")

    playable_indexes = state.get("playable_indexes", [])
    hand = state["you"]["hand"]
    has_drawn = state["you"].get("has_drawn_this_turn", False)

    if action == "draw":
        if has_drawn:
            return {"action": "pass"}
        return {"action": "draw"}

    if action == "pass":
        if playable_indexes and not has_drawn:
            raise OllamaAgentError("Cannot pass while playable cards are available before drawing.")
        return {"action": "pass"}

    card_index = raw_action.get("card_index")
    if not isinstance(card_index, int) or card_index not in playable_indexes or card_index >= len(hand):
        raise OllamaAgentError("play actions require card_index from playable_indexes.")

    card = hand[card_index]
    chosen_color = raw_action.get("chosen_color")
    if card["type"] == "wild":
        if chosen_color not in COLORS:
            raise OllamaAgentError("Wild cards require a valid chosen_color.")
    else:
        chosen_color = None

    return {
        "action": "play",
        "card_index": card_index,
        "chosen_color": chosen_color,
        "declare_uno": bool(raw_action.get("declare_uno", len(hand) == 2)),
    }


def parse_json_object(content: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise OllamaAgentError("Model did not return JSON.") from exc
        value = json.loads(content[start : end + 1])
    if not isinstance(value, dict):
        raise OllamaAgentError("Model response must be a JSON object.")
    return value


def run_ollama_agents(
    server: str,
    ollama_url: str,
    model: str,
    max_turns: int,
    delay_seconds: float,
) -> dict[str, Any]:
    tools = UnoGameTools(server)
    client = OllamaClient(ollama_url, model)
    agent_a = OllamaUnoAgent("Ollama Agent A", tools, client)
    agent_b = OllamaUnoAgent("Ollama Agent B", tools, client)

    agent_a.register_from_state(tools.reset_game(agent_a.name))
    agent_b.register_from_state(tools.join_game(agent_b.name))
    agents_by_id = {
        agent_a.player_id: agent_a,
        agent_b.player_id: agent_b,
    }

    for _ in range(max_turns):
        public_state = tools.get_public_state()
        if public_state["status"] == "finished":
            return public_state

        current_agent = agents_by_id.get(public_state["current_player_id"])
        if current_agent:
            current_agent.take_turn()

        if delay_seconds:
            time.sleep(delay_seconds)

    return tools.get_public_state()


def run_single_agent(
    server: str,
    ollama_url: str,
    model: str,
    name: str,
    mode: str,
    max_turns: int,
    delay_seconds: float,
    player_id: str | None = None,
) -> dict[str, Any]:
    tools = UnoGameTools(server)
    client = OllamaClient(ollama_url, model)
    agent = register_agent(tools, client, name, mode, player_id=player_id)
    print(f"{agent.name} registered with player_id={agent.player_id}")

    acted_turns = 0
    while acted_turns < max_turns:
        public_state = tools.get_public_state()
        if public_state["status"] == "finished":
            return public_state

        if public_state["status"] == "waiting":
            time.sleep(delay_seconds)
            continue

        if public_state["current_player_id"] == agent.player_id:
            result = agent.take_turn()
            if result:
                acted_turns += 1
                print(f"{agent.name}: turn={result['turn']} {result['message']}")

        if delay_seconds:
            time.sleep(delay_seconds)

    return tools.get_public_state()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Ollama-backed UNO agents.")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="UNO API base URL.")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama API base URL.")
    parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL, help="Ollama model name.")
    parser.add_argument(
        "--mode",
        choices=("local-two-agent", "create", "reset", "join", "resume"),
        default="local-two-agent",
        help="Run two local Ollama agents, create/reset as one remote agent, join as one remote agent, or resume by player id.",
    )
    parser.add_argument("--name", default="Ollama Agent", help="Agent name for single-agent modes.")
    parser.add_argument("--player-id", help="Existing player id for --mode resume.")
    parser.add_argument("--max-turns", type=int, default=300, help="Stop after this many agent decisions.")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between decisions, useful for observing.")
    args = parser.parse_args()

    if args.mode == "local-two-agent":
        final_state = run_ollama_agents(args.server, args.ollama_url, args.model, args.max_turns, args.delay)
    else:
        if args.mode == "resume" and not args.player_id:
            parser.error("--mode resume requires --player-id")
        final_state = run_single_agent(
            args.server,
            args.ollama_url,
            args.model,
            args.name,
            args.mode,
            args.max_turns,
            args.delay,
            player_id=args.player_id,
        )
    print(f"status={final_state['status']} turn={final_state['turn']} message={final_state['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
