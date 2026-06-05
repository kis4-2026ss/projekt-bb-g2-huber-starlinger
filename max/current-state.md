# Current State

## Current Progress

The `max/` folder contains a working first version of a two-player UNO application.

Implemented so far:

- FastAPI server for creating, joining, resetting, and playing a UNO game.
- UNO game engine with draw pile, discard pile, turn handling, playable-card validation, skip/reverse, draw-two, wild, and wild-draw-four behavior.
- Browser frontend served by the API at `/`.
- CLI client for two human players.
- Dockerfile and `docker-compose.yml` for hosting the game server in a container.
- API documentation in `api-documentation.md`.
- Shared JSON context files in `shared/`.
- Basic engine tests in `tests/test_engine.py`.

The Docker container can host the game on port `8000`, so players can access it locally or from the same local network.

## Still Needed For Two Agents

The current version is ready for two human players, but not yet for autonomous AI agents.

Still needed:

- Agent implementations that can read game context and decide actions.
- A shared action format for agents, for example JSON containing `player_id`, `action`, `card_index`, and optional `chosen_color`.
- An orchestrator loop that alternates between Agent A and Agent B.
- Prompt templates that explain the current hand, top card, legal moves, and expected JSON response.
- Validation that rejects invalid agent responses before sending them to the API.
- Logging of agent prompts, responses, chosen actions, invalid moves, and final outcomes.
- Optional provider adapters for OpenAI, Gemini, Ollama, or mock agents.
- Evaluation logic for comparing agent strategies and game stability.

## Communication Files

The server writes shared context into `shared/`.

Files currently used for communication/context:

- `shared/rules.json`: public UNO rules used by the game.
- `shared/public_state.json`: public game state without hidden player hands.
- `shared/player_<player_id>.json`: private context for a specific player, including that player's hand and playable card indexes.
- `shared/events.jsonl`: append-only event log of game creation, joins, resets, and player actions.

For human players, the API and frontend are the main communication layer. For agents, these shared files can become the input context each agent reads before choosing an action.

## Next Steps

1. Add an `agents/` module with a common agent interface.
2. Implement a deterministic `mock_agent` first so agent-vs-agent games can run without API keys.
3. Add an orchestrator script that creates a game, joins both agents, reads each player's context, submits actions through the API, and stops when the game finishes.
4. Add prompt-based LLM agents after the mock agent works.
5. Write all prompts, responses, and actions to `shared/events.jsonl` or a dedicated run log.
6. Add tests for agent action validation and full simulated games.
7. Extend documentation with an agent-play section and example commands.

