# Daniel-Agent Als UNO Client

`daniel_uno_client.py` verbindet Daniel-Agent mit Max' UNO API.

Nach aussen ist Daniel-Agent ein normaler Spieler.
Intern nutzt er den kompetitiven Strategie-Agenten und sendet die Entscheidung an den Server.

## Server starten

Auf einem lokalen Rechner im Ordner `max`:

```powershell
cd .\max
docker compose up --build
```

Der Server laeuft dann unter:

```text
http://127.0.0.1:8000
```

Das Observer-Dashboard ist im Browser unter derselben Adresse erreichbar.

## Zwei Agenten lokal spielen lassen

Terminal 1: Server starten.

Terminal 2: Max' Agent als erster Spieler:

```powershell
cd .\max
$env:PYTHONPATH="src"
python -m uno_api.agents.simple_agent --mode reset --name "Max-Agent" --delay 1
```

Terminal 3: Daniel-Agent als zweiter Spieler:

```powershell
cd "C:\GitCheckouts\KIS4 - Projekt\projekt-bb-g2-huber-starlinger"
.\.venv\Scripts\Activate.ps1
python .\Daniel\competitive_agent\daniel_uno_client.py --mode join --name "Daniel-Agent" --delay 1
```

Mit dynamischen Regeln:

```powershell
python .\Daniel\competitive_agent\daniel_uno_client.py --mode join --name "Daniel-Agent" --delay 1 --enable-rules --turn-action-mode choose-one
```

Daniel-Agent versucht dann vor eigenen Zuegen serverkompatible Mutable Rules zu setzen.
Die Regeln werden ueber Max' API geschrieben, nicht direkt in Dateien.
Im Modus `choose-one` entscheidet Daniel-Agent pro Zug zwischen:

- `rule`: eine Mutable Rule setzen
- `game`: eine normale Kartenaktion ausfuehren

Falls Max' Server Rule Actions noch nicht als echten Zug weiterzaehlt, kann fuer lokale Tests dieser Modus verwendet werden:

```powershell
python .\Daniel\competitive_agent\daniel_uno_client.py --mode join --name "Daniel-Agent" --delay 1 --enable-rules --turn-action-mode opportunistic
```

`opportunistic` setzt eine starke Regel und spielt danach trotzdem eine Karte. Das ist nur fuer die aktuell getrennte API praktisch. Fuer die finale Spiel-Architektur ist `choose-one` sauberer.

## Alternative Reihenfolge

Daniel-Agent kann auch der erste Spieler sein:

```powershell
python .\Daniel\competitive_agent\daniel_uno_client.py --mode reset --name "Daniel-Agent"
```

Max' Agent joined dann:

```powershell
cd .\max
$env:PYTHONPATH="src"
python -m uno_api.agents.simple_agent --mode join --name "Max-Agent"
```

## Resume

Wenn der Prozess stoppt, kann Daniel-Agent mit seiner `player_id` fortsetzen:

```powershell
python .\Daniel\competitive_agent\daniel_uno_client.py --mode resume --player-id PLAYER_ID
```

## Logs

Daniel-Agent schreibt pro Lauf Logs in:

```text
Daniel/competitive_agent/logs/
```

Im Log stehen:

- API-Spielzustand
- Regeln
- taktische Voranalyse
- Modellantwort
- finale API-Aktion
- Serverantwort

Wenn Ollama ausfaellt oder ungueltig antwortet, nutzt der Client einen sicheren Fallback, damit das Spiel weiterlaufen kann.

## Rule-Modul

Wenn `--enable-rules` aktiv ist, nutzt der Client `rule_evolution_agent.py`.
Dieses Modul erzeugt keine freien Textregeln, sondern Regeln im Format von Max' API:

```json
{
  "id": "daniel_finish_at_three",
  "title": "Daniel Finish Window",
  "description": "When Daniel-Agent has three or fewer cards, playing a card can finish the game.",
  "type": "turn_modifier",
  "condition": {
    "scope": "current_player",
    "player_name": "Daniel-Agent",
    "current_player": {
      "hand_count": {
        "lte": 3
      }
    }
  },
  "effect": {
    "win_hand_count": 3
  }
}
```

Der Client loggt:

- vorgeschlagene Regel
- Serverantwort
- falls der Server ablehnt: Fehlermeldung

Nuetzliche Optionen:

```powershell
--enable-rules
--rule-frequency 1
--turn-action-mode choose-one
```

`--rule-frequency 1` bedeutet: Daniel-Agent prueft bei jedem eigenen Zug, ob eine neue starke Regel sinnvoll ist.
