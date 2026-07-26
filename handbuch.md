# Μαθαίνω — Griechisch · Handbuch

Μαθαίνω („ich lerne“) ist eine Lern-App für Griechisch (Niveau A1, mit
Vorbereitung auf A2): Vokabeltraining mit Karteikarten oder Tippen, dazu
Grammatiktrainer für Deklination und Konjugation. Dieses Handbuch wird
nach und nach ergänzt — die wichtigsten Punkte stehen auch in der App
unter dem ?-Symbol oben rechts. Grammatik-Übersichtstabellen (Alphabet,
Artikel, Deklinationen, Verben, Adjektive, Zahlen, Pronomen, Fragewörter
+ Präpositionen) öffnet das Buchsymbol daneben.

## Stufen (A1/A2)

In den **Einstellungen** (Zahnrad) lässt sich die sichtbare **Stufe**
umschalten: **A1** zeigt nur A1-Listen, **A2** zeigt A1- **und**
A2-Listen (der A1-Wortschatz bleibt auf A2 relevant). Eigene Listen
ohne Stufe sind in beiden Modi immer sichtbar — nach dem Update
verschwindet also nichts. Die Stufe einer eigenen Liste wird beim
Anlegen oder über „Umbenennen“ in der Vokabelverwaltung gesetzt.

Der Filter wirkt in Training, Verwaltung und Statistik; Auswahllisten
(★) werden nie gefiltert, und der Lernfortschritt ist stufenübergreifend
(er hängt an der Karte, nicht an der Stufe). Hinweis: A1-Listen können
für A2 unvollständig sein (z.B. fehlen Vokativ oder Aoristformen) —
solche Karten lassen sich später über den Reimport einer korrigierten
Textanalyse anreichern.

## Erweiterte Funktionen

Unter **Einstellungen → Erweiterte Funktionen** lassen sich
Zusatzfunktionen für Fortgeschrittene einzeln zuschalten (Standard:
aus). Eingeschaltete Funktionen erscheinen als eigene Karte im
Hauptmenü und gelten für alle Stufen gemeinsam. Aktuell verfügbar:
die **Textanalyse** (siehe unten).

## Textanalyse (erweiterte Funktion)

Die Textanalyse bringt komplette Analysen griechischer Texte in die
App — erstellt von einem Chatbot nach der mitgelieferten
**Arbeitsanweisung III** („Prompt kopieren“ in der Textanalyse-Ansicht):

1. Prompt kopieren und zusammen mit einem griechischen Text an einen
   Chatbot geben. Der Chatbot liefert **eine JSON-Datei** mit allen
   Abschnitten der Analyse.
2. In der Textanalyse-Ansicht **importieren** (Datei oder „Als Text
   importieren“). Die App legt die Analyse an und erzeugt daraus
   automatisch **zwei Vokabellisten**: „…– Vokabeln“ (Hauptvokabular)
   und „…– Etymologie“ (Zusatzwörter aus Kognaten und Synonymen,
   gebündelt nach Analysewort, ohne Dubletten).
3. Jede Analyse ist komplett einsehbar: **Originaltext** (mit
   Sprachausgabe-Button, langes Drücken = langsam), **inhaltliche
   Übersetzung**, **Wort-für-Wort-Segmente**, **Vokabeln**, **Phrasen**
   und die **Etymologieliste**.
4. Vokabeln mit Etymologie-Eintrag zeigen im Training (auf der
   griechischen Seite) und in den Wortübersichten einen
   **Info-Button** (ⓘ) mit Wortherkunft, Kognaten und Synonymen.

**Korrektur per Reimport:** Eine korrigierte Analyse-Datei mit
derselben `id` (oder demselben Titel) **ersetzt** die Analyse. Die
Vokabellisten werden dabei abgeglichen: bestehende Karten werden
aktualisiert und behalten ihren Lernstand, neue Wörter kommen dazu,
**nicht mehr enthaltene Wörter werden gelöscht** (die Analyse ist die
Quelle der Wahrheit). Beim Löschen einer Analyse fragt die App, ob die
erzeugten Listen mitgelöscht werden sollen.

## So wertet die Abfrage

- Groß-/Kleinschreibung und mehrfache Leerzeichen sind egal.
- Satzzeichen am Anfang/Ende (`; · ! ? . , …`) sind egal.
- **Wortteile in Klammern sind optional**: bei „αγαπ(ά)ω“ zählen αγαπάω
  und αγαπώ als richtig, bei „(Visiten-)Karte“ Visitenkarte und Karte
  (ein Bindestrich am Klammerrand verbindet die Teile). Klammern mit
  Satzzeichen sind reine Zusatzinfo, z.B. „Sie (Akk.)“.
- **Eckige Klammern im Satz**: genau eine Variante muss genannt werden —
  „Ich spreche [nicht/kein] Chinesisch.“ akzeptiert beide vollständigen
  Sätze, „Πώς [είσαι/είστε];“ ebenso. Ein nacktes „A / B“ auf oberster
  Ebene trennt dagegen komplette Alternativantworten („και / κι“).
- **Griechisch**: fehlende oder falsche Akzente und ein falsches
  Schluss-ς ergeben „Fast!“. Mit „Akzentfehler tolerieren“ zählt das als
  richtig. Ist die Toleranz **aus**, zählt der Akzentfehler in der Runde
  als Fehler (Fehlerrunde und Rundenergebnis) — die Leitner-Box bleibt
  dabei aber unverändert: weder hoch noch zurück. Ausnahme: **neue
  (graue) Wörter** haben noch keine Box zu schützen — sie starten bei so
  einem Fehler ganz normal in Box 1 und gelten nicht länger als „neu“.
- **Deutsch**: Enthält die Rückseite mehrere Bedeutungen (getrennt durch
  Komma, „/“ oder als eigene Sätze), genügt eine davon. Text in Klammern
  ist Zusatzinfo und muss nicht mitgetippt werden.
- Die **Fehlerrunde** am Ende wiederholt alle falschen Karten in der
  Reihenfolge der Fehler und zählt nicht in die Statistik. In der
  **nächsten Runde** kommen die falschen Wörter garantiert wieder mit
  dazu und werden zwischen die übrigen/neuen Wörter gemischt. Wörter,
  die **heute schon richtig beantwortet** wurden, rücken bei der Auswahl
  dagegen ans Ende — sie kommen erst wieder dran, wenn fällige, neue und
  ältere Karten aufgebraucht sind.
- Am Rundenende werden unter den falschen auch die **richtig
  beantworteten Wörter** aufgelistet.
- Im Verbtraining ist die **2. Person Plural 👥** zugleich die höfliche
  Anrede („ihr“ und „Sie“); Singular-/Plural-Fragen sind zusätzlich mit
  👤 (einer) bzw. 👥 (viele) markiert.

## Wortlisten bearbeiten

- **Regelmäßige Wörter brauchen nur einen Eintrag** (Grundform) —
  Deklination und Konjugation werden regelbasiert gebildet.
- **Nomen**: Artikel und Plural angeben; unregelmäßige Fälle nur bei
  Bedarf in die Zusatzfelder (Akkusativ/Genitiv Singular/Plural).
- **Verben**: unregelmäßiges Präsens als 6 Formen mit Komma
  (1sg, 2sg, 3sg, 1pl, 2pl, 3pl), „-“ = regelmäßiger Slot, z.B.
  „πάω, πας, πάει, πάμε, πάτε, πάνε“. 2. Stamm (Futur/να-Form, Aorist
  Aktiv) als einzelner Stamm („γραψ-“) oder ebenfalls 6 Formen.
  Zusätzlich (A2-Vorbereitung, vorerst nur Speicherung/Anzeige):
  **Aorist Passiv** im gleichen Format und ein unregelmäßiges
  **Perfekt-Partizip** (z.B. „γραμμένος“).
- Mehrere richtige Formen mit „/“ trennen (z.B. „2pl=είστε/είσαστε“),
  optionale Wortteile in Klammern („αγαπ(ά)ω“).
- **Adjektive**: nur ein unregelmäßiges Femininum eintragen.
- Im Editor sind nur die zum Worttyp passenden Felder sichtbar;
  „Sonstiges“ zeigt alle Felder.
- Auch **aus der Abfrage heraus** erreichbar: Der Stift öffnet den
  Notiz-Dialog; dort springt **„Alles bearbeiten“** direkt in die
  vollständige Kartenbearbeitung (bereits Getipptes wird übernommen).
  Bei Buchlisten-Karten gibt es weiterhin nur den Notiz-Dialog.

### Beispiele je Worttyp

| Worttyp | regelmäßig | unregelmäßig |
|---|---|---|
| Nomen | ο δρόμος – Straße, Plural „-οι“ | η γυναίκα – Frau, Plural „-ες“, `gen_pl=γυναικών` |
| Verb | γράφω – schreiben, 2. Stamm „γραψ-“ | πάω – gehen, Präsens „πάω, πας, πάει, πάμε, πάτε, πάνε“ |
| Adjektiv | μικρός – klein | γλυκός – süß, Femininum „γλυκιά“ |
| Adverb | εδώ – hier | — |
| Präposition | από – von, aus | — |
| Phrase | Τι κάνεις; – Wie geht's? (Notiz „per du“) | — |
| Zahl | πέντε – fünf | — |
| Sonstiges | και – und, auch | — |

## Vokabellisten per CSV importieren

In der Vokabelverwaltung über „Importieren“ eine CSV- oder JSON-Datei
wählen — oder über **„Als Text importieren“** den Inhalt direkt
einfügen: praktisch, wenn ein Chatbot keine Datei speichern kann;
seine Antwort wird einfach hineinkopiert (CSV und JSON werden
automatisch erkannt). Die CSV braucht eine Kopfzeile mit diesen
Spalten (nur `front` und `back` sind Pflicht):

```
front,back,plural,article,word_type,hints_gr,hints_de,notes_gr,notes_de,forms,stem2,aorist_passive,participle
```

Die Spalte `forms` nimmt unregelmäßige Formen als `schlüssel=form; …`
auf, z.B. `gen_pl=γυναικών; 2sg=πας`. In der App-Hilfe (?-Symbol) steht
ein fertiger Chatbot-Prompt, der aus einer Liste griechischer Wörter
(als Foto oder Text) die Import-CSV erzeugt.

## Audio (Aussprache)

Die App spricht jedes griechische Wort selbst. In den **Einstellungen**
(Zahnrad) stehen zwei Wege zur Wahl:

- **Systemstimme (Standard)**: spricht offline über die Sprachausgabe
  des Geräts — es werden keine Daten übertragen. Auf Android ist die
  griechische Stimme meist schon dabei; unter Windows das Sprachpaket
  „Ελληνικά" (mit Text-in-Sprache) installieren. Fehlt die Stimme,
  zeigt das Antippen einen Hinweis.
- **Google (online)**: holt das Audio von Google-Servern — dabei werden
  der gesprochene Text und die IP-Adresse übertragen (Details in der
  [Datenschutzerklärung](DATENSCHUTZ.md)). Danach liegt die Aufnahme im
  lokalen Cache und spielt offline. Für Geräte ohne griechische
  Systemstimme (z.B. Linux).

Bedienung:

- **Lautsprecher-Symbol an jeder Karte** in den Listenansichten:
  **kurz antippen** spielt normal, **lang drücken** langsam (zum
  Nachsprechen). Im Vokabeltraining erscheinen Lautsprecher- und
  Langsam-Symbol unter der Karte — aber erst, wenn die griechische
  Seite sichtbar ist, damit die Antwort nicht verraten wird.
- Nur im Google-Modus: **„Audio vorbereiten"** im Listenmenü (⋮, auch
  bei Buchlisten) lädt alle Wörter einer Liste auf einmal in den
  Cache — praktisch vor einer Reise, damit die ganze Liste offline
  anhörbar ist (~100 Wörter in 1–2 Minuten, etwa 1–1,5 MB). Wird ein
  Wort geändert, entsteht beim nächsten Abspielen automatisch neues
  Audio; veraltetes Audio kann es nicht geben.

**Auto-Play:** In allen drei Trainings sitzt oben rechts ein
Lautsprecher-Umschalter. Ist er an, wird automatisch vorgelesen, sobald
der griechische Text erscheint — im Vokabeltraining bei Griechisch →
Deutsch sofort mit der Frage, bei Deutsch → Griechisch mit dem Aufdecken
der Lösung. **Nomen- und Verbtraining sprechen die echte Lösungsform**
(z.B. „θα γράψετε“ oder „τους μικρούς δρόμους“), zusätzlich gibt es dort
ein Lautsprecher-Symbol neben der aufgedeckten Lösung. Die Einstellung
bleibt gespeichert.

Scheitert die Wiedergabe (fehlende Stimme bzw. im Google-Modus kein
Internet), bleibt Auto-Play lautlos; manuelles Antippen zeigt einen
kurzen Hinweis. Klammern und Alternativen werden beim Sprechen
bereinigt: „αγαπ(ά)ω“ wird als „αγαπάω“ gesprochen, „και / κι“ als
„και“, Zusätze wie „(ΕΕ)“ entfallen.

## Wie kommt die Statistik zustande?

### Das Boxen-System (Leitner)

Jede Vokabelkarte hat einen eigenen Lernstand, der in einer lokalen
Datenbank (`progress.db`) gespeichert wird:

- **Box 1–5**: die Leitner-Box der Karte. Jede Karte startet in Box 1.
- **richtig/falsch-Zähler** und **Streak** (richtige Antworten in Folge).
- **Fälligkeit**: wann die Karte wieder abgefragt werden sollte.

Bei jeder gewerteten Antwort passiert Folgendes:

| Antwort | Wirkung |
|---|---|
| richtig | Box steigt um 1 (max. Box 5), Karte wird später wieder fällig |
| falsch | Karte fällt zurück in Box 1 und ist sofort wieder fällig |

**Nur die Produktionsrichtung Deutsch → Griechisch (das Wort schreiben
können) bringt eine Karte über Box 3 hinaus.** Reines Wiedererkennen
(Griechisch → Deutsch) befördert höchstens bis Box 3 — eine bereits
höhere Box bleibt dabei stehen, wird aber nicht zurückgestuft. Bei der
Einstellung „Gemischt“ zählt die Richtung, in der die Karte tatsächlich
abgefragt wurde.

Über das Papierkorb-Symbol in der Statistik-Ansicht lässt sich der
Lernstand einer Liste komplett auf null zurücksetzen; die Karten gelten
danach wieder als neu.

Die Wartezeit bis zur nächsten Fälligkeit hängt von der Box ab:
Box 1 = sofort, Box 2 = 1 Tag, Box 3 = 3 Tage, Box 4 = 7 Tage,
Box 5 = 30 Tage. Beim Start einer Trainingsrunde werden **überfällige
Karten zuerst** gezogen, dann neue (noch nie trainierte), dann der Rest.

In der Statistik-Ansicht gilt eine Karte als „sicher“, wenn sie in
Box 4 oder 5 liegt. Die „Problemwörter“ sind die Karten mit den meisten
falschen Antworten.

### Was zählt in die Statistik — und was nicht?

- **Vokabeltraining**: Jede Antwort der ersten Runde zählt (richtig oder
  falsch). Die optionale **Fehlerrunde** am Ende zählt nicht noch einmal —
  sie dient nur dem Wiederholen.
  - Im Tipp-Modus zählt „Fast!“ (nur Akzent-/Schluss-ς-Fehler) als richtig.
  - Im Karteikarten-Modus zählt die Selbstbewertung („Gewusst“ /
    „Nicht gewusst“).
- **Deklination**: Hier kommt es auf die eingestellte **Vorgabe** an:
  - Vorgabe **Griechisch** (die Nominativphrase wird angezeigt): Das ist
    reines Formentraining — es fließt **nicht** in die Vokabelstatistik ein.
  - Vorgabe **Deutsch** (nur die deutsche Bedeutung wird angezeigt): Wer
    hier richtig dekliniert, hat die Vokabel zugleich aktiv gewusst. Eine
    **richtige Antwort zählt deshalb positiv** für die Vokabelstatistik der
    Karte (Box steigt). Eine falsche Antwort setzt die Box **nicht**
    zurück — ein Deklinationsfehler ist kein Beweis, dass die Vokabel
    unbekannt ist. Auch hier zählt nur die erste Runde, nicht die
    Fehlerrunde.
- **Konjugation**: fließt derzeit nicht in die Vokabelstatistik ein.

Deklinations- und Konjugationsrunden zeigen am Ende zusätzlich ihr eigenes
Rundenergebnis (x von y richtig); das ist unabhängig von der dauerhaften
Vokabelstatistik.

### Statistik exportieren

Über das Download-Symbol oben in der Statistik-Ansicht lassen sich die
Statistikdaten exportieren — „Als Text“ (Zwischenablage) oder als Datei:

- **CSV**: eine Zeile pro Karte aller sichtbaren Listen (auch
  untrainierte Karten, dann mit leeren Fortschrittsspalten) mit den
  Spalten `liste, front, back, word_type, box, correct, wrong, streak,
  last_seen, due`.
- **JSON**: dieselben Kartendaten plus eine Zusammenfassung pro Liste
  (Kartenzahl, trainiert, sicher, Boxen-Verteilung).

Der Export enthält genau die Listen, die die Statistik gerade anzeigt —
die eingestellte Stufe wirkt also auch hier.
