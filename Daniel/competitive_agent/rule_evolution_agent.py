import json
from datetime import datetime
from pathlib import Path
import urllib.error
import urllib.request


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"


SYSTEM_PROMPT = """
Du bist Daniel-Agent fuer ein UNO-Projekt mit dynamisch veraenderbaren Regeln.
Du sollst noch keine echte Regeldatei veraendern.
Du sollst nur einen sicheren Regelvorschlag als JSON erzeugen.

Ziel:
- Schlage Regeln vor, die Daniel-Agent taktisch helfen koennen.
- Vermeide Regeln, die das Spiel kaputt machen.
- Vermeide widerspruechliche oder unfair unendliche Regeln.
- Regeln muessen kurz, eindeutig und maschinenlesbar sein.
- Dynamische Regeln sollen Zusatzregeln sein, keine neuen Matching-Basisregeln.

Erlaubte Operationen:
- add
- modify
- remove
- none

Prioritaeten:
1. Wenn eine Regel Daniel-Agent sofort oder mittelfristig hilft, darf sie vorgeschlagen werden.
2. Eine Regel darf nicht direkt private Informationen des Gegners offenlegen.
3. Eine Regel darf nicht endlose Zuege oder unendliches Kartenziehen erzeugen.
4. Eine Regel sollte fuer beide Agenten lesbar und pruefbar sein.
5. Wenn keine sichere Regel sinnvoll ist, waehle operation "none".
6. Schlage keine Regel vor, die nur eine Basisregel wiederholt.
7. Nutze bevorzugt erlaubte Regel-Templates aus dem Kontext.
8. Verwende konkrete Werte statt Platzhalter, z.B. "blue" statt "selected_color".

Antwortformat:
Antworte ausschliesslich als gueltiges JSON.

Schema:
{
  "agent_id": "daniel_agent",
  "operation": "add|modify|remove|none",
  "rule_id": "kurze_id_oder_null",
  "rule_text": "kurze Regelbeschreibung oder null",
  "condition": "wann die Regel gilt oder null",
  "effect": "was die Regel bewirkt oder null",
  "risk_level": "low|medium|high",
  "expected_advantage": "kurze taktische Einschaetzung",
  "validation_notes": "wie der Server die Regel pruefen koennte"
}

Keine Markdown-Ausgabe.
Keine Erklaerung ausserhalb des JSON.
""".strip()


EXAMPLE_RULE_CONTEXT = {
    "agent_id": "daniel_agent",
    "turn": 8,
    "my_cards_in_hand": 5,
    "opponent_cards_in_hand": 2,
    "current_rules": [
        {
            "id": "base_match",
            "text": "A card may be played if color or value matches the top card.",
            "locked": True,
        },
        {
            "id": "base_wild",
            "text": "Wild cards may be played on any card and choose the next color.",
            "locked": True,
        },
    ],
    "allowed_rule_operations": ["add", "modify", "remove", "none"],
    "allowed_rule_templates": [
        {
            "template": "color_bonus",
            "description": "A named color gives a small bonus when played.",
            "example_effect": "if played_card.color == selected_color: player_may_choose_next_color = true",
        },
        {
            "template": "action_pressure",
            "description": "A specific action card creates a small additional pressure effect.",
            "example_effect": "if played_card.value == selected_action: opponent_draws += 1",
        },
        {
            "template": "catchup_rule",
            "description": "A player with many more cards receives a limited comeback option.",
            "example_effect": "if own_cards >= opponent_cards + 4: player_may_draw_then_play = true",
        },
        {
            "template": "finish_window",
            "description": "A player who reaches one card receives a limited protection or tempo bonus.",
            "example_effect": "if own_cards_after_play == 1 and declared_uno: opponent_next_draw_count += 1",
        },
        {
            "template": "two_player_tempo",
            "description": "In two-player games, skip/reverse style effects create strong tempo advantage.",
            "example_effect": "if played_card.value in ['skip', 'reverse']: player_may_play_again = true",
        },
        {
            "template": "stacking_pressure",
            "description": "Draw penalties can become stronger if the next player cannot answer them.",
            "example_effect": "if played_card.value == 'draw_two' and opponent_cannot_stack: opponent_draws += 1",
        },
    ],
    "locked_rule_ids": ["base_match", "base_wild"],
    "recent_events": [
        "Opponent has only two cards.",
        "Daniel-Agent has several blue cards.",
    ],
    "candidate_advantages": [
        "Daniel-Agent currently benefits from blue cards.",
        "Opponent is close to winning, so limited pressure rules are useful.",
    ],
    "recommended_rule_direction": {
        "rule_id": "blue_action_pressure",
        "condition": "played_card.color == 'blue' and played_card.type == 'action'",
        "effect": "opponent_draws += 1",
        "reason": "Daniel-Agent currently benefits from blue cards and the opponent is close to winning.",
    },
    "high_power_rule_ideas": [
        {
            "rule_id": "declared_uno_pressure",
            "condition": "own_cards_after_play == 1 and declared_uno == true",
            "effect": "opponent_draws += 1",
            "why_strong": "Turns reaching UNO into both progress and pressure.",
        },
        {
            "rule_id": "blue_combo_turn",
            "condition": "played_card.color == 'blue' and played_card.type == 'action'",
            "effect": "player_may_play_again = true",
            "why_strong": "Creates a possible finish sequence if Daniel-Agent has blue action cards.",
        },
        {
            "rule_id": "draw_two_escalation",
            "condition": "played_card.value == 'draw_two' and opponent_cards_in_hand <= 2",
            "effect": "opponent_draws += 1",
            "why_strong": "Makes draw cards decisive when the opponent is close to winning.",
        },
    ],
}


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


def build_prompt(rule_context: dict) -> str:
    return f"""
{SYSTEM_PROMPT}

Aktueller Regel-Kontext:
{json.dumps(rule_context, indent=2, ensure_ascii=False)}

Erzeuge jetzt genau einen sicheren Regelvorschlag.
""".strip()


def extract_json_object(raw_response: str) -> str:
    stripped = raw_response.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return stripped

    return stripped[start:end + 1]


def parse_rule_proposal(raw_response: str, rule_context: dict) -> dict:
    try:
        proposal = json.loads(extract_json_object(raw_response))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Response is not valid JSON: {raw_response}") from exc

    required_fields = [
        "agent_id",
        "operation",
        "rule_id",
        "rule_text",
        "condition",
        "effect",
        "risk_level",
        "expected_advantage",
        "validation_notes",
    ]
    missing = [field for field in required_fields if field not in proposal]
    if missing:
        raise ValueError(f"Missing fields: {missing}")

    if proposal["agent_id"] != "daniel_agent":
        raise ValueError("Wrong agent_id")

    if proposal["operation"] not in rule_context.get("allowed_rule_operations", []):
        raise ValueError("Operation is not allowed")

    if proposal["risk_level"] not in {"low", "medium", "high"}:
        raise ValueError("Invalid risk_level")

    string_or_null_fields = ["rule_id", "rule_text", "condition", "effect"]
    for field in string_or_null_fields:
        if proposal[field] is not None and not isinstance(proposal[field], str):
            raise ValueError(f"{field} must be a string or null")

    if proposal["operation"] in {"modify", "remove"}:
        if proposal["rule_id"] in rule_context.get("locked_rule_ids", []):
            raise ValueError("Locked base rules must not be modified or removed")

    if proposal["operation"] != "none":
        for field in ["rule_id", "rule_text", "condition", "effect"]:
            if not proposal.get(field):
                raise ValueError(f"{field} is required for rule operation")

        existing_rule_ids = {rule["id"] for rule in rule_context.get("current_rules", [])}
        if proposal["rule_id"] in existing_rule_ids:
            raise ValueError("New rule_id must not duplicate an existing rule")

        normalized_rule_text = proposal["rule_text"].lower()
        repeated_base_phrases = [
            "color or value matches",
            "color matches the top card",
            "same color as the top card",
            "wild cards may be played on any card",
            "farbe wie die oberste karte",
            "gleichen farbe wie die oberste karte",
            "oberste karte auf dem stapel",
        ]
        if any(phrase in normalized_rule_text for phrase in repeated_base_phrases):
            raise ValueError("Rule proposal repeats an existing base rule")

        normalized_condition = proposal["condition"].lower()
        normalized_effect = proposal["effect"].lower()
        placeholders = ["selected_color", "selected_action", "bonus_value"]
        if any(placeholder in normalized_condition or placeholder in normalized_effect for placeholder in placeholders):
            raise ValueError("Rule must use concrete values instead of placeholders")

        if "top_card" in normalized_condition and "played_card.color" in normalized_condition:
            raise ValueError("Rule condition is too close to the base matching rule")

    return proposal


def build_repair_prompt(raw_response: str, error: str, rule_context: dict) -> str:
    return f"""
Dein vorheriger Regelvorschlag war ungueltig.

Fehler:
{error}

Vorherige Antwort:
{raw_response}

Regel-Kontext:
{json.dumps(rule_context, indent=2, ensure_ascii=False)}

Repariere den Vorschlag.
Antworte ausschliesslich mit gueltigem JSON im verlangten Schema.
""".strip()


def write_log(log_file: Path, title: str, content: str) -> None:
    with log_file.open("a", encoding="utf-8") as file:
        file.write(f"\n\n===== {title} =====\n")
        file.write(content)
        file.write("\n")


def propose_rule(rule_context: dict, log_file: Path) -> dict:
    prompt = build_prompt(rule_context)

    write_log(log_file, "RULE CONTEXT", json.dumps(rule_context, indent=2, ensure_ascii=False))
    write_log(log_file, "PROMPT SENT TO OLLAMA", prompt)

    for attempt in range(1, 3):
        raw_response = ask_ollama(prompt)
        write_log(log_file, f"RAW MODEL RESPONSE {attempt}", raw_response)

        try:
            proposal = parse_rule_proposal(raw_response, rule_context)
        except ValueError as exc:
            write_log(log_file, f"VALIDATION FAILED {attempt}", str(exc))

            if attempt == 2:
                raise

            prompt = build_repair_prompt(raw_response, str(exc), rule_context)
            write_log(log_file, "REPAIR PROMPT", prompt)
            continue

        write_log(log_file, "VALID RULE PROPOSAL", json.dumps(proposal, indent=2, ensure_ascii=False))
        return proposal

    raise ValueError("No valid rule proposal generated.")


def main() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = LOG_DIR / f"rule-evolution-run-{timestamp}.txt"

    print("Daniel Rule Evolution Agent")
    print("Uebt sichere Regelvorschlaege, ohne echte Regeln zu veraendern.")
    print(f"Log-Datei: {log_file}")

    try:
        proposal = propose_rule(EXAMPLE_RULE_CONTEXT, log_file)
    except urllib.error.URLError as exc:
        print(f"Ollama ist nicht erreichbar: {exc}")
        return
    except ValueError as exc:
        print(f"Kein gueltiger Regelvorschlag: {exc}")
        return

    print("\nRegelvorschlag:")
    print(json.dumps(proposal, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
