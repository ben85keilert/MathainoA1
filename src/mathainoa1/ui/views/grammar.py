"""Deklinations- und Konjugationstrainer auf Basis einer Liste.

Beide Trainer sind eigenständige Hauptmenüpunkte (setup_view für
Deklination, conjugation_setup_view für Konjugation). Aufbau wie beim
Vokabeltraining: Liste/Auswahlliste wählen, Optionen setzen, Runde
starten. Die Formen entstehen regelbasiert aus den Vokabelkarten
(siehe logic/declension.py bzw. logic/conjugation.py) — Karten mit
unbekanntem Muster werden automatisch übersprungen. Trainingsrunde und
Ergebnis teilen sich beide Trainer (run_view/result_view); die
Aufgaben-Objekte haben dieselbe Schnittstelle.
"""

from __future__ import annotations

import random

import flet as ft

from mathainoa1.logic import conjugation as conj
from mathainoa1.logic import declension as decl
from mathainoa1.logic.answer_check import Result
from mathainoa1.logic.conjugation import ConjugationSettings
from mathainoa1.logic.declension import (
    CASE_NAMES,
    NUMBER_NAMES,
    DeclensionSession,
    DeclensionSettings,
)
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.storage.settings import (
    load_app_settings,
    load_conjugation_settings,
    load_declension_settings,
    save_conjugation_settings,
    save_declension_settings,
)


def _make_session(tasks, settings, on_result=None) -> DeclensionSession:
    """DeclensionSession mit der App-Box-Reset-Policy (Akzent/Groß-Klein)."""
    app = load_app_settings()
    return DeclensionSession(tasks, settings, on_result=on_result,
                             accent_resets_box=app.accent_resets_box,
                             case_resets_box=app.case_resets_box)


def _verb_sample(verb: conj.Verb) -> str:
    """Beispielform eines Verbs für die Vorschau — nie ungeprüft [0].

    Bevorzugt 2. Person Plural; fehlt sie (z.B. „custom"-Verben ohne diese
    Form), wird die erste vorhandene Präsensform genommen. Optional wird die
    Futurform ergänzt."""
    order = [(2, "pl"), (1, "sg"), (3, "sg"), (1, "pl"), (2, "sg"), (3, "pl")]
    for person, num in order:
        forms = conj.conjugate(verb, person, num)
        if forms:
            label = f"{person}. Person {NUMBER_NAMES[num]}"
            sample = f"{label}: {forms[0]}"
            fut = conj.conjugate_future(verb, person, num)
            if fut:
                sample += f" · Futur: θα {fut[0]}"
            return sample
    return "—"


def _preview_header(nav, store: ContentStore, progress: ProgressStore,
                    title: str, source_id: str) -> ft.Control:
    """Kopfzeile der Wörter-/Verben-Vorschau: Titel + „Liste bearbeiten“."""
    from mathainoa1.ui.views.manager import open_source_editor
    return ft.Row(
        [
            ft.Text(title, size=16, weight=ft.FontWeight.BOLD, expand=True),
            ft.OutlinedButton(
                "Liste bearbeiten", icon=ft.Icons.EDIT_OUTLINED,
                on_click=lambda e: open_source_editor(
                    nav, store, progress, source_id)),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def setup_view(nav, store: ContentStore, progress: ProgressStore,
               preselect_id: str | None = None) -> ft.Control:
    s = load_declension_settings()
    lists = sorted(store.lists.values(),
                   key=lambda l: (l.chapter is None, l.chapter or 0, l.name))
    selections = sorted(store.selections.values(), key=lambda x: x.name)
    if not lists:
        return ft.Text("Keine Vokabellisten gefunden.")
    valid_ids = {l.id for l in lists} | {x.id for x in selections}
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
    info_text = ft.Text("", size=13)
    seg_mode = ft.SegmentedButton(
        selected=[s.mode],
        segments=[
            ft.Segment(value="flashcard", label=ft.Text("Karteikarte"),
                       icon=ft.Icons.STYLE),
            ft.Segment(value="typing", label=ft.Text("Schreiben"),
                       icon=ft.Icons.KEYBOARD),
        ],
    )
    seg_direction = ft.SegmentedButton(
        selected=[s.direction if s.direction in ("gr", "de") else "gr"],
        segments=[
            ft.Segment(value="gr", label=ft.Text("Griechisch"),
                       icon=ft.Icons.TRANSLATE),
            ft.Segment(value="de", label=ft.Text("Deutsch"),
                       icon=ft.Icons.PSYCHOLOGY),
        ],
    )
    seg_cases = ft.SegmentedButton(
        allow_multiple_selection=True,
        show_selected_icon=True,
        selected=[c for c in s.cases if c in CASE_NAMES] or ["acc"],
        segments=[
            # Nominativ = Pluraltraining (nur Plural abgefragt); Standard aus
            ft.Segment(value="nom", label=ft.Text("Nominativ (Pl.)")),
            ft.Segment(value="acc", label=ft.Text("Akkusativ")),
            ft.Segment(value="gen", label=ft.Text("Genitiv")),
        ],
    )
    seg_numbers = ft.SegmentedButton(
        allow_multiple_selection=True,
        show_selected_icon=True,
        selected=[n for n in s.numbers if n in NUMBER_NAMES] or ["sg"],
        segments=[
            ft.Segment(value="sg", label=ft.Text("Singular")),
            ft.Segment(value="pl", label=ft.Text("Plural")),
        ],
    )
    tf_count = ft.TextField(
        label="Aufgabenanzahl", value=str(s.word_count),
        keyboard_type=ft.KeyboardType.NUMBER, width=160,
    )
    sw_adjectives = ft.Switch(label="Adjektive aus der Liste mitdeklinieren",
                              value=s.with_adjectives)
    sw_repeat = ft.Switch(label="Fehler am Ende wiederholen", value=s.repeat_errors)
    sw_accent = ft.Switch(label="Akzentfehler tolerieren", value=s.accent_tolerant)
    sw_case = ft.Switch(label="Groß-/Kleinschreibung tolerieren (nur Nomen)",
                        value=s.case_tolerant)
    error_text = ft.Text("", color=ft.Colors.ERROR)

    def refresh_info(e=None):
        cards = store.cards_for(dd_list.value)
        nouns = decl.declinable_nouns(cards)
        adjs = decl.usable_adjectives(cards)
        info_text.value = (f"{len(nouns)} deklinierbare Nomen · "
                           f"{len(adjs)} Adjektive in dieser Liste")
        sw_adjectives.disabled = not adjs
        if not adjs:
            sw_adjectives.value = False
        nav.page.update()

    # Flet-0.85-Dropdowns feuern on_select (on_change existiert nicht)
    dd_list.on_select = refresh_info
    refresh_info()

    def multi_values(seg: ft.SegmentedButton) -> list[str]:
        sel = seg.selected
        if isinstance(sel, (list, set, tuple)):
            return list(sel)
        return [sel] if sel else []

    def current_settings() -> DeclensionSettings | None:
        try:
            count = max(1, int(tf_count.value))
        except (TypeError, ValueError):
            error_text.value = "Bitte eine gültige Aufgabenanzahl eingeben."
            nav.page.update()
            return None
        cases = [c for c in ("nom", "acc", "gen") if c in multi_values(seg_cases)]
        numbers = [n for n in ("sg", "pl") if n in multi_values(seg_numbers)]
        if not cases or not numbers:
            error_text.value = "Bitte mindestens einen Fall und eine Zahl wählen."
            nav.page.update()
            return None
        mode_sel = multi_values(seg_mode)
        dir_sel = multi_values(seg_direction)
        return DeclensionSettings(
            mode=mode_sel[0] if mode_sel else "typing",
            direction=dir_sel[0] if dir_sel else "gr",
            word_count=count,
            cases=cases,
            numbers=numbers,
            with_adjectives=sw_adjectives.value,
            repeat_errors=sw_repeat.value,
            accent_tolerant=sw_accent.value,
            case_tolerant=sw_case.value,
            list_id=dd_list.value,
        )

    def new_selection(e):
        from mathainoa1.ui.views.manager import selection_editor

        def on_saved(sel):
            # Setup-Seite neu aufbauen und die neue Auswahlliste vorwählen
            nav.stack[-2] = ("Nomentraining",
                             setup_view(nav, store, progress, preselect_id=sel.id))
            nav.back()

        nav.go("Neue Auswahlliste",
               selection_editor(nav, store, None, on_saved, progress))

    def show_words(e):
        settings = current_settings()
        if settings is None:
            return
        cards = store.cards_for(settings.list_id)
        nouns = decl.declinable_nouns(cards)
        if not nouns:
            error_text.value = "Keine deklinierbaren Nomen in dieser Liste."
            nav.page.update()
            return
        adjs = decl.usable_adjectives(cards)
        rows: list[ft.Control] = [
            _preview_header(nav, store, progress,
                            f"{store.name_for(settings.list_id)} — "
                            f"{len(nouns)} Nomen", settings.list_id)
        ]
        for c, n in nouns:
            acc = decl.decline(n, "acc", "sg")
            gen = decl.decline(n, "gen", "sg")
            sub = " · ".join(
                f"{CASE_NAMES[case]}: {decl.ARTICLES[(case, 'sg')][n.gender]} {f}"
                for case, f in (("acc", acc), ("gen", gen)) if f
            ) or "nur Plural"
            rows.append(ft.ListTile(
                dense=True,
                title=ft.Row([ft.Text(c.front, expand=1), ft.Text(c.back, expand=1)],
                             spacing=12),
                subtitle=ft.Text(sub, size=12),
            ))
        if adjs:
            rows.append(ft.Text(f"{len(adjs)} Adjektive", size=16,
                                weight=ft.FontWeight.BOLD))
            rows.append(ft.Text(", ".join(a.word for a in adjs)))
        nav.go(f"Wörter ({len(nouns)})",
               ft.Column(rows, spacing=4, scroll=ft.ScrollMode.AUTO))

    def start(e):
        settings = current_settings()
        if settings is None:
            return
        tasks = decl.generate_tasks(store.cards_for(settings.list_id), settings)
        if not tasks:
            error_text.value = "Keine passenden Aufgaben für diese Auswahl gefunden."
            nav.page.update()
            return
        save_declension_settings(settings)
        # Bei deutscher Vorgabe zählt eine richtig deklinierte Antwort auch
        # als gewusste Vokabel (nur positiv — Deklinationsfehler setzen die
        # Vokabel-Box nicht zurück)
        def record_vocab(card, correct):
            if correct:
                progress.record(card.id, True)

        on_result = record_vocab if settings.direction == "de" else None
        session = _make_session(tasks, settings, on_result=on_result)
        nav.go("Nomentraining", run_view(
            nav, store, session, title="Nomentraining",
            make_tasks=lambda s: decl.generate_tasks(store.cards_for(s.list_id), s)))

    return ft.Column(
        [
            dd_list,
            ft.Row([ft.TextButton("Neue Auswahlliste erstellen…",
                                  icon=ft.Icons.PLAYLIST_ADD, on_click=new_selection)]),
            info_text,
            ft.Divider(),
            ft.Row([seg_mode, tf_count], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            seg_direction,
            seg_cases,
            seg_numbers,
            sw_adjectives, sw_repeat, sw_accent, sw_case,
            error_text,
            ft.Row(
                [
                    ft.FilledButton("Training starten", icon=ft.Icons.PLAY_ARROW,
                                    on_click=start),
                    ft.OutlinedButton("Wörter anzeigen", icon=ft.Icons.LIST,
                                      on_click=show_words),
                ],
                spacing=8, wrap=True,
            ),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )


def conjugation_setup_view(nav, store: ContentStore, progress: ProgressStore,
                           preselect_id: str | None = None) -> ft.Control:
    s = load_conjugation_settings()
    lists = sorted(store.lists.values(),
                   key=lambda l: (l.chapter is None, l.chapter or 0, l.name))
    selections = sorted(store.selections.values(), key=lambda x: x.name)
    if not lists:
        return ft.Text("Keine Vokabellisten gefunden.")
    valid_ids = {l.id for l in lists} | {x.id for x in selections}
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
    info_text = ft.Text("", size=13)
    seg_mode = ft.SegmentedButton(
        selected=[s.mode],
        segments=[
            ft.Segment(value="flashcard", label=ft.Text("Karteikarte"),
                       icon=ft.Icons.STYLE),
            ft.Segment(value="typing", label=ft.Text("Schreiben"),
                       icon=ft.Icons.KEYBOARD),
        ],
    )
    seg_tenses = ft.SegmentedButton(
        allow_multiple_selection=True,
        show_selected_icon=True,
        selected=[t for t in s.tenses if t in conj.TENSES] or ["present"],
        segments=[
            ft.Segment(value="present", label=ft.Text("Präsens")),
            ft.Segment(value="future", label=ft.Text("Futur (θα)")),
        ],
    )
    seg_persons = ft.SegmentedButton(
        allow_multiple_selection=True,
        show_selected_icon=True,
        selected=[str(p) for p in s.persons if p in conj.PERSONS] or ["1", "2", "3"],
        segments=[
            ft.Segment(value="1", label=ft.Text("1. Pers.")),
            ft.Segment(value="2", label=ft.Text("2. Pers.")),
            ft.Segment(value="3", label=ft.Text("3. Pers.")),
        ],
    )
    seg_numbers = ft.SegmentedButton(
        allow_multiple_selection=True,
        show_selected_icon=True,
        selected=[n for n in s.numbers if n in NUMBER_NAMES] or ["sg"],
        segments=[
            ft.Segment(value="sg", label=ft.Text("Singular")),
            ft.Segment(value="pl", label=ft.Text("Plural")),
        ],
    )
    tf_count = ft.TextField(
        label="Aufgabenanzahl", value=str(s.word_count),
        keyboard_type=ft.KeyboardType.NUMBER, width=160,
    )
    sw_repeat = ft.Switch(label="Fehler am Ende wiederholen", value=s.repeat_errors)
    sw_accent = ft.Switch(label="Akzentfehler tolerieren", value=s.accent_tolerant)
    error_text = ft.Text("", color=ft.Colors.ERROR)

    def refresh_info(e=None):
        verbs = conj.conjugatable_verbs(store.cards_for(dd_list.value))
        n_fut = sum(1 for _, v in verbs if conj.has_future(v))
        info_text.value = (f"{len(verbs)} konjugierbare Verben in dieser Liste "
                           f"· {n_fut} mit 2. Stamm (Futur)")
        nav.page.update()

    # Flet-0.85-Dropdowns feuern on_select (on_change existiert nicht)
    dd_list.on_select = refresh_info
    refresh_info()

    def multi_values(seg: ft.SegmentedButton) -> list[str]:
        sel = seg.selected
        if isinstance(sel, (list, set, tuple)):
            return list(sel)
        return [sel] if sel else []

    def current_settings() -> ConjugationSettings | None:
        try:
            count = max(1, int(tf_count.value))
        except (TypeError, ValueError):
            error_text.value = "Bitte eine gültige Aufgabenanzahl eingeben."
            nav.page.update()
            return None
        persons = [p for p in conj.PERSONS if str(p) in multi_values(seg_persons)]
        numbers = [n for n in ("sg", "pl") if n in multi_values(seg_numbers)]
        if not persons or not numbers:
            error_text.value = "Bitte mindestens eine Person und eine Zahl wählen."
            nav.page.update()
            return None
        tenses = [t for t in conj.TENSES if t in multi_values(seg_tenses)]
        if not tenses:
            error_text.value = "Bitte mindestens eine Zeitform wählen."
            nav.page.update()
            return None
        mode_sel = multi_values(seg_mode)
        return ConjugationSettings(
            mode=mode_sel[0] if mode_sel else "typing",
            word_count=count,
            persons=persons,
            numbers=numbers,
            tenses=tenses,
            repeat_errors=sw_repeat.value,
            accent_tolerant=sw_accent.value,
            list_id=dd_list.value,
        )

    def new_selection(e):
        from mathainoa1.ui.views.manager import selection_editor

        def on_saved(sel):
            # Setup-Seite neu aufbauen und die neue Auswahlliste vorwählen
            nav.stack[-2] = ("Verbtraining",
                             conjugation_setup_view(nav, store, progress,
                                                    preselect_id=sel.id))
            nav.back()

        nav.go("Neue Auswahlliste",
               selection_editor(nav, store, None, on_saved, progress))

    def show_words(e):
        settings = current_settings()
        if settings is None:
            return
        verbs = conj.conjugatable_verbs(store.cards_for(settings.list_id))
        if not verbs:
            error_text.value = "Keine konjugierbaren Verben in dieser Liste."
            nav.page.update()
            return
        rows: list[ft.Control] = [
            _preview_header(nav, store, progress,
                            f"{store.name_for(settings.list_id)} — "
                            f"{len(verbs)} Verben", settings.list_id)
        ]
        for c, v in verbs:
            rows.append(ft.ListTile(
                dense=True,
                title=ft.Row([ft.Text(c.front, expand=1), ft.Text(c.back, expand=1)],
                             spacing=12),
                subtitle=ft.Text(_verb_sample(v), size=12),
            ))
        nav.go(f"Verben ({len(verbs)})",
               ft.Column(rows, spacing=4, scroll=ft.ScrollMode.AUTO))

    def start(e):
        settings = current_settings()
        if settings is None:
            return
        tasks = conj.generate_tasks(store.cards_for(settings.list_id), settings)
        if not tasks:
            error_text.value = (
                "Keine Verben mit 2. Stamm in dieser Liste — Futur braucht "
                "das Feld „2. Stamm“ in der Vokabelverwaltung."
                if settings.tenses == ["future"]
                else "Keine passenden Aufgaben für diese Auswahl gefunden.")
            nav.page.update()
            return
        save_conjugation_settings(settings)
        session = _make_session(tasks, settings)
        nav.go("Verbtraining", run_view(
            nav, store, session, title="Verbtraining",
            make_tasks=lambda s: conj.generate_tasks(store.cards_for(s.list_id), s)))

    return ft.Column(
        [
            dd_list,
            ft.Row([ft.TextButton("Neue Auswahlliste erstellen…",
                                  icon=ft.Icons.PLAYLIST_ADD, on_click=new_selection)]),
            info_text,
            ft.Divider(),
            ft.Row([seg_mode, tf_count], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            seg_tenses,
            seg_persons,
            seg_numbers,
            sw_repeat, sw_accent,
            error_text,
            ft.Row(
                [
                    ft.FilledButton("Training starten", icon=ft.Icons.PLAY_ARROW,
                                    on_click=start),
                    ft.OutlinedButton("Verben anzeigen", icon=ft.Icons.LIST,
                                      on_click=show_words),
                ],
                spacing=8, wrap=True,
            ),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )


def run_view(nav, store: ContentStore, session: DeclensionSession,
             title: str, make_tasks) -> ft.Control:
    """Trainingsrunde — gemeinsam für Deklination und Konjugation.

    make_tasks(settings) erzeugt die Aufgaben für "Neue Runde".
    """
    progress_label = ft.Text("", size=13)
    round_label = ft.Text("", size=13, color=ft.Colors.PRIMARY)
    prompt = ft.Text("", size=28, weight=ft.FontWeight.BOLD,
                     text_align=ft.TextAlign.CENTER)
    task_label = ft.Text("", size=16, color=ft.Colors.PRIMARY,
                         weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    meaning = ft.Text("", size=14, italic=True, text_align=ft.TextAlign.CENTER)
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

    tf_answer = ft.TextField(label="Antwort", autofocus=True,
                             on_submit=lambda e: check(e))

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
            show_task()  # aktuelle (unbeantwortete) Aufgabe im neuen Modus anzeigen

    seg_mode.on_change = switch_mode

    def show_task():
        task = session.current
        if task is None:
            nav.go("Ergebnis", result_view(nav, store, session, title, make_tasks))
            return
        done = len(session.answers)
        total = done + len(session.queue)
        progress_label.value = f"Aufgabe {done + 1} von {total}"
        round_label.value = "Fehlerrunde" if session.in_repeat_round else ""
        prompt.value = task.prompt
        task_label.value = f"→ {task.label}"
        meaning.value = task.meaning
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
            action_area.controls = [
                tf_answer,
                ft.FilledButton("Prüfen", icon=ft.Icons.CHECK, on_click=check),
            ]
        nav.page.update()
        if session.settings.mode == "typing":
            focus_answer()

    def reveal(e):
        task = session.current
        answer.value = task.expected
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
        nav.page.update()

    def judge(correct: bool):
        session.mark(correct)
        show_task()

    def check(e):
        task = session.current
        display = task.expected
        given = tf_answer.value or ""
        result = session.check_typed(given)
        weiter = ft.FilledButton("Weiter", icon=ft.Icons.ARROW_FORWARD,
                                 on_click=lambda e: show_task(), autofocus=True)
        if result == Result.CORRECT:
            feedback.value = "Richtig!"
            feedback.color = ft.Colors.GREEN
            action_area.controls = [weiter]
        elif result == Result.ALMOST:
            if session.settings.accent_tolerant:
                feedback.value = "Fast! Achte auf Akzente/Schluss-ς."
            else:
                feedback.value = "Fast — Akzent stimmt nicht"
            feedback.color = ft.Colors.ORANGE
            action_area.controls = [weiter]
        elif result == Result.CASE:
            feedback.value = "Fast — Groß-/Kleinschreibung beachten"
            feedback.color = ft.Colors.ORANGE
            action_area.controls = [weiter]
        else:
            feedback.value = ""
            btn_wrong.visible = True

            def show_own(e, g=given):
                wrong_label.value = "Meine Antwort:"
                wrong_eye.visible = False
                own_answer.value = g if g.strip() else "(leer)"
                own_answer.visible = True
                nav.page.update()

            btn_wrong.on_click = show_own
            # Abstand, damit man nicht versehentlich "Weiter" trifft
            action_area.controls = [ft.Container(height=24), weiter]
        answer.value = display
        nav.page.update()

    show_task()
    return ft.Column(
        [
            ft.Row([progress_label, round_label],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            seg_mode,
            ft.Container(prompt, padding=ft.Padding.only(top=20)),
            task_label, meaning,
            answer, feedback, btn_wrong, own_answer,
            action_area,
        ],
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )


def result_view(nav, store: ContentStore, session: DeclensionSession,
                title: str, make_tasks) -> ft.Control:
    stats = session.stats()
    wrong_items = [
        ft.ListTile(
            title=ft.Text(f"{t.prompt} → {t.expected}"),
            subtitle=ft.Text(" · ".join(x for x in (t.label, t.meaning) if x)),
            leading=ft.Icon(ft.Icons.CLOSE, color=ft.Colors.ERROR),
        )
        for t in stats["wrong_tasks"]
    ]

    def again(e):
        nav.stack.pop()  # Ergebnis-View ersetzen statt stapeln
        nav.stack.pop()  # alte Trainings-View entfernen
        settings = session.settings
        # Fehler der Vorrunde kommen garantiert wieder mit in die neue
        # Runde und werden zwischen die übrigen Aufgaben gemischt
        wrong = stats["wrong_tasks"]
        seen = {(t.prompt, t.expected) for t in wrong}
        fill = [t for t in make_tasks(settings)
                if (t.prompt, t.expected) not in seen]
        tasks = (wrong + fill)[: max(1, settings.word_count)]
        random.shuffle(tasks)
        session2 = _make_session(tasks, settings, on_result=session.on_result)
        nav.go(title, run_view(nav, store, session2, title, make_tasks))

    def home(e):
        del nav.stack[1:]
        nav._show()

    return ft.Column(
        [
            ft.Text(f"{stats['correct']} von {stats['total']} richtig",
                    size=24, weight=ft.FontWeight.BOLD),
            ft.ProgressBar(value=stats["correct"] / max(1, stats["total"])),
            ft.Text("Falsche Aufgaben:" if wrong_items else "Alles richtig — μπράβο! 🎉"),
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
