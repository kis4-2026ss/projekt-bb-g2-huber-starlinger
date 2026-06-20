# Daniel Competitive Agent

Dieser Ordner ist fuer Daniels staerkeren Spiel-Agenten gedacht.
Der einfache Doku-Agent in `Daniel/local_agent/agent.py` bleibt unveraendert.

## Ziel

Der Agent soll spaeter gegen Max' Agenten antreten.
Solange Max' Server-Tools noch nicht angebunden sind, arbeitet dieser Agent mit einem Beispielkontext.

Er trainiert kein Modell, aber er verbessert die Agent-Schicht:

- besserer System-Prompt
- taktische UNO-Prioritaeten
- niedrigere Temperatur fuer stabilere Antworten
- Memory-Datei fuer Strategie-Notizen
- taktische Voranalyse in Python
- JSON-Validierung
- Reparaturversuch bei ungueltigem JSON
- Log-Dateien fuer Prompt, Rohantwort, Validierung und sichtbare Begruendung

## Starten

```powershell
cd "C:\GitCheckouts\KIS4 - Projekt\projekt-bb-g2-huber-starlinger"
.\.venv\Scripts\Activate.ps1
python .\Daniel\competitive_agent\strategy_agent.py
```

## Logs

Logs werden hier geschrieben:

```text
Daniel/competitive_agent/logs/
```

Geloggte Informationen:

- aktueller Spielkontext
- Agent-Memory
- taktische Voranalyse mit spielbaren Karten, Scores und Gruenden
- kompletter Prompt
- rohe Modellantwort
- Validierungsfehler
- Reparatur-Prompt
- finale Entscheidung

Die taktische Voranalyse ist besonders nuetzlich fuer die Dokumentation:

- Welche Karten sind spielbar?
- Ist der Gegner kurz vor dem Gewinnen?
- Welche Farbe ist fuer Wild-Karten am besten?
- Welche spielbare Karte bekommt den hoechsten taktischen Score?

Die echten internen Modellgedanken werden nicht ausgelesen. Stattdessen gibt der Agent eine kurze `visible_reason` aus. Das ist eine sichtbare Begruendung fuer Menschen, keine versteckte Gedankenkette.

## Spaetere Anbindung an Max' Server

Wenn Max' API bereit ist, soll der Beispielkontext ersetzt werden durch echte Daten:

```text
max/shared/rules.json
max/shared/public_state.json
max/shared/player_<daniel_player_id>.json
```

Der Agent soll diese Dateien nur lesen.
Aktionen sollen spaeter per HTTP an den Server geschickt werden:

```text
POST http://localhost:8000/api/games/actions
```

Der Server bleibt die einzige Quelle der Wahrheit.
