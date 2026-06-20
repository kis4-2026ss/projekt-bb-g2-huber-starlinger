# Lokaler Minimal-Agent

Dieser Ordner enthaelt den ersten einfachen KI-Agenten fuer das Projekt.
Er spielt noch kein UNO und verbindet sich noch nicht mit dem Backend.

Der Agent zeigt nur den Grundablauf:

1. Python baut einen festen Prompt.
2. Python schickt den Prompt an Ollama.
3. Ollama antwortet.
4. Python prueft, ob die Antwort gueltiges JSON ist.

## Voraussetzungen

Ollama muss installiert sein und das Modell muss vorhanden sein:

```powershell
ollama pull llama3.2
```

Die Python-Umgebung im Projekt muss aktiv sein:

```powershell
cd "C:\GitCheckouts\KIS4 - Projekt\projekt-bb-g2-huber-starlinger"
.\.venv\Scripts\Activate.ps1
```

## Starten

```powershell
python .\Daniel\local_agent\agent.py
```

Beispielaufgabe:

```text
Sage kurz, dass der Agent bereit ist.
```

Erwartete Antwort:

```json
{
  "agent_id": "agent_a",
  "action": "answer",
  "message": "Der Agent ist bereit."
}
```

## Warum ist das schon ein Agent?

Ein normales `ollama run llama3.2` ist nur ein Chat mit dem Modell.

Dieser Agent ist mehr als nur Chat:

- Er hat eine feste Rolle.
- Er hat ein festes Ausgabeformat.
- Er wird von Python gesteuert.
- Seine Antwort wird validiert.

Spaeter kann dieselbe Struktur erweitert werden:

- `rules.json` lesen
- `public_state.json` lesen
- private Spielerinformationen lesen
- erlaubte Aktionen berechnen
- Aktion an das Backend senden
- Ergebnis loggen
