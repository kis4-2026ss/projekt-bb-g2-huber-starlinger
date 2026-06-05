# Grunddokumentation: Lokale KI-Agenten fuer ein regelbasiertes Spiel

## 1. Ziel dieser Dokumentation

Diese Dokumentation beschreibt die Grundlagen fuer ein Studienprojekt, in dem zwei lokal laufende KI-Agenten gegeneinander ein Spiel spielen. Beide Agenten sollen Regeln aus einem gemeinsamen Ordner lesen, daraus ihren aktuellen Handlungsspielraum ableiten und anschliessend ueber eine definierte Schnittstelle, zum Beispiel Sockets, Zuege ausfuehren.

Das Ziel ist nicht nur ein funktionierendes Spiel, sondern vor allem ein besseres Verstaendnis dafuer:

- wie KI-Agenten aufgebaut sind
- wie sie Informationen aufnehmen und daraus Entscheidungen ableiten
- wie mehrere Agenten miteinander oder ueber ein System kommunizieren
- wie Spielregeln maschinenlesbar gespeichert werden koennen
- wie ein lokales Sprachmodell fuer einfache Agenten genutzt werden kann

## 2. Was ist ein KI-Agent?

Ein KI-Agent ist ein Programm, das Informationen ueber eine Umgebung bekommt, daraus eine Entscheidung ableitet und anschliessend eine Aktion ausfuehrt.

Ein einfacher Agent besteht meistens aus folgenden Teilen:

| Bestandteil | Aufgabe |
|---|---|
| Wahrnehmung / Input | Der Agent bekommt Informationen, zum Beispiel Spielstand, Regeln oder Nachrichten. |
| Kontext / Gedaechtnis | Der Agent speichert relevante Informationen, zum Beispiel bisherige Zuege. |
| Entscheidungslogik | Der Agent entscheidet, welche Aktion sinnvoll ist. |
| Aktion / Output | Der Agent gibt einen Zug, eine Regelaenderung oder eine Nachricht aus. |
| Feedback | Das System meldet zurueck, ob die Aktion gueltig war und was sich geaendert hat. |

Bei klassischen Programmen wird die Entscheidungslogik exakt programmiert. Bei einem LLM-Agenten wird ein Sprachmodell genutzt, um aus einem Prompt eine strukturierte Entscheidung zu erzeugen.

## 3. Unterschied zwischen LLM und Agent

Ein Large Language Model, kurz LLM, ist zuerst nur ein Modell, das Text verarbeitet und Text erzeugt. Es ist noch kein vollstaendiger Agent.

Ein Agent entsteht erst, wenn man das Modell in eine Umgebung einbettet:

1. Das Programm liest den aktuellen Spielzustand.
2. Das Programm liest die aktiven Regeln.
3. Das Programm baut daraus einen Prompt.
4. Das LLM erzeugt eine Entscheidung.
5. Das Programm prueft die Antwort.
6. Das Programm fuehrt die Aktion im Spiel aus.
7. Das Ergebnis wird gespeichert und dem Agenten im naechsten Zug wieder gegeben.

Das LLM ist also das "Denkmodul", aber der Agent ist das gesamte System aus Modell, Code, Kontext, Regeln und Aktionen.

## 4. Vorgeschlagene Architektur fuer das Projekt

Eine einfache lokale Architektur kann so aussehen:

```text
Shared-Ordner
  rules.json
  game_state.json
  history.jsonl
        |
        v
+-------------------+
|    Game Server    |
| Python + Sockets  |
+---------+---------+
          |
   -----------------
   |               |
   v               v
+--------+     +--------+
| Agent A|     | Agent B|
| lokal  |     | lokal  |
+--------+     +--------+
```

### Komponenten

| Komponente | Beschreibung |
|---|---|
| Shared-Ordner | Gemeinsamer Ordner fuer Regeln, Spielstand und Logs. |
| Game Server | Zentrale Instanz, die Zuege annimmt, Regeln validiert und den Spielstand aktualisiert. |
| Agent A / Agent B | Lokale Programme, die den Zustand lesen und Aktionen vorschlagen. |
| Rule Engine | Teil des Game Servers, der prueft, ob Aktionen mit den Regeln vereinbar sind. |
| Logging | Speichert Prompts, Antworten, Zuege und Regelaenderungen fuer die spaetere Analyse. |

## 5. Warum ein zentraler Game Server sinnvoll ist

Man koennte beide Agenten direkt miteinander sprechen lassen. Fuer den Anfang ist ein zentraler Game Server aber einfacher und stabiler.

Der Game Server ist die einzige Quelle der Wahrheit. Er entscheidet:

- welcher Agent gerade an der Reihe ist
- welche Regeln aktuell gelten
- ob ein Zug gueltig ist
- ob eine Regelaenderung erlaubt ist
- wie der neue Spielstand aussieht

Dadurch verhindert man, dass beide Agenten unterschiedliche Versionen des Spiels im Kopf haben.

## 6. Installation und lokales Setup

Die einfachste Variante fuer lokale KI-Agenten ist Python plus Ollama. Ollama ist ein lokaler LLM-Runner, mit dem man Sprachmodelle auf dem eigenen Rechner starten kann. Laut offizieller Ollama-Dokumentation ist Ollama fuer Windows, macOS und Linux verfuegbar; unter Windows wird die Installation ueber den `OllamaSetup.exe` Installer empfohlen.

Offizielle Links:

- Ollama Windows: https://docs.ollama.com/windows
- Ollama Quickstart: https://docs.ollama.com/quickstart
- Python Downloads: https://www.python.org/downloads/

### 6.1 Voraussetzungen

Empfohlen:

- Windows 10/11 oder Linux/macOS
- Python 3.11 oder neuer
- Git
- VS Code
- Ollama
- ausreichend RAM, idealerweise 16 GB oder mehr

Kleinere Modelle laufen auch auf schwaecheren Rechnern, aber Antworten werden langsamer.

### 6.2 Python installieren

1. Python von https://www.python.org/downloads/ installieren.
2. Beim Installer darauf achten, dass `Add Python to PATH` aktiviert ist.
3. Danach in PowerShell pruefen:

```powershell
python --version
pip --version
```

### 6.3 Virtuelle Python-Umgebung erstellen

Im Projektordner:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 6.4 Python-Abhaengigkeiten installieren

Fuer einen ersten Prototyp reichen wenige Pakete:

```powershell
pip install requests pydantic python-dotenv
```

Optional fuer spaetere Ausbaustufen:

```powershell
pip install fastapi uvicorn websockets
```

### 6.5 Ollama installieren

1. Ollama von der offiziellen Website installieren.
2. Nach der Installation PowerShell oeffnen.
3. Testen:

```powershell
ollama --version
```

4. Ein kleines Modell herunterladen:

```powershell
ollama pull llama3.2:3b
```

Alternative Modelle:

```powershell
ollama pull qwen2.5:3b
ollama pull gemma2:2b
```

5. Modell testen:

```powershell
ollama run llama3.2:3b
```

Wenn das Modell antwortet, ist die lokale KI-Basis einsatzbereit.

## 7. Wie bringt man den Agenten dazu, die Regeln zu "lernen"?

In diesem Projekt bedeutet "lernen" nicht, dass das Modell neu trainiert wird. Ein echtes Training oder Fine-Tuning ist fuer das Projekt wahrscheinlich zu aufwendig.

Stattdessen lernt der Agent die Regeln zur Laufzeit ueber Kontext:

1. Die Regeln stehen in einer Datei, zum Beispiel `rules.json`.
2. Vor jedem Zug liest der Agent die Regeln neu ein.
3. Der Agent bekommt die Regeln im Prompt.
4. Das Modell entscheidet auf Basis dieser Regeln.
5. Der Game Server validiert die Entscheidung.
6. Fehlerhafte Aktionen werden geloggt und dem Agenten im naechsten Zug als Feedback gegeben.

Dieses Verfahren nennt man haeufig In-Context Learning. Das Modell wird nicht dauerhaft veraendert, aber es nutzt die bereitgestellten Informationen innerhalb des aktuellen Prompts.

## 8. Beispiel fuer maschinenlesbare Regeln

Eine einfache `rules.json` koennte so aussehen:

```json
{
  "game_name": "Number Duel",
  "version": 1,
  "rules": [
    {
      "id": "R001",
      "description": "Each player starts with 0 points.",
      "type": "initial_state"
    },
    {
      "id": "R002",
      "description": "On each turn, a player may add 1, 2, or 3 points to their own score.",
      "type": "action"
    },
    {
      "id": "R003",
      "description": "The first player with 20 or more points wins.",
      "type": "win_condition"
    }
  ]
}
```

Wichtig ist, dass Regeln eindeutig und versioniert sind. Jede Regel sollte eine ID haben, damit Agenten und Logs darauf referenzieren koennen.

## 9. Beispiel fuer Spielzustand

```json
{
  "turn": 5,
  "current_player": "agent_a",
  "players": {
    "agent_a": {
      "score": 8
    },
    "agent_b": {
      "score": 6
    }
  },
  "winner": null
}
```

Der Spielzustand sollte moeglichst klein und eindeutig bleiben. Je klarer der Zustand ist, desto einfacher kann der Agent gute Entscheidungen treffen.

## 10. Beispiel fuer eine Agent-Antwort

Damit das Programm die Antwort des Modells verarbeiten kann, sollte der Agent immer JSON ausgeben.

```json
{
  "action_type": "move",
  "move": {
    "add_points": 3
  },
  "reason": "Adding 3 points maximizes progress toward the winning score."
}
```

Wenn Regelaenderungen erlaubt sind:

```json
{
  "action_type": "propose_rule_change",
  "rule_change": {
    "operation": "add",
    "description": "A player may subtract 1 point from the opponent once per game."
  },
  "reason": "This creates a defensive option and makes the game less linear."
}
```

## 11. Prompt-Aufbau fuer den Agenten

Ein guter Prompt trennt Rolle, Regeln, Zustand und Ausgabeformat.

```text
You are Agent A in a turn-based game.

Your goal is to win the game while following all active rules.

Active rules:
{rules_json}

Current game state:
{game_state_json}

Recent history:
{history}

Return exactly one JSON object.
Allowed action types:
- move
- propose_rule_change

Do not include markdown.
Do not explain outside the JSON.
```

Wichtig: Das Programm sollte trotzdem pruefen, ob die Antwort wirklich valides JSON ist. LLMs koennen trotz Anweisung manchmal ungueltige Antworten liefern.

## 12. Kommunikation ueber Sockets

Sockets sind sinnvoll, wenn beide Agenten als eigene Prozesse laufen sollen.

Ein einfacher Ablauf:

1. Game Server startet und wartet auf Verbindungen.
2. Agent A verbindet sich mit dem Server.
3. Agent B verbindet sich mit dem Server.
4. Server sendet an den aktuellen Agenten:
   - aktive Regeln
   - aktuellen Spielstand
   - Zughistorie
5. Agent sendet eine JSON-Aktion zurueck.
6. Server validiert und aktualisiert den Zustand.
7. Server sendet den neuen Zustand an beide Agenten.

### Beispiel-Nachricht vom Server

```json
{
  "message_type": "your_turn",
  "agent_id": "agent_a",
  "rules": [],
  "game_state": {},
  "history": []
}
```

### Beispiel-Nachricht vom Agenten

```json
{
  "message_type": "action",
  "agent_id": "agent_a",
  "payload": {
    "action_type": "move",
    "move": {
      "add_points": 3
    }
  }
}
```

## 13. Minimaler Projektaufbau

Empfohlene Struktur:

```text
projekt-bb-g2-huber-starlinger/
  Daniel/
    README.md
  shared/
    rules.json
    game_state.json
    history.jsonl
  src/
    server/
      game_server.py
      rule_engine.py
    agents/
      agent_base.py
      agent_a.py
      agent_b.py
    llm/
      ollama_client.py
    common/
      schemas.py
```

## 14. Minimaler Ollama-Client in Python

Ollama stellt lokal eine HTTP-API bereit. Standardmaessig ist sie unter `http://localhost:11434` erreichbar.

```python
import requests


def ask_ollama(prompt: str, model: str = "llama3.2:3b") -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"]
```

Dieser Client ist bewusst einfach. Spaeter sollte man Fehlerbehandlung, Logging und JSON-Validierung ergaenzen.

## 15. Validierung der Agent-Aktionen

Der Agent darf nicht direkt den Spielstand veraendern. Er darf nur Vorschlaege machen.

Der Game Server muss pruefen:

- Ist die Antwort valides JSON?
- Ist `action_type` erlaubt?
- Ist der Zug laut Regeln erlaubt?
- Ist der Agent gerade wirklich an der Reihe?
- Wird eine Regelaenderung korrekt beschrieben?
- Entsteht ein unspielbarer oder widerspruechlicher Zustand?

Das ist wichtig, weil LLMs Fehler machen koennen. Die Spiellogik muss deterministisch im Code liegen.

## 16. Logging und Auswertung

Fuer ein Studienprojekt ist Logging besonders wichtig, weil ihr spaeter zeigen koennt, wie die Agenten gearbeitet haben.

Empfohlenes Logformat: `history.jsonl`, also eine JSON-Zeile pro Ereignis.

Beispiel:

```json
{"turn":1,"agent":"agent_a","action":{"add_points":3},"valid":true}
{"turn":2,"agent":"agent_b","action":{"add_points":2},"valid":true}
```

Zusaetzlich koennt ihr speichern:

- kompletter Prompt
- rohe Modellantwort
- geparste JSON-Antwort
- Validierungsergebnis
- Regelversion vor und nach dem Zug
- Dauer der Modellantwort

## 17. Typische Probleme und Loesungen

| Problem | Ursache | Loesung |
|---|---|---|
| Modell antwortet nicht als JSON | Prompt ist zu offen | Striktes Ausgabeformat verwenden und Antwort validieren. |
| Agent ignoriert Regeln | Regeln sind unklar oder zu lang | Regeln nummerieren, kurz halten und Beispiele geben. |
| Beide Agenten haben anderen Zustand | Kein zentraler Server | Game Server als einzige Quelle der Wahrheit nutzen. |
| Lokales Modell ist langsam | Modell zu gross oder Hardware schwach | Kleineres Modell verwenden, zum Beispiel 2B oder 3B. |
| Regelaenderungen machen Spiel kaputt | Keine Regelvalidierung | Rule Engine mit erlaubten Operationen und Constraints bauen. |

## 18. Empfohlene erste Umsetzung

Fuer den ersten Prototyp sollte das Projekt klein bleiben.

1. Ein sehr einfaches Spiel definieren, zum Beispiel "wer zuerst 20 Punkte erreicht".
2. Regeln in `shared/rules.json` speichern.
3. Spielstand in `shared/game_state.json` speichern.
4. Einen Game Server schreiben, der Zuege validiert.
5. Einen Agenten schreiben, der Ollama fragt.
6. Den gleichen Agenten zweimal mit unterschiedlicher `agent_id` starten.
7. Jeden Zug in `history.jsonl` speichern.
8. Danach erst Regelaenderungen erlauben.

## 19. Was spaeter erweitert werden kann

Moegliche Erweiterungen:

- Weboberflaeche zur Anzeige von Spielstand und Regeln
- WebSocket statt einfacher TCP-Sockets
- verschiedene Modelle gegeneinander antreten lassen
- Agent A nutzt Ollama, Agent B nutzt OpenAI oder Gemini
- automatische Analyse der Spielhistorie
- Regelkonflikt-Erkennung
- Bewertungsmetriken fuer Agentenentscheidungen
- Turniermodus mit mehreren Spielen

## 20. Fazit

Fuer dieses Projekt muss der KI-Agent nicht wirklich trainiert werden. Der sinnvolle Einstieg ist ein lokaler LLM-Agent, der vor jedem Zug Regeln, Spielstand und Historie als Kontext bekommt. Die eigentliche Spiel- und Regelvalidierung bleibt im normalen Python-Code.

Damit lernt ihr sehr gut, wie Agenten praktisch funktionieren:

- Kontext wird gesammelt
- ein Prompt wird gebaut
- ein Modell erzeugt eine Entscheidung
- Code validiert die Entscheidung
- die Umgebung wird aktualisiert
- der neue Zustand beeinflusst die naechste Entscheidung

Genau dieser Kreislauf ist der Kern vieler KI-Agenten.
