from __future__ import annotations

import argparse
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

from .tools import DEFAULT_SERVER, UnoGameTools

VALID_COLORS = ("red", "yellow", "green", "blue")


@dataclass
class SimpleUnoAgent:
    """Deterministic baseline agent that uses the UNO API tool wrapper."""

    name: str
    tools: UnoGameTools
    player_id: str | None = None

    def register_from_state(self, state: dict[str, Any]) -> None:
        self.player_id = state["you"]["id"]

    def take_turn(self) -> dict[str, Any] | None:
        if not self.player_id:
            raise RuntimeError(f"{self.name} has no player_id. Register the agent first.")

        state = self.tools.get_player_state(self.player_id)
        if state["status"] != "active" or not state["you"]["is_current_turn"]:
            return None

        decision = decide_action(state)
        return self.tools.submit_action(self.player_id, decision)


def register_agent(tools: UnoGameTools, name: str, mode: str, player_id: str | None = None) -> SimpleUnoAgent:
    agent = SimpleUnoAgent(name, tools, player_id=player_id)
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


def decide_action(state: dict[str, Any]) -> dict[str, Any]:
    """Choose the next action from an agent's private state view."""

    playable_indexes = state.get("playable_indexes", [])
    hand = state["you"]["hand"]

    if playable_indexes:
        card_index = playable_indexes[0]
        card = hand[card_index]
        return {
            "action": "play",
            "card_index": card_index,
            "chosen_color": choose_wild_color(hand) if card["type"] == "wild" else None,
            "declare_uno": len(hand) == 2,
        }

    if state["you"].get("has_drawn_this_turn"):
        return {"action": "pass"}

    return {"action": "draw"}


def choose_wild_color(hand: list[dict[str, Any]]) -> str:
    colors = [card["color"] for card in hand if card.get("color") in VALID_COLORS]
    if not colors:
        return "red"
    return Counter(colors).most_common(1)[0][0]


def run_simple_agents(server: str, max_turns: int, delay_seconds: float) -> dict[str, Any]:
    tools = UnoGameTools(server)
    agent_a = SimpleUnoAgent("Agent A", tools)
    agent_b = SimpleUnoAgent("Agent B", tools)

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
    name: str,
    mode: str,
    max_turns: int,
    delay_seconds: float,
    player_id: str | None = None,
) -> dict[str, Any]:
    tools = UnoGameTools(server)
    agent = register_agent(tools, name, mode, player_id=player_id)
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
    parser = argparse.ArgumentParser(description="Run deterministic UNO agents.")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="UNO API base URL.")
    parser.add_argument(
        "--mode",
        choices=("local-two-agent", "create", "reset", "join", "resume"),
        default="local-two-agent",
        help="Run two local agents, create/reset as one remote agent, join as one remote agent, or resume by player id.",
    )
    parser.add_argument("--name", default="Agent", help="Agent name for single-agent modes.")
    parser.add_argument("--player-id", help="Existing player id for --mode resume.")
    parser.add_argument("--max-turns", type=int, default=300, help="Stop after this many agent decisions.")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between decisions, useful for observing.")
    args = parser.parse_args()

    if args.mode == "local-two-agent":
        final_state = run_simple_agents(args.server, args.max_turns, args.delay)
    else:
        if args.mode == "resume" and not args.player_id:
            parser.error("--mode resume requires --player-id")
        final_state = run_single_agent(
            args.server,
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
