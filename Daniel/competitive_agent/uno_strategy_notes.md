# UNO Strategy Notes For Daniel-Agent

Diese Notizen sind fuer den kompetitiven Agenten gedacht. Sie sind kein Fine-Tuning, sondern Kontext und Strategie-Memory.

## Quellenbasierte Regeln

- Ziel ist es, als erster alle eigenen Karten loszuwerden.
- Ein Zug ist gueltig, wenn Farbe, Zahl oder Symbol zur obersten Karte passt, oder wenn eine Wild-Karte legal gespielt wird.
- Wild-Karten erlauben die Wahl der naechsten Farbe.
- Draw Two laesst den naechsten Spieler zwei Karten ziehen und den Zug verlieren.
- Wild Draw Four laesst den naechsten Spieler vier Karten ziehen und den Zug verlieren, ist aber nur unter bestimmten Bedingungen legal.
- In einem Zwei-Spieler-Spiel wirkt Reverse wie Skip.
- Wer auf eine Karte herunterspielt, sollte UNO deklarieren, wenn das Spielsystem diese Information nutzt.

## Taktische Prioritaeten

1. Sofort gewinnen, wenn ein legaler Gewinnzug moeglich ist.
2. Wenn der Gegner nur eine oder zwei Karten hat, blockieren statt nur irgendeine Karte loswerden.
3. In Zwei-Spieler-UNO sind Skip und Reverse sehr stark, weil sie dem Gegner den naechsten Zug nehmen.
4. Draw Two und Wild Draw Four sind besonders wertvoll, wenn der Gegner kurz vor dem Gewinnen ist.
5. Wild-Karten nicht zu frueh verschwenden; sie sind gut zum Gewinnen, Retten aus schlechter Farbe oder Blockieren.
6. Bei Wild-Farbwahl die Farbe nehmen, die in der eigenen Resthand am haeufigsten vorkommt.
7. Wenn mehrere normale Karten spielbar sind, eine Karte waehlen, die eine starke Folgefarbe offen haelt.
8. Legalitaet ist wichtiger als Aggressivitaet: Ein ungueltiger Zug ist schlechter als ein konservativer legaler Zug.
9. Wenn keine Karte spielbar ist, ziehen.

## Quellen

- Wikipedia, UNO official rules summary: https://en.wikipedia.org/wiki/Uno_(card_game)
- Mattel service/instruction sheets are referenced from the UNO rules summary and describe the standard card effects.
