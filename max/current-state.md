# Current State

## Current Progress

The `max/` folder contains an agent-focused UNO environment.

Implemented so far:

- FastAPI server for creating, joining, resetting, and playing a UNO game.
- UNO game engine with draw pile, discard pile, turn handling, playable-card validation, skip/reverse, draw-two, wild, and wild-draw-four behavior.
- Read-only browser observer dashboard served by the API at `/`, including visible hands, animations, impact text, and generated sound effects.
- Dockerfile and `docker-compose.yml` for hosting the game server in a container.
- API documentation in `api-documentation.md`.
- Shared JSON context files in `shared/`, including immutable base rules and mutable agent-created rules.
- Rule-change API endpoints for adding, modifying, and removing mutable rules.
- Engine integration for supported mutable rule effects: `max_plays_per_turn`, `draw_count`, `draw_two_penalty`, and `wild_draw_four_penalty`.
- Agent API tool wrapper in `src/uno_api/agents/tools.py`.
- Deterministic simple agent, local two-agent runner, and single-agent local-network runner in `src/uno_api/agents/simple_agent.py`.
- Ollama-backed LLM agent with JSON action validation and deterministic fallback in `src/uno_api/agents/ollama_agent.py`.
- Basic engine and agent-tool tests in `tests/`.

The Docker container can host the game on port `8000`, so agents can call the API and observers can watch the public game state locally or from the same local network.

## Still Needed For Two Agents

The current version exposes the game through an agent-friendly API and tool wrapper, but does not yet include autonomous decision-making agents.

Still needed:

- OpenAI/Gemini agent implementations if additional model providers are needed.
- Prompt templates that explain the current hand, top card, current mutable rules, legal moves, and expected JSON response.
- Validation that rejects invalid agent responses before sending them to the API.
- More supported mutable rule effects if the project needs additional mechanics.
- Logging of agent prompts, responses, chosen actions, invalid moves, and final outcomes.
- Optional provider adapters for OpenAI, Gemini, Ollama, or mock agents.
- Evaluation logic for comparing agent strategies and game stability.

## Communication Files

The server writes shared context into `shared/`.

Files currently used for communication/context:

- `shared/rules.json`: public UNO rules used by the game.
- `shared/base_rules.json`: immutable base UNO rules. Agents may read this but not modify it.
- `shared/mutable_rules.json`: mutable agent-created rule layer.
- `shared/public_state.json`: public game state without hidden agent hands.
- `shared/player_<player_id>.json`: private context for a specific agent, including that agent's hand and playable card indexes.
- `shared/events.jsonl`: append-only event log of game creation, joins, resets, and agent actions.

The browser frontend is read-only and uses `/api/games/observer` so humans can watch both hands during agent play. Agents should use the API tool wrapper and can also read the shared context files before choosing an action.

Agents can use the named API tools in `src/uno_api/agents/tools.py` instead of calling raw HTTP endpoints directly. The available wrapper methods include `get_rules`, `get_base_rules`, `get_mutable_rules`, `add_mutable_rule`, `modify_mutable_rule`, `remove_mutable_rule`, `create_game`, `join_game`, `reset_game`, `get_public_state`, `get_observer_state`, `get_player_state`, `play_card`, `draw_card`, `pass_turn`, and `submit_action`.

## Next Steps

1. Add a common agent interface if more agent types are introduced.
2. Teach LLM agents when to choose normal card actions versus mutable rule changes.
3. Add more supported mutable rule effects after the first rule-evolution experiments.
4. Try the Ollama agent with different local models and compare behavior.
5. Write all prompts, responses, and actions to `shared/events.jsonl` or a dedicated run log.
6. Add stricter validation for LLM-generated action JSON.
7. Add tests for full simulated games and LLM response handling.
