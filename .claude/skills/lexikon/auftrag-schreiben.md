# Auftrag: Lexikoneinträge schreiben

Vorlage für einen Schreib-Agenten (`general-purpose`, `model: opus`).
Platzhalter ersetzen: `<REPO>` (absoluter Repo-Pfad), `<ORDNER>`
(Arbeitsordner, absolut), `<ID>`, `<TEILE>` (z.B. „alle“ oder „teil04–teil06“).

---

Du schreibst Lexikoneinträge (Etymologie-Pakete) für die Liste `<ID>`.

LIES ZUERST VOLLSTÄNDIG:
1. `<REPO>/.claude/skills/lexikon/regeln.md` — alle Inhaltsregeln und
   bekannten Fehler. Halte sie exakt ein.
2. `<ORDNER>/arbeit/<ID>_woerter.tsv` — erste Zeile „Liste: …“, danach
   Nr, front, back, Artikel, Wortart, Zusatzinfos. Für jede Zeile genau
   einen Eintrag, `word` = front exakt.

ARBEITSWEISE
- Zu schreiben: `<TEILE>` laut Teilplan (je 20 Wörter: teil01 = Nr. 1–20,
  teil02 = Nr. 21–40 …). Ist eine Teildatei schon vorhanden und fehlerfrei,
  überspringen (Wiederaufnahme nach Abbruch).
- Je Teil: JSON-Array der Einträge (kein umschließendes Objekt) nach
  `<ORDNER>/<ID>/teilNN.json` schreiben (Bash-Heredoc `cat > … <<'EOF'`),
  dann sofort prüfen:
  `python3 <REPO>/tools/lexikon.py pruefen <ORDNER> <ID> --teilweise`
  Alle FEHLER beheben, bevor du den nächsten Teil schreibst. Die
  Meldungen nennen die Korrektur (z.B. den genauen -μα-Plural).
- Schwierige Formen eines Zusatzworts prüfen:
  `python3 <REPO>/tools/lexikon.py formen <ORDNER> <ID>` zeigt, welche
  Formen die App erzeugt (`<ORDNER>/arbeit/<ID>_formen.txt`); falsche
  Formen über `forms` korrigieren.
- Sparsam: Lies keine anderen Kapitel oder Pakete. Recherchiere im Netz
  nur bei echten Zweifeln (höchstens ~5 Nachschlagungen) — sonst
  vorsichtig formulieren („wohl“, „umstritten“) oder weglassen.
- Keine anderen Dateien ändern, nichts committen.

ABSCHLUSS: `python3 <REPO>/tools/lexikon.py pruefen <ORDNER> <ID>` (ohne
--teilweise, wenn du alle Teile geschrieben hast) muss 0 Fehler melden.

BERICHT (kurz): Einträge und Zusatzwörter je Teil, verbleibende
Validator-Warnungen wörtlich, höchstens 5 Wörter mit unsicherer
Etymologie (je eine Zeile, warum).
