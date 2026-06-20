import json
import urllib.error
import urllib.request


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"

# Das ist die Anweisung an das KI Modell!!!
# sagt ihm im vorhinein was er tun soll und wie er damit umgehen soll

SYSTEM_PROMPT = """
Du bist ein lokaler KI-Agent fuer ein spaeteres Spielprojekt.
Du sollst noch kein Spiel spielen.

Deine Aufgabe:
- lies die Aufgabe des Benutzers
- entscheide eine einfache Aktion
- antworte ausschliesslich als gueltiges JSON

Erlaubtes Ausgabeformat:
{
  "agent_id": "agent_a",
  "action": "answer",
  "message": "kurze Antwort"
}

Wichtig:
- Gib keinen Markdown-Text aus.
- Gib keine Erklaerung ausserhalb des JSON aus.
- Das JSON muss mit { beginnen und mit } enden.
""".strip()



def ask_ollama(prompt: str, model: str = MODEL) -> str:
    # Baut die Payload zusammen
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    #  dann wird ein Post-Request an Ollama geschickt
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    # Die Json antwort von Ollama wird gelesen
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data["response"]


    #wird gechecked ob es wirklich ein json ist was geleifert wird.
def parse_agent_response(raw_response: str) -> dict:
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Agent response is not valid JSON: {raw_response}") from exc

    #Pflichtfelder geprüft ob vorhanden
    required_fields = ["agent_id", "action", "message"]
    missing_fields = [field for field in required_fields if field not in parsed]
    if missing_fields:
        raise ValueError(f"Agent response is missing fields: {missing_fields}")

    # agent muss agent_a heißen
    if parsed["agent_id"] != "agent_a":
        raise ValueError("Agent response has wrong agent_id")

    # er hat nur die erlaubniss als action answer zu schreiben
    if parsed["action"] != "answer":
        raise ValueError("Agent response has unsupported action")

    return parsed

    # baut den prompt zusammen, also zuerst: Du bist ein lokaler KI-Agent...
    # Aufgabe des Benutzers:
    # Wie baue ich einen KI-Agenten
def build_prompt(user_task: str) -> str:
    return f"{SYSTEM_PROMPT}\n\nAufgabe des Benutzers:\n{user_task}"


def main() -> None:
    print("Lokaler Agent gestartet. Schreibe /bye zum Beenden.")

    # Endlosschleife
    while True:
        # User gibt input
        user_task = input("\nAufgabe> ").strip()
        # bei den actionen wird abgebrochen und beendet
        if user_task.lower() in {"/bye", "bye", "exit", "quit"}:
            break

        # promt wird gebaut
        prompt = build_prompt(user_task)
        
        try:
            #anfrage los schicken
            raw_response = ask_ollama(prompt)
            # schauen ob die Antwort richtig ist
            parsed_response = parse_agent_response(raw_response)
        except urllib.error.URLError as exc:
            # Fehlerbehandlung wenn nicht erreichbar
            print(f"Ollama ist nicht erreichbar: {exc}")
            print("Pruefe mit: ollama run llama3.2")
            continue
        except ValueError as exc:
            # kommt wenn er eine ungültige antwort gebaut hat
            print(f"Ungueltige Agent-Antwort: {exc}")
            continue

            # Die Antwort ausgeben
        print(json.dumps(parsed_response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
