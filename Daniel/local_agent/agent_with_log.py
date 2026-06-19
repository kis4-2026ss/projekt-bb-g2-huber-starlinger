import json
from datetime import datetime
from pathlib import Path
import urllib.error

from agent import ask_ollama, build_prompt, parse_agent_response


LOG_DIR = Path(__file__).parent / "logs"


def write_log(log_file: Path, title: str, content: str) -> None:
    with log_file.open("a", encoding="utf-8") as file:
        file.write(f"\n\n===== {title} =====\n")
        file.write(content)
        file.write("\n")


def build_repair_prompt(raw_response: str, error_message: str) -> str:
    return f"""
Die vorherige Antwort war kein gueltiges Agent-JSON.

Fehler:
{error_message}

Vorherige Antwort:
{raw_response}

Bitte repariere die Antwort.
Antworte ausschliesslich mit gueltigem JSON in diesem Format:
{{
  "agent_id": "agent_a",
  "action": "answer",
  "message": "kurze Antwort"
}}
""".strip()


def build_explanation_prompt(user_task: str, parsed_response: dict) -> str:
    return f"""
Erklaere kurz und sachlich, warum diese Agent-Antwort zur Aufgabe passt.
Gib keine versteckte Gedankenkette aus, sondern nur eine kurze nachvollziehbare Begruendung.

Aufgabe:
{user_task}

Agent-Antwort:
{json.dumps(parsed_response, ensure_ascii=False)}
""".strip()


def ask_with_logging(user_task: str, log_file: Path) -> dict:
    prompt = build_prompt(user_task)

    write_log(log_file, "USER TASK", user_task)
    write_log(log_file, "PROMPT SENT TO OLLAMA", prompt)

    for attempt in range(1, 3):
        write_log(log_file, f"ATTEMPT {attempt}", "Sending prompt to Ollama.")

        raw_response = ask_ollama(prompt)
        write_log(log_file, f"RAW MODEL RESPONSE {attempt}", raw_response)

        try:
            parsed_response = parse_agent_response(raw_response)
        except ValueError as exc:
            write_log(log_file, f"VALIDATION FAILED {attempt}", str(exc))

            if attempt == 2:
                raise

            prompt = build_repair_prompt(raw_response, str(exc))
            write_log(log_file, "REPAIR PROMPT", prompt)
            continue

        formatted_response = json.dumps(parsed_response, indent=2, ensure_ascii=False)
        write_log(log_file, f"VALID JSON RESPONSE {attempt}", formatted_response)

        explanation_prompt = build_explanation_prompt(user_task, parsed_response)
        explanation = ask_ollama(explanation_prompt)
        write_log(log_file, "MODEL EXPLANATION", explanation)

        return parsed_response

    raise ValueError("Agent did not produce valid JSON.")


def main() -> None:
    LOG_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = LOG_DIR / f"agent-run-{timestamp}.txt"

    print("Geloggter Agent gestartet. Schreibe /bye zum Beenden.")
    print("Hinweis: Interne Modell-Gedanken werden nicht ausgelesen.")
    print("Geloggte Datei:")
    print(log_file)

    while True:
        user_task = input("\nAufgabe> ").strip()
        if user_task.lower() in {"/bye", "bye", "exit", "quit"}:
            break

        try:
            parsed_response = ask_with_logging(user_task, log_file)
        except urllib.error.URLError as exc:
            message = f"Ollama ist nicht erreichbar: {exc}"
            write_log(log_file, "OLLAMA ERROR", message)
            print(message)
            continue
        except ValueError as exc:
            message = f"Ungueltige Agent-Antwort nach Korrekturversuch: {exc}"
            write_log(log_file, "FINAL ERROR", message)
            print(message)
            continue

        print("\nGueltige Agent-Antwort:")
        print(json.dumps(parsed_response, indent=2, ensure_ascii=False))
        print(f"\nLog geschrieben nach: {log_file}")


if __name__ == "__main__":
    main()
