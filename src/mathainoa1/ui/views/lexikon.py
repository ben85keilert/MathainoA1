"""Lexikon (erweiterte Funktion): zentrales Nachschlagewerk zum
Worthintergrund — Zerlegung, Kognaten, Synonyme.

Gespeist wird es aus eigenständigen Etymologie-Paketen (Arbeitsanweisung
IV), die wortweise gemergt werden; die Zusatzwörter jedes Pakets landen
in der globalen Liste "Lexikon – Zusatzwörter" plus einer Auswahlliste
pro Paket (storage/textanalyse.LexiconStore). Der ⓘ-Infobutton in
Wortlisten, Trainer und Wortsuche zieht seine Daten aus demselben Index.
"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from mathainoa1.logic.answer_check import normalize, strip_accents
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.storage.textanalyse import (
    EtymologyEntry,
    LexiconStore,
    lexicon_store,
    word_key,
)
from mathainoa1.ui.views.textanalyse import etymology_dialog

# Arbeitsanweisung IV: eigenständige Etymologie-Pakete für das Lexikon.
# Das Eintragsschema muss mit storage/textanalyse.EtymologyEntry
# übereinstimmen — Änderungen dort bitte hier nachziehen.
ARBEITSANWEISUNG_IV = """\
ARBEITSANWEISUNG IV: ETYMOLOGIE-PAKET FÜR DAS LEXIKON DER LERN-APP

AUFGABE
Du bekommst eine Liste neugriechischer Vokabeln als CSV-Zeilen im Format
front,back,article,word_type. Erstelle zu JEDEM Wort den sprachlichen
Hintergrund und gib EIN JSON-Objekt im folgenden Format aus. Gib nur das
JSON aus, keinen weiteren Text. Bearbeite höchstens etwa 10 Wörter pro
Auftrag — ist die Liste länger, bitte um Aufteilung.

SCHEMA (Beispiel mit allen Feldern)
{
  "title": "Alltag, Teil 1",
  "etymology": [
    {"word": "ο σεισμός",
     "breakdown": [
       {"element": "σει-", "meaning": "schütteln (altgr. σείω)"},
       {"element": "-σμός", "meaning": "Nomensuffix: Vorgang"}
     ],
     "total": "das Schütteln → Erdbeben",
     "semantics": "Vom altgriechischen σείω (schütteln); im Deutschen als seismisch entlehnt.",
     "cognates": {
       "identical": [{"word": "σείω", "meaning": "schütteln (gehoben)"}],
       "related": [{"word": "το σείσμα", "meaning": "Erschütterung"}],
       "german_latin": [{"word": "seismisch, Seismograph",
                         "meaning": "über griech. σεισμός"}]
     },
     "synonyms": [{"word": "η δόνηση",
                   "nuance": "Erschütterung — auch technisch"}],
     "extra_vocab": [
       {"front": "η δόνηση", "back": "Erschütterung / Vibration",
        "article": "η", "plural": "-εις", "word_type": "Nomen"}
     ]}
  ]
}

REGELN
1. Genau EIN "etymology"-Eintrag pro Eingabewort, in der Reihenfolge
   der Eingabeliste — NICHT alphabetisch sortieren.
2. "breakdown" ist die Wortzerlegung, "total" die Gesamt-Zeile,
   "semantics" genau eine Prosazeile. "cognates" hat genau die drei
   Gruppen "identical" (neugriechisch, gleiche Wurzel), "related"
   (Ableitungen) und "german_latin" (deutsche/lateinische Verwandte).
   "synonyms" nur lernwürdige Alternativen anderer Wurzel mit Nuance.
3. extra_vocab: NUR die zusätzlichen neugriechischen Lernwörter aus
   Kognaten und Synonymen DIESES Eingabeworts, als Vokabeleinträge
   (front mit Artikel, back, article, plural, word_type; bei Verben auch
   stem2, aorist_passive, participle; unregelmäßige Formen ins Feld
   "forms" wie "gen_sg=του άντρα"). NIEMALS das Eingabewort selbst,
   keine altgriechischen Wurzeln, keine deutschen oder lateinischen
   Wörter. Beim jeweiligen Eingabewort lassen — die App bündelt die
   Zusatzwörter in dieser Reihenfolge.
4. Bedeutungen eigenständig prüfen; gängige Zusatzbedeutungen in "back"
   mit " / " ergänzen. word_type: Nomen, Verb, Adjektiv, Adverb,
   Präposition, Phrase, Zahl oder Sonstiges.
5. "title": kurzer sprechender Paketname (z.B. Thema + Teil) — er wird
   in der App der Name der Trainings-Auswahlliste.
6. KORREKTUR: Um einen Lexikon-Eintrag zu verbessern, liefere das Wort
   einfach in einem neuen Paket erneut — die App ersetzt Einträge
   wortweise, alle übrigen bleiben unverändert.
"""


def _import_stats_text(stats: dict) -> str:
    parts = [f"{stats['new']} neu, {stats['updated']} aktualisiert"]
    if stats["extra_new"] or stats["extra_updated"]:
        parts.append(f"Zusatzwörter: {stats['extra_new']} neu, "
                     f"{stats['extra_updated']} aktualisiert")
    if stats["selection"]:
        parts.append(f"Auswahlliste „{stats['selection']}“ angelegt")
    return "Lexikon: " + " · ".join(parts)


def open_import_dialog(page: ft.Page, lex: LexiconStore,
                       on_done=None) -> None:
    """Paste-Dialog für Etymologie-Pakete — auch aus dem Listen-Menü
    erreichbar (der Import ist global, egal von wo er startet)."""
    tf_text = ft.TextField(
        label="Etymologie-Paket (JSON) hier einfügen",
        multiline=True, min_lines=8, max_lines=14,
    )
    error = ft.Text("", color=ft.Colors.ERROR, size=13)

    def run_import(e):
        text = (tf_text.value or "").strip()
        if not text:
            error.value = "Bitte zuerst das JSON einfügen."
            page.update()
            return
        try:
            stats = lex.import_package(text)
        except ValueError as exc:
            error.value = str(exc)
            page.update()
            return
        page.pop_dialog()
        page.show_dialog(ft.SnackBar(ft.Text(_import_stats_text(stats))))
        if on_done:
            on_done()

    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Wort-Infos importieren"),
        content=ft.Column([tf_text, error], tight=True, spacing=10,
                          width=420, scroll=ft.ScrollMode.AUTO),
        actions=[ft.TextButton("Abbrechen",
                               on_click=lambda e: page.pop_dialog()),
                 ft.FilledButton("Importieren", on_click=run_import)],
    ))


def open_prompt_dialog(page: ft.Page, clipboard: ft.Clipboard) -> None:
    def copy(e):
        async def do():
            await clipboard.set(ARBEITSANWEISUNG_IV)
        page.run_task(do)
        page.pop_dialog()
        page.show_dialog(ft.SnackBar(ft.Text("Prompt kopiert.")))

    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Arbeitsanweisung IV (Prompt)", size=16),
        content=ft.Column(
            [ft.Text(ARBEITSANWEISUNG_IV, size=12, selectable=True)],
            scroll=ft.ScrollMode.AUTO, width=420, height=440,
        ),
        actions=[
            ft.TextButton("Kopieren", icon=ft.Icons.COPY, on_click=copy),
            ft.TextButton("Schließen",
                          on_click=lambda e: page.pop_dialog()),
        ],
    ))


def lexikon_view(nav, store: ContentStore,
                 progress: ProgressStore) -> ft.Control:
    """Hauptansicht: Suche + alphabetische Einträge + Import/Prompt."""
    page = nav.page
    lex = lexicon_store(store)
    picker = ft.FilePicker()
    if picker not in page.services:
        page.services.append(picker)
    clipboard = ft.Clipboard()
    page.services.append(clipboard)
    tf_search = ft.TextField(label="Im Lexikon suchen",
                             prefix_icon=ft.Icons.SEARCH)
    body = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

    async def import_file(e):
        files = await picker.pick_files(
            dialog_title="Etymologie-Paket importieren",
            allowed_extensions=["json"], with_data=True,
        )
        if not files:
            return
        f = files[0]
        data = f.bytes_data if hasattr(f, "bytes_data") else None
        if data is None and f.path:
            data = Path(f.path).read_bytes()
        if data is None:
            return
        try:
            stats = lex.import_package(data.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as exc:
            page.show_dialog(ft.SnackBar(ft.Text(
                f"Import fehlgeschlagen: {exc}")))
            return
        page.show_dialog(ft.SnackBar(ft.Text(_import_stats_text(stats))))
        refresh()

    def delete_dialog(entry: EtymologyEntry):
        def do_delete(e):
            lex.delete_entry(entry.word)
            page.pop_dialog()
            refresh()

        page.show_dialog(ft.AlertDialog(
            title=ft.Text(f"„{entry.word}“ aus dem Lexikon löschen?"),
            content=ft.Text("Nur der Lexikon-Eintrag wird entfernt — die "
                            "Liste „Lexikon – Zusatzwörter“ und der "
                            "Lernstand bleiben unberührt."),
            actions=[ft.TextButton("Abbrechen",
                                   on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Löschen", on_click=do_delete)],
        ))

    def entry_tile(entry: EtymologyEntry) -> ft.Control:
        subtitle = entry.total or entry.semantics
        return ft.Card(content=ft.ListTile(
            dense=True,
            title=ft.Text(entry.word, weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(subtitle, size=13) if subtitle else None,
            trailing=ft.IconButton(
                ft.Icons.DELETE_OUTLINE, tooltip="Eintrag löschen",
                on_click=lambda e, x=entry: delete_dialog(x)),
            on_click=lambda e, x=entry: etymology_dialog(page, x),
        ))

    def matches(entry: EtymologyEntry, query: str) -> bool:
        hay = " ".join([entry.word, entry.total, entry.semantics]
                       + [s.word for s in entry.synonyms])
        return query in strip_accents(normalize(hay))

    def refresh(e=None):
        rows: list[ft.Control] = [
            ft.Row([
                ft.FilledButton("Importieren", icon=ft.Icons.UPLOAD_FILE,
                                on_click=import_file),
                ft.OutlinedButton(
                    "Als Text importieren", icon=ft.Icons.CONTENT_PASTE,
                    on_click=lambda e: open_import_dialog(
                        page, lex, on_done=refresh)),
                ft.OutlinedButton(
                    "Prompt kopieren", icon=ft.Icons.COPY,
                    on_click=lambda e: open_prompt_dialog(page, clipboard)),
            ], spacing=8, wrap=True),
        ]
        if lex.entries:
            # Nachschlagewerk: hier ist alphabetisch die richtige Ordnung
            entries = sorted(lex.entries, key=lambda x: word_key(x.word))
            query = strip_accents(normalize(tf_search.value or ""))
            if query:
                entries = [x for x in entries if matches(x, query)]
            rows.append(tf_search)
            rows.append(ft.Text(
                f"{len(entries)} von {len(lex.entries)} Einträgen"
                if query else f"{len(lex.entries)} Einträge", size=13))
            rows += [entry_tile(x) for x in entries]
        else:
            rows.append(ft.Text(
                "Das Lexikon ist noch leer. So funktioniert es: In einer "
                "Wortliste über das Menü „Fehlende Wort-Infos exportieren“ "
                "die ungedeckten Wörter kopieren, zusammen mit dem Prompt "
                "(Arbeitsanweisung IV) an einen Chatbot geben und das "
                "erzeugte JSON-Paket hier importieren. Die App merkt sich "
                "den Worthintergrund (ⓘ an jeder Vokabel), sammelt die "
                "Zusatzwörter in der Liste „Lexikon – Zusatzwörter“ und "
                "legt pro Paket eine kleine Auswahlliste zum Trainieren "
                "an. Ein Wort erneut zu liefern ersetzt seinen Eintrag.",
                size=14))
        body.controls = rows
        page.update()

    tf_search.on_change = refresh
    refresh()

    def reload(e=None):
        lex.load()
        refresh()

    body.on_reappear = reload
    return body
