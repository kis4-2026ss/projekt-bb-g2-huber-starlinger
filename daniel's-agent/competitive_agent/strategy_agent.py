import json
from datetime import datetime
from pathlib import Path
import urllib.error
import urllib.request


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
MEMORY_PATH = BASE_DIR / "memory.json"


SYSTEM_PROMPT = """
Du bist Daniel-Agent, ein kompetitiver UNO-Agent.
Dein Ziel ist es, moeglichst viele Spiele gegen einen anderen Agenten zu gewinnen.

Du darfst nur Entscheidungen vorschlagen. Der Server prueft spaeter, ob sie gueltig sind.

Prioritaeten:
1. Spiele immer einen legalen Gewinnzug, wenn du dadurch sofort gewinnen kannst.
2. Wenn der Gegner nur wenige Karten hat, priorisiere Blockade: draw_two, wild_draw_four, skip oder reverse.
3. In einem Zwei-Spieler-Spiel sind skip und reverse besonders stark, weil sie dem Gegner den Zug nehmen.
4. Nutze Wild-Karten taktisch, um eine Farbe zu waehlen, die du selbst oft hast.
5. Hebe Wild-Karten eher fuer kritische Situationen auf, ausser du kannst dadurch gewinnen oder den Gegner stark blockieren.
6. Reduziere deine Handkarten, aber vermeide ungueltige Aktionen.
7. Wenn mehrere Zahlenkarten spielbar sind, bevorzuge die Farbe, von der du danach noch weitere Karten hast.
8. Wenn keine Karte spielbar ist, ziehe eine Karte.
9. Gib niemals eine Aktion aus, die nicht im Kontext als erlaubt erkennbar ist.

Antwortformat:
Antworte ausschliesslich als gueltiges JSON.

Schema:
{
  "agent_id": "daniel_agent",
  "action": "play|draw|pass",
  "card_index": 0,
  "chosen_color": "red|yellow|green|blue|null",
  "declare_uno": true,
  "visible_reason": "kurze Begruendung fuer Menschen",
  "confidence": 0.0
}

Regeln:
- Keine Markdown-Ausgabe.
- Keine Erklaerung ausserhalb des JSON.
- visible_reason ist keine versteckte Gedankenkette, sondern nur eine kurze sichtbare Begruendung.
- Wenn action draw oder pass ist, muss card_index null sein.
- Wenn keine Farbe gewaehlt werden muss, ist chosen_color null.
""".strip()


EXAMPLE_CONTEXT = {
    "agent_id": "daniel_agent",
    "current_turn": True,
    "top_card": {"color": "red", "value": "7", "type": "number"},
    "hand": [
        {"color": "red", "value": "2", "type": "number"},
        {"color": "blue", "value": "draw_two", "type": "action"},
        {"color": None, "value": "wild", "type": "wild"},
    ],
    "playable_indexes": [0, 2],
    "opponent_cards_in_hand": 2,
    "valid_colors": ["red", "yellow", "green", "blue"],
    "allowed_actions": ["play", "draw", "pass"],
}


def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        return {
            "agent_id": "daniel_agent",
            "strategy_notes": [
                "Legal moves are more important than risky moves.",
                "When using wild cards, prefer colors that occur often in own hand.",
                "If opponent has few cards, blocking and draw cards become more valuable.",
                "In two-player UNO, reverse behaves like skip and can immediately deny the opponent a turn.",
                "Save wild cards for winning, escaping bad colors, or blocking a nearly finished opponent.",
                "Prefer moves that leave a strong follow-up color in hand.",
            ],
            "invalid_move_count": 0,
            "games_observed": 0,
        }

    return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))


def save_memory(memory: dict) -> None:
    MEMORY_PATH.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")


def ask_ollama(prompt: str, model: str = MODEL) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data["response"]


def analyze_context(game_context: dict) -> dict:
    hand = game_context.get("hand", [])
    playable_indexes = set(game_context.get("playable_indexes", []))
    opponent_cards = game_context.get("opponent_cards_in_hand")

    color_counts: dict[str, int] = {}
    playable_cards = []
    tactical_flags = []

    for index, card in enumerate(hand):
        color = card.get("color")
        if color:
            color_counts[color] = color_counts.get(color, 0) + 1

        if index in playable_indexes:
            playable_cards.append({"index": index, "card": card})

    preferred_color = None
    if color_counts:
        preferred_color = max(color_counts, key=color_counts.get)

    if opponent_cards is not None and opponent_cards <= 2:
        tactical_flags.append("opponent_near_win")

    if len(hand) == 2:
        tactical_flags.append("uno_after_one_play")

    if not playable_cards:
        tactical_flags.append("no_playable_card")

    ranked_moves = []
    for playable in playable_cards:
        index = playable["index"]
        card = playable["card"]
        value = card.get("value")
        card_type = card.get("type")
        score = 10
        reasons = []

        if len(hand) == 1:
            score += 100
            reasons.append("winning move")

        if opponent_cards is not None and opponent_cards <= 2:
            if value in {"draw_two", "wild_draw_four"}:
                score += 45
                reasons.append("punishes near-winning opponent")
            if value in {"skip", "reverse"}:
                score += 35
                reasons.append("blocks near-winning opponent")

        if value == "wild_draw_four":
            score += 30
            reasons.append("strongest blocking card")
        elif value == "draw_two":
            score += 25
            reasons.append("draw penalty")
        elif value in {"skip", "reverse"}:
            score += 20
            reasons.append("denies opponent turn in two-player UNO")
        elif card_type == "wild":
            score += 12
            reasons.append("controls next color")

        card_color = card.get("color")
        if card_color and color_counts.get(card_color, 0) > 1:
            score += color_counts[card_color]
            reasons.append(f"keeps strong {card_color} color path")

        if card_type == "number":
            score += 3
            reasons.append("safe legal discard")

        ranked_moves.append({
            "card_index": index,
            "card": card,
            "score": score,
            "reasons": reasons,
        })

    ranked_moves.sort(key=lambda move: move["score"], reverse=True)

    return {
        "opponent_cards_in_hand": opponent_cards,
        "color_counts": color_counts,
        "preferred_wild_color": preferred_color,
        "tactical_flags": tactical_flags,
        "ranked_playable_moves": ranked_moves,
        "fallback_action": "draw" if "draw" in game_context.get("allowed_actions", []) else "pass",
    }


def build_prompt(game_context: dict, memory: dict, tactical_analysis: dict) -> str:
    return f"""
{SYSTEM_PROMPT}

Memory:
{json.dumps(memory, indent=2, ensure_ascii=False)}

Taktische Voranalyse aus Python:
{json.dumps(tactical_analysis, indent=2, ensure_ascii=False)}

Aktueller Spielkontext:
{json.dumps(game_context, indent=2, ensure_ascii=False)}

Waehle jetzt die beste Aktion.
Nutze die taktische Voranalyse als Hilfe, aber beachte immer den Spielkontext und das erlaubte JSON-Schema.
""".strip()


def parse_decision(raw_response: str, game_context: dict) -> dict:
    try:
        decision = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Response is not valid JSON: {raw_response}") from exc

    required_fields = [
        "agent_id",
        "action",
        "card_index",
        "chosen_color",
        "declare_uno",
        "visible_reason",
        "confidence",
    ]
    missing = [field for field in required_fields if field not in decision]
    if missing:
        raise ValueError(f"Missing fields: {missing}")

    if decision["agent_id"] != "daniel_agent":
        raise ValueError("Wrong agent_id")

    if decision["action"] not in game_context.get("allowed_actions", []):
        raise ValueError("Action is not allowed by context")

    if decision["action"] == "play":
        playable_indexes = game_context.get("playable_indexes", [])
        if decision["card_index"] not in playable_indexes:
            raise ValueError("card_index is not playable")
    else:
        if decision["card_index"] is not None:
            raise ValueError("card_index must be null for draw/pass")

    if decision["chosen_color"] is not None:
        if decision["chosen_color"] not in game_context.get("valid_colors", []):
            raise ValueError("chosen_color is not valid")

    if not isinstance(decision["visible_reason"], str) or not decision["visible_reason"].strip():
        raise ValueError("visible_reason must be a non-empty string")

    return decision


def build_repair_prompt(raw_response: str, error: str, game_context: dict) -> str:
    return f"""
Deine vorherige Antwort war ungueltig.

Fehler:
{error}

Vorherige Antwort:
{raw_response}

Aktueller Spielkontext:
{json.dumps(game_context, indent=2, ensure_ascii=False)}

Repariere die Antwort.
Antworte ausschliesslich mit gueltigem JSON im verlangten Schema.
""".strip()


def write_log(log_file: Path, title: str, content: str) -> None:
    with log_file.open("a", encoding="utf-8") as file:
        file.write(f"\n\n===== {title} =====\n")
        file.write(content)
        file.write("\n")


def decide(game_context: dict, log_file: Path) -> dict:
    memory = load_memory()
    tactical_analysis = analyze_context(game_context)
    prompt = build_prompt(game_context, memory, tactical_analysis)

    write_log(log_file, "GAME CONTEXT", json.dumps(game_context, indent=2, ensure_ascii=False))
    write_log(log_file, "MEMORY", json.dumps(memory, indent=2, ensure_ascii=False))
    write_log(log_file, "TACTICAL ANALYSIS", json.dumps(tactical_analysis, indent=2, ensure_ascii=False))
    write_log(log_file, "PROMPT SENT TO OLLAMA", prompt)

    for attempt in range(1, 3):
        raw_response = ask_ollama(prompt)
        write_log(log_file, f"RAW MODEL RESPONSE {attempt}", raw_response)

        try:
            decision = parse_decision(raw_response, game_context)
        except ValueError as exc:
            memory["invalid_move_count"] = memory.get("invalid_move_count", 0) + 1
            save_memory(memory)
            write_log(log_file, f"VALIDATION FAILED {attempt}", str(exc))

            if attempt == 2:
                raise

            prompt = build_repair_prompt(raw_response, str(exc), game_context)
            write_log(log_file, "REPAIR PROMPT", prompt)
            continue

        write_log(log_file, "VALID DECISION", json.dumps(decision, indent=2, ensure_ascii=False))
        save_memory(memory)
        return decision

    raise ValueError("No valid decision generated.")


def main() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = LOG_DIR / f"strategy-run-{timestamp}.txt"

    print("Daniel Strategy Agent")
    print("Nutzt einen Beispielkontext, solange Max' Server-Tools noch nicht angebunden sind.")
    print(f"Log-Datei: {log_file}")

    try:
        decision = decide(EXAMPLE_CONTEXT, log_file)
    except urllib.error.URLError as exc:
        print(f"Ollama ist nicht erreichbar: {exc}")
        return
    except ValueError as exc:
        print(f"Keine gueltige Entscheidung: {exc}")
        return

    print("\nEntscheidung:")
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
