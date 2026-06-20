# Training Fuer Dynamische Regeln

Max' Server trennt Regeln in zwei Ebenen:

- `base_rules`: feste UNO-Basisregeln, nicht veraenderbar
- `mutable_rules`: Agent-Regeln, die ueber API hinzugefuegt, geaendert oder entfernt werden koennen

Daniel-Agent schreibt keine Regeldateien direkt. Er verwendet Max' Tool-Wrapper:

```text
add_mutable_rule
modify_mutable_rule
remove_mutable_rule
```

## Aktuelles Server-Schema

Eine Regel muss dieses Format haben:

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

## Erlaubte Effekte

Besonders nuetzlich fuer Daniel-Agent:

- `win_hand_count`: erlaubt frueheres Gewinnen
- `max_plays_per_turn`: erlaubt mehrere Karten pro Zug
- `allow_number_on_number`: macht mehr Zahlenkarten spielbar
- `allow_action_on_action`: macht mehr Aktionskarten spielbar
- `draw_two_penalty`: macht Draw Two staerker
- `skip_penalty_cards`: Skip laesst Gegner zusaetzlich ziehen
- `reverse_penalty_cards`: Reverse laesst Gegner zusaetzlich ziehen

## Aktuelle Strategie

`rule_evolution_agent.py` erzeugt Regeln deterministisch statt frei per LLM.
Das ist absichtlich so, weil Max' Server nur bestimmte strukturierte Mechaniken akzeptiert.

Prioritaet:

1. Wenn Daniel-Agent wenige Karten hat: `win_hand_count`.
2. Wenn Daniel-Agent fast fertig ist: `max_plays_per_turn`.
3. Wenn Top Card und Hand passen: Matching-Freiheiten wie `allow_number_on_number`.
4. Wenn starke Aktionskarten spielbar sind: Draw-/Skip-/Reverse-Penalties.
5. Keine Duplikate erzeugen.

## Einschalten im Client

```powershell
python .\Daniel\competitive_agent\daniel_uno_client.py --mode join --name "Daniel-Agent" --delay 1 --enable-rules
```

Der Client versucht dann vor Daniel-Agents Kartenentscheidung, eine starke Mutable Rule hinzuzufuegen.
