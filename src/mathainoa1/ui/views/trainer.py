"""Vokabeltrainer: Setup, Trainingsrunde (Karteikarte/Tippen), Ergebnis."""

from __future__ import annotations

import flet as ft

from mathainoa1.logic.answer_check import Result
from mathainoa1.logic.session import TrainingSession, TrainingSettings, filter_cards
from mathainoa1.models import WORD_TYPES, VocabCard
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.progress import ProgressStore, max_box_for_mode
from mathainoa1.storage.settings import (
    load_app_settings,
    load_default_settings,
    save_default_settings,
)
from mathainoa1.ui.audio import (
    autoplay_button,
    maybe_autoplay,
    play_text,
)

ALL = "__all__"


def make_session(store: ContentStore, progress: ProgressStore,
                 settings: TrainingSettings) -> TrainingSession:
    cards = filter_cards(store.cards_for(settings.list_id), settings)
    app = load_app_settings()
    session = TrainingSession(cards, settings, progress=progress.all(),
                              accent_resets_box=app.accent_resets_box,
                              case_resets_box=app.case_resets_box)

    # Box-Deckel je Abfrageart (per Einstellungen abschaltbar); bei
    # "Gemischt" zählt die Richtung der jeweiligen Karte
    def max_box_for(card: VocabCard) -> int:
        production = session.direction_for(card) == "de_gr"
        typed = production and settings.mode == "typing"
        return max_box_for_mode(
            production, typed,
            high_needs_production=app.high_boxes_need_production,
            top_needs_typing=app.top_box_needs_typing)

    session.on_result = lambda card, ok: progress.record(
        card.id, ok, max_box=max_box_for(card))
    return session


def notes_text(card: VocabCard, sides: str = "gr,de") -> str:
    """Alle Hinweise/Notizen der genannten Seiten, für Listenansichten."""
    parts = []
    for side in sides.split(","):
        if card.notes_for(side):
            parts.append(f"📝 {card.notes_for(side)}")
        if card.hints_for(side):
            parts.append(f"💡 {card.hints_for(side)}")
    return "\n".join(parts)


def edit_notes_dialog(page: ft.Page, store: ContentStore, card: VocabCard,
                      on_saved=None) -> None:
    tf_notes_gr = ft.TextField(label="Notiz (griechische Seite)", value=card.notes_gr)
    tf_notes_de = ft.TextField(label="Notiz (deutsche Seite)", value=card.notes_de)
    tf_hints_gr = ft.TextField(label="Hinweis (griechische Seite)", value=card.hints_gr)
    tf_hints_de = ft.TextField(label="Hinweis (deutsche Seite)", value=card.hints_de)

    def save(e):
        store.update_notes(
            card,
            (tf_hints_gr.value or "").strip(), (tf_hints_de.value or "").strip(),
            (tf_notes_gr.value or "").strip(), (tf_notes_de.value or "").strip(),
        )
        page.pop_dialog()
        if on_saved:
            on_saved()

    page.show_dialog(ft.AlertDialog(
        title=ft.Text(f"Notizen zu „{card.front}“"),
        content=ft.Column([tf_notes_gr, tf_notes_de, tf_hints_gr, tf_hints_de],
                          tight=True, spacing=12, width=400,
                          scroll=ft.ScrollMode.AUTO),
        actions=[ft.IconButton(ft.Icons.CLOSE, tooltip="Abbrechen",
                               on_click=lambda e: page.pop_dialog()),
                 ft.IconButton(ft.Icons.SAVE, tooltip="Speichern", on_click=save)],
    ))


def setup_view(nav, store: ContentStore, progress: ProgressStore,
               preselect_id: str | None = None) -> ft.Control:
    s = load_default_settings()
    lists = sorted(store.lists.values(),
                   key=lambda l: (l.chapter is None, l.chapter or 0, l.name))
    selections = sorted(store.selections.values(), key=lambda x: x.name)
    if not lists:
        return ft.Text("Keine Vokabellisten gefunden.")
    valid_ids = {l.id for l in lists} | {x.id for x in selections}
    # frisch erstellte Auswahlliste direkt vorwählen
    if preselect_id and preselect_id in valid_ids:
        s.list_id = preselect_id
    if s.list_id not in valid_ids:
        s.list_id = lists[0].id

    dd_list = ft.Dropdown(
        label="Liste",
        value=s.list_id,
        options=[ft.DropdownOption(key=l.id, text=l.name) for l in lists]
        + [ft.DropdownOption(key=x.id, text=f"★ {x.name}") for x in selections],
    )
    dd_type = ft.Dropdown(label="Worttyp", value=s.word_type or ALL, expand=True)
    seg_mode = ft.SegmentedButton(
        selected=[s.mode],
        segments=[
            ft.Segment(value="flashcard", label=ft.Text("Karteikarte"),
                       icon=ft.Icons.STYLE),
            ft.Segment(value="typing", label=ft.Text("Schreiben"),
                       icon=ft.Icons.KEYBOARD),
        ],
    )
    seg_dir = ft.SegmentedButton(
        selected=[s.direction],
        segments=[
            # leichter zuerst: Wiedererkennen (GR → DE), dann Produktion
            ft.Segment(value="gr_de", label=ft.Text("GR → DE")),
            ft.Segment(value="de_gr", label=ft.Text("DE → GR")),
            ft.Segment(value="mixed", label=ft.Text("Gemischt")),
        ],
    )
    tf_count = ft.TextField(
        label="Wortanzahl", value=str(s.word_count),
        keyboard_type=ft.KeyboardType.NUMBER, width=140,
    )
    sw_article = ft.Switch(label="Artikel muss mitgetippt werden", value=s.with_article)
    sw_repeat = ft.Switch(label="Fehler am Ende wiederholen", value=s.repeat_errors)
    sw_accent = ft.Switch(label="Akzentfehler tolerieren", value=s.accent_tolerant)
    sw_case = ft.Switch(label="Groß-/Kleinschreibung tolerieren (nur Nomen)",
                        value=s.case_tolerant)
    seg_notes = ft.SegmentedButton(
        allow_multiple_selection=True,
        show_selected_icon=True,
        allow_empty_selection=True,
        selected=[x for x, on in (("notes", s.notes_on), ("hints", s.hints_on)) if on],
        segments=[
            ft.Segment(value="notes", label=ft.Text("Notizen"),
                       icon=ft.Icons.STICKY_NOTE_2_OUTLINED),
            ft.Segment(value="hints", label=ft.Text("Hinweise"),
                       icon=ft.Icons.LIGHTBULB_OUTLINE),
        ],
    )

    error_text = ft.Text("", color=ft.Colors.ERROR)

    def cards_for_list() -> list[VocabCard]:
        return store.cards_for(dd_list.value)

    def refresh_filters(e=None):
        cards = cards_for_list()
        types = [t for t in WORD_TYPES if any(c.word_type == t for c in cards)]
        dd_type.options = [ft.DropdownOption(key=ALL, text="Alle Worttypen")] + [
            ft.DropdownOption(key=t, text=t) for t in types
        ]
        if dd_type.value != ALL and dd_type.value not in types:
            dd_type.value = ALL
        nav.page.update()

    # Achtung: Flet-0.85-Dropdowns feuern on_select (on_change existiert nicht)
    dd_list.on_select = refresh_filters
    refresh_filters()

    def seg_value(seg: ft.SegmentedButton, default: str) -> str:
        sel = seg.selected
        if isinstance(sel, (list, set, tuple)) and sel:
            return next(iter(sel))
        return sel or default

    def current_settings() -> TrainingSettings | None:
        try:
            count = max(1, int(tf_count.value))
        except (TypeError, ValueError):
            error_text.value = "Bitte eine gültige Wortanzahl eingeben."
            nav.page.update()
            return None
        notes_sel = seg_notes.selected or []
        return TrainingSettings(
            mode=seg_value(seg_mode, "flashcard"),
            direction=seg_value(seg_dir, "de_gr"),
            word_count=count,
            with_article=sw_article.value,
            repeat_errors=sw_repeat.value,
            accent_tolerant=sw_accent.value,
            case_tolerant=sw_case.value,
            notes_on="notes" in notes_sel,
            hints_on="hints" in notes_sel,
            list_id=dd_list.value,
            # Aufgaben-Filter aus der UI entfernt; None überschreibt auch
            # einen evtl. alten persistierten Wert (sonst 0 Karten gefiltert)
            task=None,
            word_type=None if dd_type.value == ALL else dd_type.value,
        )

    def filtered_cards(settings: TrainingSettings) -> list[VocabCard]:
        cards = filter_cards(store.cards_for(settings.list_id), settings)
        if not cards:
            error_text.value = "Keine Karten für diese Auswahl gefunden."
            nav.page.update()
        return cards

    def show_cards(e):
        settings = current_settings()
        if settings is None:
            return
        cards = filtered_cards(settings)
        if not cards:
            return
        from mathainoa1.ui.views.manager import open_source_editor
        from mathainoa1.ui.views.wordlist import word_list_panel
        list_id = settings.list_id
        header = ft.Row(
            [
                ft.Text(f"{store.name_for(list_id)} — {len(cards)} Karten",
                        size=16, weight=ft.FontWeight.BOLD, expand=True),
                ft.OutlinedButton(
                    "Liste bearbeiten", icon=ft.Icons.EDIT_OUTLINED,
                    on_click=lambda e: open_source_editor(
                        nav, store, progress, list_id)),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        nav.go(
            f"Auswahl ({len(cards)} Karten)",
            ft.Column(
                [header, word_list_panel(nav.page, cards, progress.all(),
                                         store=store, source_id=list_id)],
                spacing=4, expand=True,
            ),
        )

    def new_selection(e):
        from mathainoa1.ui.views.manager import selection_editor

        def on_saved(sel):
            # Setup-Seite neu aufbauen und die neue Auswahlliste vorwählen
            nav.stack[-2] = ("Vokabeltraining",
                             setup_view(nav, store, progress, preselect_id=sel.id))
            nav.back()

        nav.go("Neue Auswahlliste",
               selection_editor(nav, store, None, on_saved, progress))

    def start(e):
        settings = current_settings()
        if settings is None:
            return
        if not filtered_cards(settings):
            return
        save_default_settings(settings)
        session = make_session(store, progress, settings)
        nav.go("Training", run_view(nav, store, progress, session))

    return ft.Column(
        [
            dd_list,
            ft.Row([ft.TextButton("Neue Auswahlliste erstellen…",
                                  icon=ft.Icons.PLAYLIST_ADD, on_click=new_selection)]),
            ft.Row([dd_type], spacing=8),
            ft.Divider(),
            ft.Row([seg_mode, tf_count], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            seg_dir,
            sw_article, sw_repeat, sw_accent, sw_case,
            ft.Text("Bei der Frage einblenden", size=13),
            # Lautsprecher (Auto-Vorlesen) rechts daneben, ohne Label —
            # gespeichert wie die anderen Einstellungen (app_settings.json)
            ft.Row([seg_notes, autoplay_button(nav.page)], spacing=8,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            error_text,
            ft.Row(
                [
                    ft.FilledButton("Training starten", icon=ft.Icons.PLAY_ARROW,
                                    on_click=start),
                    ft.OutlinedButton("Vokabeln anzeigen", icon=ft.Icons.LIST,
                                      on_click=show_cards),
                ],
                spacing=8, wrap=True,
            ),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )


def run_view(nav, store: ContentStore, progress: ProgressStore,
             session: TrainingSession) -> ft.Control:
    progress_label = ft.Text("", size=13)
    round_label = ft.Text("", size=13, color=ft.Colors.PRIMARY)
    prompt = ft.Text("", size=28, weight=ft.FontWeight.BOLD,
                     text_align=ft.TextAlign.CENTER)
    notes_col = ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    answer = ft.Text("", size=22, text_align=ft.TextAlign.CENTER)
    feedback = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    # Bei falscher Antwort: rotes Kreuz + Label + Augensymbol; Klick blendet
    # die eigene Antwort darunter ein, das Label wird „Meine Antwort:" und
    # das Auge verschwindet
    own_answer = ft.Text("", size=14, italic=True, color=ft.Colors.ERROR,
                         text_align=ft.TextAlign.CENTER, visible=False)
    wrong_label = ft.Text("Meine Antwort anzeigen", color=ft.Colors.ERROR)
    wrong_eye = ft.Icon(ft.Icons.VISIBILITY_OUTLINED, color=ft.Colors.ERROR,
                        size=18)
    btn_wrong = ft.TextButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.CLOSE, color=ft.Colors.ERROR, size=18),
             wrong_label, wrong_eye],
            tight=True, spacing=6,
        ),
        visible=False,
        style=ft.ButtonStyle(color=ft.Colors.ERROR),
    )
    action_area = ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    tf_answer = ft.TextField(label="Antwort", autofocus=True, on_submit=lambda e: check(e))
    # Die gerade angezeigte Karte — nach check_typed() ist session.current
    # bereits die nächste, daher eigene Referenz führen
    shown: dict = {"card": None}

    def focus_answer():
        # focus() ist in Flet eine Coroutine und muss über run_task laufen
        nav.page.run_task(tf_answer.focus)

    seg_mode = ft.SegmentedButton(
        selected=[session.settings.mode],
        segments=[
            ft.Segment(value="flashcard", label=ft.Text("Karteikarte"),
                       icon=ft.Icons.STYLE),
            ft.Segment(value="typing", label=ft.Text("Schreiben"),
                       icon=ft.Icons.KEYBOARD),
        ],
    )

    def switch_mode(e):
        sel = seg_mode.selected
        mode = next(iter(sel)) if isinstance(sel, (list, set, tuple)) else sel
        if mode and mode != session.settings.mode:
            session.settings.mode = mode
            show_card()  # aktuelle (unbeantwortete) Karte im neuen Modus anzeigen

    seg_mode.on_change = switch_mode

    btn_notes = ft.TextButton("Notizen", icon=ft.Icons.STICKY_NOTE_2_OUTLINED)
    btn_hint = ft.TextButton("Hinweis", icon=ft.Icons.LIGHTBULB_OUTLINE)
    btn_edit = ft.IconButton(ft.Icons.EDIT_NOTE, tooltip="Hinweise/Notizen bearbeiten")
    # Notizen/Hinweis auf Höhe ihrer eingeblendeten Texte; darunter die
    # Zeile mit den drei Symbolen (Anhören, Langsam, Bearbeiten)
    hint_row = ft.Row([btn_notes, btn_hint],
                      alignment=ft.MainAxisAlignment.CENTER, spacing=0)
    # Per Klick eingeblendet — gilt nur für die aktuelle Karte
    revealed = {"notes": False, "hints": False, "answered": False}

    # Audiobuttons neben dem Bearbeiten-Symbol: drei Symbole in einer
    # kompakten Zeile direkt über dem Antwortfeld
    btn_play = ft.IconButton(
        ft.Icons.VOLUME_UP, tooltip="Anhören",
        on_click=lambda e: play_text(nav.page, shown["card"].front))
    btn_play_slow = ft.IconButton(
        ft.Icons.SLOW_MOTION_VIDEO, tooltip="Langsam — zum Nachsprechen",
        on_click=lambda e: play_text(nav.page, shown["card"].front, slow=True))
    icons_row = ft.Row([btn_play, btn_play_slow, btn_edit],
                       alignment=ft.MainAxisAlignment.CENTER, spacing=0)

    def update_audio_row():
        # Immer die griechische Seite abspielen — bei DE->GR also erst nach
        # dem Aufdecken, sonst wäre die Antwort verraten
        card = shown["card"]
        on = session.prompt_side(card) == "gr" or revealed["answered"]
        btn_play.visible = btn_play_slow.visible = on

    def refresh_notes():
        card = shown["card"]
        if card is None:
            return
        s = session.settings
        if revealed["answered"]:
            sides = [session.prompt_side(card), session.answer_side(card)]
        else:
            sides = [session.prompt_side(card)]
        show_notes = s.notes_on or revealed["notes"] or revealed["answered"]
        show_hints = s.hints_on or revealed["hints"] or revealed["answered"]

        def note_row(icon: str, text: str) -> ft.Row:
            # dieselben Icons wie die Buttons "Notizen"/"Hinweis" (Primärblau)
            return ft.Row(
                [ft.Icon(icon, size=16, color=ft.Colors.PRIMARY),
                 ft.Text(text, size=14, italic=True, expand=True)],
                spacing=6, vertical_alignment=ft.CrossAxisAlignment.START,
            )

        rows = []
        for side in sides:
            if show_notes and card.notes_for(side):
                rows.append(note_row(ft.Icons.STICKY_NOTE_2_OUTLINED,
                                     card.notes_for(side)))
            if show_hints and card.hints_for(side):
                rows.append(note_row(ft.Icons.LIGHTBULB_OUTLINE,
                                     card.hints_for(side)))
        notes_col.controls = rows
        # Buttons nur, wenn es dafür verborgenen Inhalt gibt
        has_notes = any(card.notes_for(x) for x in sides)
        has_hints = any(card.hints_for(x) for x in sides)
        btn_notes.visible = has_notes and not show_notes
        btn_hint.visible = has_hints and not show_hints
        update_audio_row()
        nav.page.update()

    def reveal_notes(e):
        revealed["notes"] = True
        refresh_notes()

    def reveal_hints(e):
        revealed["hints"] = True
        refresh_notes()

    def edit_notes(e):
        card = shown["card"]
        if card is None:
            return
        # Nach dem Speichern direkt einblenden — man hat sie ja bewusst ergänzt
        def after_save():
            revealed["notes"] = True
            revealed["hints"] = True
            refresh_notes()
        edit_notes_dialog(nav.page, store, card, on_saved=after_save)

    btn_notes.on_click = reveal_notes
    btn_hint.on_click = reveal_hints
    btn_edit.on_click = edit_notes

    def show_card():
        card = session.current
        if card is None:
            nav.go("Ergebnis", result_view(nav, store, progress, session))
            return
        shown["card"] = card
        revealed["notes"] = revealed["hints"] = revealed["answered"] = False
        done = len(session.answers)
        total = done + len(session.queue)
        progress_label.value = f"Karte {done + 1} von {total}"
        round_label.value = "Fehlerrunde" if session.in_repeat_round else ""
        prompt.value = session.prompt_for(card)
        answer.value = ""
        feedback.value = ""
        btn_wrong.visible = False
        wrong_label.value = "Meine Antwort anzeigen"
        wrong_eye.visible = True
        own_answer.visible = False
        own_answer.value = ""
        if session.settings.mode == "flashcard":
            action_area.controls = [ft.FilledButton("Zeigen", icon=ft.Icons.VISIBILITY,
                                                    on_click=reveal)]
        else:
            tf_answer.value = ""
            # Prüfen direkt neben dem Feld: kein Scrollen nötig, wenn die
            # Tastatur eingeblendet ist
            action_area.controls = [
                ft.Row(
                    [ft.Container(tf_answer, expand=True),
                     ft.IconButton(
                         ft.Icons.CHECK, tooltip="Prüfen", icon_size=28,
                         style=ft.ButtonStyle(
                             bgcolor=ft.Colors.PRIMARY_CONTAINER),
                         on_click=check)],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ]
        refresh_notes()
        # GR->DE: das griechische Wort steht schon in der Frage
        if session.prompt_side(card) == "gr":
            maybe_autoplay(nav.page, card.front)
        if session.settings.mode == "typing":
            focus_answer()

    def after_answer():
        """Nach Antwort/Aufdecken: alle Notizen/Hinweise beider Seiten zeigen."""
        revealed["answered"] = True
        refresh_notes()
        # DE->GR: die griechische Seite erscheint erst jetzt mit der Antwort
        card = shown["card"]
        if session.prompt_side(card) == "de":
            maybe_autoplay(nav.page, card.front)

    def reveal(e):
        card = session.current
        answer.value = session.answer_display_for(card)
        if session.in_repeat_round:
            # Fehlerrunde zählt nicht — Selbstbewertung wäre Scheinauswahl
            action_area.controls = [
                ft.FilledButton("Weiter", icon=ft.Icons.ARROW_FORWARD,
                                on_click=lambda e: judge(True))
            ]
        else:
            action_area.controls = [
                ft.Row(
                    [
                        ft.FilledButton("Gewusst", icon=ft.Icons.THUMB_UP,
                                        on_click=lambda e: judge(True)),
                        ft.OutlinedButton("Nicht gewusst", icon=ft.Icons.THUMB_DOWN,
                                          on_click=lambda e: judge(False)),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            ]
        after_answer()

    def judge(correct: bool):
        session.mark(correct)
        show_card()

    def check(e):
        card = session.current
        display = session.answer_display_for(card)
        given = tf_answer.value or ""
        result = session.check_typed(given)
        weiter = ft.FilledButton("Weiter", icon=ft.Icons.ARROW_FORWARD,
                                 on_click=lambda e: show_card(), autofocus=True)

        def show_own(e, g=given):
            wrong_label.value = "Meine Antwort:"
            wrong_eye.visible = False
            own_answer.value = g if g.strip() else "(leer)"
            own_answer.visible = True
            nav.page.update()

        if result == Result.CORRECT:
            feedback.value = "Richtig!"
            feedback.color = ft.Colors.GREEN
            action_area.controls = [weiter]
        elif result == Result.ALMOST:
            if session.settings.accent_tolerant:
                feedback.value = "Fast! Achte auf Akzente/Schluss-ς."
            else:
                feedback.value = "Fast - Akzent stimmt nicht"
            feedback.color = ft.Colors.ORANGE
            action_area.controls = [weiter]
        elif result == Result.CASE:
            feedback.value = "Fast - Groß-/Kleinschreibung beachten"
            feedback.color = ft.Colors.ORANGE
            action_area.controls = [weiter]
        else:
            feedback.value = ""
            # Abstand, damit man nicht versehentlich "Weiter" trifft
            action_area.controls = [ft.Container(height=24), weiter]
        if result != Result.CORRECT:
            # Auch bei Akzent-/Groß-Klein-Fehlern die eigene (falsche)
            # Antwort einblendbar machen — nur so sieht man den Fehler
            btn_wrong.visible = True
            btn_wrong.on_click = show_own
        answer.value = display
        after_answer()

    show_card()
    return ft.Column(
        [
            ft.Row([progress_label, round_label, autoplay_button(nav.page)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            seg_mode,
            ft.Container(prompt, padding=ft.Padding.symmetric(vertical=8)),
            notes_col, hint_row,
            icons_row,
            answer, feedback, btn_wrong, own_answer,
            action_area,
        ],
        # enge Abstände: mit allen Symbolen darf der Prüfen-Button bei
        # eingeblendeter Tastatur nicht unter den Rand rutschen
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )


def result_view(nav, store: ContentStore, progress: ProgressStore,
                session: TrainingSession) -> ft.Control:
    stats = session.stats()
    wrong_items = [
        ft.ListTile(
            title=ft.Text(c.front),
            subtitle=ft.Text(c.back),
            leading=ft.Icon(ft.Icons.CLOSE, color=ft.Colors.ERROR),
            trailing=ft.IconButton(
                ft.Icons.EDIT_NOTE, tooltip="Hinweise/Notizen bearbeiten",
                on_click=lambda e, c=c: edit_notes_dialog(nav.page, store, c),
            ),
        )
        for c in stats["wrong_cards"]
    ]

    def again(e):
        nav.stack.pop()  # Ergebnis-View ersetzen statt stapeln
        nav.stack.pop()  # alte Trainings-View entfernen
        new_session = make_session(store, progress, session.settings)
        nav.go("Training", run_view(nav, store, progress, new_session))

    def home(e):
        del nav.stack[1:]
        nav._show()

    return ft.Column(
        [
            ft.Text(f"{stats['correct']} von {stats['total']} richtig",
                    size=24, weight=ft.FontWeight.BOLD),
            ft.ProgressBar(value=stats["correct"] / max(1, stats["total"])),
            ft.Text("Falsche Karten:" if wrong_items else "Alles richtig — μπράβο! 🎉"),
            *wrong_items,
            ft.Row(
                [
                    ft.FilledButton("Neue Runde", icon=ft.Icons.REPLAY, on_click=again),
                    ft.OutlinedButton("Zur Startseite", icon=ft.Icons.HOME, on_click=home),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ],
        spacing=16,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )
