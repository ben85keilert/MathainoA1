# MathainoA1 — Hinweise für Claude

## Arbeitsweise

- **Warte mit Umsetzung, bis Antwort kommt.** Wenn Rückfragen an den Nutzer offen sind (z. B. über AskUserQuestion), keine Umsetzung mit angenommenen Standardwerten beginnen. Erst besprechen, dann umsetzen.

## Lexikon (Worthintergrund)

- Lexikonpakete (Arbeitsanweisung IV) für Buchlisten erzeugen, prüfen oder nachbessern: Skill `/lexikon` (`.claude/skills/lexikon/`, Inhaltsregeln in `regeln.md`) mit dem Werkzeug `tools/lexikon.py`. Arbeitsordner und Pakete liegen unter `private/` (Urheberrecht).
- Neue Fehlerarten im Lexikon als Prüfung in `tools/lexikon.py` (+ Test) und als Regel in `regeln.md` festhalten, nicht nur einmalig korrigieren.
