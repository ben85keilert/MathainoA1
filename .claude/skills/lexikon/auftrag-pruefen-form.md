# Auftrag: Formprüfung (Zusatzwörter, Griechisch, Deutsch)

Vorlage für einen Prüf-Agenten (`general-purpose`, `model: sonnet`).
Platzhalter: `<REPO>`, `<ORDNER>`, `<AUSZUG>` (Datei aus
`tools/lexikon.py auszug <ORDNER> form …`), `<NAME>` (z.B. `form_kap05-kap06`).

---

Du prüfst die Zusatzwörter (Lernkarten) von Lexikoneinträgen formal.
Etymologie ist NICHT deine Aufgabe (macht ein anderer Prüfer).

LIES ZUERST VOLLSTÄNDIG: `<REPO>/.claude/skills/lexikon/regeln.md`
(Abschnitte 5–7 sind dein Prüfmaßstab). Dann `<AUSZUG>` vollständig in
Abschnitten. Je Eintrag: Kopfzeile, total, „griech.:“ (griechische
Wörter aus Kognaten/Synonymen), dann je Zusatzwort eine Zeile
`+ front | back | Angaben → von der App erzeugte Formen [weitere Felder]`;
⚑ = automatischer Akzent-Verdacht.

PRÜFEN je Zusatzwort
1. front: Schreibung, Akzent, Artikel/Genus; Adjektiv im Maskulinum,
   Verb in der 1. Sg. Präsens.
2. back: richtige, idiomatische deutsche Bedeutung(en), „ / “ als Trenner.
3. Die von der App erzeugten Formen (Gen. Sg., Nom. Pl., Gen. Pl.;
   Präsens, Futur, Aorist; Femininum/Neutrum): ist eine falsch, das Feld
   korrigieren (plural, stem2, aorist, hints_gr-Endungen) oder `forms`
   setzen (`gen_pl=…; gen_sg=…`, Semikolon, ohne Artikel).
4. Verben: stem2/aorist/imperative stimmig (Deponentien Passivstamm,
   Imperativ = Aorist-Imperativ, groß, „!“, leer wenn ungebräuchlich).
5. Griechische Wörter in „griech.:“ nur formal (Schreibung, Akzent,
   Artikel) und das Deutsch in total.
Alles, was der Validator schon erzwingt (Feldnamen, Trenner, -μα-Plural,
bekannte App-Fallen), ist bereits sauber — nicht erneut darauf prüfen.

AUSGABE: nur Patches, keine Dateien ändern. JSON-Liste nach
`<ORDNER>/patches/offen/<NAME>.json`, nach jedem Block von etwa 40
Einträgen vollständig neu schreiben. Format:
- Zusatzwort ersetzen: `{"chapter": "<id>", "word": "<Eintrags-word exakt>",
  "field": "extra_vocab", "item": "<front exakt>", "value": {<vollständiges
  neues Zusatzwort-Objekt>}, "reason": "<kurz>"}` — EIN Patch genügt, das
  Werkzeug ändert gleiche Zusatzwörter in allen Kapiteln mit.
- Kognat/Synonym formal korrigieren: `"field": "cognates.identical" |
  "cognates.related" | "synonyms"`, `"item": "<word exakt>"`, `"value":
  {"word","meaning"}` bzw. `{"word","nuance"}`.
- total: `{"chapter", "word", "field": "total", "value": "…", "reason"}`.
Am Ende `python3 <REPO>/tools/lexikon.py patch <ORDNER>` (Probelauf) und
Meldungen zu deiner Datei beheben.

BERICHT (kurz): Anzahl Patches, die 10 wichtigsten je eine Zeile, Zweifelsfälle.
