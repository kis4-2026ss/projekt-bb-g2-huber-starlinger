# Current State

## Current Progress

The `max/` folder contains an agent-focused UNO environment.

Implemented so far:

- FastAPI server for creating, joining, resetting, and playing a UNO game.
- UNO game engine with draw pile, discard pile, turn handling, playable-card validation, skip/reverse, draw-two, wild, and wild-draw-four behavior.
- Read-only browser observer dashboard served by the API at `/`, including visible hands, animations, impact text, and generated sound effects.
- Dockerfile and `docker-compose.yml` for hosting the game server in a container.
- API documentation in `api-documentation.md`.
- Shared JSON context files in `shared/`.
- Agent API tool wrapper in `src/uno_api/agents/tools.py`.
- Deterministic simple agent, local two-agent runner, and single-agent local-network runner in `src/uno_api/agents/simple_agent.py`.
- Basic engine and agent-tool tests in `tests/`.

The Docker container can host the game on port `8000`, so agents can call the API and observers can watch the public game state locally or from the same local network.

## Still Needed For Two Agents

The current version exposes the game through an agent-friendly API and tool wrapper, but does not yet include autonomous decision-making agents.

Still needed:

- LLM-backed agent implementations that can read game context and decide actions.
- Prompt templates that explain the current hand, top card, legal moves, and expected JSON response.
- Validation that rejects invalid agent responses before sending them to the API.
- Logging of agent prompts, responses, chosen actions, invalid moves, and final outcomes.
- Optional provider adapters for OpenAI, Gemini, Ollama, or mock agents.
- Evaluation logic for comparing agent strategies and game stability.

## Communication Files

The server writes shared context into `shared/`.

Files currently used for communication/context:

- `shared/rules.json`: public UNO rules used by the game.
- `shared/public_state.json`: public game state without hidden agent hands.
- `shared/player_<player_id>.json`: private context for a specific agent, including that agent's hand and playable card indexes.
- `shared/events.jsonl`: append-only event log of game creation, joins, resets, and agent actions.

The browser frontend is read-only and uses `/api/games/observer` so humans can watch both hands during agent play. Agents should use the API tool wrapper and can also read the shared context files before choosing an action.

Agents can use the named API tools in `src/uno_api/agents/tools.py` instead of calling raw HTTP endpoints directly. The available wrapper methods include `create_game`, `join_game`, `reset_game`, `get_public_state`, `get_observer_state`, `get_player_state`, `play_card`, `draw_card`, `pass_turn`, and `submit_action`.

## Next Steps

1. Add a common agent interface if more agent types are introduced.
2. Add prompt-based LLM agents after the simple deterministic agent remains stable.
3. Write all prompts, responses, and actions to `shared/events.jsonl` or a dedicated run log.
4. Add stricter validation for LLM-generated action JSON.
5. Add tests for full simulated games and LLM response handling.
6. Extend documentation with Ollama/OpenAI/Gemini agent setup examples.
