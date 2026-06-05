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

## 4. Wie funktioniert Kontext bei KI-Agenten?

Ein wichtiger Punkt: Ein LLM behaelt normalerweise nicht automatisch alles dauerhaft im Kopf. Bei jedem Modellaufruf bekommt das Modell einen Input, also den Prompt plus eventuell bisherige Nachrichten. Daraus erzeugt es eine Antwort. Was nicht im Prompt, im Kontextfenster oder in externem Speicher steht, kann das Modell beim naechsten Aufruf nicht sicher wissen.

Man kann sich das grob so vorstellen:

```text
Agent-Code
  liest Regeln
  liest Spielstand
  liest History/Memory
  baut Prompt
        |
        v
LLM
  verarbeitet nur den aktuellen Kontext
  erzeugt Antwort
        |
        v
Agent-Code
  validiert Antwort
  speichert Ergebnis
```

### 4.1 Hat ein LLM RAM?

Nicht im klassischen Sinn. Ein LLM hat waehrend eines einzelnen Aufrufs einen Arbeitsbereich, das sogenannte Kontextfenster. In diesem Kontextfenster stehen Tokens aus dem aktuellen Prompt, zum Beispiel:

- System-Anweisung
- Spielregeln
- aktueller Spielstand
- bisherige Zuege
- Memory-Zusammenfassung
- Frage oder Aufgabe

Das Modell nutzt diesen Kontext, um die naechsten Tokens zu berechnen. Nach dem Aufruf ist dieser interne Arbeitszustand fuer normale Anwendungen nicht dauerhaft gespeichert.

### 4.2 Was bleibt zwischen Prompts erhalten?

Es gibt drei verschiedene Arten von "Gedaechtnis":

| Art | Was bedeutet das? | Beispiel |
|---|---|---|
| Modellgewichte | Wissen, das beim Training im Modell steckt. | Sprache, allgemeines Wissen, Muster. |
| Kontextfenster | Informationen im aktuellen Prompt. | Regeln und Spielstand fuer diesen Zug. |
| Externer Speicher | Daten, die der Agent-Code speichert und spaeter wieder laedt. | `history.jsonl`, `memory.json`, Datenbank. |

Wenn ein Agent sich an fruehere Runden erinnern soll, muss der Agent-Code diese Informationen speichern und beim naechsten Prompt wieder einfuegen.

### 4.3 Laden Agenten den Kontext nach jedem Prompt neu?

In vielen lokalen Agent-Systemen: ja. Der Agent baut fuer jeden Zug einen neuen Prompt. Dafuer liest er erneut:

1. aktuelle Regeln
2. aktuellen Spielstand
3. relevante Historie
4. eigene Notizen oder Memory
5. feste Agent-Anweisungen

Dann fragt er das Modell erneut. Das ist normal und sogar gut, weil der Agent dadurch immer mit dem aktuellen Zustand arbeitet.

### 4.4 Warum wirkt ChatGPT dann so, als wuerde es sich erinnern?

In einem Chat werden die bisherigen Nachrichten meistens wieder an das Modell mitgegeben. Das Modell sieht also nicht nur deine letzte Frage, sondern auch Teile des bisherigen Verlaufs. Dadurch wirkt es so, als haette es ein dauerhaftes Kurzzeitgedaechtnis.

Technisch ist es eher so:

```text
Neue Antwort = Modell(Systemnachricht + bisheriger Chatverlauf + neue Frage)
```

Wenn der Verlauf zu lang wird, muss das System kuerzen, zusammenfassen oder alte Teile weglassen. Dann kann es passieren, dass Details verloren gehen.

### 4.5 Was bedeutet das fuer euer Spielprojekt?

Fuer euren Agenten sollte nicht das Modell selbst die einzige Erinnerung sein. Besser ist:

- Regeln immer aus `rules.json` laden
- Spielstand immer aus `game_state.json` oder vom Server bekommen
- Zuege in `history.jsonl` speichern
- wichtige Erkenntnisse in `memory.json` zusammenfassen
- nur relevante Historie in den Prompt packen

Beispiel fuer `memory.json`:

```json
{
  "agent_id": "agent_a",
  "strategy_notes": [
    "Opponent often chooses maximum points.",
    "Avoid rule changes that help both players equally.",
    "Invalid moves are worse than conservative legal moves."
  ],
  "last_updated_after_game": 4
}
```

Der Agent kann diese Datei vor jedem Zug laden und in den Prompt einfuegen. Dadurch entsteht praktisches Agent-Gedaechtnis.

### 4.6 Kontextfenster vs. echter Speicher

Das Kontextfenster ist begrenzt. Je nach Modell kann es nur eine bestimmte Menge Text gleichzeitig verarbeiten. Wenn ihr die komplette Spielhistorie nach 200 Runden in den Prompt kopiert, wird es irgendwann zu lang, teuer oder langsam.

Deshalb ist eine gute Agent-Architektur meistens so aufgebaut:

```text
Komplette History bleibt in Dateien/Logs.
Nur die relevanten letzten Zuege kommen in den Prompt.
Langfristige Erkenntnisse werden als kurze Memory-Zusammenfassung gespeichert.
```

Fuer euer Spiel waere ein sinnvoller Prompt-Kontext:

- vollstaendige aktuelle Regeln
- vollstaendiger aktueller Spielstand
- die letzten 5 bis 10 Zuege
- kurze Memory-Zusammenfassung
- klares JSON-Ausgabeformat

### 4.7 Kurz gesagt

Ein KI-Agent "denkt" nicht dauerhaft im Hintergrund, ausser ihr programmiert genau das. Er wird typischerweise immer wieder aufgerufen:

1. Kontext sammeln
2. Prompt bauen
3. Modell fragen
4. Antwort pruefen
5. Aktion ausfuehren
6. Ergebnis speichern

Das wiederholt sich bei jedem Zug. Das eigentliche Langzeitgedaechtnis entsteht durch euren Agent-Code, nicht automatisch durch das LLM.

## 5. Vorgeschlagene Architektur fuer das Projekt

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

## 6. Warum ein zentraler Game Server sinnvoll ist

Man koennte beide Agenten direkt miteinander sprechen lassen. Fuer den Anfang ist ein zentraler Game Server aber einfacher und stabiler.

Der Game Server ist die einzige Quelle der Wahrheit. Er entscheidet:

- welcher Agent gerade an der Reihe ist
- welche Regeln aktuell gelten
- ob ein Zug gueltig ist
- ob eine Regelaenderung erlaubt ist
- wie der neue Spielstand aussieht

Dadurch verhindert man, dass beide Agenten unterschiedliche Versionen des Spiels im Kopf haben.

## 7. Installation und lokales Setup

Die einfachste Variante fuer lokale KI-Agenten ist Python plus Ollama. Ollama ist ein lokaler LLM-Runner, mit dem man Sprachmodelle auf dem eigenen Rechner starten kann. Laut offizieller Ollama-Dokumentation ist Ollama fuer Windows, macOS und Linux verfuegbar; unter Windows wird die Installation ueber den `OllamaSetup.exe` Installer empfohlen.

Offizielle Links:

- Ollama Windows: https://docs.ollama.com/windows
- Ollama Quickstart: https://docs.ollama.com/quickstart
- Python Downloads: https://www.python.org/downloads/

### 7.1 Voraussetzungen

Empfohlen:

- Windows 10/11 oder Linux/macOS
- Python 3.11 oder neuer
- Git
- VS Code
- Ollama
- ausreichend RAM, idealerweise 16 GB oder mehr

Kleinere Modelle laufen auch auf schwaecheren Rechnern, aber Antworten werden langsamer.

### 7.2 Python installieren

1. Python von https://www.python.org/downloads/ installieren.
2. Beim Installer darauf achten, dass `Add Python to PATH` aktiviert ist.
3. Danach in PowerShell pruefen:

```powershell
python --version
pip --version
```

### 7.3 Virtuelle Python-Umgebung erstellen

Im Projektordner:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 7.4 Python-Abhaengigkeiten installieren

Fuer einen ersten Prototyp reichen wenige Pakete:

```powershell
pip install requests pydantic python-dotenv
```

Optional fuer spaetere Ausbaustufen:

```powershell
pip install fastapi uvicorn websockets
```

### 7.5 Ollama installieren

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

## 8. Wie bringt man den Agenten dazu, die Regeln zu "lernen"?

In diesem Projekt bedeutet "lernen" nicht, dass das Modell neu trainiert wird. Ein echtes Training oder Fine-Tuning ist fuer das Projekt wahrscheinlich zu aufwendig.

Stattdessen lernt der Agent die Regeln zur Laufzeit ueber Kontext:

1. Die Regeln stehen in einer Datei, zum Beispiel `rules.json`.
2. Vor jedem Zug liest der Agent die Regeln neu ein.
3. Der Agent bekommt die Regeln im Prompt.
4. Das Modell entscheidet auf Basis dieser Regeln.
5. Der Game Server validiert die Entscheidung.
6. Fehlerhafte Aktionen werden geloggt und dem Agenten im naechsten Zug als Feedback gegeben.

Dieses Verfahren nennt man haeufig In-Context Learning. Das Modell wird nicht dauerhaft veraendert, aber es nutzt die bereitgestellten Informationen innerhalb des aktuellen Prompts.

## 9. Kann man den lokalen Agenten trainieren oder fine-tunen?

Ja, grundsaetzlich kann man einen lokalen KI-Agenten verbessern. Wichtig ist aber die Unterscheidung zwischen mehreren Stufen:

| Methode | Was passiert? | Aufwand | Empfehlung fuer dieses Projekt |
|---|---|---|---|
| Prompt Engineering | Bessere Anweisungen, Rollenbeschreibung, Ausgabeformat und Strategiehinweise. | gering | Sehr empfohlen |
| Kontext / Memory | Der Agent bekommt Regeln, Spielstand, Historie und eigene Fehler pro Zug mitgegeben. | gering bis mittel | Sehr empfohlen |
| Strategie-Code | Der Agent nutzt zusaetzliche Python-Logik, zum Beispiel Simulationen oder Heuristiken. | mittel | Sehr stark, wenn erlaubt |
| Ollama Modelfile | Ein lokales Modell bekommt feste System-Prompts und Parameter. | gering | Empfehlenswert |
| Fine-Tuning mit LoRA/QLoRA | Modellgewichte werden mit Beispieldaten angepasst. | hoch | Erst spaeter sinnvoll |
| Vollstaendiges Training | Ein Modell wird von Grund auf trainiert. | extrem hoch | Fuer dieses Projekt nicht realistisch |

### 9.1 Warum Fine-Tuning meistens nicht der erste Schritt ist

Fine-Tuning klingt verlockend, ist aber fuer ein kleines Spielprojekt oft nicht der beste erste Hebel. Ein Fine-Tuning macht das Modell nicht automatisch "intelligenter". Es lernt vor allem Antwortmuster, Stil, Formate und typische Entscheidungen aus Trainingsbeispielen.

Fuer euren Anwendungsfall ist der Agent oft besser, wenn er:

- die Regeln jedes Mal sauber im Prompt bekommt
- gueltiges JSON ausgeben muss
- aus vergangenen Fehlern Feedback bekommt
- mehrere moegliche Zuege intern bewertet
- den gegnerischen Agenten beobachtet
- einfache Simulationen oder Heuristiken verwendet

Das passt auch besser zur Projektidee aus dem `project-proposal.md`, weil dort Prompt Engineering, Shared Context, Logging, Evaluation und dynamische Regeln im Mittelpunkt stehen.

### 9.2 Was ist der Unterschied zwischen Agent verbessern und Modell fine-tunen?

Der Agent kann besser werden, ohne dass das Modell trainiert wird.

Beispiel:

- Das Modell bleibt `llama3.2:3b`.
- Dein Agent bekommt aber einen besseren System-Prompt.
- Dein Agent speichert Fehler aus vergangenen Runden.
- Dein Agent bewertet vor der finalen Antwort mehrere Optionen.
- Dein Agent prueft seine eigene JSON-Ausgabe.

Dann ist dein Agent wahrscheinlich staerker als ein anderer Agent mit gleichem Modell, aber schlechterer Steuerung.

### 9.3 Empfohlene Verbesserungsstrategie fuer deinen Agenten

Statt sofort Fine-Tuning zu machen, sollte dein Agent in Stufen besser werden.

#### Stufe 1: Stabiler JSON-Agent

Ziel:

- antwortet immer in gueltigem JSON
- macht nur erlaubte Aktionen
- erklaert kurz den Grund im Feld `reason`

#### Stufe 2: Strategie-Prompt

Der Prompt kann deinem Agenten klare Prioritaeten geben:

```text
Priorities:
1. Never make an invalid move.
2. Prefer moves that increase your chance of winning within the next turns.
3. If rule changes are allowed, only propose rules that benefit you and do not obviously benefit the opponent more.
4. Consider the opponent's likely next move before deciding.
5. Return only valid JSON.
```

#### Stufe 3: Selbstpruefung

Der Agent kann vor dem Absenden intern eine Checkliste bekommen:

```text
Before returning the final JSON, check silently:
- Is the action allowed by the current rules?
- Is it my turn?
- Does the action improve my position?
- Could the opponent benefit more from this rule change?
- Is the JSON valid?
```

#### Stufe 4: Memory aus vergangenen Spielen

Nach jedem Spiel kann man eine kleine Strategie-Datei speichern:

```json
{
  "agent_id": "agent_a",
  "lessons_learned": [
    "Adding the maximum allowed points is usually best in the base game.",
    "Rule changes that affect both players equally are only useful if I can use them first.",
    "Invalid JSON loses tempo, so output format has priority."
  ]
}
```

Diese Datei kann vor jedem Spiel wieder in den Prompt eingefuegt werden. Das ist eine einfache Form von Agent-Memory.

#### Stufe 5: Simulation vor der LLM-Frage

Wenn die Regeln einfach genug sind, kann Python mehrere moegliche Zuege testen. Das LLM bekommt dann nicht nur den Spielstand, sondern auch eine Bewertung:

```json
{
  "candidate_moves": [
    {"move": {"add_points": 1}, "estimated_score": 0.4},
    {"move": {"add_points": 2}, "estimated_score": 0.6},
    {"move": {"add_points": 3}, "estimated_score": 0.8}
  ]
}
```

Das ist oft staerker als Fine-Tuning, weil echte Spielregeln deterministisch ausgewertet werden.

### 9.4 Ollama Modelfile als leichter "Pseudo-Fine-Tune"

Ollama unterstuetzt sogenannte Modelfiles. Damit kann man ein vorhandenes Modell mit einem festen System-Prompt, Parametern und einer Vorlage verpacken. Das ist kein echtes Training, aber praktisch sehr nuetzlich.

Offizielle Dokumentation:

- Ollama Modelfile: https://docs.ollama.com/modelfile

Beispiel fuer eine Datei `Modelfile`:

```text
FROM llama3.2:3b

SYSTEM """
You are a competitive game-playing agent.
You always follow the active rules.
You return only valid JSON.
You prefer legal actions that improve your chance of winning.
"""

PARAMETER temperature 0.2
PARAMETER top_p 0.9
```

Danach kann man ein eigenes lokales Modellprofil erstellen:

```powershell
ollama create daniel-agent -f Modelfile
ollama run daniel-agent
```

Der Vorteil: Dein Agent hat immer dieselbe Grundrolle und stabilere Parameter. Fuer Spiele ist eine niedrigere `temperature` oft gut, weil der Agent weniger zufaellig antwortet.

### 9.5 Echtes Fine-Tuning mit LoRA/QLoRA

Echtes Fine-Tuning ist moeglich, aber erst sinnvoll, wenn ihr bereits viele gute Trainingsbeispiele gesammelt habt.

Geeignete Daten koennten aus euren Logs entstehen:

```json
{
  "input": {
    "rules": {},
    "game_state": {},
    "history": []
  },
  "ideal_output": {
    "action_type": "move",
    "move": {
      "add_points": 3
    },
    "reason": "This is the strongest legal move."
  }
}
```

Typischer Ablauf:

1. Viele Spiele ausfuehren und loggen.
2. Gute und schlechte Agent-Aktionen markieren.
3. Daraus Trainingsbeispiele bauen.
4. Ein kleines Modell mit LoRA oder QLoRA fine-tunen.
5. Das neue Modell gegen das Basismodell testen.
6. Ergebnisse anhand von Metriken vergleichen.

Moegliche Tools:

- Hugging Face TRL `SFTTrainer`: https://huggingface.co/docs/trl/sft_trainer
- Unsloth Fine-Tuning Docs: https://docs.unsloth.ai/

Fuer lokale Rechner ist LoRA/QLoRA deutlich realistischer als vollstaendiges Fine-Tuning, weil nur kleine Zusatzgewichte trainiert werden. Trotzdem braucht man je nach Modell und Setup eine passende GPU, Geduld und saubere Trainingsdaten.

### 9.6 Wie beweist man, dass dein Agent besser ist?

"Besser" sollte im Projekt messbar sein. Sonst bleibt es nur ein Gefuehl.

Moegliche Metriken:

| Metrik | Bedeutung |
|---|---|
| Win Rate | Wie viele Spiele gewinnt der Agent? |
| Invalid Move Rate | Wie oft macht der Agent ungueltige Aktionen? |
| JSON Error Rate | Wie oft ist die Antwort nicht parsebar? |
| Average Turns to Win | Wie schnell gewinnt der Agent? |
| Rule Change Success Rate | Wie oft helfen vorgeschlagene Regelaenderungen wirklich? |
| Stability | Bleibt das Spiel ueber viele Runden spielbar? |

Empfohlen ist ein Turniermodus:

```text
Agent A baseline vs. Agent B baseline: 50 Spiele
Daniel-Agent vs. Baseline-Agent: 50 Spiele
Daniel-Agent mit Memory vs. Daniel-Agent ohne Memory: 50 Spiele
```

Dann koennt ihr im Projekt zeigen, welche Verbesserung wirklich etwas gebracht hat.

### 9.7 Faire Regeln fuer den Vergleich mit dem Kollegen

Wenn ihr wissenschaftlich sauber vergleichen wollt, sollte vorher festgelegt werden:

- Nutzen beide Agenten dasselbe Basismodell?
- Duerfen beide eigene Prompts verwenden?
- Duerfen beide Memory verwenden?
- Duerfen beide zusaetzliche Strategie-Algorithmen verwenden?
- Duerfen Regeldateien nur gelesen oder auch vorgeschlagen geaendert werden?
- Zaehlt ein ungueltiger Zug als verlorener Zug oder gibt es Retry?

Wenn diese Punkte klar sind, kann dein Agent ruhig optimiert werden. Dann ist genau das Teil der Untersuchung: Welche Agent-Architektur spielt besser?

## 10. Beispiel fuer maschinenlesbare Regeln

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

## 11. Beispiel fuer Spielzustand

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

## 12. Beispiel fuer eine Agent-Antwort

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

## 13. Prompt-Aufbau fuer den Agenten

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

## 14. Kommunikation ueber Sockets

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

## 15. Minimaler Projektaufbau

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

## 16. Minimaler Ollama-Client in Python

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

## 17. Validierung der Agent-Aktionen

Der Agent darf nicht direkt den Spielstand veraendern. Er darf nur Vorschlaege machen.

Der Game Server muss pruefen:

- Ist die Antwort valides JSON?
- Ist `action_type` erlaubt?
- Ist der Zug laut Regeln erlaubt?
- Ist der Agent gerade wirklich an der Reihe?
- Wird eine Regelaenderung korrekt beschrieben?
- Entsteht ein unspielbarer oder widerspruechlicher Zustand?

Das ist wichtig, weil LLMs Fehler machen koennen. Die Spiellogik muss deterministisch im Code liegen.

## 18. Logging und Auswertung

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

## 19. Typische Probleme und Loesungen

| Problem | Ursache | Loesung |
|---|---|---|
| Modell antwortet nicht als JSON | Prompt ist zu offen | Striktes Ausgabeformat verwenden und Antwort validieren. |
| Agent ignoriert Regeln | Regeln sind unklar oder zu lang | Regeln nummerieren, kurz halten und Beispiele geben. |
| Beide Agenten haben anderen Zustand | Kein zentraler Server | Game Server als einzige Quelle der Wahrheit nutzen. |
| Lokales Modell ist langsam | Modell zu gross oder Hardware schwach | Kleineres Modell verwenden, zum Beispiel 2B oder 3B. |
| Regelaenderungen machen Spiel kaputt | Keine Regelvalidierung | Rule Engine mit erlaubten Operationen und Constraints bauen. |

## 20. Empfohlene erste Umsetzung

Fuer den ersten Prototyp sollte das Projekt klein bleiben.

1. Ein sehr einfaches Spiel definieren, zum Beispiel "wer zuerst 20 Punkte erreicht".
2. Regeln in `shared/rules.json` speichern.
3. Spielstand in `shared/game_state.json` speichern.
4. Einen Game Server schreiben, der Zuege validiert.
5. Einen Agenten schreiben, der Ollama fragt.
6. Den gleichen Agenten zweimal mit unterschiedlicher `agent_id` starten.
7. Jeden Zug in `history.jsonl` speichern.
8. Danach erst Regelaenderungen erlauben.

## 21. Was spaeter erweitert werden kann

Moegliche Erweiterungen:

- Weboberflaeche zur Anzeige von Spielstand und Regeln
- WebSocket statt einfacher TCP-Sockets
- verschiedene Modelle gegeneinander antreten lassen
- Agent A nutzt Ollama, Agent B nutzt OpenAI oder Gemini
- automatische Analyse der Spielhistorie
- Regelkonflikt-Erkennung
- Bewertungsmetriken fuer Agentenentscheidungen
- Turniermodus mit mehreren Spielen
- Vergleich zwischen Baseline-Agent, Prompt-Agent, Memory-Agent und fine-getuntem Agenten

## 22. Fazit

Fuer dieses Projekt muss der KI-Agent am Anfang nicht wirklich trainiert werden. Der sinnvolle Einstieg ist ein lokaler LLM-Agent, der vor jedem Zug Regeln, Spielstand und Historie als Kontext bekommt. Die eigentliche Spiel- und Regelvalidierung bleibt im normalen Python-Code.

Wenn dein Agent besser werden soll als der Agent deines Kollegen, ist die beste Reihenfolge:

1. besserer Prompt
2. stabileres JSON-Format
3. Memory aus vergangenen Spielen
4. Heuristiken oder Simulationen im Python-Code
5. erst danach echtes Fine-Tuning mit gesammelten Trainingsdaten

Damit lernt ihr sehr gut, wie Agenten praktisch funktionieren:

- Kontext wird gesammelt
- ein Prompt wird gebaut
- ein Modell erzeugt eine Entscheidung
- Code validiert die Entscheidung
- die Umgebung wird aktualisiert
- der neue Zustand beeinflusst die naechste Entscheidung

Genau dieser Kreislauf ist der Kern vieler KI-Agenten.
