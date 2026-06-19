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
DEFAULT_RULE_CHANGE_INTERVAL = int(os.getenv("UNO_RULE_CHANGE_INTERVAL", "4"))


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
    rule_change_interval: int = DEFAULT_RULE_CHANGE_INTERVAL

    def register_from_state(self, state: dict[str, Any]) -> None:
        self.player_id = state["you"]["id"]

    def take_turn(self) -> dict[str, Any] | None:
        if not self.player_id:
            raise RuntimeError(f"{self.name} has no player_id. Register the agent first.")

        state = self.tools.get_player_state(self.player_id)
        if state["status"] != "active" or not state["you"]["is_current_turn"]:
            return None

        decision = self.decide_action(state)
        try:
            return self.execute_decision(decision, state)
        except GameApiError:
            fallback = fallback_decide_action(state)
            if fallback == decision:
                raise
            return self.tools.submit_action(self.player_id, fallback)

    def decide_action(self, state: dict[str, Any]) -> dict[str, Any]:
        mutable_rules = self.tools.get_mutable_rules()
        force_rule_action = should_attempt_rule_action(state, mutable_rules, self.rule_change_interval)
        messages = build_messages(self.name, state, mutable_rules, force_rule_action)
        try:
            raw_action = self.client.chat_json(messages)
            decision = normalize_decision(raw_action, state, mutable_rules)
            if force_rule_action and decision.get("kind") != "rule_action":
                return propose_rule_decision(self.name, state, mutable_rules)
            return decision
        except Exception:
            if force_rule_action:
                try:
                    return propose_rule_decision(self.name, state, mutable_rules)
                except OllamaAgentError:
                    pass
            return {"kind": "game_action", "game_action": fallback_decide_action(state)}

    def execute_decision(self, decision: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        kind = decision.get("kind", "game_action")
        if kind == "game_action":
            game_action = decision.get("game_action")
            if game_action is None and "action" in decision:
                game_action = decision
            if not isinstance(game_action, dict):
                raise OllamaAgentError("game_action decision requires a game_action object.")
            return self.tools.submit_action(self.player_id, game_action)
        if kind == "rule_action":
            result = execute_rule_action(self.tools, self.player_id, decision["rule_action"])
            # A rule change consumes the agent's current decision opportunity.
            self.tools.consume_turn_for_rule_change(self.player_id)
            next_state = self.tools.get_player_state(self.player_id)
            next_state["rule_action_result"] = result
            return next_state
        raise OllamaAgentError(f"Unknown decision kind: {kind}")


def register_agent(
    tools: UnoGameTools,
    client: OllamaClient,
    name: str,
    mode: str,
    player_id: str | None = None,
    rule_change_interval: int = DEFAULT_RULE_CHANGE_INTERVAL,
) -> OllamaUnoAgent:
    agent = OllamaUnoAgent(name, tools, client, player_id=player_id, rule_change_interval=rule_change_interval)
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


def build_messages(
    agent_name: str,
    state: dict[str, Any],
    mutable_rules: dict[str, Any] | None = None,
    force_rule_action: bool = False,
) -> list[dict[str, str]]:
    prompt_state = {
        "agent_name": agent_name,
        "status": state["status"],
        "top_card": state["top_card"],
        "draw_pile_count": state["draw_pile_count"],
        "current_player_name": state["current_player_name"],
        "your_hand": state["you"]["hand"],
        "playable_indexes": state["playable_indexes"],
        "active_rule_mechanics": state.get("active_rule_mechanics", {}),
        "mutable_rules": mutable_rules or {"rules": []},
        "rule_action_budget": "At most one rule action may be chosen for this turn. A rule action consumes the turn.",
        "rule_change_directive": (
            "You must choose kind=rule_action this turn. Add, modify, or remove one mutable rule."
            if force_rule_action
            else "You may choose kind=rule_action when it is strategically useful."
        ),
        "supported_rule_conditions": {
            "scope": ["all", "everyone"],
            "top_card": {"color": "red|yellow|green|blue", "value": "0-9|skip|reverse|draw_two|wild|wild_draw_four", "type": "number|action|wild"},
            "current_player": {"hand_count": {"eq": 2, "lt": 3, "lte": 2, "gt": 4, "gte": 5}},
            "opponent": {"hand_count": {"eq": 2, "lt": 3, "lte": 2, "gt": 4, "gte": 5}},
        },
        "supported_rule_effects": {
            "max_plays_per_turn": "integer 1..4",
            "draw_count": "integer 1..10",
            "draw_two_penalty": "integer 1..10",
            "wild_draw_four_penalty": "integer 1..10",
            "skip_penalty_cards": "integer 1..10",
            "reverse_penalty_cards": "integer 1..10",
            "allow_same_type_match": "boolean",
            "allow_number_on_number": "boolean",
            "allow_action_on_action": "boolean",
            "win_hand_count": "integer 1..3",
        },
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
                "Choose exactly one decision for the current turn. "
                "Return only JSON. You may choose a game action or a rule action. "
                "For a game action, return: "
                '{"kind":"game_action","game_action":{"action":"play|draw|pass","card_index":0,"chosen_color":"red|yellow|green|blue|null","declare_uno":true}}. '
                "For a rule action, return: "
                '{"kind":"rule_action","rule_action":{"operation":"add|modify|remove","rule":{...},"rule_id":"existing_id","updates":{...}}}. '
                "Use game_action.play only with an index from playable_indexes. "
                "Use chosen_color only for wild cards. "
                "A rule action must use only supported_rule_conditions and supported_rule_effects. "
                "If rule_change_directive says you must choose kind=rule_action, do not return a game action. "
                "Prefer a rule action when it creates a useful strategic advantage or interesting game evolution. "
                "Do not create duplicate rules. A rule action consumes your turn."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(prompt_state, ensure_ascii=True),
        },
    ]


def normalize_decision(
    raw_action: dict[str, Any],
    state: dict[str, Any],
    mutable_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(raw_action, dict):
        raise OllamaAgentError("Model response must be a JSON object.")
    if "kind" not in raw_action and "action" in raw_action:
        return {"kind": "game_action", "game_action": normalize_action(raw_action, state)}

    kind = raw_action.get("kind")
    if kind == "game_action":
        return {"kind": "game_action", "game_action": normalize_action(raw_action.get("game_action", {}), state)}
    if kind == "rule_action":
        return {
            "kind": "rule_action",
            "rule_action": normalize_rule_action(raw_action.get("rule_action", {}), mutable_rules or {"rules": []}),
        }
    raise OllamaAgentError("Decision kind must be game_action or rule_action.")


def should_attempt_rule_action(state: dict[str, Any], mutable_rules: dict[str, Any], interval: int) -> bool:
    if interval <= 0:
        return False
    rules = mutable_rules.get("rules", [])
    if not rules:
        return True
    turn = int(state.get("turn", 0))
    return turn > 0 and turn % interval == 0


def propose_rule_decision(agent_name: str, state: dict[str, Any], mutable_rules: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "rule_action",
        "rule_action": propose_rule_action(agent_name, state, mutable_rules),
    }


def propose_rule_action(agent_name: str, state: dict[str, Any], mutable_rules: dict[str, Any]) -> dict[str, Any]:
    existing_ids = {rule["id"] for rule in mutable_rules.get("rules", [])}
    for rule in rule_proposal_templates(agent_name, state):
        if rule["id"] not in existing_ids:
            return normalize_rule_action({"operation": "add", "rule": rule}, mutable_rules)

    rules = mutable_rules.get("rules", [])
    if not rules:
        raise OllamaAgentError("No mutable rule proposal is available.")

    turn = int(state.get("turn", 0))
    if len(rules) >= 4 and turn % 12 == 0:
        return normalize_rule_action({"operation": "remove", "rule_id": rules[0]["id"]}, mutable_rules)

    rule = rules[turn % len(rules)]
    updates = {
        "description": f"{rule.get('description', 'Mutable rule')} Updated by {agent_name} on turn {turn}.",
        "effect": next_modified_effect(rule.get("effect", {}), turn),
    }
    return normalize_rule_action({"operation": "modify", "rule_id": rule["id"], "updates": updates}, mutable_rules)


def rule_proposal_templates(agent_name: str, state: dict[str, Any]) -> list[dict[str, Any]]:
    safe_agent = "".join(character.lower() if character.isalnum() else "_" for character in agent_name).strip("_") or "agent"
    turn = int(state.get("turn", 0))
    return [
        {
            "id": f"{safe_agent}_two_plays",
            "title": "Two Plays Per Turn",
            "description": "Each player may play up to two cards before the turn advances.",
            "type": "turn_modifier",
            "condition": {"scope": "all"},
            "effect": {"max_plays_per_turn": 2},
        },
        {
            "id": f"{safe_agent}_double_draw",
            "title": "Double Draw",
            "description": "Drawing from the pile now draws two cards.",
            "type": "draw_modifier",
            "condition": {"scope": "all"},
            "effect": {"draw_count": 2},
        },
        {
            "id": f"{safe_agent}_action_chain",
            "title": "Action Chain",
            "description": "Action cards may be played on other action cards.",
            "type": "turn_modifier",
            "condition": {"scope": "all"},
            "effect": {"allow_action_on_action": True},
        },
        {
            "id": f"{safe_agent}_number_freedom",
            "title": "Number Freedom",
            "description": "Number cards may be played on any other number card.",
            "type": "turn_modifier",
            "condition": {"scope": "all"},
            "effect": {"allow_number_on_number": True},
        },
    ]


def next_modified_effect(effect: dict[str, Any], turn: int) -> dict[str, Any]:
    if "max_plays_per_turn" in effect:
        return {"max_plays_per_turn": min(4, int(effect["max_plays_per_turn"]) + 1)}
    if "draw_count" in effect:
        return {"draw_count": min(10, int(effect["draw_count"]) + 1)}
    if "draw_two_penalty" in effect:
        return {"draw_two_penalty": min(10, int(effect["draw_two_penalty"]) + 1)}
    if "wild_draw_four_penalty" in effect:
        return {"wild_draw_four_penalty": min(10, int(effect["wild_draw_four_penalty"]) + 1)}
    if "skip_penalty_cards" in effect:
        return {"skip_penalty_cards": min(10, int(effect["skip_penalty_cards"]) + 1)}
    if "reverse_penalty_cards" in effect:
        return {"reverse_penalty_cards": min(10, int(effect["reverse_penalty_cards"]) + 1)}
    if "allow_action_on_action" in effect:
        return {"allow_number_on_number": True}
    if "allow_number_on_number" in effect:
        return {"allow_same_type_match": True}
    if "allow_same_type_match" in effect:
        return {"allow_action_on_action": True}
    if "win_hand_count" in effect:
        return {"win_hand_count": min(3, int(effect["win_hand_count"]) + 1)}
    return {"skip_penalty_cards": 1 + (turn % 2)}


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


def normalize_rule_action(raw_rule_action: dict[str, Any], mutable_rules: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_rule_action, dict):
        raise OllamaAgentError("rule_action must be a JSON object.")
    operation = raw_rule_action.get("operation")
    if operation not in {"add", "modify", "remove"}:
        raise OllamaAgentError("rule_action.operation must be add, modify, or remove.")

    existing_ids = {rule["id"] for rule in mutable_rules.get("rules", [])}
    if operation == "add":
        rule = raw_rule_action.get("rule")
        if not isinstance(rule, dict):
            raise OllamaAgentError("add rule_action requires rule object.")
        validate_rule_shape(rule)
        if rule.get("id") in existing_ids:
            raise OllamaAgentError("Cannot add duplicate mutable rule id.")
        return {"operation": "add", "rule": rule}

    rule_id = raw_rule_action.get("rule_id")
    if not isinstance(rule_id, str) or not rule_id:
        raise OllamaAgentError("modify/remove rule_action requires rule_id.")
    if rule_id not in existing_ids:
        raise OllamaAgentError("Cannot modify/remove an unknown mutable rule.")
    if operation == "remove":
        return {"operation": "remove", "rule_id": rule_id}

    updates = raw_rule_action.get("updates")
    if not isinstance(updates, dict):
        raise OllamaAgentError("modify rule_action requires updates object.")
    if "effect" in updates:
        validate_effect_shape(updates["effect"])
    return {"operation": "modify", "rule_id": rule_id, "updates": updates}


def validate_rule_shape(rule: dict[str, Any]) -> None:
    if not str(rule.get("title", "")).strip() or not str(rule.get("description", "")).strip():
        raise OllamaAgentError("Rule title and description are required.")
    if rule.get("type", "custom") not in {"turn_modifier", "draw_modifier", "custom"}:
        raise OllamaAgentError("Unsupported mutable rule type.")
    if not isinstance(rule.get("condition", {}), dict):
        raise OllamaAgentError("Rule condition must be an object.")
    validate_effect_shape(rule.get("effect"))


def validate_effect_shape(effect: Any) -> None:
    if not isinstance(effect, dict):
        raise OllamaAgentError("Rule effect must be an object.")
    allowed = {
        "max_plays_per_turn",
        "draw_count",
        "draw_two_penalty",
        "wild_draw_four_penalty",
        "skip_penalty_cards",
        "reverse_penalty_cards",
        "allow_same_type_match",
        "allow_number_on_number",
        "allow_action_on_action",
        "win_hand_count",
    }
    if not allowed.intersection(effect):
        raise OllamaAgentError("Rule effect must include a supported mechanic key.")


def execute_rule_action(tools: UnoGameTools, player_id: str, rule_action: dict[str, Any]) -> dict[str, Any]:
    operation = rule_action["operation"]
    if operation == "add":
        return tools.add_mutable_rule(player_id, rule_action["rule"])
    if operation == "modify":
        return tools.modify_mutable_rule(player_id, rule_action["rule_id"], rule_action["updates"])
    if operation == "remove":
        return tools.remove_mutable_rule(player_id, rule_action["rule_id"])
    raise OllamaAgentError(f"Unsupported rule action operation: {operation}")


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
    rule_change_interval: int,
) -> dict[str, Any]:
    tools = UnoGameTools(server)
    client = OllamaClient(ollama_url, model)
    agent_a = OllamaUnoAgent("Ollama Agent A", tools, client, rule_change_interval=rule_change_interval)
    agent_b = OllamaUnoAgent("Ollama Agent B", tools, client, rule_change_interval=rule_change_interval)

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
    rule_change_interval: int,
    player_id: str | None = None,
) -> dict[str, Any]:
    tools = UnoGameTools(server)
    client = OllamaClient(ollama_url, model)
    agent = register_agent(tools, client, name, mode, player_id=player_id, rule_change_interval=rule_change_interval)
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
    parser.add_argument(
        "--rule-change-interval",
        type=int,
        default=DEFAULT_RULE_CHANGE_INTERVAL,
        help="Force a mutable rule action every N turns. Use 0 to disable forced rule changes.",
    )
    args = parser.parse_args()

    if args.mode == "local-two-agent":
        final_state = run_ollama_agents(
            args.server,
            args.ollama_url,
            args.model,
            args.max_turns,
            args.delay,
            args.rule_change_interval,
        )
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
            args.rule_change_interval,
            player_id=args.player_id,
        )
    print(f"status={final_state['status']} turn={final_state['turn']} message={final_state['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
