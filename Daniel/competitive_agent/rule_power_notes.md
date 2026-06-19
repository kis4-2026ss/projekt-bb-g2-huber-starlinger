# Rule Power Notes

Diese Datei sammelt starke Regelideen fuer Daniel-Agent.
Sie sollen helfen, spaeter gute Regelvorschlaege zu machen, ohne das Spiel offensichtlich zu brechen.

## Recherche-Kurzfassung

- UNO ist ein Shedding Game: Wer zuerst alle Karten loswird, gewinnt.
- In Zwei-Spieler-UNO ist Tempo besonders wichtig, weil `skip` und `reverse` den Gegner direkt aussetzen lassen.
- Digitale und Hausregel-Varianten kennen starke Mechaniken wie Stacking, 7-0 und Jump-In.
- Aehnliche Kartenspiele nutzen Strafkarten, Extra-Zuege, gestapelte Draw-Effekte und Last-Card-Penalties.
- Aus Game-Design-Sicht sind Regeln problematisch, wenn sie eine dominante Strategie erzeugen oder den Sieger direkt festlegen. Fuer euer Projekt ist das interessant, muss aber vom Server begrenzt werden.

## Beste Regeltypen fuer Daniel-Agent

### 1. Extra-Zug-Regeln

Sehr stark, weil Daniel-Agent dadurch mehrere Karten hintereinander loswerden kann.

```json
{
  "rule_id": "blue_combo_turn",
  "condition": "played_card.color == 'blue' and played_card.type == 'action'",
  "effect": "player_may_play_again = true",
  "risk_level": "high"
}
```

### 2. UNO-Bonus-Regeln

Stark im Endspiel, weil sie den Fuehrenden schuetzen.

```json
{
  "rule_id": "declared_uno_pressure",
  "condition": "own_cards_after_play == 1 and declared_uno == true",
  "effect": "opponent_draws += 1",
  "risk_level": "medium"
}
```

### 3. Anti-Comeback-Regeln

Stark, wenn Max' Agent kurz vor dem Gewinnen ist.

```json
{
  "rule_id": "draw_two_escalation",
  "condition": "played_card.value == 'draw_two' and opponent_cards_in_hand <= 2",
  "effect": "opponent_draws += 1",
  "risk_level": "medium"
}
```

### 4. Farbkontroll-Regeln

Stark, wenn Daniel-Agent viele Karten einer Farbe hat.

```json
{
  "rule_id": "blue_color_lock",
  "condition": "played_card.color == 'blue' and own_blue_cards_after_play >= 2",
  "effect": "next_required_color = 'blue'",
  "risk_level": "medium"
}
```

## Direktes Gewinnen

Eine Regel wie diese waere maximal stark:

```json
{
  "rule_id": "instant_blue_win",
  "condition": "played_card.color == 'blue'",
  "effect": "current_player_wins = true",
  "risk_level": "high"
}
```

Aber: Diese Regel ist fuer ein stabiles Projekt wahrscheinlich zu offensichtlich unfair.
Besser ist, solche Regeln als Negativbeispiel zu dokumentieren und stattdessen starke, aber begrenzte Regeln vorzuschlagen.

## Quellen

- UNO rules summary: https://en.wikipedia.org/wiki/Uno_(card_game)
- Ubisoft UNO house rules summary: https://en.wikipedia.org/wiki/Uno_(video_game)
- Switch card game variants: https://en.wikipedia.org/wiki/Switch_(card_game)
- Kingmaker/game design risk: https://en.wikipedia.org/wiki/Kingmaker_scenario
