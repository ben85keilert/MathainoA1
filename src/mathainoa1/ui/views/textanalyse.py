"""Textanalyse (erweiterte Funktion): Gesamtschau, Detail, Etymologie.

Gesamtschau = Liste aller importierten Analysen mit Import (Datei oder
Text), Prompt zum Kopieren (Arbeitsanweisung III) und Lösch-/Korrektur-
Menü. Die Detailansicht zeigt pro Text: Originaltext (mit Sprachausgabe),
inhaltliche Übersetzung, Wort-für-Wort-Segmente, die erzeugten
Vokabellisten, Phrasen und die Etymologieliste.

Der etymology_dialog wird auch aus Trainer und Wortlisten geöffnet
(Info-Button an Vokabeln mit Etymologie-Eintrag).
"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.storage.textanalyse import (
    COGNATE_GROUPS,
    AnalysisStore,
    EtymologyEntry,
    TextAnalysis,
    analyses_dir,
)
from mathainoa1.ui.audio import speaker_button
from mathainoa1.ui.views.wordlist import word_list_panel
from mathainoa1.ui.scale import sz

# Arbeitsanweisung III: erweitert die Analyse-Prompts des Nutzers
# (Arbeitsanweisung I/II) um den JSON-Export für diese App. Das Schema
# muss mit storage/textanalyse.py übereinstimmen — Änderungen dort bitte
# hier nachziehen.
ARBEITSANWEISUNG_III = """\
ARBEITSANWEISUNG III: JSON-EXPORT FÜR DIE LERN-APP

AUFGABE
Du hast einen neugriechischen Text nach der Haupt-Arbeitsanweisung
analysiert (sechsteiliger Aufbau) — oder bekommst jetzt einen Text und
erstellst die Analyse. Gib die vollständige Analyse als EINE JSON-Datei
im folgenden Format aus. Gib nur das JSON aus, keinen weiteren Text.

SCHEMA (Beispiel mit allen Feldern)
{
  "schema_version": 1,
  "id": "",
  "title": "Σεισμός στην Αθήνα",
  "source": "kathimerini.gr",
  "date": "2026-07-20",
  "original_text": "Der komplette griechische Originaltext, unverändert.",
  "translation": "Die natürliche deutsche Übersetzung des Gesamtsinns.",
  "segments": [
    {"gr": "Χθες έγινε", "de": "gestern geschah",
     "note": "Aorist Aktiv, 3. Sg."},
    {"gr": "σεισμός", "de": "ein Erdbeben", "note": ""}
  ],
  "vocab": [
    {"front": "ο σεισμός", "back": "Erdbeben", "article": "ο",
     "plural": "-οί", "word_type": "Nomen", "forms": "",
     "stem2": "", "aorist_passive": "", "participle": "",
     "hints_gr": "", "hints_de": "", "notes_gr": "", "notes_de": ""}
  ],
  "phrases": [
    {"gr": "έγινε σεισμός", "de": "es gab ein Erdbeben",
     "note": "unpersönliche Konstruktion"}
  ]
}

REGELN
1. Pflichtfelder: title, original_text, translation. Alles andere darf
   leer sein oder fehlen.
2. segments: der ganze Text lückenlos in kleinen Sinneinheiten (jedes
   Inhaltswort, jeder Artikel möglichst eigene Zeile). Grammatische
   Angaben wie "Aorist Aktiv, 3. Pl." gehören ins Feld "note", nie
   in "de".
3. vocab: nur Inhaltswörter in der Grundform (Nomen: Nominativ Singular
   MIT Artikel in "front", Artikel zusätzlich im Feld "article";
   Verben: 1. Person Singular Präsens; Adjektive: Maskulinum).
   word_type: Nomen, Verb, Adjektiv, Adverb, Präposition, Phrase, Zahl
   oder Sonstiges. Jedes Lemma genau einmal.
4. Strukturierte Felder statt Klammernotation: Plural ins Feld "plural"
   (z.B. "-οί" oder Vollform "οι άνθρωποι"), unregelmäßiger Genitiv ins
   Feld "forms" als "gen_sg=άντρα" (Formen OHNE Artikel — die App setzt
   ihn selbst davor), abweichendes Femininum als "fem=γλυκιά".
   Keine Zusatzangaben in Klammern in "front". Kurze Lernhilfen:
   "hints_gr"/"hints_de" (Gebrauchshinweis, z.B. "mit Akk.") und
   "notes_gr"/"notes_de" (Zusatznotiz, z.B. "per du") — gr erscheint
   bei der griechischen Abfrageseite, de bei der deutschen.
5. Verb-Stammformen: "stem2" = Aorist Aktiv / 2. Stamm (Stamm mit
   Bindestrich, z.B. "γράψ-", oder 6 Personenformen kommagetrennt),
   "aorist_passive" = Aorist Passiv im gleichen Format (angeben, wenn
   bekannt — er ist nicht aus dem Aktiv berechenbar und wird ab Stufe
   A2 trainiert), "participle" = Perfekt-Partizip nur bei
   Unregelmäßigkeit (z.B. "γραμμένος").
6. Komplette Alternativantworten mit " / " trennen ("και / κι");
   optionale Wortteile in runde Klammern ("αγαπ(ά)ω", "(Visiten-)Karte").
   Muss innerhalb eines Satzes genau EINE von mehreren Varianten genannt
   werden, eckige Klammern verwenden: "Ich spreche [nicht/kein]
   Chinesisch." bzw. "Πώς [είσαι/είστε];" — kein nacktes "/" mitten im
   Satz.
7. Feste Wendungen, die als Vokabel gelernt werden sollen (z.B.
   Grußformeln), gehören mit word_type "Phrase" in "vocab"; "phrases"
   ist dagegen für satzweise Konstruktionen AUS dem Text (nur Anzeige,
   keine Lernkarten).
8. KEINE Etymologie in dieser Datei: Wortherkunft, Kognaten, Synonyme
   und Zusatzwörter liefert die separate Arbeitsanweisung IV (Lexikon
   der App) — hier weglassen.
9. KORREKTUR: Wenn du eine frühere Analyse korrigierst, übernimm "id"
   und "title" unverändert aus der alten Datei. Die App ersetzt die
   Analyse dann und erhält den Lernstand der Vokabeln.
"""


def _analysis_store(store: ContentStore) -> AnalysisStore:
    astore = AnalysisStore(analyses_dir(), store)
    astore.load_all()
    return astore


def _stats_text(stats: dict) -> str:
    if stats["created"]:
        return "importiert"
    parts = [f"{stats['changed']} Karten geändert",
             f"{stats['new']} neu", f"{stats['removed']} entfernt"]
    return "aktualisiert: " + ", ".join(parts)


def overview_view(nav, store: ContentStore,
                  progress: ProgressStore) -> ft.Control:
    """Gesamtschau: alle importierten Textanalysen + Import/Prompt."""
    page = nav.page
    astore = _analysis_store(store)
    picker = ft.FilePicker()
    if picker not in page.services:
        page.services.append(picker)
    clipboard = ft.Clipboard()
    page.services.append(clipboard)
    body = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

    def do_import(text: str) -> tuple[TextAnalysis, dict]:
        result = astore.import_analysis(text)
        refresh()
        return result

    def import_text_dialog(e=None, hint: str = ""):
        tf_text = ft.TextField(
            label="Analyse-JSON hier einfügen",
            multiline=True, min_lines=8, max_lines=14,
        )
        error = ft.Text("", color=ft.Colors.ERROR, size=sz(13))

        def run_import(e):
            text = (tf_text.value or "").strip()
            if not text:
                error.value = "Bitte zuerst das JSON einfügen."
                page.update()
                return
            try:
                analysis, stats = do_import(text)
            except ValueError as exc:
                error.value = str(exc)
                page.update()
                return
            page.pop_dialog()
            page.show_dialog(ft.SnackBar(ft.Text(
                f"„{analysis.title}“ {_stats_text(stats)}.")))

        content_items: list[ft.Control] = []
        if hint:
            content_items.append(ft.Text(hint, size=sz(13), italic=True))
        content_items += [tf_text, error]
        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Analyse als Text importieren"),
            content=ft.Column(content_items, tight=True, spacing=10,
                              width=420, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Abbrechen",
                                   on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Importieren", on_click=run_import)],
        ))

    async def import_file(e):
        files = await picker.pick_files(
            dialog_title="Analyse importieren",
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
            analysis, stats = do_import(data.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as exc:
            page.show_dialog(ft.SnackBar(ft.Text(
                f"Import fehlgeschlagen: {exc}")))
            return
        page.show_dialog(ft.SnackBar(ft.Text(
            f"„{analysis.title}“ {_stats_text(stats)}.")))

    def copy_prompt(e):
        def copy(e):
            async def do():
                await clipboard.set(ARBEITSANWEISUNG_III)
            page.run_task(do)
            page.pop_dialog()
            page.show_dialog(ft.SnackBar(ft.Text("Prompt kopiert.")))

        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Arbeitsanweisung III (Prompt)", size=sz(16)),
            content=ft.Column(
                [ft.Text(ARBEITSANWEISUNG_III, size=sz(12), selectable=True)],
                scroll=ft.ScrollMode.AUTO, width=420, height=440,
            ),
            actions=[
                ft.TextButton("Kopieren", icon=ft.Icons.COPY, on_click=copy),
                ft.TextButton("Schließen",
                              on_click=lambda e: page.pop_dialog()),
            ],
        ))

    def delete_dialog(analysis: TextAnalysis):
        has_lists = any(i in store.lists for i in
                        (analysis.vocab_list_id, analysis.etym_list_id))
        cb_lists = ft.Checkbox(
            label="Erzeugte Vokabellisten mitlöschen", value=True,
            visible=has_lists)

        def do_delete(e):
            astore.delete_analysis(analysis.id,
                                   delete_lists=has_lists and cb_lists.value)
            page.pop_dialog()
            refresh()

        warning = ("Beim Mitlöschen der Listen geht auch der Lernstand "
                   "dieser Karten verloren." if has_lists else
                   "Die Analyse-Datei wird gelöscht.")
        page.show_dialog(ft.AlertDialog(
            title=ft.Text(f"„{analysis.title}“ löschen?"),
            content=ft.Column([ft.Text(warning), cb_lists],
                              tight=True, spacing=10),
            actions=[ft.TextButton("Abbrechen",
                                   on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Löschen", on_click=do_delete)],
        ))

    def correct_hint(analysis: TextAnalysis):
        import_text_dialog(hint=(
            "Korrigierte Analyse mit gleicher id bzw. gleichem Titel "
            f"(„{analysis.title}“) einfügen — die Analyse wird ersetzt, "
            "Karten und Lernstand bleiben erhalten."))

    def open_detail(analysis: TextAnalysis):
        nav.go(analysis.title,
               detail_view(nav, astore, store, progress, analysis))

    def analysis_tile(analysis: TextAnalysis) -> ft.Control:
        extra = sum(len(e.extra_vocab) for e in analysis.etymology)
        parts = [p for p in (
            analysis.date,
            f"{len(analysis.vocab)} Vokabeln",
            f"{len(analysis.etymology)} Etymologien" if analysis.etymology
            else "",
            f"{extra} Zusatzwörter" if extra else "",
        ) if p]
        menu = ft.PopupMenuButton(items=[
            ft.PopupMenuItem(content="Öffnen", icon=ft.Icons.ARTICLE_OUTLINED,
                             on_click=lambda e, a=analysis: open_detail(a)),
            ft.PopupMenuItem(content="Korrigieren (Reimport)",
                             icon=ft.Icons.PUBLISHED_WITH_CHANGES,
                             on_click=lambda e, a=analysis: correct_hint(a)),
            ft.PopupMenuItem(content="Löschen", icon=ft.Icons.DELETE,
                             on_click=lambda e, a=analysis: delete_dialog(a)),
        ])
        return ft.Card(content=ft.ListTile(
            leading=ft.Icon(ft.Icons.ARTICLE_OUTLINED),
            title=ft.Text(analysis.title, weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(" · ".join(parts), size=sz(13)),
            trailing=menu,
            on_click=lambda e, a=analysis: open_detail(a),
        ))

    def refresh():
        astore.load_all()
        rows: list[ft.Control] = [
            ft.Row([
                ft.FilledButton("Importieren", icon=ft.Icons.UPLOAD_FILE,
                                on_click=import_file),
                ft.OutlinedButton("Als Text importieren",
                                  icon=ft.Icons.CONTENT_PASTE,
                                  on_click=import_text_dialog),
                ft.OutlinedButton("Prompt kopieren", icon=ft.Icons.COPY,
                                  on_click=copy_prompt),
            ], spacing=8, wrap=True),
        ]
        ordered = astore.ordered()
        if ordered:
            rows += [analysis_tile(a) for a in ordered]
        else:
            rows.append(ft.Text(
                "Noch keine Textanalysen. So funktioniert es: Prompt "
                "kopieren, zusammen mit einem griechischen Text an einen "
                "Chatbot geben, das erzeugte JSON hier importieren. Die "
                "App legt daraus die Analyse und passende Vokabellisten "
                "an; eine korrigierte Fassung ersetzt die Analyse per "
                "Reimport, der Lernstand bleibt erhalten.",
                size=sz(14)))
        body.controls = rows
        page.update()

    refresh()
    body.on_reappear = refresh
    return body


def _section(nav, title: str, icon: str, build_controls) -> ft.Control:
    """Kapitel-Kachel wie in der Hilfe: öffnet den Inhalt als eigene Seite.

    build_controls ist eine Funktion, damit der Inhalt erst beim Öffnen
    gebaut wird (word_list_panel & Co. sind nicht ganz billig).
    """
    return ft.Card(content=ft.ListTile(
        leading=ft.Icon(icon, color=ft.Colors.PRIMARY),
        title=ft.Text(title, size=sz(15), weight=ft.FontWeight.BOLD),
        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
        on_click=lambda e: nav.go(title, ft.Column(
            build_controls(), spacing=10, scroll=ft.ScrollMode.AUTO)),
    ))


def detail_view(nav, astore: AnalysisStore, store: ContentStore,
                progress: ProgressStore,
                analysis: TextAnalysis) -> ft.Control:
    """Detailansicht einer Analyse: Kapitel-Kacheln je Abschnitt."""
    page = nav.page

    def text_controls() -> list[ft.Control]:
        speaker = speaker_button(page, lambda: analysis.original_text,
                                 long_text=True)
        items: list[ft.Control] = [
            ft.Row([ft.Text("Originaltext", size=sz(15),
                            weight=ft.FontWeight.BOLD, expand=True), speaker],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text(analysis.original_text, size=sz(14), selectable=True),
            ft.Divider(),
            ft.Text("Inhaltliche Übersetzung", size=sz(15),
                    weight=ft.FontWeight.BOLD),
            ft.Text(analysis.translation, size=sz(14), selectable=True),
        ]
        if analysis.source or analysis.date:
            items.append(ft.Text(
                " · ".join(p for p in (analysis.source, analysis.date) if p),
                size=sz(12), italic=True))
        return items

    def segment_controls() -> list[ft.Control]:
        rows: list[ft.Control] = [ft.Text(
            "Kleine Sinneinheiten: links Griechisch, rechts wörtlich.",
            size=sz(13), italic=True)]
        for s in analysis.segments:
            title = ft.Row(
                [ft.Text(s.gr, expand=1, selectable=True),
                 ft.Text(s.de, expand=1)],
                spacing=12, vertical_alignment=ft.CrossAxisAlignment.START)
            rows.append(ft.ListTile(
                dense=True, title=title,
                subtitle=ft.Text(s.note, size=sz(12), italic=True)
                if s.note else None,
                trailing=speaker_button(page, lambda s=s: s.gr,
                                        long_text=True, icon_size=sz(18)),
            ))
        return rows

    def vocab_controls() -> list[ft.Control]:
        cards = store.cards_for(analysis.vocab_list_id)
        if not cards:
            return [ft.Text("Keine Vokabelliste zu dieser Analyse — die "
                            "Liste wurde gelöscht oder die Analyse enthält "
                            "keine Vokabeln.", italic=True)]
        return [word_list_panel(page, cards, progress.all())]

    def extra_vocab_controls() -> list[ft.Control]:
        cards = store.cards_for(analysis.etym_list_id)
        if not cards:
            return [ft.Text("Keine Zusatzwörter zu dieser Analyse.",
                            italic=True)]
        return [word_list_panel(page, cards, progress.all())]

    def phrase_controls() -> list[ft.Control]:
        rows: list[ft.Control] = []
        for p in analysis.phrases:
            rows.append(ft.ListTile(
                dense=True,
                title=ft.Text(p.gr, weight=ft.FontWeight.BOLD,
                              selectable=True),
                subtitle=ft.Text(" — ".join(x for x in (p.de, p.note) if x),
                                 size=sz(13)),
                trailing=speaker_button(page, lambda p=p: p.gr,
                                        long_text=True, icon_size=sz(18)),
            ))
        return rows

    def etymology_controls() -> list[ft.Control]:
        rows: list[ft.Control] = []
        for i, entry in enumerate(analysis.etymology):
            if i:
                rows.append(ft.Divider())
            rows += render_etymology(entry)
        return rows

    sections = [
        _section(nav, "Originaltext & Übersetzung",
                 ft.Icons.TRANSLATE, text_controls),
    ]
    if analysis.segments:
        sections.append(_section(nav, "Wort für Wort",
                                 ft.Icons.SEGMENT, segment_controls))
    sections.append(_section(nav, "Vokabeln",
                             ft.Icons.STYLE, vocab_controls))
    if analysis.etym_list_id and store.cards_for(analysis.etym_list_id):
        sections.append(_section(
            nav, "Zusatzwörter (Kognaten & Synonyme)",
            ft.Icons.ACCOUNT_TREE_OUTLINED, extra_vocab_controls))
    if analysis.phrases:
        sections.append(_section(nav, "Phrasen & Satzbausteine",
                                 ft.Icons.FORMAT_QUOTE, phrase_controls))
    if analysis.etymology:
        sections.append(_section(nav, "Etymologie",
                                 ft.Icons.HISTORY_EDU, etymology_controls))
    return ft.Column(sections, spacing=8, scroll=ft.ScrollMode.AUTO)


def render_etymology(entry: EtymologyEntry,
                     with_title: bool = True) -> list[ft.Control]:
    """Etymologie-Eintrag als Controls: Zerlegung, Semantik, Kognaten,
    Synonyme — Aufbau wie in der Arbeitsanweisung des Nutzers."""

    def two_cols(left: str, right: str, bold_left: bool = False,
                 bg: str | None = None) -> ft.Control:
        return ft.Container(
            ft.Row([
                ft.Text(left, size=sz(13), width=130,
                        weight=ft.FontWeight.BOLD if bold_left else None),
                ft.Text(right, size=sz(13), expand=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
            bgcolor=bg, border_radius=6,
            padding=ft.Padding.symmetric(horizontal=6, vertical=4),
        )

    rows: list[ft.Control] = []
    if with_title:
        rows.append(ft.Text(entry.word, size=sz(16), weight=ft.FontWeight.BOLD))
    for part in entry.breakdown:
        rows.append(two_cols(str(part.get("element", "")),
                             str(part.get("meaning", ""))))
    if entry.total:
        rows.append(two_cols("Gesamt", entry.total, bold_left=True,
                             bg=ft.Colors.PRIMARY_CONTAINER))
    if entry.semantics:
        rows.append(ft.Text(f"Semantik: {entry.semantics}",
                            size=sz(13), italic=True))
    cognate_rows = [
        (label, ", ".join(
            " — ".join(x for x in (str(r.get("word", "")),
                                   str(r.get("meaning", ""))) if x)
            for r in entry.cognates.get(key, [])))
        for key, label in COGNATE_GROUPS
    ]
    if any(text for _label, text in cognate_rows):
        rows.append(ft.Text("Kognaten", size=sz(14), weight=ft.FontWeight.BOLD))
        for label, text in cognate_rows:
            if text:
                rows.append(two_cols(label, text))
    if entry.synonyms:
        rows.append(ft.Text("Synonyme", size=sz(14), weight=ft.FontWeight.BOLD))
        for syn in entry.synonyms:
            rows.append(two_cols(syn.word, syn.nuance, bold_left=True))
    return rows


def etymology_dialog(page: ft.Page, entry: EtymologyEntry) -> None:
    """Wortherkunft als Dialog — aus Trainer und Wortlisten erreichbar.

    Nutzt fast den ganzen Bildschirm (schmaler Rand), damit möglichst
    wenig gescrollt werden muss."""
    w = getattr(page, "width", None) or 420
    h = getattr(page, "height", None) or 700
    page.show_dialog(ft.AlertDialog(
        title=ft.Text(entry.word, size=sz(16)),
        inset_padding=ft.Padding.all(12),
        content=ft.Column(
            render_etymology(entry, with_title=False),
            scroll=ft.ScrollMode.AUTO, width=w, height=h - 180,
        ),
        actions=[ft.TextButton("Schließen",
                               on_click=lambda e: page.pop_dialog())],
    ))
