# Logging fuer den Minimal-Agenten

`agent.py` bleibt der einfache, dokumentierte Basis-Agent.

`agent_with_log.py` legt nur eine Logging-Schicht darum. Dadurch kann man nachvollziehen:

- welche Aufgabe eingegeben wurde
- welcher Prompt an Ollama geschickt wurde
- welche Rohantwort vom Modell kam
- ob die JSON-Validierung erfolgreich war
- welcher Fehler aufgetreten ist, falls die Antwort ungueltig war
- welcher Reparatur-Prompt gesendet wurde, falls ein zweiter Versuch noetig ist
- welche kurze Begruendung das Modell nachtraeglich zur Antwort gibt

Wichtig: Die echten internen Gedanken des Modells werden nicht ausgelesen. Sichtbar ist nur der technische Ablauf rund um Prompt, Antwort und Validierung. Die Begruendung ist eine extra erzeugte Zusammenfassung, keine versteckte Gedankenkette.

## Starten

```powershell
cd "C:\GitCheckouts\KIS4 - Projekt\projekt-bb-g2-huber-starlinger"
.\.venv\Scripts\Activate.ps1
python .\Daniel\local_agent\agent_with_log.py
```

Die Logs werden automatisch hier gespeichert:

```text
Daniel/local_agent/logs/
```

Eine Log-Datei heisst zum Beispiel:

```text
agent-run-20260619-141530.txt
```

## Was man in der Vorstellung sagen kann

Der Agent zeigt nicht die privaten Modellgedanken, aber er macht den Entscheidungsprozess technisch nachvollziehbar:

1. Kontext wird als Prompt zusammengesetzt.
2. Ollama erzeugt eine Rohantwort.
3. Python prueft, ob die Antwort gueltiges JSON ist.
4. Falls nicht, wird ein Korrektur-Prompt erzeugt.
5. Das finale gueltige JSON wird ausgegeben und geloggt.
6. Das Modell gibt zusaetzlich eine kurze, vorzeigbare Begruendung aus.
