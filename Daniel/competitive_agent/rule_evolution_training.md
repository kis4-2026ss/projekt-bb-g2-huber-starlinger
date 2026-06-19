# Training Fuer Dynamische Regeln

Diese Datei beschreibt, wie Daniel-Agent spaeter mit dynamischen Regeln umgehen soll.
Es ist kein echtes Fine-Tuning, sondern Prompt-, Schema- und Validierungstraining.

## Grundidee

Die festen Basisregeln bleiben gesperrt. Daneben gibt es spaeter eine dynamische Regelliste, z.B.:

```text
max/shared/dynamic_rules.json
```

Oder eine API:

```text
POST /api/rules/proposals
```

Der Agent soll Regeln nicht direkt schreiben. Er soll nur Vorschlaege machen. Der Server entscheidet:

- Ist die Regel erlaubt?
- Widerspricht sie Basisregeln?
- Ist sie maschinenlesbar?
- Ist sie fuer beide Agenten sichtbar?
- Ab welchem Zug gilt sie?

## Vorgeschlagenes JSON-Schema

```json
{
  "agent_id": "daniel_agent",
  "operation": "add",
  "rule_id": "blue_bonus_draw_pressure",
  "rule_text": "If a player plays a blue action card, the opponent draws one extra card.",
  "condition": "played_card.color == 'blue' and played_card.type == 'action'",
  "effect": "opponent_draws += 1",
  "risk_level": "medium",
  "expected_advantage": "Useful if Daniel-Agent has many blue action cards.",
  "validation_notes": "Server checks card color and type before applying the extra draw."
}
```

## Gute Regelvorschlaege

Gute Regeln sind:

- kurz
- eindeutig
- pruefbar
- nicht privat
- nicht endlos
- fuer beide Agenten sichtbar
- taktisch nuetzlich

Beispiele:

- Wenn eine bestimmte Farbe gespielt wird, bekommt der Spieler einen kleinen Bonus.
- Wenn ein Spieler drei Zuege hintereinander zieht, darf er danach eine Farbe waehlen.
- Wenn ein Spieler eine Aktionskarte spielt, wird ein Zusatzpunkt im Log vermerkt.

## Starke Regelmuster aus UNO und aehnlichen Spielen

Diese Muster sind stark, aber noch besser begruendbar als "Daniel gewinnt sofort":

| Muster | Warum stark? | Beispiel fuer dynamische Regel |
|---|---|---|
| Tempo-Bonus | Extra-Zuege sind in Zwei-Spieler-Spielen extrem wertvoll. | Wenn eine blaue Aktionskarte gespielt wird, darf der Spieler eine weitere Karte spielen. |
| Draw-Pressure | Strafkarten vergroessern den Abstand zwischen den Spielern. | Wenn Draw Two gespielt wird und der Gegner hoechstens zwei Karten hat, zieht er eine Zusatzkarte. |
| UNO-Pressure | Der Moment mit einer Restkarte wird in einen Vorteil verwandelt. | Wenn ein Spieler korrekt UNO deklariert, zieht der Gegner eine Karte. |
| Color-Control | Wild- und Farbwahl-Regeln halten den Agenten in seiner staerksten Farbe. | Wenn ein Spieler drei Karten einer Farbe hat, darf er nach einem Wild diese Farbe erneut schuetzen. |
| Stacking | Aus bekannten UNO-Hausregeln: Draw-Karten koennen Druck aufbauen. | Wenn der Gegner eine Draw-Karte nicht beantworten kann, steigt die Strafe um eins. |
| Jump-In-aehnlich | Bekannt aus UNO-Hausregeln und digitalen Varianten. | Wenn ein Spieler dieselbe Karte wie die oberste Karte besitzt, darf er sie in einem Zusatzfenster spielen. |

## Regeln, die fast sofort gewinnen koennen

Diese Regeln sind sehr stark, aber sollten vom Server wahrscheinlich nur begrenzt erlaubt werden:

```json
{
  "rule_id": "blue_combo_turn",
  "condition": "played_card.color == 'blue' and played_card.type == 'action'",
  "effect": "player_may_play_again = true"
}
```

Warum stark:
Wenn Daniel-Agent mehrere blaue Karten oder blaue Aktionskarten hat, kann er mehrere Zuege hintereinander erzeugen und schneller auf null Karten kommen.

```json
{
  "rule_id": "declared_uno_pressure",
  "condition": "own_cards_after_play == 1 and declared_uno == true",
  "effect": "opponent_draws += 1"
}
```

Warum stark:
Der Agent wird belohnt, sobald er kurz vor dem Gewinnen ist. Gleichzeitig wird der Gegner gebremst.

```json
{
  "rule_id": "draw_two_escalation",
  "condition": "played_card.value == 'draw_two' and opponent_cards_in_hand <= 2",
  "effect": "opponent_draws += 1"
}
```

Warum stark:
Die Regel ist situativ, wirkt aber genau dann, wenn der Gegner gefaehrlich wird.

## Was der Server begrenzen sollte

Damit das Projekt stabil bleibt, sollte Max' Server solche Grenzen pruefen:

- keine direkte Regel mit `winner = daniel_agent`
- keine privaten Gegnerkarten als Bedingung, ausser nur oeffentliche Anzahl wie `opponent_cards_in_hand`
- maximal ein Extra-Zug pro normalem Zug
- maximal kleine Zusatzstrafen, z.B. `opponent_draws += 1`
- keine Regel, die Basisregeln loescht
- neue Regeln erst ab dem naechsten Zug aktivieren
- jede Regel bekommt `rule_id`, `condition`, `effect`, `created_by`, `created_turn`

## Schlechte Regelvorschlaege

Schlechte Regeln sind:

- "Daniel gewinnt sofort."
- "Max muss alle Karten zeigen."
- "Der Gegner muss unendlich ziehen."
- "Daniel darf immer nochmal spielen."
- "Die Basisregel fuer gueltige Karten wird geloescht."

Solche Regeln sind zu unfair, nicht stabil oder brechen das Spiel.

## Trainingsziel

Daniel-Agent soll lernen:

1. Keine Basisregeln loeschen.
2. Nur erlaubte Operationen verwenden.
3. Regeln mit klarer Condition und klarem Effect ausgeben.
4. Bei hohem Risiko lieber `operation: "none"` waehlen.
5. Regelvorschlaege im Log nachvollziehbar machen.
