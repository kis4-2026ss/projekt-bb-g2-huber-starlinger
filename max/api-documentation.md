# UNO Agent API Documentation

Base URL when running locally:

```text
http://127.0.0.1:8000
```

For other agent processes or observer browsers in the same local network, replace `127.0.0.1` with the host machine's LAN IP, for example:

```text
http://192.168.1.42:8000
```

The read-only observer dashboard is served at `/`. Interactive OpenAPI docs are available at `/docs` when the server is running.

## Shared Files

The server publishes agent-accessible context files into `shared/`:

| File | Purpose |
|---|---|
| `shared/rules.json` | Current public UNO rule set used by the engine. |
| `shared/base_rules.json` | Immutable base UNO rules. Agents may read this but must not modify it. |
| `shared/mutable_rules.json` | Agent-created rules that may be added, modified, or removed during a game. |
| `shared/public_state.json` | Public game state without hidden hands. |
| `shared/player_<player_id>.json` | Agent-specific context containing that agent's hand. |
| `shared/events.jsonl` | Append-only event log of game creation, joins, and actions. |

The private full game state is stored under `src/uno_api/runtime/game_state.json` and should not be edited by agents.

`shared/rules.json` combines both rule layers:

```json
{
  "base_rules": {},
  "mutable_rules": {},
  "note": "Only mutable_rules may be changed by agents. base_rules are immutable."
}
```

## Data Model

### Card

```json
{
  "color": "red",
  "value": "7",
  "type": "number"
}
```

Wild cards use `color: null` and receive a `chosen_color` after play:

```json
{
  "color": null,
  "value": "wild",
  "type": "wild",
  "chosen_color": "blue"
}
```

### Actions

Allowed agent actions:

```text
play
draw
pass
```

`play` requires `card_index`. Wild cards also require `chosen_color`.

## Endpoints

### `GET /api/health`

Checks whether the server is running.

Response:

```json
{
  "message": "UNO API is running."
}
```

### `GET /api/rules`

Returns the combined rule document containing immutable `base_rules` and changeable `mutable_rules`.

### `GET /api/rules/base`

Returns the immutable base UNO rules. These are the current original rules and cannot be modified by agents.

### `GET /api/rules/mutable`

Returns the current agent-created mutable rule layer.

### `POST /api/rules/mutable`

Adds a mutable rule.

Request:

```json
{
  "player_id": "PLAYER_ID",
  "rule": {
    "id": "bonus_red_7",
    "title": "Bonus Red Seven",
    "description": "Playing a red 7 is worth style points.",
    "type": "scoring",
    "condition": {
      "color": "red",
      "value": "7"
    },
    "effect": {
      "style_points": 1
    }
  }
}
```

Allowed mutable rule types:

```text
turn_modifier
draw_modifier
custom
```

Supported mechanic effects:

| Effect | Meaning |
|---|---|
| `max_plays_per_turn` | Maximum normal card plays an agent may make before the turn advances. |
| `draw_count` | Number of cards drawn by the normal `draw` action. |
| `draw_two_penalty` | Number of cards drawn by the opponent after `draw_two`. |
| `wild_draw_four_penalty` | Number of cards drawn by the opponent after `wild_draw_four`. |
| `skip_penalty_cards` | Number of cards drawn by the opponent after `skip`. |
| `reverse_penalty_cards` | Number of cards drawn by the opponent after `reverse`. |
| `allow_same_type_match` | Allows cards to be played on cards of the same type, even without color/value match. |
| `allow_number_on_number` | Allows any number card to be played on any other number card. |
| `allow_action_on_action` | Allows any action card to be played on any other action card. |
| `win_hand_count` | Allows a player to win after a play leaves them with this many cards or fewer. |

Aliases accepted for `max_plays_per_turn`:

```text
max_cards_per_turn
cards_per_turn
play_limit
```

Example: allow every agent to play up to two cards per turn:

```json
{
  "player_id": "PLAYER_ID",
  "rule": {
    "id": "two_cards_per_turn",
    "title": "Two Cards Per Turn",
    "description": "Every agent may play up to two normal cards before the turn advances.",
    "type": "turn_modifier",
    "condition": {
      "scope": "all"
    },
    "effect": {
      "max_plays_per_turn": 2
    }
  }
}
```

Every accepted mutable rule must contain at least one supported mechanic effect. Text-only mutable rules are rejected because mutable rules must affect gameplay.

Supported condition primitives:

| Condition | Example |
|---|---|
| Global scope | `"condition": {"scope": "all"}` |
| Top-card shorthand | `"condition": {"top_color": "red", "top_value": "7", "top_type": "number"}` |
| Top-card object | `"condition": {"top_card": {"color": "red", "type": "number"}}` |
| Current player | `"condition": {"current_player": {"hand_count": {"lte": 2}}}` |
| Opponent | `"condition": {"opponent": {"hand_count": {"gte": 5}}}` |

Numeric comparisons support:

```text
eq
lt
lte
gt
gte
```

Example: if the current agent has two or fewer cards, they may play any number on any number:

```json
{
  "player_id": "PLAYER_ID",
  "rule": {
    "id": "low_hand_number_freedom",
    "title": "Low Hand Number Freedom",
    "description": "Agents with two or fewer cards may play any number card on any number card.",
    "type": "turn_modifier",
    "condition": {
      "current_player": {
        "hand_count": {
          "lte": 2
        }
      }
    },
    "effect": {
      "allow_number_on_number": true
    }
  }
}
```

### `PATCH /api/rules/mutable/{rule_id}`

Modifies an existing mutable rule.

Request:

```json
{
  "player_id": "PLAYER_ID",
  "updates": {
    "description": "Updated rule description.",
    "effect": {
      "style_points": 2
    }
  }
}
```

### `DELETE /api/rules/mutable/{rule_id}`

Removes an existing mutable rule.

Request:

```json
{
  "player_id": "PLAYER_ID"
}
```

Rule-change endpoints update the shared rule context and immediately alter core UNO engine behavior for supported mechanic effects.

### `POST /api/games`

Creates a new waiting game and registers the first agent.

Request:

```json
{
  "player_name": "Agent A"
}
```

Response:

Returns Agent A's private state view. Save `you.id`; this is required for future calls.

### `POST /api/games/join`

Joins the waiting game as the second agent. The game starts immediately after this request.

Request:

```json
{
  "player_name": "Agent B"
}
```

Response:

Returns Agent B's private state view.

### `GET /api/games/state`

Returns the public game state without hidden hands.

Example:

```bash
curl http://127.0.0.1:8000/api/games/state
```

### `GET /api/games/observer`

Returns the observer dashboard state, including both agents' visible hands. This endpoint is intended for visualization, not for agent decision-making.

Example:

```bash
curl http://127.0.0.1:8000/api/games/observer
```

### `GET /api/games/state?player_id=<id>`

Returns the private state view for the given agent, including that agent's hand and playable card indexes.

Example:

```bash
curl "http://127.0.0.1:8000/api/games/state?player_id=PLAYER_ID"
```

### `POST /api/games/actions`

Submits an agent action.

Draw:

```json
{
  "player_id": "PLAYER_ID",
  "action": "draw"
}
```

Pass:

```json
{
  "player_id": "PLAYER_ID",
  "action": "pass"
}
```

Play a normal card:

```json
{
  "player_id": "PLAYER_ID",
  "action": "play",
  "card_index": 2,
  "declare_uno": true
}
```

Play a wild card:

```json
{
  "player_id": "PLAYER_ID",
  "action": "play",
  "card_index": 4,
  "chosen_color": "green",
  "declare_uno": true
}
```

### `POST /api/games/reset`

Resets the current game and registers the first agent for the new game.

Request:

```json
{
  "player_name": "Agent A"
}
```

## Agent Tool Wrapper

Agents should usually use the Python wrapper in `src/uno_api/agents/tools.py` instead of constructing raw HTTP requests manually.

Example:

```python
from uno_api.agents.tools import UnoGameTools

tools = UnoGameTools("http://127.0.0.1:8000")
agent_a = tools.reset_game("Agent A")
agent_b = tools.join_game("Agent B")

state = tools.get_player_state(agent_a["you"]["id"])
if state["playable_indexes"]:
    tools.play_card(agent_a["you"]["id"], state["playable_indexes"][0])
else:
    tools.draw_card(agent_a["you"]["id"])
```

Available wrapper methods:

```text
health
get_rules
get_base_rules
get_mutable_rules
add_mutable_rule
modify_mutable_rule
remove_mutable_rule
create_game
join_game
reset_game
get_public_state
get_observer_state
get_player_state
play_card
draw_card
pass_turn
submit_action
```

## Observer Dashboard

The browser dashboard does not create games, join games, or submit actions. It polls `GET /api/games/observer`, shows both agents' hands, animates card/state changes, and can play generated sound effects after sound is enabled in the browser.

Open it locally:

```text
http://127.0.0.1:8000
```

Observers on the same local network can open:

```text
http://<host-lan-ip>:8000
```

## Simple Agent Runner

The deterministic baseline agent is implemented in `src/uno_api/agents/simple_agent.py`.

Run two simple agents against each other:

```bash
PYTHONPATH=src python -m uno_api.agents.simple_agent
```

Against a server on another host or port:

```bash
PYTHONPATH=src python -m uno_api.agents.simple_agent --server http://127.0.0.1:8000
```

Run agents from two different computers on the same local network:

On computer 1:

```bash
PYTHONPATH=src python -m uno_api.agents.simple_agent \
  --server http://192.168.1.42:8000 \
  --mode reset \
  --name "Agent A" \
  --delay 1
```

On computer 2:

```bash
PYTHONPATH=src python -m uno_api.agents.simple_agent \
  --server http://192.168.1.42:8000 \
  --mode join \
  --name "Agent B" \
  --delay 1
```

Replace `192.168.1.42` with the LAN IP of the computer running the Docker container.

If a single-agent process stops, restart it with the printed `player_id`:

```bash
PYTHONPATH=src python -m uno_api.agents.simple_agent \
  --server http://192.168.1.42:8000 \
  --mode resume \
  --name "Agent A" \
  --player-id PLAYER_ID
```

The simple agent always follows the same strategy:

1. Play the first playable card.
2. For wild cards, choose the most common color still in its hand, defaulting to red.
3. Draw if no card is playable.
4. Pass if it already drew this turn and still has no playable card.

## Ollama Agent Runner

The Ollama-backed agent is implemented in `src/uno_api/agents/ollama_agent.py`.

Prerequisites:

```bash
ollama serve
ollama pull llama3.2:3b
```

Run two Ollama agents locally against the UNO server:

```bash
PYTHONPATH=src python -m uno_api.agents.ollama_agent \
  --server http://127.0.0.1:8000 \
  --ollama-url http://127.0.0.1:11434 \
  --model llama3.2:3b \
  --delay 1
```

Run one Ollama agent per computer on a local network:

Computer 1:

```bash
PYTHONPATH=src python -m uno_api.agents.ollama_agent \
  --server http://192.168.1.42:8000 \
  --ollama-url http://127.0.0.1:11434 \
  --model llama3.2:3b \
  --mode reset \
  --name "Ollama Agent A" \
  --delay 1
```

Computer 2:

```bash
PYTHONPATH=src python -m uno_api.agents.ollama_agent \
  --server http://192.168.1.42:8000 \
  --ollama-url http://127.0.0.1:11434 \
  --model llama3.2:3b \
  --mode join \
  --name "Ollama Agent B" \
  --delay 1
```

The Ollama agent asks the model for one strict JSON action per turn. If Ollama returns invalid JSON, an illegal action, or is temporarily unavailable, the agent falls back to the deterministic simple-agent action for that turn so the game can continue.

## Docker Usage

Build and start the server:

```bash
docker compose up --build
```

The compose file mounts `shared/` and `src/uno_api/runtime/` as volumes so game context survives container restarts.
