# Auftrag: Inhaltsprüfung (Etymologie, Kognaten, Grammatik)

Vorlage für einen Prüf-Agenten (`general-purpose`, `model: opus`).
Platzhalter: `<REPO>`, `<ORDNER>`, `<AUSZUG>` (Pfad der Datei aus
`tools/lexikon.py auszug <ORDNER> inhalt …`), `<NAME>` (Dateiname der
Patchliste, z.B. `inhalt_kap05-kap06`).

---

Du prüfst Lexikoneinträge inhaltlich. Fehler im Lexikon wären peinlich —
prüfe jede Angabe kritisch, ändere aber nur, was falsch oder irreführend
ist (keine Stilüberarbeitung).

LIES ZUERST VOLLSTÄNDIG: `<REPO>/.claude/skills/lexikon/regeln.md`
(Abschnitte 1–4 sind dein Prüfmaßstab, dort stehen die typischen Fehler).
Dann den Auszug `<AUSZUG>` vollständig, in Abschnitten (Read mit
offset/limit), nichts überspringen. Je Eintrag: Kopfzeile `## <id> #<nr>
<word> — <Rückseite> (<Wortart>)`, darunter zerlegung, total, semantics,
identical, related, german_latin, synonyme, zusatzwörter (die daraus
gebildeten Lernkarten; deren Formen prüft ein anderer); Zeilen mit ⚑ sind
automatische Verdachtsfälle — gezielt prüfen.

PRÜFEN je Eintrag
1. Etymologie: Herleitung, altgriechische Formen, Lehnwortquelle und
   -weg, Unsicheres als unsicher gekennzeichnet; keine Volksetymologie.
2. Kognaten: identical/related nur echte Wurzelverwandtschaft (gemeinsames
   Präfix/Suffix reicht nicht); Wortfeld/Gegenwort nicht als Kognat —
   löschen (ggf. in semantics erwähnen) oder, wenn es als Zusatzwort
   dient, mit „(Wortfeld, andere Wurzel)“/„(Gegenwort)“ kennzeichnen;
   german_latin nur gesicherte Verwandtschaft/Entlehnung mit richtigem Weg.
3. Synonyme: andere Wurzel, Nuance stimmt.
4. Phrasen/Verbformen: grammatische Erklärung richtig (Person, Tempus,
   Kasus, Lemma); breakdown, total und semantics widerspruchsfrei.
5. Deutsch in total/semantics/meaning: korrekt und verständlich.
Recherche im Netz nur bei echten Zweifeln (höchstens ~10 insgesamt).

AUSGABE: nur Patches, keine Dateien ändern. JSON-Liste nach
`<ORDNER>/patches/offen/<NAME>.json`, **nach jedem Block von etwa 30
Einträgen die vollständige Liste neu schreiben** (bei Abbruch bleibt
die Arbeit erhalten). Format:
- `{"chapter": "<id>", "word": "<word exakt>", "field": "semantics" | "total" | "breakdown", "value": <neuer Wert; breakdown = ganze Liste>, "reason": "<kurz>"}`
- Listenfelder `cognates.identical` | `cognates.related` |
  `cognates.german_latin` | `synonyms`: zusätzlich `"item": "<word der Zeile exakt>"`;
  `value` = neues Objekt (`{"word","meaning"}` bzw. `{"word","nuance"}`),
  `null` = Zeile löschen, unbekanntes item = Zeile anhängen.
- Wird ein Kognat/Synonym gelöscht, das zugleich Zusatzwort ist, und
  gehört das Zusatzwort dann nicht mehr dazu: auch `"field": "extra_vocab",
  "item": "<front>", "value": null`.
Am Ende `python3 <REPO>/tools/lexikon.py patch <ORDNER>` (Probelauf) —
„nicht gefunden“ und Konflikte in deiner Datei beheben.

BERICHT (kurz): Anzahl Patches nach Art, die 10 wichtigsten Korrekturen
je eine Zeile, offene Zweifelsfälle, die du NICHT geändert hast.
