# Μαθαίνω — Griechisch · Handbuch

Μαθαίνω („ich lerne“) ist eine Lern-App für Griechisch (Niveau A1, mit
Vorbereitung auf A2): Vokabeltraining mit Karteikarten oder Tippen, dazu
Grammatiktrainer für Deklination und Konjugation. Dieses Handbuch wird
nach und nach ergänzt — die wichtigsten Punkte stehen auch in der App
unter dem ?-Symbol oben rechts. Grammatik-Übersichtstabellen (Alphabet,
Artikel, Deklinationen, Verben, Adjektive, Zahlen, Pronomen, Fragewörter
+ Präpositionen) öffnet das Buchsymbol daneben. Zusätzlich gibt es in
allen Trainern **ein gemeinsames Wort-Symbol** für Beugungsformen und
Wort-Info: Gibt es beides, zeigt das **ⓘ-Symbol** einen Dialog mit dem
Lexikoneintrag oben und der Beugungstabelle darunter (durch einen
Querbalken getrennt); gibt es nur die Beugungsformen (Deklination bei
Nomen/Adjektiven, Konjugation bei Verben), erscheint das
**Tabellen-Symbol**, gibt es nur den Lexikoneintrag, das
**Buch-Symbol**. Die Beugungstabelle ist bei Deutsch → Griechisch erst
nach dem Aufdecken enthalten, damit die Antwort nicht verraten wird.
Dasselbe Wort-Symbol erscheint auch in Wortlisten, in der Wortsuche, in
den Vorschauen der Trainings, in den Ergebnislisten und bei den
Problemwörtern der Statistik.

## Zoom

In den **Einstellungen** (Zahnrad → Ansicht → **Zoom**) lassen sich
alle Schriften der App skalieren: **70–150 %, Standard 100 %**. Kleinere
Werte bringen auf kleinen Displays mehr auf den Bildschirm, größere
verbessern die Lesbarkeit. Es handelt sich um echte
Schriftgrößen-Skalierung — die Oberfläche ordnet sich neu an, nichts
wird abgeschnitten. Die Änderung wirkt sofort auf die
Einstellungsseite; andere Ansichten übernehmen sie beim Öffnen. Die
skalierten Schriften folgen dabei den Farben des gewählten Themes —
auch im hellen Modus bleibt alles lesbar.

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
die **Textanalyse** und das **Lexikon** (siehe unten).

## Textanalyse (erweiterte Funktion)

Die Textanalyse bringt komplette Analysen griechischer Texte in die
App — erstellt von einem Chatbot nach der mitgelieferten
**Arbeitsanweisung III** („Prompt kopieren“ in der Textanalyse-Ansicht):

1. Prompt kopieren und zusammen mit einem griechischen Text an einen
   Chatbot geben. Der Chatbot liefert **eine JSON-Datei** mit allen
   Abschnitten der Analyse.
2. In der Textanalyse-Ansicht **importieren** (Datei oder „Als Text
   importieren“). Die App legt die Analyse an und erzeugt daraus
   automatisch die Vokabelliste „…– Vokabeln“ (Hauptvokabular).
3. Jede Analyse ist komplett einsehbar: **Originaltext**, **inhaltliche
   Übersetzung**, **Wort-für-Wort-Segmente**, **Vokabeln** und
   **Phrasen** — Originaltext, jedes Segment und jede Phrase haben
   einen eigenen Sprachausgabe-Button (langes Drücken schaltet den
   Langsam-Modus um, siehe Kapitel „Audio“).

Wortherkunft, Kognaten und Synonyme sind seit Version 0.6 **nicht mehr
Teil der Analyse** — dafür gibt es das **Lexikon** mit der eigenen
Arbeitsanweisung IV (siehe nächstes Kapitel). Ältere Analysen mit
eingebauter Etymologie funktionieren unverändert weiter.

**Korrektur per Reimport:** Eine korrigierte Analyse-Datei mit
derselben `id` (oder demselben Titel) **ersetzt** die Analyse. Die
Vokabellisten werden dabei abgeglichen: bestehende Karten werden
aktualisiert und behalten ihren Lernstand, neue Wörter kommen dazu,
**nicht mehr enthaltene Wörter werden gelöscht** (die Analyse ist die
Quelle der Wahrheit). Beim Löschen einer Analyse fragt die App, ob die
erzeugten Listen mitgelöscht werden sollen.

## Lexikon (erweiterte Funktion)

Das Lexikon ist das zentrale Nachschlagewerk zum **Worthintergrund**:
Wortzerlegung, Bedeutungsentwicklung, Kognaten (verwandte Wörter) und
Synonyme. Es wächst paketweise und speist die **ⓘ-Infobuttons** an
Vokabeln überall in der App (Training, Wortlisten, Wortsuche) — ein
Eintrag gilt für jedes Vorkommen des Wortes, egal in welcher Liste.

So kommt Inhalt hinein:

1. In einer Wortliste über das Listen-Menü **„Fehlende Wort-Infos
   exportieren“** wählen. Die App stellt nur die Wörter zusammen, die
   **noch keinen** Lexikon-Eintrag haben (als CSV-Zeilen).
2. Diese Wörter zusammen mit der **Arbeitsanweisung IV** („Prompt
   kopieren“ in der Lexikon-Ansicht) an einen Chatbot geben — am besten
   in Portionen von etwa **10 Wörtern**. Der Chatbot liefert ein
   **JSON-Paket** mit den Etymologie-Einträgen.
3. Das Paket in der Lexikon-Ansicht (oder über das Listen-Menü:
   „Wort-Infos importieren“) **importieren**.

Beim Import passiert zweierlei:

- Die Einträge werden **wortweise ins Lexikon gemergt**: ein schon
  vorhandenes Wort wird ersetzt (so bessert man Einträge nach, indem
  man das Wort einfach erneut liefert), neue kommen dazu, alle übrigen
  bleiben unverändert.
- Die **Zusatzwörter** des Pakets (lernwürdige Kognaten und Synonyme)
  landen in einer normal editierbaren Liste **„Zusatzwörter –
  <Listenname>“** je Quellliste (der Export liefert den Namen in der
  ersten Zeile mit, der Chatbot übernimmt ihn als „title“) — gebündelt
  nach Ursprungswort, ohne Dubletten; bestehende Karten behalten beim
  Aktualisieren ihren Lernstand. So bleibt der Stoff kapitelweise
  überschaubar statt in einer Riesenliste. Zum Trainieren kleinerer
  Portionen lassen sich daraus wie gewohnt manuell Auswahllisten
  erstellen (Mehrfachauswahl → „Zur Auswahlliste hinzufügen“).

**Geerbte Wort-Infos lösen:** Zusatzwörter zeigen per ⓘ auf den
Eintrag ihres Ursprungsworts (πρωί → Eintrag πρωινό). Passt das nicht,
markiert man die Wörter in der Liste (Mehrfachauswahl) und wählt
**„Wort-Info-Verknüpfung lösen“** — sie gelten dann wieder als „ohne
Eintrag“, erscheinen beim nächsten „Fehlende Wort-Infos exportieren“
und bekommen so einen eigenen Eintrag; der gewinnt automatisch gegen
den geerbten Verweis. Eigene (echte) Einträge lassen sich so nicht
lösen — dafür gibt es das Löschen in der Lexikon-Ansicht.

In der Lexikon-Ansicht lassen sich alle Einträge **durchsuchen**
(alphabetisch sortiert), einzeln ansehen und löschen. Wortlisten mit
Worthintergrund zeigen zusätzlich oben ein **Buchsymbol**, das den
gesammelten Worthintergrund der ganzen Liste öffnet.

## Adjektivtraining

Das Adjektivtraining (eigener Hauptmenüpunkt) dekliniert **Adjektiv +
Nomen zusammen** („ο μικρός δρόμος“ → „τους μικρούς δρόμους“). Welche
Kombinationen abgefragt werden, steuert die Einstellung
**„Adjektivtraining“** im Zahnrad-Menü:

- **Whitelisting (Standard):** Es werden nur **selbst aktivierte
  Verbindungen** abgefragt. Unter **„Verbindungen festlegen…“** wählt
  man ein Adjektiv, blättert durch die Listen und aktiviert die Nomen,
  zu denen es passt (mit Beispielphrase in der Vorschau, „Alle an/aus“
  je Liste).
- **Blacklisting:** Die Adjektive der gewählten Liste werden **beliebig
  mit Nomen kombiniert** — außer mit den unter **„Ausnahmen
  festlegen…“** gesperrten Kombinationen. Als Nomen dienen die Nomen
  der gewählten Liste; enthält sie keine (z.B. eine reine
  Adjektiv-Auswahlliste), werden **alle Nomen der App** verwendet —
  ein kurzer Hinweis beim Rundenstart sagt das an.

Verbindungen wie Ausnahmen gelten **listenübergreifend** — einmal
festgelegt, egal in welcher Liste das Nomen steckt. Im Dialog stehen
nur die **Adjektive der gerade gewählten Liste** zur Auswahl; wer alle
Adjektive auf einmal kuratieren will, sammelt sie in einer gemeinsamen
(Adjektiv-)Liste und wählt diese oben im Adjektivtraining aus.

- Trainierbar sind normale Vokabellisten (es zählen ihre Adjektive)
  und eigene **Adjektiv-Listen**, die im Adjektivtraining und in der
  **Listenverwaltung** (eigener Abschnitt zwischen Auswahl- und
  Vokabellisten) erstellt, bearbeitet, umbenannt, sortiert und
  gelöscht werden können.
- Verschwindet ein Wort aus allen Listen, werden tote Verbindungen
  und Ausnahmen automatisch aufgeräumt.

In allen vier Trainings-Startdialogen führt der **Stift-Button** neben
der Listenauswahl direkt in das Bearbeitungsmenü der gewählten Liste
(Vokabelliste oder Auswahlliste).

Das frühere Zulosen zufälliger Adjektive im Nomentraining entfällt —
das Nomentraining dekliniert jetzt nur noch Nomen.

## So wertet die Abfrage

- Groß-/Kleinschreibung und mehrfache Leerzeichen sind egal.
- Satzzeichen am Anfang/Ende (`; · ! ? . , …`) sind egal.
- **Kommas zählen nie als Fehler** — auch mitten im Satz: „Γεια σου, τι
  κάνεις;“ und „Γεια σου τι κάνεις“ sind gleichwertig (auf der
  deutschen Seite trennen Kommas weiterhin Alternativen, siehe unten).
- **Wortteile in Klammern sind optional**: bei „αγαπ(ά)ω“ zählen αγαπάω
  und αγαπώ als richtig, bei „(Visiten-)Karte“ Visitenkarte und Karte
  (ein Bindestrich am Klammerrand verbindet die Teile). Klammern mit
  Satzzeichen sind reine Zusatzinfo, z.B. „Sie (Akk.)“.
- **Eckige Klammern im Satz**: genau eine Variante muss genannt werden —
  „Ich spreche [nicht/kein] Chinesisch.“ akzeptiert beide vollständigen
  Sätze, „Πώς [είσαι/είστε];“ ebenso. Das gilt auf beiden Sprachseiten,
  auch mit mehr als zwei Varianten („[α/β/γ]“) und mit mehreren Gruppen
  im selben Satz; anders als bei runden Klammern ist die Angabe Pflicht.
  Ein nacktes „A / B“ auf oberster Ebene trennt dagegen komplette
  Alternativantworten („και / κι“).
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
  Reihenfolge der Fehler und zählt nicht in die Statistik („Fehler am
  Ende wiederholen“). Mit **„Fehler in nächster Runde wiederholen“**
  kommen die falschen Wörter bei „Neue Runde“ bzw. beim nächsten Start
  derselben Liste garantiert wieder mit dazu und werden zwischen die
  übrigen/neuen Wörter gemischt. Wörter, die **heute schon richtig
  beantwortet** wurden, rücken bei der Auswahl dagegen ans Ende — sie
  kommen erst wieder dran, wenn fällige, neue und ältere Karten
  aufgebraucht sind.
- Beide Optionen — und die übrigen Schalter (Toleranzen, Artikel,
  Einblendungen) — stehen auf den Startseiten kompakt unter den
  Start-Buttons („Weitere Optionen“). Antippen öffnet einen Dialog;
  Änderungen dort werden **sofort gespeichert**, nicht erst beim
  Trainingsstart.
- Am Rundenende werden unter den falschen auch die **richtig
  beantworteten Wörter** aufgelistet — beide mit Stift zum Bearbeiten
  und (abschaltbar in den Einstellungen) einem **zweigeteilten
  Farbpunkt**: linke Hälfte = Leitner-Box vor der Runde, rechte Hälfte
  = Box danach (grau = noch nicht trainiert). Gilt für alle Trainings
  gleichermaßen; im Beugungstraining nur bei Vorgabe Deutsch (mit
  Vorgabe Griechisch bewegt die Runde keine Boxen).
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
- **Komplette Alternativantworten**: griechisch mit „ / “ trennen
  („και / κι“), deutsch mit Komma oder „/“ („und, auch“) — jede
  Alternative zählt bei der Abfrage als richtig.
- **Genau eine von mehreren Varianten Pflicht**: eckige Klammern im
  Satz, z.B. „Ich spreche [nicht/kein] Chinesisch.“ oder
  „Πώς [είσαι/είστε];“ — auf beiden Sprachseiten, auch mit mehr als
  zwei Varianten („[α/β/γ]“). Kein nacktes „A / B“ mitten im Satz —
  das würde als zwei Komplettantworten gewertet.
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

## Bestehende Liste aktualisieren (Sammelbearbeitung)

Ein Import legt immer eine **neue** Liste an. Um eine **vorhandene**
Liste im Sammelauftrag zu ändern (z.B. allen Verben den 2. Stamm
nachtragen oder die Notizen einer ganzen Kapitelliste überarbeiten),
gibt es im Listen-Menü **„Liste aktualisieren…“**:

1. Liste **exportieren** — dabei die Spalte **„ID“** ankreuzen
   (JSON schreibt sie immer mit). Sie ist der Schlüssel zur Karte.
2. Die Datei außerhalb der App bearbeiten — Tabellenprogramm,
   Editor oder Chatbot. **Nur die Spalten mitgeben, die sich ändern
   sollen**; die ID-Spalte muss bleiben.
3. Über „Liste aktualisieren…“ die Datei wählen oder den Text
   einfügen. Die App meldet danach, wie viele Karten aktualisiert bzw.
   neu angelegt wurden.

Regeln beim Aktualisieren:

- Zugeordnet wird **über die ID** — ohne ID-Spalte bricht der Vorgang
  mit einem Hinweis ab (sonst entstünden Dubletten).
- Angefasst werden **nur die Spalten der Datei**. Alles andere bleibt
  unverändert — auch der Lernstand.
- Eine **leere Zelle löscht** den Wert dieser Spalte (so lassen sich
  Notizen gezielt leeren). Ausnahme: leeres `front`/`back` wird
  ignoriert, sonst wäre die Karte kaputt.
- Zeilen mit **unbekannter oder fehlender ID** werden als neue Karten
  angehängt (nur mit `front` und `back`).
- **Gelöscht wird nie**: Karten, die in der Datei fehlen, bleiben in
  der Liste.
- **Buchlisten** sind nicht editierbar — dort heißt der Menüpunkt
  „Notizen aktualisieren…“ und akzeptiert nur die Spalten `hints_gr`,
  `hints_de`, `notes_gr`, `notes_de`. Sie landen wie im Notiz-Dialog
  als Overlay neben der Buchliste.

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

- **Lautsprecher-Symbol** (an jeder Karte, im Training, in der
  Textanalyse): **kurz antippen** spielt ab, **lang drücken oder
  zweimal tippen** schaltet den **Langsam-Modus** um — danach spielt
  jedes Antippen überall langsam (zum Nachsprechen), bis wieder
  umgeschaltet wird. Das Symbol wird dabei zur Schildkröte 🐢, und
  eine kurze Meldung bestätigt das Umschalten; beim App-Start ist das
  Tempo wieder normal. Das Zeitfenster für den Doppeltipp lässt sich
  in den Einstellungen ändern. Im Vokabeltraining erscheint der
  Lautsprecher unter der Karte erst, wenn die griechische Seite
  sichtbar ist, damit die Antwort nicht verraten wird.
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

## Backup (Sichern & Gerätewechsel)

Unter **Einstellungen → Backup** lassen sich die eigenen Daten als
**eine ZIP-Datei** sichern und wiederherstellen — für Sicherungskopien
und den Umzug auf ein neues Gerät.

Beim **Erstellen** wählst du, was in die Datei soll:

- **Vokabeln & Auswahllisten** (eigene Listen, Auswahllisten,
  Reihenfolge, Anmerkungen)
- **Lernfortschritt** (Leitner-Boxen und Zähler — nur zusammen mit den
  Vokabeln wählbar, denn der Fortschritt hängt an den Karten)
- **Notizen**, **Textanalysen**, **Lexikon**, **Einstellungen**

Heruntergeladenes Audio ist nie enthalten — es wird bei Bedarf einfach
neu geladen (bzw. über „Audio vorbereiten“ im Listenmenü).

Beim **Wiederherstellen** zeigt die App vorher an, welche Bereiche die
Datei enthält: genau diese Bereiche werden auf dem Gerät **ersetzt**
(nicht zusammengeführt — das lässt sich nicht rückgängig machen);
alle nicht enthaltenen Bereiche bleiben unverändert. Ein Neustart ist
nicht nötig.

Das Backup ersetzt auch den früheren Statistik-Export: Der Lernstand
steckt vollständig in der Kategorie „Lernfortschritt“.

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

Diese Obergrenzen sind einstellbar (Zahnrad → Abfrage → „Beschränkung
durch die Abfragemodi“) — drei Schalter: „Box 4 und 5 nur über
Deutsch → Griechisch“, „Box 5 nur über Deutsch → Griechisch mit
Schreiben“ und **„Box 5 nur über das Beugungstraining“**. Ist der
dritte Schalter an, rücken alle übrigen Obergrenzen eine Box nach
unten: Griechisch → Deutsch höchstens **Box 2**, Deutsch → Griechisch
als Karteikarte **Box 3**, Deutsch → Griechisch getippt **Box 4** —
**Box 5** erreicht nur noch das Nomen-/Adjektiv-/Verbtraining mit
Vorgabe Deutsch.

Über das Papierkorb-Symbol in der Statistik-Ansicht lässt sich der
Lernstand einer Liste komplett auf null zurücksetzen; die Karten gelten
danach wieder als neu.

Die Wartezeit bis zur nächsten Fälligkeit hängt von der Box ab:
Box 1 = sofort, Box 2 = 1 Tag, Box 3 = 3 Tage, Box 4 = 7 Tage,
Box 5 = 30 Tage. Beim Start einer Trainingsrunde werden **überfällige
Karten zuerst** gezogen, dann neue (noch nie trainierte), dann der Rest.
Innerhalb des Restes rücken Wörter, die **heute schon** beantwortet
wurden, ans Ende — so kommt bei mehreren Runden am selben Tag erst
einmal alles andere dran.

**Das gilt in allen Trainings gleich**, auch im Nomen-, Adjektiv- und
Verbtraining: Gezogen werden dort zuerst die *Wörter* nach ihrem
Lernstand, und je Wort kommt zunächst nur **eine** Form in die Runde.
Erst wenn zu wenige Wörter übrig sind, werden weitere Formen desselben
Worts nachgelegt. Im Adjektivtraining zählt die schwächere der beiden
Karten (Adjektiv oder Nomen).

**Boxen abwählen:** Auf jeder Trainings-Startseite gibt es eine Zeile
mit den farbigen Box-Symbolen (1–5 und „neu“). Abgeschaltete Boxen
kommen gar nicht erst in die Runde — praktisch, um die gekonnten
Wörter (Box 4/5) auszuklammern und nur das Wackelige zu üben. Es lässt
sich auch alles bis auf Box 5 abwählen; bleibt dann kein Wort übrig,
sagt das die Startseite und es kommt keine Runde zustande.

In der Statistik-Ansicht gilt eine Karte als „sicher“, wenn sie in
Box 4 oder 5 liegt. Die „Problemwörter“ sind die Karten mit den meisten
falschen Antworten. Erreicht eine Karte **Box 5**, wird ihr
Fehlerzähler gelöscht — sie gilt als gelernt und verschwindet aus den
Problemwörtern (erst ein neuer Fehler zählt wieder).

### Was zählt in die Statistik — und was nicht?

- **Vokabeltraining**: Jede Antwort der ersten Runde zählt (richtig oder
  falsch). Die optionale **Fehlerrunde** am Ende zählt nicht noch einmal —
  sie dient nur dem Wiederholen. Ausnahme: In den Einstellungen lässt
  sich unter „Fehlerrunde“ wählen, wohin ein dort **richtig**
  beantwortetes Wort wandert (Leichtsinnsfehler werden so weniger hart
  bestraft). Vier Stufen: keine Verbesserung (Wort bleibt in Box 1),
  Box 2, zurück in die ursprüngliche Box, oder eine Box unter der
  ursprünglichen — mindestens Box 2 (Standard). Falsche Antworten in
  der Fehlerrunde bleiben immer folgenlos.
  - Im Tipp-Modus zählt „Fast!“ (nur Akzent-/Schluss-ς-Fehler) als richtig.
  - Im Karteikarten-Modus zählt die Selbstbewertung („Gewusst“ /
    „Nicht gewusst“).
- **Beugungstraining (Nomen, Adjektive, Verben)**: Hier kommt es auf
  die eingestellte **Vorgabe** an:
  - Vorgabe **Griechisch** (die Nominativphrase bzw. das Lemma wird
    angezeigt): Das ist reines Formentraining — es fließt **nicht** in
    die Vokabelstatistik ein.
  - Vorgabe **Deutsch** (nur die deutsche Bedeutung wird angezeigt):
    Wer hier richtig beugt, hat die Vokabel zugleich aktiv gewusst. Es
    gilt die **volle Wertung wie im Vokabeltraining**: richtig = Box
    steigt (bis Box 5), **falsch = Karte fällt zurück in Box 1**. Die
    Fehlerrunde am Ende zählt auch hier nicht — für ein dort richtig
    beantwortetes Wort gilt dieselbe „Fehlerrunde“-Einstellung wie im
    Vokabeltraining (Standard: eine Box unter der ursprünglichen,
    mindestens Box 2).
  - Im **Adjektivtraining** wandern **Adjektiv- und Nomenkarte
    gemeinsam**: Eine richtige Antwort befördert beide, eine falsche
    setzt beide zurück.

Deklinations- und Konjugationsrunden zeigen am Ende zusätzlich ihr eigenes
Rundenergebnis (x von y richtig); das ist unabhängig von der dauerhaften
Vokabelstatistik.

**Statistik je Training abschalten:** Unter Zahnrad → Abfrage →
**„Statistik einschalten für“** lässt sich für jedes Training einzeln
(Vokabel-, Nomen-, Adjektiv-, Verbtraining) festlegen, ob es den
Lernstand überhaupt bewegen darf. Ist ein Training aus, fällt es
komplett aus der Statistik: keine Box rauf oder runter, keine
Fehlerzähler, auch keine Boxen-Punkte in der Ergebnisliste. Die
Auswahl der Wörter richtet sich weiterhin nach den Boxen — man übt
also normal weiter, nur ohne Folgen für den Lernstand.

In der Ergebnisliste nach jeder Runde stehen **✗ und ✓ einmal in der
Überschrift** der jeweiligen Gruppe („Falsche Karten:“ / „Richtig:“) —
nicht mehr vor jedem einzelnen Wort. Vor den Wörtern bleibt (falls
eingeschaltet) nur der zweigeteilte Boxen-Punkt.

### Statistik sichern

Den kompletten Lernstand sicherst du über **Einstellungen → Backup**
(Kategorie „Lernfortschritt“, zusammen mit den Vokabeln) — siehe das
Kapitel „Backup“. Einen separaten Statistik-Export gibt es nicht mehr.
