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
