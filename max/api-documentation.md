# UNO Local Network API Documentation

Base URL when running locally:

```text
http://127.0.0.1:8000
```

For other players in the same local network, replace `127.0.0.1` with the host machine's LAN IP, for example:

```text
http://192.168.1.42:8000
```

The browser frontend is served at `/`. Interactive OpenAPI docs are available at `/docs` when the server is running.

## Shared Files

The server publishes player-accessible context files into `shared/`:

| File | Purpose |
|---|---|
| `shared/rules.json` | Current public UNO rule set used by the engine. |
| `shared/public_state.json` | Public game state without hidden hands. |
| `shared/player_<player_id>.json` | Player-specific context containing that player's hand. |
| `shared/events.jsonl` | Append-only event log of game creation, joins, and actions. |

The private full game state is stored under `src/uno_api/runtime/game_state.json` and should not be edited by players.

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

Allowed player actions:

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

Returns the currently applicable public UNO rules.

### `POST /api/games`

Creates a new waiting game and registers the first player.

Request:

```json
{
  "player_name": "Alice"
}
```

Response:

Returns Alice's private player view. Save `you.id`; this is required for future calls.

### `POST /api/games/join`

Joins the waiting game as the second player. The game starts immediately after this request.

Request:

```json
{
  "player_name": "Bob"
}
```

Response:

Returns Bob's private player view.

### `GET /api/games/state`

Returns the public game state.

Example:

```bash
curl http://127.0.0.1:8000/api/games/state
```

### `GET /api/games/state?player_id=<id>`

Returns the private player view for the given player, including that player's hand and playable card indexes.

Example:

```bash
curl "http://127.0.0.1:8000/api/games/state?player_id=PLAYER_ID"
```

### `POST /api/games/actions`

Submits a player action.

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

Resets the current game and registers the first player for the new game.

Request:

```json
{
  "player_name": "Alice"
}
```

## CLI Usage

From the `max` directory after dependencies are installed:

```bash
python -m uno_api.cli --name Alice
python -m uno_api.cli --name Bob --join
```

When running without installing the package, set `PYTHONPATH`:

```bash
PYTHONPATH=src python -m uno_api.cli --name Alice
PYTHONPATH=src python -m uno_api.cli --name Bob --join
```

Useful CLI commands:

```text
play <card_index> [wild_color]
draw
pass
refresh
quit
```

## Docker Usage

Build and start the server:

```bash
docker compose up --build
```

Open the frontend:

```text
http://127.0.0.1:8000
```

Players on the same local network can open:

```text
http://<host-lan-ip>:8000
```

The compose file mounts `shared/` and `src/uno_api/runtime/` as volumes so game context survives container restarts.

