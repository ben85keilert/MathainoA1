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
from mathainoa1.storage import content
from mathainoa1.storage.content import CSV_FIELDS

# Gemeinsamer Teil beider Chatbot-Prompts: Ausgabeformat, Spaltenregeln
# und Beispielzeilen der Import-CSV
_CSV_FORMAT_RULES = f"""\
AUSGABEFORMAT
Eine CSV-Datei: UTF-8, Komma-getrennt, alle Werte in doppelten
Anführungszeichen, mit genau dieser Kopfzeile:

{",".join(CSV_FIELDS)}

Gib nur die CSV aus, keinen weiteren Text. Spalten ohne Angabe leer lassen.

REGELN FÜR DIE SPALTEN
1. front = Griechisch (bei Nomen mit Artikel, z.B. "ο δρόμος"),
   back = Deutsch. Beide Pflicht — sonst die Zeile weglassen.
2. article: ο/η/το/οι/τα (nur bei Nomen).
3. word_type: Nomen, Verb, Adjektiv, Adverb, Präposition, Phrase,
   Zahl oder Sonstiges.
4. plural: Pluralendung oder -form, z.B. "-οι" (nur zur Anzeige).
5. Griechische Alternativformen mit " / " trennen, z.B. "και / κι" oder
   "τρεις / τρία" — jede Form zählt bei der Abfrage als richtig.
6. Optionale Wortteile in runde Klammern: Verben auf -άω als "αγαπ(ά)ω"
   (akzeptiert αγαπάω und αγαπώ); Zusätze wie "η λαϊκή (αγορά)".
7. Deutsche Alternativen mit Komma oder "/" trennen ("und, auch");
   Deutsches in Klammern ist Zusatzinfo und muss nicht mitgetippt
   werden, z.B. "(Visiten-)Karte" oder "Sie (Akk.)".
8. hints/notes: nur kurze Lernhilfen (z.B. "nur Plural", "mit Akk.",
   "wörtl.: …") — keine Verweise auf Buchseiten oder Übungen.
9. forms nur bei Unregelmäßigkeit: "schlüssel=form; …" mit den
   Schlüsseln acc_sg, gen_sg, acc_pl, gen_pl, fem, 1sg…3pl
   (z.B. "gen_pl=γυναικών").
10. stem2: der 2. Stamm (Aoriststamm, für θα/να) — bei JEDEM Verb
    angeben, das einen hat (ohne ihn kein Futur-Training):
    - regelmäßig ein Stamm mit Bindestrich; die Betonung entscheidet
      über die Endungen: "γράψ-" → θα γράψω, aber unbetont
      "κοιμηθ-" → θα κοιμηθώ (endbetont).
    - unregelmäßig stattdessen die 6 Personenformen kommagetrennt,
      z.B. für βλέπω: "δω, δεις, δει, δούμε, δείτε, δουν/δούνε".
    - weglassen nur, wenn der Futurstamm dem Präsens entspricht und
      unbekannt ist, oder bei Fixformen (κοστίζει, θα δούμε).

BEISPIELZEILEN (je Worttyp; regelmäßige Wörter brauchen keine forms)
"ο δρόμος","Straße","-οι","ο","Nomen",,,,,,
"η γυναίκα","Frau","-ες","η","Nomen",,,,,"gen_pl=γυναικών",
"γράφω","schreiben",,,"Verb",,,,,,"γράψ-"
"βλέπω","sehen",,,"Verb",,,,,,"δω, δεις, δει, δούμε, δείτε, δουν/δούνε"
"πάω","gehen",,,"Verb",,,,,"1sg=πάω; 2sg=πας; 3sg=πάει; 1pl=πάμε; 2pl=πάτε; 3pl=πάνε","πάω, πας, πάει, πάμε, πάτε, πάνε"
"μικρός","klein",,,"Adjektiv",,,,,,
"γλυκός","süß",,,"Adjektiv",,,,,"fem=γλυκιά",
"εδώ","hier",,,"Adverb",,,,,,
"από","von, aus",,,"Präposition",,,,,,
"Τι κάνεις;","Wie geht's?",,,"Phrase",,,"per du",,,
"πέντε","fünf",,,"Zahl",,,,,,
"και","und, auch",,,"Sonstiges",,,,,,
"""

# Prompt 1 — Wortlisten-Prompt: fertige Vokabellisten (Grundformen)
CHATBOT_PROMPT = f"""\
AUFGABE
Du bekommst eine Liste griechischer Vokabeln (Grundformen) mit
deutschen Bedeutungen — als Foto oder als Text. Erstelle daraus eine
Import-CSV für eine Griechisch-Lern-App (Niveau A1).

{_CSV_FORMAT_RULES}"""

# Prompt 2 — Lesetext-Prompt: beliebige griechische Texte, Wörter
# stehen dort gebeugt und müssen auf die Grundform zurückgeführt werden
TEXT_PROMPT = f"""\
AUFGABE
Du bekommst einen griechischen Text — z.B. einen abfotografierten
Zeitungsausschnitt, eine Buchseite oder ein Schild. Die Wörter stehen
dort in gebeugten Formen. Erstelle daraus eine Vokabel-CSV für eine
Griechisch-Lern-App (Niveau A1): jedes Wort in seiner Grundform.

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

{_CSV_FORMAT_RULES}"""


def _p(text: str) -> ft.Text:
    return ft.Text(text, size=14)


def _bullets(items: list[str]) -> ft.Column:
    return ft.Column(
        [ft.Row([ft.Text("•", size=14), ft.Text(t, size=14, expand=True)],
                spacing=6, vertical_alignment=ft.CrossAxisAlignment.START)
         for t in items],
        spacing=6,
    )


def _chapter(nav, title: str, icon: str,
             controls: list[ft.Control]) -> ft.Control:
    """Kapitel-Kachel: öffnet den Inhalt als eigene Seite (statt Aufklappen)."""
    return ft.Card(content=ft.ListTile(
        leading=ft.Icon(icon, color=ft.Colors.PRIMARY),
        title=ft.Text(title, size=15, weight=ft.FontWeight.BOLD),
        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
        on_click=lambda e: nav.go(title, ft.Column(
            list(controls), spacing=10, scroll=ft.ScrollMode.AUTO)),
    ))


def help_view(nav, store=None) -> ft.Control:
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
                title=ft.Text(title, size=16),
                content=ft.Column(
                    [ft.Text(text, size=12, selectable=True)],
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
        ft.Text("Vokabeltraining", size=14, weight=ft.FontWeight.BOLD),
        _bullets([
            "Karteikarte (Selbstbewertung) oder Schreiben (Tippen), "
            "gefiltert nach Liste und Worttyp.",
            "Richtungen: Griechisch → Deutsch ist Wiedererkennen "
            "(leichter), Deutsch → Griechisch ist aktives Erinnern — nur "
            "das bringt eine Karte in die hohen Boxen (siehe "
            "Leitner-Boxen).",
        ]),
        ft.Text("Nomentraining", size=14, weight=ft.FontWeight.BOLD),
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
            "Optional werden Adjektive aus der Liste mitdekliniert "
            "(ο μικρός δρόμος → τους μικρούς δρόμους).",
        ]),
        ft.Text("Verbtraining", size=14, weight=ft.FontWeight.BOLD),
        _bullets([
            "Vom deutschen Infinitiv zur konjugierten Form; Personen "
            "und Singular/Plural wählbar.",
            "Präsens und Futur (θα + 2. Stamm) — Futur nur für Verben, "
            "bei denen der 2. Stamm eingetragen ist.",
        ]),
        _p("Alle drei Bereiche arbeiten auf denselben Vokabel- und "
           "Auswahllisten; regelmäßige Formen entstehen automatisch, "
           "Unregelmäßiges kommt aus den Zusatzfeldern der Karten."),
    ])

    wertung = _chapter(nav, "Wertung", ft.Icons.RULE, [
        _bullets([
            "Groß-/Kleinschreibung und mehrfache Leerzeichen sind egal — "
            "außer wenn „Groß-/Kleinschreibung tolerieren“ aus ist (siehe "
            "unten).",
            "Satzzeichen am Anfang/Ende (z.B. ; · ! ? . , …) sind egal.",
            "Wortteile in Klammern sind optional: bei „αγαπ(ά)ω“ zählen "
            "αγαπάω und αγαπώ als richtig.",
            "Steht auf einer Karte „A / B“ (z.B. „και / κι“), zählt jede "
            "der Alternativen als richtig — auf beiden Sprachseiten.",
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
            "dient nur dem Wiederholen.",
        ]),
        ft.Text("Akzent- und Groß-/Kleinschreibung tolerieren", size=14,
                weight=ft.FontWeight.BOLD),
        _bullets([
            "Beide Schalter (Vokabel- und Deklinationstraining) wirken "
            "gleich: ist der Schalter AN, wird der jeweilige Fehler "
            "verziehen und die Antwort zählt als richtig.",
            "Ist der Schalter AUS, ist eine sonst richtige Antwort mit "
            "nur diesem Fehler ein „Fast“: Sie zählt als Fehler der Runde "
            "und wird in dieser und der nächsten Runde wiederholt — die "
            "Leitner-Box bleibt dabei aber unverändert (weder hoch noch "
            "zurück).",
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
            "Diese beiden Beschränkungen lassen sich in den Einstellungen "
            "(Zahnrad) abschalten.",
            "„Sicher“ ist eine Karte ab Box 4.",
            "Die Fehlerrunde wiederholt falsche Karten sofort in der "
            "Reihenfolge der Fehler; in der nächsten Runde sind sie "
            "garantiert wieder dabei, gemischt zwischen den übrigen und "
            "neuen Wörtern.",
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
            "Mehrere richtige Formen mit „/“ trennen, z.B. "
            "„2pl=είστε/είσαστε“ oder „δουν/δούνε“.",
            "Optionale Wortteile in Klammern schreiben, z.B. „αγαπ(ά)ω“.",
            "Adjektive: nur ein unregelmäßiges Femininum eintragen "
            "(z.B. „γλυκιά“).",
            "Worttyp „Sonstiges“ zeigt im Editor alle Felder.",
        ]),
        ft.Text("Beispiele je Worttyp", size=14, weight=ft.FontWeight.BOLD),
        _bullets([
            "Nomen, regelmäßig: „ο δρόμος“ – Straße, Plural „-οι“ — "
            "sonst nichts nötig.",
            "Nomen, unregelmäßig: „η γυναίκα“ – Frau, Plural „-ες“, dazu "
            "Genitiv Plural „γυναικών“ ins Zusatzfeld.",
            "Verb, regelmäßig: „γράφω“ – schreiben, 2. Stamm „γράψ-“ — "
            "Präsensfelder leer lassen.",
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
            ft.Text(",".join(CSV_FIELDS), size=12, selectable=True,
                    font_family="monospace"),
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
                ft.OutlinedButton("Wortlisten-Prompt",
                                  icon=ft.Icons.LIST_ALT,
                                  on_click=open_prompt_dialog(
                                      "Wortlisten-Prompt", CHATBOT_PROMPT)),
                ft.OutlinedButton("Lesetext-Prompt",
                                  icon=ft.Icons.NEWSPAPER,
                                  on_click=open_prompt_dialog(
                                      "Lesetext-Prompt", TEXT_PROMPT)),
            ],
            wrap=True, spacing=8,
        ),
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
            "Lautsprecher-Symbol an jeder Karte: kurz antippen spielt "
            "normal, lang drücken langsam (zum Nachsprechen). Im "
            "Vokabeltraining gibt es dafür zwei Symbole unter der Karte — "
            "sie erscheinen erst, wenn die griechische Seite sichtbar ist.",
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
            "Erreichbar über das runde Such-Symbol unten links in der "
            "Vokabelverwaltung.",
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

    def show_about(e):
        try:
            flet_version = metadata.version("flet")
        except metadata.PackageNotFoundError:
            flet_version = "?"
        nav.page.show_dialog(ft.AlertDialog(
            title=ft.Text(APP_NAME),
            content=ft.Column(
                [
                    ft.Text(f"Version {__version__}", size=14),
                    ft.Text("Lern-App für Griechisch (Niveau A1): "
                            "Vokabeln, Deklination und Konjugation.", size=14),
                    ft.Divider(),
                    ft.Text("Lizenz: MIT — © 2026 Benjamin Ebert", size=13),
                    ft.Text("Quellcode:\n"
                            "github.com/ben85keilert/MathainoA1",
                            size=13, selectable=True),
                    ft.Text(f"Entwickelt mit Flet {flet_version} (Python).",
                            size=13),
                    ft.Text("Alle Daten (Listen, Lernstand) bleiben lokal "
                            "auf diesem Gerät.", size=13),
                ],
                tight=True, spacing=8, width=360,
            ),
            actions=[ft.TextButton("Schließen",
                                   on_click=lambda e: nav.page.pop_dialog())],
        ))

    about_row = ft.Row(
        [ft.TextButton("Über diese App", icon=ft.Icons.INFO_OUTLINE,
                       on_click=show_about)],
        alignment=ft.MainAxisAlignment.END,
    )

    return ft.Column(
        [
            _p("Grammatik-Übersichten (Alphabet, Artikel, Deklinationen, "
               "Verben …) findest du über das Buchsymbol oben in der "
               "Leiste."),
            trainings, wertung, leitner, editing, wortsuche, prompts,
            audio, about_row,
        ],
        spacing=4,
        scroll=ft.ScrollMode.AUTO,
    )
