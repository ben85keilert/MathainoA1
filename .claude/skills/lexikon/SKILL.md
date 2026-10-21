---
name: lexikon
description: Lexikoneinträge (Etymologie-Pakete nach Arbeitsanweisung IV) für Vokabellisten erzeugen, prüfen oder nachbessern — zuverlässig und sparsam im KI-Verbrauch. Verwenden, wenn neue Lexikonpakete für Buchkapitel entstehen sollen, vorhandene Pakete (auch von einem Chatbot erzeugte) geprüft oder einzelne Einträge korrigiert werden sollen. Aufruf z.B. "/lexikon erstellen private/pame-a2/lexikon kap05 kap06" oder "/lexikon prüfen private/pame-a2/lexikon kap01".
---

# Lexikoneinträge erzeugen und prüfen

Grundsatz: **Was sich maschinell prüfen lässt, prüft `tools/lexikon.py` —
die KI schreibt Inhalte und liest gezielte Auszüge.** Korrektheit geht vor
Sparsamkeit; gespart wird an Wiederholungen, nicht an Sorgfalt.

Bestandteile:
- `tools/lexikon.py` — Validator, Formenkontrolle, Prüfauszüge, Patches,
  Angleichen, Importtest (Befehle: `python3 tools/lexikon.py` ohne Argumente)
- `regeln.md` (dieser Ordner) — alle Inhaltsregeln und bekannten
  Stolperfallen; einzige Regelquelle für Schreiber UND Prüfer
- `auftrag-schreiben.md`, `auftrag-pruefen-inhalt.md`,
  `auftrag-pruefen-form.md` — Vorlagen für die Agenten-Aufträge

Argumente: Modus (`erstellen` | `prüfen` | `nachbessern`), Arbeitsordner,
Listen-ids. Fehlt etwas, aus dem Kontext ableiten (`status` zeigt, welche
Listen offen sind); nur fragen, wenn es wirklich unklar ist — und dann
laut CLAUDE.md erst nach der Antwort loslegen.

## Arbeitsordner

Liegt unter `private/` (gitignored, Buchinhalte bleiben lokal), z.B.
`private/pame-a2/lexikon/`. Neues Projekt anlegen: `projekt.json` nach dem
Muster im Kopf von `tools/lexikon.py` (Stufe, Listen in Buchreihenfolge,
Paketpfad, ggf. `bekannt` = schon vorhandene Lexikonpakete, deren Wörter
nicht neu geschrieben werden). Die Teildateien `<id>/teilNN.json` sind die
Quelle der Wahrheit — die Pakete werden daraus gebaut, nie von Hand
geändert. Korrekturen laufen nur über Patches (`patches/offen/`), damit
jede Änderung nachvollziehbar bleibt (`patches/angewendet/`).

## Modus „erstellen“

1. `python3 tools/lexikon.py status <ordner>` und für jede Liste
   `vorbereiten <ordner> <id>` → `arbeit/<id>_woerter.tsv` + Teilplan.
   Wörter früherer Listen und `bekannt`-Pakete fallen automatisch weg.
2. **Schreiben**: je Liste EIN Agent (`subagent_type: general-purpose`,
   `model: opus`), Auftrag aus `auftrag-schreiben.md`. Mehrere Listen
   parallel in einer Nachricht starten. Listen über ~160 Wörter auf zwei
   Agenten nach Teilnummern aufteilen. Der Agent schreibt Teil für Teil
   und prüft jeden Teil sofort (`pruefen --teilweise`) — bricht er ab
   (Kontingent, Fehler), zeigt `vorbereiten` die offenen Teile, ein neuer
   Agent macht dort weiter.
3. Nach allen Schreibern: `pruefen <ordner> <ids>` (muss 0 Fehler haben),
   `angleichen <ordner>` (Zusatzwörter kapitelübergreifend auf die frühere,
   schon geprüfte Fassung bringen; mit `--anwenden`).
4. **Prüfen**: `auszug <ordner> inhalt <ids>` und `auszug <ordner> form <ids>`
   erzeugen. Dann parallel:
   - Inhaltsprüfer (`model: opus`, `auftrag-pruefen-inhalt.md`):
     Etymologie, Kognaten, dt./lat. Verwandte, Grammatik-Erklärungen.
     Bis ~250 Einträge pro Agent.
   - Formprüfer (`model: sonnet`, `auftrag-pruefen-form.md`): griechische
     Formen der Zusatzwörter, deutsche Rückseiten, Rechtschreibung.
     Bis ~400 Einträge pro Agent (die Formen hat das Skript schon
     vorberechnet und die bekannten App-Fallen abgefangen).
   Prüfer ändern keine Dateien, sie schreiben Patches nach `patches/offen/`.
5. `patch <ordner>` (Probelauf: Konflikte, nicht gefundene Wörter) →
   Konflikte selbst entscheiden (Patchdatei korrigieren) → `patch <ordner>
   --anwenden` → `bauen <ordner> <ids>` → `importtest <ordner>`.
6. Nur wenn die Prüfer viele inhaltliche Korrekturen gemacht haben
   (Faustregel > 15 % der Einträge): **Nachprüfung nur der geänderten
   Einträge** — `auszug <ordner> inhalt <ids> --nur 'patches/angewendet/<stand>/*.json'`
   an einen Inhaltsprüfer. Keine weitere Volllesung: unveränderte
   Einträge sind geprüft.
7. Bericht an den Nutzer (siehe unten).

## Modus „prüfen“ (vorhandene Pakete)

- Pakete ohne Teildateien (z.B. vom Chatbot über die App-Arbeitsanweisung
  erzeugt): `zerlegen <ordner> <id> <paket.json>`.
- `pruefen` → mechanische Fehler zuerst beheben: wenige per Patch durch
  dich, viele per Schreib-Agent mit dem Auftrag „nur die gemeldeten
  Validator-Fehler beheben“.
- Dann Schritte 4–7 wie oben.

## Modus „nachbessern“ (einzelne Wörter)

Der Nutzer nennt Fehler oder Wörter: Patch selbst schreiben (Format im
Docstring von `cmd_patch`), `patch --anwenden`, `bauen`, `importtest`.
Bei inhaltlichen Zweifeln nur diese Wörter per `auszug … --nur <patch>`
prüfen lassen. Ein ersetztes Zusatzwort ändert der Patch automatisch in
allen Kapiteln mit.

## Sparregeln (wichtig)

- **Keine Forks** (`subagent_type: fork` erbt den ganzen Gesprächskontext
  und kostet entsprechend) — immer frische Agenten mit vollständigem,
  knappem Auftrag aus den Vorlagen.
- Du selbst liest weder Teildateien noch Auszüge komplett — nur
  Skriptausgaben und die kurzen Agentenberichte. Stichproben gezielt mit
  `grep`/`python3 -c`.
- Prüfer lesen die Auszüge (je etwa ein Drittel so groß wie das
  Paket-JSON, nur die Felder ihrer Prüfung) statt der Pakete, und jede
  Prüfung nur einmal je Fehlerart: Inhalt und Form getrennt, statt
  mehrerer Volllesungen „auf alles“.
- Korrekturen als Patches (nur die geänderte Stelle), nie ganze Einträge
  neu schreiben lassen.
- Recherche im Netz nur für echte Zweifelsfälle (≲ 5 pro Liste); sonst
  vorsichtig formulieren oder weglassen (regeln.md).
- Fehlerarten, die öfter als vereinzelt auftauchen, als Prüfung in
  `tools/lexikon.py` (+ Test in `tests/test_lexikon_tool.py`) und als
  Regel in `regeln.md` aufnehmen — so verschwinden sie beim nächsten Mal
  schon beim Schreiben statt in einer teuren Korrekturrunde.
- Agenten-Berichte kurz halten (Zahlen + höchstens 10 Zeilen + Zweifelsfälle).

## Abschlussbericht an den Nutzer

Je Liste: Einträge, Zusatzwörter, Validator-Stand (Fehler/Warnungen),
Importtest-Ergebnis; Zahl der Korrekturen nach Art; die wichtigsten
inhaltlichen Korrekturen; offene Zweifelsfälle (unsichere Etymologien);
neu entdeckte App-Fehler. Hinweis: Pakete liegen unter `<paket>`-Pfad,
Re-Import ersetzt Einträge wortweise, Lernstand der Zusatzwörter bleibt.

## Wenn sich die App ändert

Schema und Felder kommen aus der App (`ui/views/lexikon.py`
`_ARBEITSANWEISUNG_IV`, `storage/textanalyse.py`, `models.py`,
`storage/content.verb_fields_for`). Ändert sich dort etwas (neue Stufe,
neue Felder, Deklinationsfehler behoben), `tools/lexikon.py`, `regeln.md`
und die Tests nachziehen — z.B. entfallen behobene App-Fallen in
`app_formfehler`.
