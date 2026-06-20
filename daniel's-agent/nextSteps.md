# Next Steps fuer Daniels KI-Agent

## Kurzfazit

Der aktuelle Stand im Ordner `max/` ist eine solide erste Basis: Es gibt eine FastAPI-App, eine UNO-Engine, Shared-Dateien, CLI, Browser-Frontend, Docker-Konfiguration und erste Engine-Tests. Fuer zwei menschliche Spieler ist das ein guter Prototyp.

Fuer euer eigentliches Projektziel, also zwei autonome KI-Agenten, fehlen aber noch die Agentenschicht, ein sauberer Orchestrator, sichere private Agent-Kontexte und eine Evaluation.

## Code Review

### 1. Private Spielerinformationen sind fuer Agenten nicht wirklich privat

Betroffene Stellen:

- `max/src/uno_api/engine.py`, `public_view`, Zeilen 96-120
- `max/src/uno_api/api.py`, `get_state`, Zeilen 71-79
- `max/src/uno_api/storage.py`, `publish_shared_context`, Zeilen 46-52

Aktuell enthaelt der Public State die Player-IDs. Mit diesen IDs kann jeder Client ueber `/api/games/state?player_id=<id>` die private Hand eines Spielers abrufen. Zusaetzlich schreibt `publish_shared_context` fuer jeden Spieler eine Datei `shared/player_<player_id>.json`, die die jeweilige Hand enthaelt.

Fuer Menschen ist das als lokaler Prototyp noch akzeptabel. Fuer KI-Agenten ist es aber ein Fairness-Problem: Wenn beide Agenten Zugriff auf denselben Shared-Ordner haben, kann ein Agent theoretisch die Hand des Gegners lesen.

Empfohlene Loesung:

- Public State darf keine geheimen Zugriffsschluessel enthalten.
- Jeder Agent sollte nur seinen eigenen privaten Kontext bekommen.
- Statt `player_id` als "Secret" sollte es ein separates `player_token` geben.
- Shared-Dateien sollten getrennt werden, zum Beispiel:

```text
shared/
  public_state.json
  rules.json
  agent_a/
    private_state.json
  agent_b/
    private_state.json
```

Wenn ihr wirklich ueber Sockets oder API arbeitet, sollte der Server den privaten Kontext aktiv an den jeweiligen Agenten senden, statt alle privaten Dateien in einen gemeinsamen Ordner zu schreiben.

### 2. `rules.json` wird bei jedem Publish wieder ueberschrieben

Betroffene Stelle:

- `max/src/uno_api/storage.py`, Zeile 48

In `publish_shared_context` wird immer `_write_json(RULES_PATH, default_rules())` aufgerufen. Dadurch werden manuelle Aenderungen an `shared/rules.json` bei jedem Speichern wieder durch die Default-Regeln ersetzt.

Das passt noch zu einer statischen UNO-Version, widerspricht aber eurer Projektidee aus `project-proposal.md`, wo Regeln dynamisch hinzugefuegt, geaendert oder entfernt werden koennen.

Empfohlene Loesung:

- `rules.json` nur beim ersten Setup erzeugen.
- Danach Regeln aus `rules.json` laden und nicht automatisch ueberschreiben.
- Eine spaetere `RuleEngine` sollte Regelversionen verwalten.
- Regelveraenderungen sollten als eigene Events geloggt werden.

### 3. Die Engine nutzt aktuell feste UNO-Regeln statt eine echte Rule Engine

Betroffene Bereiche:

- `max/src/uno_api/engine.py`
- `max/shared/rules.json`

Die Datei `rules.json` beschreibt Regeln, aber die echte Spiellogik ist hart in Python codiert. Der Agent kann Regeln also lesen, aber eine Regelveraenderung wuerde das Verhalten der Engine noch nicht veraendern.

Das ist fuer den ersten Prototyp in Ordnung. Fuer das Projektziel "Emergent Rule Evolution Game" braucht ihr aber spaeter eine Schicht, die zumindest bestimmte Regelparameter dynamisch ausliest.

Pragmatischer Vorschlag:

Nicht sofort "jede beliebige Regel" dynamisch machen. Besser zuerst eine kleine Menge erlaubter Regelparameter definieren:

```json
{
  "starting_hand_size": 7,
  "draw_two_amount": 2,
  "wild_draw_four_amount": 4,
  "allow_stack_draw_cards": false,
  "must_declare_uno": false
}
```

Dann kann die Engine diese Werte wirklich verwenden und Agenten koennen kontrolliert Regelvorschlaege machen.

### 4. Agenten-Orchestrierung fehlt noch komplett

Betroffene Stelle:

- `max/current-state.md`, Zeilen 25-33

Max dokumentiert selbst korrekt, dass Agenten, Prompt Templates, Response-Validierung, Provider-Adapter und Evaluation noch fehlen.

Fuer Daniels Teil sollte daher nicht zuerst Fine-Tuning kommen, sondern ein lauffaehiger Agent Loop:

```text
create game
join second agent
while game active:
  read current player context
  ask agent for action
  validate action JSON
  send action to API
  log prompt, response, validation, result
```

### 5. Tests sind vorhanden, aber noch sehr knapp

Betroffene Stelle:

- `max/tests/test_engine.py`

Es gibt erste Tests fuer Join, Turn Order, Matching Color und Wild Color. Das ist gut, deckt aber noch nicht genug ab fuer Agentenspiele.

Wichtige fehlende Tests:

- draw + pass flow
- negative/ungueltige card indexes auf Engine-Ebene
- draw_two Effekt
- wild_draw_four Effekt
- skip/reverse im Zwei-Spieler-Modus
- Reshuffle wenn Draw Pile leer ist
- Public View darf keine privaten Haende enthalten
- Agent Action Validation
- kompletter Mock-Agent-vs-Mock-Agent-Lauf

Hinweis: Ich konnte die Tests lokal nicht ausfuehren, weil `pytest` in der aktuell verwendeten Python-Umgebung nicht installiert ist (`No module named pytest`).

## Empfohlene naechste Schritte

### Schritt 1: Agent-Fairness absichern

Prioritaet: hoch

Bevor echte KI-Agenten gegeneinander spielen, sollte verhindert werden, dass ein Agent den privaten Kontext des Gegners lesen kann.

Konkrete Aufgaben:

- Public State ohne private Zugriffsdaten bereitstellen.
- Private Agent-Kontexte trennen.
- API-Zugriff auf private Player View mit Token absichern.
- Shared-Ordner-Struktur fuer Agent A und Agent B festlegen.

### Schritt 2: Deterministischen Mock-Agent bauen

Prioritaet: hoch

Der erste Agent sollte noch kein LLM verwenden. Ein Mock-Agent ist besser zum Testen.

Beispielstrategie:

1. Wenn eine Karte spielbar ist, spiele die erste spielbare Karte.
2. Wenn es eine Wild Card ist, waehle die Farbe, die am haeufigsten in der eigenen Hand vorkommt.
3. Wenn keine Karte spielbar ist, ziehe.
4. Wenn bereits gezogen wurde und nichts spielbar ist, passe.

Damit koennt ihr den kompletten Agenten-Loop testen, ohne dass LLM-Antworten stoeren.

### Schritt 3: Orchestrator-Script erstellen

Prioritaet: hoch

Empfohlener Ort:

```text
max/src/uno_api/agents/orchestrator.py
```

Aufgabe:

- neues Spiel starten
- Agent B joinen
- aktuellen Spieler erkennen
- passenden Agenten aufrufen
- Aktion an API senden
- bis Spielende wiederholen
- Ergebnis loggen

### Schritt 4: Gemeinsames Agent-Action-Schema definieren

Prioritaet: hoch

Alle Agenten sollten dasselbe JSON-Format ausgeben:

```json
{
  "action": "play",
  "card_index": 2,
  "chosen_color": null,
  "declare_uno": true,
  "reason": "This card matches the top card by color."
}
```

Der Orchestrator sollte dieses JSON pruefen, bevor es an die API geht.

### Schritt 5: LLM-Agent mit Ollama bauen

Prioritaet: mittel

Erst wenn Mock-Agent und Orchestrator laufen, sollte ein Ollama-Agent dazukommen.

Empfohlene Struktur:

```text
max/src/uno_api/agents/
  base.py
  mock_agent.py
  ollama_agent.py
  prompt_templates.py
  validator.py
  orchestrator.py
```

Der Ollama-Agent sollte:

- Regeln lesen
- eigene Hand lesen
- Top Card und playable indexes lesen
- letzten Verlauf bekommen
- exakt JSON antworten
- bei ungueltiger Antwort maximal einmal reparieren lassen

### Schritt 6: Logging fuer Evaluation erweitern

Prioritaet: mittel

Fuer die Studienarbeit solltet ihr mehr loggen als nur Aktionen.

Empfohlenes Log:

```json
{
  "run_id": "2026-06-05T18-30-00",
  "turn": 12,
  "agent_id": "agent_a",
  "agent_type": "ollama",
  "prompt": "...",
  "raw_response": "...",
  "parsed_action": {},
  "valid": true,
  "api_result": {},
  "duration_ms": 823
}
```

Diese Logs sind spaeter wichtig, um zu zeigen, wie Agenten Entscheidungen treffen.

### Schritt 7: Evaluation bauen

Prioritaet: mittel

Ihr solltet automatisch mehrere Spiele laufen lassen koennen:

```text
mock_agent vs mock_agent: 20 Spiele
ollama_agent vs mock_agent: 20 Spiele
daniel_agent vs baseline_agent: 50 Spiele
```

Metriken:

- Win Rate
- Invalid Move Rate
- JSON Error Rate
- durchschnittliche Spielzuege bis Ende
- Anzahl gezogener Karten
- Stabilitaet ueber viele Spiele

### Schritt 8: Dynamische Regeln nur kontrolliert einfuehren

Prioritaet: spaeter

Da UNO-Regeln komplex sind, sollte Rule Evolution nicht sofort beliebige freie Textregeln erlauben. Besser ist eine kontrollierte Liste erlaubter Regelparameter.

Beispiele:

- `draw_two_amount`
- `wild_draw_four_amount`
- `starting_hand_size`
- `allow_play_after_draw`
- `skip_steps`

Agenten duerfen dann nur diese Parameter vorschlagen. Die Rule Engine prueft, ob Werte erlaubt sind.

## Daniels sinnvoller Fokus

Fuer deinen Teil waere der staerkste Beitrag:

1. Agent-Konzept finalisieren.
2. Mock-Agent implementieren.
3. Ollama-Agent implementieren.
4. Prompt und JSON-Validierung bauen.
5. Memory-Datei fuer Daniels Agent bauen.
6. Evaluation gegen Baseline-Agent durchfuehren.

Das passt sehr gut zu deiner bisherigen Dokumentation, weil du damit nicht nur Code lieferst, sondern auch zeigen kannst, wie ein Agent Kontext laedt, Entscheidungen trifft, Fehler verarbeitet und ueber mehrere Spiele verbessert wird.

## Konkreter erster Arbeitsplan

1. Mit Max klaeren, ob private Agent-Kontexte ueber Dateien oder API/Sockets laufen sollen.
2. Danach Agent-Ordnerstruktur anlegen.
3. `MockAgent` bauen und testen.
4. Orchestrator bauen.
5. Einen kompletten Mock-vs-Mock-Lauf automatisieren.
6. Erst danach Ollama anbinden.
7. Danach Daniels Agent mit besserem Prompt und Memory verbessern.

