# Regeln für Lexikoneinträge (Etymologie-Pakete)

Einzige Regelquelle für Schreiber und Prüfer. Grundlage ist die
Arbeitsanweisung IV der App (`src/mathainoa1/ui/views/lexikon.py`); hier
stehen zusätzlich die Konventionen der Buchlisten und alle Fehler, die in
früheren Runden gefunden wurden. `tools/lexikon.py pruefen` setzt alles
Mechanische durch — die Meldungen sagen, was zu tun ist.

**Leitsatz: Lieber eine leere Gruppe oder eine vorsichtige Formulierung
als eine falsche Angabe.** Fehler im Lexikon sind peinlich; Lücken nicht.

## 1. Aufbau eines Eintrags

```json
{"word": "το μάθημα",
 "breakdown": [{"element": "μαθ-", "meaning": "lernen (altgr. μανθάνω, Aorist ἔμαθον)"},
               {"element": "-μα", "meaning": "Nomensuffix: Ergebnis einer Handlung"}],
 "total": "das Gelernte → Lektion, Unterrichtsstunde, Fach",
 "semantics": "Vom altgriechischen μάθημα „das Gelernte, Kenntnis“ zu μανθάνω „lernen“; dazu τα μαθηματικά „Mathematik“.",
 "cognates": {"identical": [{"word": "μαθαίνω", "meaning": "lernen, erfahren"}],
              "related": [{"word": "τα μαθηματικά", "meaning": "Mathematik"}],
              "german_latin": [{"word": "Mathematik", "meaning": "über lat. mathematica aus griech. μαθηματική (τέχνη)"}]},
 "synonyms": [],
 "extra_vocab": [{"front": "μαθαίνω", "back": "lernen / erfahren", "word_type": "Verb",
                  "stem2": "μάθ-", "aorist": "έμαθα", "imperative": "Μάθε!"}]}
```

- **word**: exakt die Vorderseite der Karte (mit Artikel, Satzzeichen,
  Klammern, `[ο/η]`, `/`-Varianten). Ein Eintrag je Karte, in
  Listenreihenfolge; Wörter früherer Listen bekommen keinen neuen Eintrag
  (`vorbereiten` hat sie schon herausgenommen).
- **breakdown**: 1–3 Bestandteile, die wirklich im Wort stecken (mit
  Lautwandel erklären: γραμμή = γραφ- + -μή, nicht γράμμα + -ή). Bei
  Lehnwörtern Quellsprache und Quellwort (`türk. çanta`, `venez. …`).
  Bei Phrasen die tragenden Wörter mit grammatischer Bestimmung
  (`ήσουν = du warst (Imperfekt 2. Sg. von είμαι)`).
- **total**: „wörtlich → heute“ mit höchstens einem Pfeil; bei Phrasen die
  wörtliche Übersetzung, wenn sie von der Rückseite abweicht.
- **semantics**: genau eine deutsche Prosazeile mit Schlusspunkt, etwa
  80–220 Zeichen (höchstens 320): Bedeutungsentwicklung, Herkunft,
  Lehnbeziehungen; bei Phrasen und Verbformen die Grammatik korrekt
  (Person, Tempus, Lemma, Kasus).
- **cognates**: immer alle drei Gruppen, notfalls leer.
  - `identical`: neugriechische Wörter derselben Wurzel (Grundwort,
    direkte Ableitungen), Nomen mit Artikel.
  - `related`: weitere neugriechische Ableitungen/Komposita derselben
    Wurzel.
  - `german_latin`: deutsche, lateinische oder internationale Wörter, die
    nachweislich verwandt oder entlehnt sind; `meaning` nennt den Weg
    („über lat. … aus griech. …“, „aus griech. …“, „urverwandt“).
- **synonyms**: lernwürdige Alternativen **anderer Wurzel** mit Nuance
  (Stil, Gebrauch, Region). Ein Wort steht nie zugleich in cognates und
  synonyms.
- **extra_vocab**: 0–4 Lernkarten (Abschnitt 5).

## 2. Kognaten — häufigste Fehlerquelle

In früheren Runden mussten rund 100 Kognaten gestrichen oder umgedeutet
werden. Deshalb streng:

- **Nur echte Wurzelverwandtschaft.** Ein gemeinsames Präfix oder Suffix
  reicht nicht: είσοδος (εἰς + ὁδός) ist kein Kognat von εισιτήριο
  (Wurzel ἰ- „gehen“); έξοδος nicht von βγαίνω; μεταξύ ist kein Kognat
  von ανάμεσα. Komposita, die nur EIN Glied teilen, gehören höchstens zu
  `related` (τραγωδία zu κωμωδία über ᾠδή), nicht zu `identical`.
- **Wortfeld und Gegenwort sind keine Kognaten**: πάλι zu ξανά, ολικός zu
  μερικοί, η αρχή zu στο τέλος. Lernwürdige Wortfeld-/Gegenwörter nennt
  man in semantics („Gegenteil: κάνει κακό“) und kann sie dann als
  Zusatzwort aufnehmen. (Ältere Pakete führen solche Wörter in `related`
  mit dem Zusatz „(Wortfeld, andere Wurzel)“ oder „(Gegenwort)“ — das
  bleibt gültig, für neue Einträge aber semantics bevorzugen.)
- Gleich lautend ist nicht verwandt: Zufallsähnlichkeiten prüfen
  (κρητικός ≠ κριτικός — als Verwechslungshinweis in semantics, nicht
  als Kognat).
- Nicht das Eintragswort selbst als Kognat aufführen — außer in anderer
  Wortart (Adjektiv ηλεκτρικός zum Nomen ο ηλεκτρικός).

## 3. Etymologie und Entlehnungen

- **Keine Volksetymologien.** Bereits aufgefallen: τουρισμός ist im
  Englischen entstanden (frz. tourisme daraus); Brasserie gehört zu frz.
  brasser „brauen“, nicht zu braise (μπριζόλα); μαγιό kommt von frz.
  maillot < maille, nicht vom „Strumpfwirker Maillot“; καραμέλα nicht aus
  canna mellis; Rhodos ist nicht die „Roseninsel“ (vorgriechisch);
  Mauretanien gehört zu lat. Mauri, nicht zu μαύρος; letal ≠ λήθη;
  Kirche ≠ ἐκκλησία (Kirche < κυριακόν); Kokosnuss ≠ κόκκος;
  ἀστυνόμοι ≠ ἀγορανόμοι.
- **Entlehnungsweg und -richtung genau**: dt. Zucker kommt nicht direkt
  aus σάκχαρον, sondern über arab. sukkar/ital. zucchero; κατσαρόλα
  frz. → ital., nicht umgekehrt; μαγαζί venez./ital., nicht türkisch;
  γιλέκο türk. yelek; φιστίκι ist byzantinisch belegt (nicht über das
  Türkische); classicus ist lateinisch (keine „Rückentlehnung“).
- **Standardherleitungen** für Neugriechisch: Λεξικό της Κοινής
  Νεοελληνικής (Τριανταφυλλίδης, greek-language.gr), Babiniotis,
  Andriotis; Altgriechisch: Beekes, Frisk, Chantraine; Deutsch: Kluge,
  Pfeifer (DWDS). Bsp.: ξεχνώ < mittelgr. ξεχάνω < ξε- + χάνω; πέρσι <
  πέρυσι mit altem Wort für „Jahr“ (nicht Endung -σι); μήπως enthält
  unbetontes πως „irgendwie“, nicht πώς.
- **Unsicheres kennzeichnen**: „wohl“, „vermutlich“, „Herkunft
  umstritten/unklar“ — nicht als Tatsache formulieren (τσίχλα, παρέα,
  γαύρος, γούνα, φούντα). Erfundene Zwischenstufen („aus dem
  Makedonischen“, „aus arab. …“ ohne Beleg) weglassen.
- Altgriechische Formen mit korrektem Akzent und Spiritus; Bedeutung des
  Präfixes richtig (ἐπι- heißt nicht „heraus“; πρός nicht „neu“).
- Deutsche Vergleichswörter müssen gebräuchlich sein und existieren
  („Dexterität“, „Fahrrad-Cycle“ nein; Lehnwort heißt Berlocke, nicht
  Breloque). Nur die passende Bedeutung nennen (Fuge = Musikform zu
  fuga; Mauerfuge ist germanisch).

## 4. Phrasen, Grammatik, Deutsch

- Grammatische Erklärungen exakt: Imperfekt vs. Aorist, Person, Kasus
  (pro Stunde = την ώρα, Akkusativ); και τα δύο = „beide“, nicht „sowohl
  … als auch“; Καλώς ορίσατε: ορίζω hier „gebieten, geruhen“; dt.
  willkommen < ahd. willicomo „nach Willen Gekommener“.
- Keine Widersprüche zwischen breakdown, total und semantics (z.B.
  „steht ohne να“ und dann ein Beispiel mit να).
- Deutsch idiomatisch und korrekt: „Verzeihen Sie mir“, nicht „mich“;
  keine falschen Freunde (γευστικός/νόστιμος = lecker, schmackhaft —
  „geschmackvoll“ heißt ästhetisch); aktuelle Rechtschreibung („High
  Heels“); fremdsprachige Wörter richtig geschrieben (ital. cinese).
- Mehrere Bedeutungen in `back` mit „ / “ trennen, nicht mit „;“.

## 5. Zusatzwörter (extra_vocab)

Auswahl:
- Alltagstaugliche Wörter der Stufe (A2: häufig, konkret). Keine
  gelehrten/seltenen Wörter (το λήμμα, ο παιδαγωγός), keine alt-
  griechischen, deutschen oder lateinischen Wörter, nie das Eintragswort
  oder ein Buchwort dieser/früherer Listen (Validator warnt).
- Jedes Zusatzwort kommt im Eintrag vor (cognates, synonyms oder
  semantics) — sonst weiß der Lerner nicht, warum es da ist.
- Kommt ein Zusatzwort in mehreren Listen vor, gilt die Fassung der
  frühesten Liste (`angleichen`); Korrekturen per Patch wirken überall.

Felder (nur diese; auf A2 keine `aorist_passive`/`participle` — der
Validator kennt die Felder je Stufe):

| Wortart | front | Pflichtangaben |
|---|---|---|
| Nomen | mit Artikel: `η πόλη` | `article` = Artikel aus front; `plural` als Endung (`-εις`, `-ιά`, `-έδες`, `-` = unveränderlich) |
| Nomen ohne Plural | `το σουσάμι` | `plural` leer, `hints_gr`: „nur Singular“ |
| Pluralwort | `τα μαθηματικά` | `hints_gr`: „nur Plural“; Gen. Pl. immer ausdrücklich in `forms` (`gen_pl=μαθηματικών`) |
| Eigenname | `η Αίγινα` | `hints_gr`: „Eigenname“, kein Plural |
| Doppelgenus | `[ο/η] παιδίατρος` | `article` leer, `hints_gr`: „gleiche Form für m und f“ |
| -μα-Neutrum | `το γράμμα` | Buchkonvention `-ματα` bzw. `-(θή)ματα` (Validator nennt den genauen Wert) |
| Femininum auf -ος | `η έξοδος` | `hints_gr`: „weiblich trotz -ος“ |
| Verb | 1. Sg. Präsens: `γράφω`, `κοιμάμαι` | `stem2` mit Bindestrich (`γράψ-`; Deponentien Passivstamm: `κοιμηθ-`, `ετοιμαστ-`, `σταθ-`); `aorist` 1. Sg. (`έγραψα`, Innenaugment `παρέδωσα`, Suppletiv `πήρα`); `imperative` = Aorist-Imperativ 2. Sg., groß, mit „!“ (`Γράψε!`, Varianten `Κάτσε!/Κάθισε!`, Deponens `Ετοιμάσου!`), leer lassen, wenn ungebräuchlich |
| Verb ohne Stämme | `συμβαίνει` | Grund in `hints_gr`: „unpersönlich, nur 3. Person (Aorist συνέβη)“, „kein Aorist (διέφερα ist Imperfekt)“, „nur Präsens/Imperfekt“ |
| Adjektiv | Maskulinum Sg.: `υπέροχος` | `hints_gr`: „Endungen: -ος, -η, -ο“ (bzw. „-ός, -ή, -ό“, „-ος, -α, -ο“, „-ός, -ιά, -ό“, „-ύς, -ιά, -ύ“, „-ής, -ής, -ές“, „-ης, -α, -ικο“, „-ων, -ουσα, -ον“) oder „unveränderlich“ |
| Phrase/Sonstiges | wie gebraucht | `word_type` „Phrase“ bzw. „Sonstiges“ (Pronomen, Konjunktionen; Endungen in `hints_gr`) |

`forms` (unregelmäßige Formen): String `schlüssel=form; schlüssel=form`
— **Semikolon** als Trenner, Formen **ohne Artikel**. Schlüssel: Nomen
`acc_sg gen_sg nom_pl acc_pl gen_pl`, Adjektiv `fem`, Verb `1sg … 3pl`.

## 6. App-Formen (bekannte Schwächen der App)

Die App bildet Formen regelbasiert (`logic/declension.py`,
`logic/conjugation.py`). Wo sie falsch liegt, braucht das Zusatzwort
explizite `forms`. Der Validator erkennt die bekannten Fälle:

- -ότητα: Gen. Pl. wird endbetont (ποιοτητών) → `gen_pl=ποιοτήτων`.
- Adjektive, deren Femininum die App falsch rät: σκούρος → σκούρα und
  μοντέρνος → μοντέρνα (App: -η), βέβαιος → βέβαιη (App: βέβαια),
  ευθύς → ευθεία (App: ευθιά) → `fem=…`. Der Validator vergleicht das
  App-Femininum mit den Endungen in hints_gr — deshalb müssen die stimmen.
- Pluralwörter: den Akzent im Gen. Pl. rät die App oft falsch
  (μεσάνυχτων statt μεσανύχτων, γενεθλιών statt γενεθλίων) → `gen_pl=…`
  immer angeben, auch wenn die App-Form stimmt.
- Darüber hinaus zeigt `formen`/der Form-Auszug jede erzeugte Form —
  z.B. γεγονός → γεγονότος (`gen_sg=γεγονότος; gen_pl=γεγονότων`).
- Nicht behebbar per forms (App-Grenze, kein Datenfehler): `[ο/η]`-Nomen
  werden nicht dekliniert; Verben auf -ούμαι/-ιέμαι nicht konjugiert.

## 7. Schreibweise

Griechisch in NFC mit korrekten Akzenten (einsilbige Wörter ohne), keine
lateinischen Doppelgänger (o, v, a, p, x, k …) — der Validator meldet
gemischte Schrift. Deutsche Anführungszeichen „…“. Keine doppelten oder
randständigen Leerzeichen.
