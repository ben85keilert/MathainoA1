"""Hilfeseite: Trainingsbereiche, Wertung, Leitner-Boxen, Listen, Prompts.

Erreichbar über das ?-Symbol oben rechts in der App-Leiste; die Kapitel
sind Kacheln, die jeweils eine eigene Seite öffnen. Die Texte müssen mit
der Logik in logic/answer_check.py, models.py und storage/content.py
übereinstimmen — bei Änderungen dort bitte hier nachziehen.
"""

from __future__ import annotations

from importlib import metadata

import flet as ft

from mathainoa1 import APP_NAME, __version__
from mathainoa1.ui.updates import manual_check
from mathainoa1.storage import content
from mathainoa1.storage.content import csv_fields_for, verb_fields_for
from mathainoa1.storage.settings import load_app_settings
from mathainoa1.ui.scale import sz

# Beispielzeilen der Import-CSV (je Worttyp; regelmäßige Wörter brauchen
# keine forms). Ausgegeben werden nur die Spalten der aktiven Stufe —
# Beispiele, die auf der Stufe kein Stoff sind (level="A2"), entfallen.
_EXAMPLE_ROWS: list[dict] = [
    {"front": "ο δρόμος", "back": "Straße", "plural": "-οι", "article": "ο",
     "word_type": "Nomen"},
    {"front": "η γυναίκα", "back": "Frau", "plural": "-ες", "article": "η",
     "word_type": "Nomen", "forms": "gen_pl=γυναικών"},
    {"front": "ο βράχος", "back": "Felsen", "plural": "τα βράχια",
     "article": "ο", "word_type": "Nomen", "level": "A2"},
    {"front": "γράφω", "back": "schreiben", "word_type": "Verb",
     "stem2": "γράψ-", "aorist": "έγραψα", "imperative": "Γράψε!",
     "aorist_passive": "γραφτ-", "participle": "γραμμένος"},
    {"front": "κοιμάμαι", "back": "schlafen", "word_type": "Verb",
     "stem2": "κοιμηθ-", "aorist": "κοιμήθηκα", "imperative": "Κοιμήσου!"},
    {"front": "βλέπω", "back": "sehen", "word_type": "Verb",
     "stem2": "δω, δεις, δει, δούμε, δείτε, δουν/δούνε", "aorist": "είδα",
     "imperative": "Δες!"},
    {"front": "πάω", "back": "gehen", "word_type": "Verb",
     "forms": "1sg=πάω; 2sg=πας; 3sg=πάει; 1pl=πάμε; 2pl=πάτε; 3pl=πάνε",
     "stem2": "πάω, πας, πάει, πάμε, πάτε, πάνε", "aorist": "πήγα",
     "imperative": "Πήγαινε!"},
    {"front": "ήρθα", "back": "ich bin gekommen", "word_type": "Verb",
     "hints_gr": "Aorist von έρχομαι", "level": "A2"},
    {"front": "μικρός", "back": "klein", "word_type": "Adjektiv"},
    {"front": "γλυκός", "back": "süß", "word_type": "Adjektiv",
     "forms": "fem=γλυκιά"},
    {"front": "βαρύς", "back": "schwer", "word_type": "Adjektiv",
     "level": "A2"},
    {"front": "εδώ", "back": "hier", "word_type": "Adverb"},
    {"front": "από", "back": "von, aus", "word_type": "Präposition",
     "hints_de": "mit Akk."},
    {"front": "Τι κάνεις;", "back": "Wie geht's?", "word_type": "Phrase",
     "notes_de": "per du"},
    {"front": "πέντε", "back": "fünf", "word_type": "Zahl"},
    {"front": "και", "back": "und, auch", "word_type": "Sonstiges"},
]


def _example_lines(level: str, fields: list[str]) -> str:
    """Beispielzeilen mit genau den Spalten der Stufe (Werte in
    Anführungszeichen, leere Spalten leer)."""
    lines = []
    for row in _EXAMPLE_ROWS:
        if row.get("level") == "A2" and level == "A1":
            continue
        values = [row.get(f, "") for f in fields]
        lines.append(",".join(f'"{v}"' if v else "" for v in values))
    return "\n".join(lines)


def _verb_rules(level: str, first: int) -> list[str]:
    """Spaltenregeln der Verbfelder, die auf der Stufe Stoff sind."""
    fields = verb_fields_for(level)
    rules = [f"""\
{first}. stem2: der 2. Stamm (für θα/να) — bei JEDEM Verb angeben, das
    einen hat (ohne ihn kein Futur-Training):
    - regelmäßig ein Stamm mit Bindestrich; die Betonung entscheidet
      über die Endungen: "γράψ-" → θα γράψω, aber unbetont
      "κοιμηθ-" → θα κοιμηθώ (endbetont).
    - unregelmäßig stattdessen die 6 Personenformen kommagetrennt,
      z.B. für βλέπω: "δω, δεις, δει, δούμε, δείτε, δουν/δούνε".
    - weglassen nur, wenn der Futurstamm dem Präsens entspricht und
      unbekannt ist, oder bei Fixformen (κοστίζει, θα δούμε)."""]
    n = first + 1
    if "aorist" in fields:
        rules.append(f"""\
{n}. aorist: der Aorist (Vergangenheit) — bei JEDEM Verb angeben, das
    einen hat (ohne ihn kein Aorist-Training). Die 1. Person Singular
    genügt: "έγραψα", "ήρθα", "κοιμήθηκα" — die App bildet die übrigen
    Personen selbst (auch bei ήμουν, ήθελα, ήξερα, ήπια). Zwei Aoriste
    mit "/" ("έκατσα/κάθισα"). Nur wenn Formen vom Muster abweichen,
    alle 6 Personenformen kommagetrennt (1sg, 2sg, 3sg, 1pl, 2pl, 3pl).
    Steht eine Verbliste dabei, ihre Formen übernehmen.""")
        n += 1
    if "imperative" in fields:
        rules.append(f"""\
{n}. imperative: der Imperativ (einmalig) in der 2. Person Singular,
    geschrieben wie in der Verbliste: "Γράψε!", "Έλα!", "Άκου(σε)!"
    (runde Klammern = optionaler Teil), zwei Formen mit "/"
    ("Κάτσε!/Κάθισε!"). Leer lassen, wenn er nicht gebräuchlich ist
    (z.B. bei μπορώ, ξέρω, πρέπει).""")
        n += 1
    if "aorist_passive" in fields or "participle" in fields:
        rules.append(f"""\
{n}. aorist_passive: der Aorist Passiv (3. Stamm) im gleichen Format wie
    stem2 — angeben, wenn bekannt (nicht aus dem Aktiv berechenbar).
    participle: das Perfekt-Partizip nur bei unregelmäßiger Form
    (z.B. γραμμένος). Beide Spalten sonst leer lassen.""")
        n += 1
    if "aorist" in fields:
        rules.append(f"""\
{n}. Schreibweise im Lehrbuch (Pame A2): Verben stehen dort mit dem
    2. Stamm hinter dem Komma — "πιστεύω, -έψω", "φεύγω, φύγω",
    "παντρεύομαι, -ευτώ". front ist nur die Präsensform; der 2. Stamm
    gehört nach stem2 ("πιστέψ-", "φύγ-", "παντρευτ-"). Die angehängte
    Endung ersetzt den hervorgehobenen Teil: "περνάω, -άσω" →
    "περάσ-". Zusätze wie "(-είς)" (μπορώ (-είς)) weglassen; zweite
    Präsensform ("πάω (πηγαίνω)") in hints_gr ("auch: πηγαίνω").
    Vergangenheitsformen als eigene Einträge ("ήρθα (von έρχομαι)"):
    front = nur die Form, word_type Verb, hints_gr "Aorist von
    έρχομαι".""")
    return rules


def csv_format_rules(level: str) -> str:
    """Gemeinsamer Teil beider Chatbot-Prompts: Ausgabeformat,
    Spaltenregeln und Beispielzeilen der Import-CSV — mit den Spalten
    und Regeln der Stufe (content.csv_fields_for)."""
    fields = csv_fields_for(level)
    verb_rules = "\n".join(_verb_rules(level, 11))
    return f"""\
AUSGABEFORMAT
Eine CSV-Datei: UTF-8, Komma-getrennt, alle Werte in doppelten
Anführungszeichen, mit genau dieser Kopfzeile:

{",".join(fields)}

Gib nur die CSV aus, keinen weiteren Text. Spalten ohne Angabe leer lassen.

REGELN FÜR DIE SPALTEN
1. front = Griechisch (bei Nomen mit Artikel, z.B. "ο δρόμος"),
   back = Deutsch. Beide Pflicht — sonst die Zeile weglassen.
2. article: ο/η/το/οι/τα (nur bei Nomen).
3. word_type: Nomen, Verb, Adjektiv, Adverb, Präposition, Phrase,
   Zahl oder Sonstiges.
4. plural: Pluralendung oder -form, z.B. "-οι" (nur zur Anzeige).
   Wechselt das Genus im Plural, die komplette Form MIT Artikel
   ("ο βράχος" → "τα βράχια"). Adjektive: front nur in der männlichen
   Form ("μικρός", nicht "μικρός, -ή, -ό").
5. Griechische Alternativformen mit " / " trennen, z.B. "και / κι" oder
   "τρεις / τρία" — jede Form zählt bei der Abfrage als richtig.
6. Optionale Wortteile in runde Klammern: Verben auf -άω als "αγαπ(ά)ω"
   (akzeptiert αγαπάω und αγαπώ); Zusätze wie "η λαϊκή (αγορά)" oder
   "(Visiten-)Karte" (ein Bindestrich am Klammerrand verbindet).
   Klammern MIT Satzzeichen sind reine Zusatzinfo und werden bei der
   Abfrage ignoriert, z.B. "Sie (Akk.)".
7. Deutsche Alternativen mit Komma oder "/" trennen ("und, auch").
8. Muss innerhalb eines Satzes genau EINE von mehreren Varianten
   genannt werden, eckige Klammern verwenden — auf beiden Seiten:
   "Ich spreche [nicht/kein] Chinesisch." akzeptiert beide Sätze,
   "Πώς [είσαι/είστε];" ebenso. KEIN nacktes "a / b" mitten im Satz
   (das würde als zwei Komplett-Alternativen gewertet).
9. Vier Notiz-Spalten, nur kurze Lernhilfen (keine Buchseiten oder
   Übungsnummern): hints_gr/notes_gr erscheinen, wenn die griechische
   Seite abgefragt wird, hints_de/notes_de bei der deutschen. hints =
   Gebrauchshinweis zum Wort (z.B. "mit Akk.", "nur Plural"), notes =
   Zusatznotiz (z.B. "per du", "wörtl.: …").
10. forms nur bei Unregelmäßigkeit: "schlüssel=form; …" mit den
   Schlüsseln acc_sg, gen_sg, nom_pl, acc_pl, gen_pl, fem, 1sg…3pl
   (z.B. "gen_pl=γυναικών") — Formen ohne Artikel eintragen.
{verb_rules}

BEISPIELZEILEN (je Worttyp; regelmäßige Wörter brauchen keine forms —
jede Zeile hat alle {len(fields)} Spalten)
{_example_lines(level, fields)}
"""


def chatbot_prompt(level: str) -> str:
    """Prompt 1 — Wortlisten-Prompt: fertige Vokabellisten (Grundformen)
    für die aktive Stufe (AppSettings.level) — Spalten und Regeln müssen
    zur Stufe passen (siehe features.py)."""
    return f"""\
AUFGABE
Du bekommst eine Liste griechischer Vokabeln (Grundformen) mit
deutschen Bedeutungen — als Foto oder als Text. Erstelle daraus eine
Import-CSV für eine Griechisch-Lern-App (Niveau {level}).

{csv_format_rules(level)}"""


def text_prompt(level: str) -> str:
    """Prompt 2 — Lesetext-Prompt: beliebige griechische Texte, Wörter
    stehen dort gebeugt und müssen auf die Grundform zurückgeführt werden."""
    return f"""\
AUFGABE
Du bekommst einen griechischen Text — z.B. einen abfotografierten
Zeitungsausschnitt, eine Buchseite oder ein Schild. Die Wörter stehen
dort in gebeugten Formen. Erstelle daraus eine Vokabel-CSV für eine
Griechisch-Lern-App (Niveau {level}): jedes Wort in seiner Grundform.

ZURÜCKFÜHREN AUF DIE GRUNDFORM
- Nomen → Nominativ Singular mit Artikel (z.B. τους δρόμους →
  "ο δρόμος"); reine Pluralwörter → Nominativ Plural mit οι/τα.
- Verben → 1. Person Singular Präsens (z.B. έγραψε → "γράφω").
- Adjektive → Maskulinum Nominativ Singular (z.B. μικρή → "μικρός").
- Jede Grundform nur einmal aufnehmen, auch wenn sie mehrfach vorkommt.
- Die deutsche Bedeutung so wählen, wie das Wort im Text gebraucht wird.
- Weglassen: Eigennamen (Personen, Orte, Marken), Zahlen in Ziffern,
  Artikel, Pronomen und Partikeln wie να/θα/δεν.
- Unleserliche oder unsichere Wörter weglassen statt zu raten.

{csv_format_rules(level)}"""


def _p(text: str) -> ft.Text:
    return ft.Text(text, size=sz(14))


def _bullets(items: list[str]) -> ft.Column:
    return ft.Column(
        [ft.Row([ft.Text("•", size=sz(14)), ft.Text(t, size=sz(14), expand=True)],
                spacing=6, vertical_alignment=ft.CrossAxisAlignment.START)
         for t in items],
        spacing=6,
    )


def _chapter(nav, title: str, icon: str,
             controls: list[ft.Control]) -> ft.Control:
    """Kapitel-Kachel: öffnet den Inhalt als eigene Seite (statt Aufklappen)."""
    return ft.Card(content=ft.ListTile(
        leading=ft.Icon(icon, color=ft.Colors.PRIMARY),
        title=ft.Text(title, size=sz(15), weight=ft.FontWeight.BOLD),
        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
        on_click=lambda e: nav.go(title, ft.Column(
            list(controls), spacing=10, scroll=ft.ScrollMode.AUTO)),
    ))


def help_view(nav, store=None) -> ft.Control:
    # Prompts, Spalten und Stufen-Texte richten sich nach der aktiven Stufe
    level = load_app_settings().level
    clipboard = ft.Clipboard()
    nav.page.services.append(clipboard)

    def add_example_list(e):
        if store is None:
            return
        existing = next((l for l in store.lists.values()
                         if l.name == content.EXAMPLE_LIST_NAME), None)
        if existing is not None:
            nav.page.show_dialog(ft.SnackBar(
                ft.Text("Beispielliste ist schon vorhanden.")))
            return
        vlist = content.example_vocab_list()
        store.save_user_list(vlist)
        nav.page.show_dialog(ft.SnackBar(ft.Text(
            "Beispielliste hinzugefügt — in der Vokabelverwaltung "
            "zu finden (dort auch exportierbar).")))

    def copy_text(text: str):
        async def do():
            await clipboard.set(text)
        nav.page.run_task(do)

    def open_prompt_dialog(title: str, text: str):
        def handler(e):
            def copy(e):
                copy_text(text)
                nav.page.pop_dialog()
                nav.page.show_dialog(ft.SnackBar(ft.Text("Prompt kopiert.")))
            nav.page.show_dialog(ft.AlertDialog(
                title=ft.Text(title, size=sz(16)),
                content=ft.Column(
                    [ft.Text(text, size=sz(12), selectable=True)],
                    scroll=ft.ScrollMode.AUTO, width=420, height=440,
                ),
                actions=[
                    ft.TextButton("Kopieren", icon=ft.Icons.COPY, on_click=copy),
                    ft.TextButton("Schließen",
                                  on_click=lambda e: nav.page.pop_dialog()),
                ],
            ))
        return handler

    trainings = _chapter(nav, "Trainingsbereiche", ft.Icons.SCHOOL_OUTLINED, [
        ft.Text("Vokabeltraining", size=sz(14), weight=ft.FontWeight.BOLD),
        _bullets([
            "Karteikarte (Selbstbewertung) oder Schreiben (Tippen), "
            "gefiltert nach Liste und Worttyp.",
            "Richtungen: Griechisch → Deutsch ist Wiedererkennen "
            "(leichter), Deutsch → Griechisch ist aktives Erinnern — nur "
            "das bringt eine Karte in die hohen Boxen (siehe "
            "Leitner-Boxen).",
        ]),
        ft.Text("Nomentraining", size=sz(14), weight=ft.FontWeight.BOLD),
        _bullets([
            "Setzt Nomen (mit Artikel) in andere Formen — regelbasiert "
            "aus den Vokabelkarten, ohne eigene Formenlisten.",
            "Nominativ (Pl.): fragt die Pluralform ab (ο δρόμος → οι "
            "δρόμοι). Der Nominativ Singular wird nie abgefragt — er "
            "steht ja schon in der Aufgabe. Damit lässt sich gezielt "
            "der Plural üben; standardmäßig ausgeschaltet.",
            "Akkusativ: der wichtigste Fall für A1 — nach σε, από, με, "
            "για … und für das direkte Objekt.",
            "Genitiv: für Besitz und Mengenangaben (του, της, των).",
        ]),
        ft.Text("Adjektivtraining", size=sz(14), weight=ft.FontWeight.BOLD),
        _bullets([
            "Dekliniert Adjektiv + Nomen zusammen (ο μικρός δρόμος → "
            "τους μικρούς δρόμους) — Adjektive auf -ος, ab A2 auch auf "
            "-ύς (βαρύς, βαριά, βαρύ) sowie πολύς.",
            "Whitelisting (Standard): nur selbst festgelegte Adjektiv↔"
            "Nomen-Verbindungen werden abgefragt („Verbindungen "
            "festlegen…“). Blacklisting (umschaltbar in den "
            "Einstellungen): alle Kombinationen außer den festgelegten "
            "Ausnahmen — Nomen kommen aus der gewählten Liste, ohne "
            "eigene Nomen aus allen Listen.",
            "Im Festlegen-Dialog stehen nur die Adjektive der gerade "
            "gewählten Liste zur Auswahl; Verbindungen und Ausnahmen "
            "gelten listenübergreifend.",
            "Adjektiv-Listen lassen sich im Adjektivtraining und in der "
            "Listenverwaltung anlegen und bearbeiten.",
        ]),
        ft.Text("Verbtraining", size=sz(14), weight=ft.FontWeight.BOLD),
        _bullets([
            "Vom deutschen Infinitiv zur konjugierten Form; Personen "
            "und Singular/Plural wählbar.",
            "Präsens und Futur (θα + 2. Stamm) — Futur nur für Verben, "
            "bei denen der 2. Stamm eingetragen ist.",
            "Ab Stufe A2 zusätzlich Aorist (Vergangenheit) und Imperativ: "
            "der Aorist für Verben mit Eintrag im Feld „Aorist“ (die "
            "1. Person genügt, z.B. „έγραψα“ — den Rest bildet die App), "
            "der Imperativ als 2. Person Singular wie in der Verbliste "
            "(„Γράψε!“) — er ist eine Aufgabe je Verb, unabhängig von der "
            "Personen-/Zahl-Auswahl.",
        ]),
        _p("Alle drei Bereiche arbeiten auf denselben Vokabel- und "
           "Auswahllisten; regelmäßige Formen entstehen automatisch, "
           "Unregelmäßiges kommt aus den Zusatzfeldern der Karten."),
        ft.Text("Startseiten & weitere Optionen", size=sz(14),
                weight=ft.FontWeight.BOLD),
        _bullets([
            "Auf allen Startseiten stehen die selteneren Optionen "
            "kompakt unter den Start-Buttons („Weitere Optionen“). "
            "Antippen öffnet einen Dialog — Änderungen dort werden "
            "sofort gespeichert, nicht erst beim Trainingsstart.",
            "„Fehler am Ende wiederholen“: falsche Antworten kommen "
            "direkt nach der Hauptrunde noch einmal dran (Fehlerrunde, "
            "zählt nicht in die Statistik).",
            "„Fehler in nächster Runde wiederholen“: die Fehler der "
            "Hauptrunde sind bei „Neue Runde“ bzw. beim nächsten Start "
            "derselben Liste garantiert wieder dabei, aufgefüllt mit "
            "neuen Wörtern. Im Vokabeltraining gilt das bis zum "
            "App-Neustart — danach sorgt ohnehin Box 1 dafür, dass die "
            "Fehler sofort wieder fällig sind.",
        ]),
    ])

    symbole = _chapter(nav, "Symbole in Training & Listen",
                       ft.Icons.INFO_OUTLINE, [
        _p("Unter der Karte in der Abfrage — und am Rand vieler "
           "Listenzeilen — stehen bis zu drei Symbole:"),
        _bullets([
            "Lautsprecher: liest das griechische Wort vor. Langes Drücken "
            "(oder Doppeltipp) schaltet den app-weiten Langsam-Modus zum "
            "Nachsprechen um — mehr dazu im Kapitel „Audio“.",
            "Wort-Symbol für Beugungsformen und Wort-Info — ein Button, "
            "drei Gesichter: Gibt es beides, zeigt das ⓘ-Symbol einen "
            "Dialog mit dem Lexikoneintrag oben und der Beugungstabelle "
            "darunter (durch einen Querbalken getrennt). Gibt es nur die "
            "Beugungsformen (Deklination bei Nomen/Adjektiven, "
            "Konjugation bei Verben), erscheint das Tabellen-Symbol; gibt "
            "es nur den Lexikoneintrag (Wortherkunft & Synonyme, Teil der "
            "erweiterten Funktion „Textanalyse“), das Buch-Symbol.",
            "Stift: öffnet den Notiz-Dialog für Hinweise/Notizen — "
            "„Alles bearbeiten“ springt von dort in die vollständige "
            "Kartenbearbeitung (nicht bei Buchlisten).",
        ]),
        _p("Das Wort-Symbol erscheint auch in Wortlisten, in der "
           "Wortsuche, in den Vorschauen der Trainings, in den "
           "Ergebnislisten und bei den Problemwörtern der Statistik."),
        _p("Spoilerschutz bei Deutsch → Griechisch: Solange die "
           "griechische Seite noch verdeckt ist, bleiben Lautsprecher "
           "und Beugungstabelle gesperrt — sie würden sonst die Lösung "
           "verraten."),
    ])

    wertung = _chapter(nav, "Wertung", ft.Icons.RULE, [
        _bullets([
            "Groß-/Kleinschreibung und mehrfache Leerzeichen sind egal — "
            "außer wenn „Groß-/Kleinschreibung tolerieren“ aus ist (siehe "
            "unten).",
            "Satzzeichen am Anfang/Ende (z.B. ; · ! ? . , …) sind egal.",
            "Kommas zählen nie als Fehler — auch mitten im Satz: "
            "„Γεια σου, τι κάνεις;“ und „Γεια σου τι κάνεις“ sind "
            "gleichwertig. Genauso egal: Auslassungspunkte („δεν ... "
            "άλλο“), Apostrophe („geht's“ = „gehts“) und ein Bindestrich "
            "am Wortrand („Kinder-“ = „Kinder“).",
            "Wortteile in Klammern sind optional: bei „αγαπ(ά)ω“ zählen "
            "αγαπάω und αγαπώ als richtig; bei „(Visiten-)Karte“ zählen "
            "Visitenkarte und Karte (ein Bindestrich am Klammerrand "
            "verbindet). Klammern mit Satzzeichen sind reine Zusatzinfo "
            "(z.B. „Sie (Akk.)“).",
            "Steht auf einer Karte „A / B“ (z.B. „και / κι“), zählt jede "
            "der Alternativen als richtig — auf beiden Sprachseiten.",
            "Eckige Klammern im Satz: genau eine Variante muss genannt "
            "werden — „Ich spreche [nicht/kein] Chinesisch.“ akzeptiert "
            "beide vollständigen Sätze, „Πώς [είσαι/είστε];“ ebenso. "
            "Das gilt auf beiden Sprachseiten, auch mit mehr als zwei "
            "Varianten („[α/β/γ]“) und mit mehreren Gruppen im selben "
            "Satz. Weglassen der Stelle zählt als Fehler — anders als "
            "bei runden Klammern ist die Angabe Pflicht.",
            "Griechisch: fehlende oder falsche Akzente und ein falsches "
            "Schluss-ς ergeben „Fast!“. Mit „Akzentfehler tolerieren“ zählt "
            "das als richtig.",
            "Deutsch: Enthält die Rückseite mehrere Bedeutungen (getrennt "
            "durch Komma, „/“ oder als eigene Sätze), genügt eine davon. "
            "Text in Klammern ist Zusatzinfo und muss nicht mitgetippt "
            "werden.",
            "Karteikarten-Modus: Die Selbstbewertung „Gewusst“/„Nicht "
            "gewusst“ zählt wie eine getippte Antwort.",
            "Die Fehlerrunde am Ende zählt nie in die Statistik — sie "
            "dient nur dem Wiederholen. In den Einstellungen (Zahnrad) "
            "lässt sich aber wählen, wohin ein dort richtig beantwortetes "
            "Wort wandert: Box 1 (keine Verbesserung), Box 2, die "
            "ursprüngliche Box oder eine Box darunter — mindestens "
            "Box 2 (Standard). Dieselbe Regel gilt auch in den "
            "Fehlerrunden des Nomen-/Adjektiv-/Verbtrainings mit "
            "Vorgabe Deutsch. Für Akzent- und Schreibungsfehler in der "
            "Fehlerrunde gilt die eigene Einstellung „Akzent- und "
            "Schreibungsfehler“ (siehe unten).",
        ]),
        ft.Text("Akzent- und Groß-/Kleinschreibung tolerieren", size=sz(14),
                weight=ft.FontWeight.BOLD),
        _bullets([
            "Beide Schalter (Vokabel- und Deklinationstraining) wirken "
            "gleich: ist der Schalter AN, wird der jeweilige Fehler "
            "verziehen und die Antwort zählt als richtig.",
            "Ist der Schalter AUS, ist eine sonst richtige Antwort mit "
            "nur diesem Fehler ein „Fast“: Sie zählt als Fehler der Runde "
            "und wird in dieser und der nächsten Runde wiederholt.",
            "Was dabei mit der Leitner-Box passiert, bestimmt die "
            "Einstellung Zahnrad → Abfrage → „Akzent- und "
            "Schreibungsfehler“ — getrennt für Akzent- und "
            "Schreibungsfehler, mit vier Stufen: Box zurücksetzen "
            "(Box 1, gilt auch in der Fehlerrunde), Box bleibt "
            "unverändert (Standard — dann ändert auch ein solcher "
            "Fehler in der Fehlerrunde nichts an der Box), in der "
            "Fehlerrunde wie richtig (Verschiebung nach der "
            "Fehlerrunden-Regel), oder in der Fehlerrunde eine Box "
            "zurück (mindestens Box 1).",
            "Ausnahme: Neue (graue) Wörter haben noch keine Box zu "
            "schützen — sie starten bei so einem Fehler ganz normal "
            "in Box 1.",
            "Groß-/Kleinschreibung wird nur bei Nomen geprüft (z.B. „η "
            "Αθήνα“, deutsch „Straße“), nie bei Phrasen oder anderen "
            "Worttypen.",
        ]),
    ])

    leitner = _chapter(nav, "Leitner-Boxen (Statistik)", ft.Icons.INSIGHTS, [
        _bullets([
            "Jede Karte wandert durch 5 Boxen: richtig = eine Box höher, "
            "falsch = zurück in Box 1.",
            "Wartezeit bis zur nächsten Abfrage: Box 1 sofort, Box 2 ein "
            "Tag, Box 3 drei Tage, Box 4 sieben Tage, Box 5 dreißig Tage.",
            "Wie hoch eine Karte steigen kann, hängt von der Abfrageart "
            "ab: Griechisch → Deutsch (Wiedererkennen) höchstens Box 3, "
            "Deutsch → Griechisch als Karteikarte höchstens Box 4, "
            "Deutsch → Griechisch getippt (schreiben können) bis Box 5. "
            "Diese Beschränkungen lassen sich in den Einstellungen "
            "(Zahnrad) abschalten.",
            "Zusätzlich einschaltbar: „Box 5 nur über das "
            "Beugungstraining“ — dann rücken alle Obergrenzen eine Box "
            "nach unten (Wiedererkennen Box 2, Karteikarte Box 3, "
            "Schreiben Box 4) und nur das Nomen-/Adjektiv-/Verbtraining "
            "mit Vorgabe Deutsch führt bis Box 5.",
            "Beugungstraining mit Vorgabe Deutsch wertet voll wie das "
            "Vokabeltraining: richtig = Box rauf, falsch = zurück in "
            "Box 1. Im Adjektivtraining wandern Adjektiv- und Nomenkarte "
            "gemeinsam. Mit Vorgabe Griechisch bleibt es reines "
            "Formentraining ohne Wirkung auf die Boxen.",
            "„Sicher“ ist eine Karte ab Box 4. Erreicht eine Karte "
            "Box 5, wird ihr Fehlerzähler gelöscht — sie verschwindet "
            "aus den Problemwörtern der Statistik.",
            "Die Fehlerrunde wiederholt falsche Karten sofort in der "
            "Reihenfolge der Fehler; in der nächsten Runde sind sie "
            "garantiert wieder dabei, gemischt zwischen den übrigen und "
            "neuen Wörtern. Falsche Antworten in der Fehlerrunde bleiben "
            "für die Box folgenlos — außer Akzent- und "
            "Schreibungsfehler, für die die Einstellung „Akzent- und "
            "Schreibungsfehler“ gilt (Kapitel „Wertung“).",
            "Die Ergebnisliste nach jeder Runde zeigt vor jedem Wort "
            "einen zweigeteilten Farbpunkt: die linke Hälfte ist die "
            "Box vor der Runde, die rechte die Box danach (grau = noch "
            "nicht trainiert; Farben wie in den Wortlisten). Das gilt "
            "für alle Trainings gleichermaßen und lässt sich in den "
            "Einstellungen (Zahnrad → Ergebnisliste) abschalten. Über "
            "den Stift daneben lassen sich falsche wie richtige Wörter "
            "direkt bearbeiten. ✗ und ✓ stehen einmal in der "
            "Überschrift der Gruppe, nicht vor jedem Wort.",
            "Wörter, die heute schon (richtig) beantwortet wurden, rücken "
            "bei der Auswahl ans Ende — sie kommen erst wieder dran, wenn "
            "fällige, neue und ältere Karten aufgebraucht sind. So blockieren "
            "frisch gekonnte Wörter nicht mehrere Runden am selben Tag.",
            "Nomen-, Adjektiv- und Verbtraining ziehen nach denselben "
            "Regeln: erst die Wörter nach Lernstand (fällige, dann neue, "
            "dann der Rest), je Wort zunächst nur eine Form. Erst wenn "
            "die Wörter ausgehen, kommen weitere Formen desselben Worts "
            "dazu; im Adjektivtraining zählt die schwächere der beiden "
            "Karten.",
            "Auf jeder Trainings-Startseite lassen sich einzelne Boxen "
            "abwählen (Zeile „Boxen“ mit den farbigen Symbolen 1–5 und "
            "„neu“) — abgewählte Wörter kommen gar nicht erst in die "
            "Runde. Bleibt nichts übrig, sagt das die Startseite.",
            "Statistik je Training abschaltbar (Zahnrad → Abfrage → "
            "„Statistik einschalten für“): Ist ein Training aus, bewegt "
            "es weder Boxen noch Fehlerzähler — geübt wird trotzdem "
            "normal, die Wortauswahl folgt weiter den Boxen.",
            "In der Statistik-Ansicht lässt sich der Lernstand einer "
            "Liste über das Papierkorb-Symbol auf null zurücksetzen.",
        ]),
    ])

    editing = _chapter(nav, "Wortlisten bearbeiten", ft.Icons.EDIT_NOTE, [
        _bullets([
            "Regelmäßige Wörter brauchen nur einen Eintrag (Grundform) — "
            "Deklination und Konjugation werden regelbasiert gebildet.",
            "Nomen: Artikel und Plural angeben; unregelmäßige Fälle "
            "(Akkusativ/Genitiv) nur bei Bedarf in die Zusatzfelder.",
            "Verben: Unregelmäßiges Präsens als 6 Formen mit Komma "
            "(1sg, 2sg, 3sg, 1pl, 2pl, 3pl), „-“ = regelmäßiger Slot, "
            "z.B. „πάω, πας, πάει, πάμε, πάτε, πάνε“.",
            "2. Stamm (Futur/να-Form): ein Stamm wie „γράψ-“ — oder bei "
            "Unregelmäßigkeit wieder 6 Formen mit Komma.",
            "Ab Stufe A2: Aorist als 1. Person Singular wie in der "
            "Verbliste („έγραψα“, „ήρθα“, „κοιμήθηκα“) — die übrigen "
            "Personen bildet die App; nur Abweichler als 6 Formen. "
            "Imperativ als 2. Person Singular („Γράψε!“, „Άκου(σε)!“, "
            "„Κάτσε!/Κάθισε!“).",
            "Mehrere richtige Formen mit „/“ trennen, z.B. "
            "„2pl=είστε/είσαστε“ oder „δουν/δούνε“.",
            "Komplette Alternativantworten: griechisch mit „ / “ trennen "
            "(„και / κι“), deutsch mit Komma oder „/“ („und, auch“) — "
            "jede Alternative zählt bei der Abfrage als richtig.",
            "Muss genau EINE von mehreren Varianten im Satz genannt "
            "werden, eckige Klammern verwenden — auf beiden Sprachseiten: "
            "„Ich spreche [nicht/kein] Chinesisch.“ akzeptiert beide "
            "Sätze, „Πώς [είσαι/είστε];“ ebenso; auch mit mehr als zwei "
            "Varianten („[α/β/γ]“). Kein nacktes „A / B“ mitten im Satz — "
            "das würde als zwei Komplettantworten gewertet.",
            "Optionale Wortteile in Klammern schreiben, z.B. „αγαπ(ά)ω“ "
            "oder „(Visiten-)Karte“ — mit und ohne Klammerinhalt zählt. "
            "Klammern mit Satzzeichen sind reine Zusatzinfo („Sie (Akk.)“).",
            "Aus der Abfrage heraus: Der Stift öffnet den Notiz-Dialog — "
            "„Alles bearbeiten“ springt von dort in die vollständige "
            "Kartenbearbeitung (nicht bei Buchlisten).",
            "Adjektive: nur ein unregelmäßiges Femininum eintragen "
            "(z.B. „γλυκιά“).",
            "Worttyp „Sonstiges“ zeigt im Editor alle Felder.",
        ]),
        ft.Text("Beispiele je Worttyp", size=sz(14), weight=ft.FontWeight.BOLD),
        _bullets([
            "Nomen, regelmäßig: „ο δρόμος“ – Straße, Plural „-οι“ — "
            "sonst nichts nötig.",
            "Nomen, unregelmäßig: „η γυναίκα“ – Frau, Plural „-ες“, dazu "
            "Genitiv Plural „γυναικών“ ins Zusatzfeld.",
            "Verb, regelmäßig: „γράφω“ – schreiben, 2. Stamm „γράψ-“ — "
            "Präsensfelder leer lassen; ab A2 dazu Aorist „έγραψα“ und "
            "Imperativ „Γράψε!“.",
            "Verb, unregelmäßig: „πάω“ – gehen, Präsens als 6 Formen: "
            "„πάω, πας, πάει, πάμε, πάτε, πάνε“.",
            "Adjektiv, regelmäßig: „μικρός“ – klein — sonst nichts nötig.",
            "Adjektiv, unregelmäßig: „γλυκός“ – süß, Femininum „γλυκιά“ "
            "ins Zusatzfeld.",
            "Adverb: „εδώ“ – hier (keine Formen nötig).",
            "Präposition: „από“ – von, aus.",
            "Phrase: „Τι κάνεις;“ – Wie geht's? (Notiz z.B. „per du“).",
            "Zahl: „πέντε“ – fünf.",
            "Sonstiges: „και“ – und, auch (für alles ohne passenden Typ).",
        ]),
        _p("Genau diese Beispiele gibt es als fertige Liste — sie ist "
           "standardmäßig nicht dabei. Einmal hinzufügen, dann in der "
           "Vokabelverwaltung ansehen, bearbeiten oder exportieren (zeigt "
           "das CSV-/JSON-Format)."),
        ft.Row([ft.OutlinedButton(
            "Beispielliste hinzufügen", icon=ft.Icons.PLAYLIST_ADD,
            on_click=add_example_list)]),
    ])

    prompts = _chapter(nav, "Prompts für neue Wortlisten", ft.Icons.SMART_TOY_OUTLINED, [
        _p("In der Vokabelverwaltung über „Importieren“ eine CSV- oder "
           "JSON-Datei wählen. Die CSV braucht eine Kopfzeile mit diesen "
           "Spalten (nur front und back sind Pflicht):"),
        ft.Container(
            ft.Text(",".join(csv_fields_for(level)), size=sz(12),
                    selectable=True, font_family="monospace"),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=8, padding=8,
        ),
        _p("Die Spalte forms nimmt unregelmäßige Formen als "
           "„schlüssel=form; …“ auf, z.B. „gen_pl=γυναικών; 2sg=πας“."),
        _p("Kann der Chatbot keine Datei speichern (bei CSV häufig), "
           "seine Antwort einfach kopieren und über „Als Text "
           "importieren“ in der Vokabelverwaltung einfügen — dort Namen "
           "vergeben, Text einfügen, fertig. CSV und JSON werden "
           "automatisch erkannt."),
        _p("Eine BESTEHENDE Liste ändert man dagegen über „Liste "
           "aktualisieren…“ im Listen-Menü: Liste mit der Spalte „ID“ "
           "exportieren, außerhalb im Sammelauftrag bearbeiten, wieder "
           "einlesen. Zugeordnet wird über die ID; angefasst werden nur "
           "die mitgelieferten Spalten (leere Zelle = Wert löschen), "
           "Zeilen ohne bekannte ID werden angehängt, gelöscht wird "
           "nichts. Bei Buchlisten sind so nur Hinweise und Notizen "
           "änderbar."),
        _p("Einen der beiden Prompts zusammen mit dem Foto (oder Text) an "
           "einen Chatbot geben — er liefert die fertige Import-CSV:"),
        _bullets([
            "Wortlisten-Prompt: für fertige Vokabellisten, deren Wörter "
            "schon in der Grundform stehen (z.B. Buch-Vokabelverzeichnis).",
            "Lesetext-Prompt: für beliebige griechische Texte (Zeitung, "
            "Buchseite, Schild) — der Chatbot führt die gebeugten Wörter "
            "auf ihre Grundform zurück.",
        ]),
        ft.Row(
            [
                ft.OutlinedButton(
                    "Wortlisten-Prompt", icon=ft.Icons.LIST_ALT,
                    on_click=open_prompt_dialog(
                        "Wortlisten-Prompt", chatbot_prompt(level))),
                ft.OutlinedButton(
                    "Lesetext-Prompt", icon=ft.Icons.NEWSPAPER,
                    on_click=open_prompt_dialog(
                        "Lesetext-Prompt", text_prompt(level))),
            ],
            wrap=True, spacing=8,
        ),
        _p("Mit den erweiterten Funktionen (Einstellungen → Erweiterte "
           "Funktionen) kommen zwei weitere Prompts dazu: "
           "Arbeitsanweisung III für komplette Textanalysen („Prompt "
           "kopieren“ in der Textanalyse-Ansicht) und Arbeitsanweisung IV "
           "für Etymologie-Pakete („Prompt kopieren“ im Lexikon)."),
    ])

    stufen = _chapter(nav, "Stufen & erweiterte Funktionen",
                      ft.Icons.TUNE, [
        ft.Text("Stufe (A1/A2)", size=sz(14), weight=ft.FontWeight.BOLD),
        _bullets([
            "In den Einstellungen umschaltbar; die Stufen sind strikt "
            "getrennt: A1 zeigt nur A1-Listen, A2 nur A2-Listen. Zum "
            "Üben alter A1-Listen auf A1 zurückschalten.",
            "Listen und Auswahllisten ohne Stufe sind auf jeder Stufe "
            "sichtbar. Neue eigene Listen und Auswahllisten erhalten "
            "beim Anlegen automatisch die aktive Stufe.",
            "Die Stufe lässt sich über „Umbenennen“ in der "
            "Vokabelverwaltung ändern — bei Listen wie bei "
            "Auswahllisten.",
            "Der Filter wirkt auch in der Wortsuche, den Ziellisten beim "
            "Verschieben/Kopieren und den Adjektiv-Kombinationen; die "
            "Inhalte einer geöffneten Auswahlliste werden nie gefiltert.",
            "Der Lernfortschritt hängt an der Karte und gilt "
            "stufenübergreifend.",
            "Jede Stufe zeigt nur ihren Stoff: A1 Präsens und Futur, A2 "
            "zusätzlich Aorist und Imperativ (Verbtraining, Karten-Editor, "
            "Prompts) sowie die Adjektive auf -ύς (βαρύς) und πολύς. "
            "Felder, die auf keiner Stufe Stoff sind (Aorist Passiv, "
            "Partizip), sind ausgeblendet — ihre Werte bleiben gespeichert.",
        ]),
        ft.Text("Zoom", size=sz(14), weight=ft.FontWeight.BOLD),
        _p("In den Einstellungen (Ansicht → Zoom) lassen sich alle "
           "Schriften der App verkleinern oder vergrößern (70–150 %, "
           "Standard 100 %) — kleiner, damit auf kleine Displays mehr "
           "passt, größer für bessere Lesbarkeit. Die Änderung wirkt "
           "sofort; andere Ansichten übernehmen sie beim Öffnen."),
        ft.Text("Erweiterte Funktionen", size=sz(14), weight=ft.FontWeight.BOLD),
        _bullets([
            "Zusatzfunktionen für Fortgeschrittene — in den Einstellungen "
            "einzeln zuschaltbar (Standard: aus); eingeschaltete "
            "erscheinen als eigene Karte im Hauptmenü.",
            "Textanalyse: importiert komplette Chatbot-Analysen "
            "griechischer Texte (Originaltext mit Sprachausgabe, "
            "Übersetzung, Wort-für-Wort, Vokabelliste, Phrasen). "
            "Details im Handbuch.",
            "Lexikon: zentrales Nachschlagewerk zum Worthintergrund "
            "(Zerlegung, Kognaten, Synonyme), gefüllt über Chatbot-"
            "Pakete (Arbeitsanweisung IV). Speist die ⓘ-Infobuttons in "
            "Training, Wortlisten und Wortsuche, sammelt Zusatzwörter "
            "in der Liste „Lexikon – Zusatzwörter“ und legt pro Paket "
            "eine Trainings-Auswahlliste an. In den Wortlisten: "
            "„Fehlende Wort-Infos exportieren“ stellt die noch "
            "ungedeckten Wörter für den Chatbot zusammen. Details im "
            "Handbuch.",
        ]),
    ])

    backup_ch = _chapter(nav, "Backup", ft.Icons.ARCHIVE_OUTLINED, [
        _p("Einstellungen → Backup sichert deine Daten als eine "
           "ZIP-Datei — für Sicherungskopien und den Umzug auf ein "
           "neues Gerät."),
        _bullets([
            "Beim Erstellen wählbar: Vokabeln & Auswahllisten, "
            "Lernfortschritt (nur zusammen mit den Vokabeln), Notizen, "
            "Textanalysen, Lexikon, Einstellungen.",
            "Heruntergeladenes Audio ist nie enthalten — es wird bei "
            "Bedarf neu geladen.",
            "Beim Wiederherstellen wählst du, welche der enthaltenen "
            "Bereiche ersetzt werden (nach Sicherheitsabfrage, nicht "
            "rückgängig zu machen); alles andere bleibt unverändert. "
            "Kein Neustart nötig.",
            "Ersetzt den früheren Statistik-Export — der Lernstand "
            "steckt in der Kategorie „Lernfortschritt“.",
        ]),
    ])

    audio = _chapter(nav, "Audio (Aussprache)", ft.Icons.VOLUME_UP, [
        _p("Die App spricht jedes griechische Wort selbst. In den "
           "Einstellungen (Zahnrad) stehen zwei Wege zur Wahl:"),
        _bullets([
            "Systemstimme (Standard): spricht offline über die "
            "Sprachausgabe des Geräts — es werden keine Daten übertragen. "
            "Auf Android ist die griechische Stimme meist schon dabei; "
            "unter Windows das Sprachpaket „Ελληνικά“ (mit "
            "Text-in-Sprache) installieren. Fehlt die Stimme, zeigt das "
            "Antippen einen Hinweis.",
            "Google (online): holt das Audio von Google-Servern — dabei "
            "werden der Text und die IP-Adresse übertragen. Danach liegt "
            "die Aufnahme im lokalen Cache und spielt offline. Für "
            "Geräte ohne griechische Systemstimme.",
        ]),
        _p("Bedienung in allen Listen und Trainings:"),
        _bullets([
            "Lautsprecher-Symbol: kurz antippen spielt ab, lang drücken "
            "schaltet den Langsam-Modus um — danach spielt jedes "
            "Antippen überall langsam (zum Nachsprechen), bis wieder "
            "lange gedrückt wird; beim App-Start ist das Tempo wieder "
            "normal. Im Vokabeltraining erscheint der Lautsprecher "
            "unter der Karte erst, wenn die griechische Seite sichtbar "
            "ist.",
            "Auto-Play: In allen drei Trainings schaltet das "
            "Lautsprecher-Symbol oben rechts um, ob automatisch "
            "vorgelesen wird, sobald der griechische Text erscheint. "
            "Nomen- und Verbtraining sprechen dabei die echte "
            "Lösungsform, z.B. „θα γράψετε“ oder „τους δρόμους“.",
            "Nur im Google-Modus: „Audio vorbereiten“ im Listenmenü (⋮) "
            "lädt alle Wörter einer Liste auf einmal in den Cache — "
            "praktisch vor einer Reise (~100 Wörter in 1–2 Minuten, "
            "etwa 1–1,5 MB). „Audio löschen“ in der Mehrfachauswahl "
            "erneuert kaputte Aufnahmen.",
        ]),
    ])

    wortsuche = _chapter(nav, "Wortsuche", ft.Icons.SEARCH, [
        _bullets([
            "Erreichbar über die Lupe oben in der Leiste — von überall "
            "in der App.",
            "Sucht in allen Listen — Deutsch oder Griechisch tippen; "
            "Groß-/Kleinschreibung und Akzente sind egal.",
            "Steht dasselbe Wort in mehreren Vokabellisten, erscheint es "
            "mehrfach — der Listenname steht jeweils darunter.",
            "Ein ★ bedeutet: die Karte ist zusätzlich in einer Auswahlliste "
            "(der Tooltip nennt welche).",
            "Antippen öffnet die Karte zum Bearbeiten (bei Buchlisten nur "
            "Notizen/Hinweise).",
        ]),
    ])

    DATENSCHUTZ_URL = ("https://github.com/ben85keilert/MathainoA1/"
                       "blob/main/DATENSCHUTZ.md")

    def open_privacy(e):
        async def run():
            await ft.UrlLauncher().launch_url(DATENSCHUTZ_URL)
        nav.page.run_task(run)

    # Google Play verlangt den Datenschutz-Link auch innerhalb der App
    datenschutz = _chapter(nav, "Datenschutz", ft.Icons.PRIVACY_TIP_OUTLINED, [
        _p("Die App erhebt keine Daten: kein Konto, kein Tracking, keine "
           "Analyse-Dienste. Lernstand, Listen, Notizen und Einstellungen "
           "bleiben lokal auf diesem Gerät."),
        _bullets([
            "Sprachausgabe „Systemstimme“ (Standard): läuft komplett "
            "offline — es werden keine Daten übertragen.",
            "Sprachausgabe „Google (online)“ (nur nach aktiver Auswahl in "
            "den Einstellungen): beim Laden eines Worts werden der Text "
            "und die IP-Adresse an Google übertragen; danach liegt das "
            "Audio im lokalen Cache und spielt offline.",
        ]),
        ft.Row([ft.OutlinedButton(
            "Datenschutzerklärung öffnen", icon=ft.Icons.OPEN_IN_NEW,
            on_click=open_privacy)]),
    ])

    def show_about(e):
        try:
            flet_version = metadata.version("flet")
        except metadata.PackageNotFoundError:
            flet_version = "?"
        nav.page.show_dialog(ft.AlertDialog(
            title=ft.Text(APP_NAME),
            content=ft.Column(
                [
                    ft.Text(f"Version {__version__}", size=sz(14)),
                    ft.Text("Lern-App für Griechisch (Niveau A1 und A2): "
                            "Vokabeln, Deklination und Konjugation.",
                            size=sz(14)),
                    ft.Divider(),
                    ft.Text("Lizenz: MIT — © 2026 Benjamin Ebert", size=sz(13)),
                    ft.Text("Quellcode:\n"
                            "github.com/ben85keilert/MathainoA1",
                            size=sz(13), selectable=True),
                    ft.Text(f"Entwickelt mit Flet {flet_version} (Python).",
                            size=sz(13)),
                    ft.Text("Alle Daten (Listen, Lernstand) bleiben lokal "
                            "auf diesem Gerät.", size=sz(13)),
                ],
                tight=True, spacing=8, width=360,
            ),
            actions=[ft.TextButton("Schließen",
                                   on_click=lambda e: nav.page.pop_dialog())],
        ))

    about_row = ft.Row(
        [ft.TextButton("Nach Updates suchen",
                       icon=ft.Icons.SYSTEM_UPDATE_ALT,
                       on_click=lambda e: manual_check(nav.page)),
         ft.TextButton("Über diese App", icon=ft.Icons.INFO_OUTLINE,
                       on_click=show_about)],
        alignment=ft.MainAxisAlignment.END, wrap=True,
    )

    return ft.Column(
        [
            _p("Grammatik-Übersichten (Alphabet, Artikel, Deklinationen, "
               "Verben …) findest du über das Buchsymbol oben in der "
               "Leiste."),
            trainings, symbole, wertung, leitner, editing, wortsuche,
            prompts, stufen, audio, backup_ch, datenschutz, about_row,
        ],
        spacing=4,
        scroll=ft.ScrollMode.AUTO,
    )
