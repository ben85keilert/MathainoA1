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
from mathainoa1.logic.answer_check import Result, almost_kind, check_greek
from mathainoa1.logic.conjugation import ConjugationSettings
from mathainoa1.logic.declension import (
    CASE_NAMES,
    NUMBER_NAMES,
    DeclensionSession,
    DeclensionSettings,
)
from mathainoa1.models import SelectionList
from mathainoa1.storage.adjective_combos import (
    combo_key,
    load_combos,
    prune_combos,
    save_combos,
)
from mathainoa1.storage.content import ContentStore, filter_level
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.storage.settings import (
    load_adjective_settings,
    load_app_settings,
    load_conjugation_settings,
    load_declension_settings,
    save_adjective_settings,
    save_conjugation_settings,
    save_declension_settings,
)
from mathainoa1.ui.audio import autoplay_button, maybe_autoplay, speaker_button
from mathainoa1.storage.textanalyse import etymology_for
from mathainoa1.ui.views.reference import has_word_forms
from mathainoa1.ui.views.trainer import (
    almost_feedback,
    edit_notes_dialog,
    hide_empty_texts,
    show_word_details,
    typing_controls,
    update_word_details_button,
)
from mathainoa1.ui.scale import sz


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
                    title: str, source_id: str,
                    extra: list[ft.Control] | None = None) -> ft.Control:
    """Kopfzeile der Wörter-/Verben-Vorschau: Titel + „Liste bearbeiten“."""
    from mathainoa1.ui.views.manager import open_source_editor
    return ft.Row(
        [
            ft.Text(title, size=sz(16), weight=ft.FontWeight.BOLD, expand=True),
            *(extra or []),
            ft.OutlinedButton(
                "Liste bearbeiten", icon=ft.Icons.EDIT_OUTLINED,
                on_click=lambda e: open_source_editor(
                    nav, store, progress, source_id)),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _grouped_word_rows(nav, store: ContentStore, source_id: str,
                       items: list, tile,
                       all_progress=None) -> tuple[list[ft.Control],
                                                   ft.Control]:
    """Wortzeilen der Vorschau mit einheitlichen Sortier-Umschaltern
    (alphabetisch, nach Lernstand — wie in den anderen Listenansichten).

    items: Paare (card, obj); tile(card, obj) -> ft.Control. Bei
    Auswahllisten stehen die Wörter unter der Überschrift ihrer
    Ursprungsliste. Gibt (Umschalt-Buttons, Spalte) zurück — die
    Buttons gehören in die Kopfzeile."""
    from mathainoa1.ui.views.wordlist import (
        alpha_key,
        box_of,
        group_heading,
        origin_names,
    )
    grouped = source_id in store.selections
    all_progress = all_progress or {}
    state = {"alpha": False, "progress": False}
    body = ft.Column(spacing=0)
    alpha_btn = ft.IconButton(
        ft.Icons.SORT_BY_ALPHA,
        tooltip="Alphabetisch sortieren"
        + (" (über alle Ursprungslisten)" if grouped else ""),
    )
    progress_btn = ft.IconButton(
        ft.Icons.SORT,
        tooltip="Nach Lernstand sortieren (schlechteste zuerst)",
    )

    def _wrong_of(card) -> int:
        p = all_progress.get(card.id)
        return p.wrong if p else 0

    def rebuild():
        alpha_btn.icon_color = ft.Colors.PRIMARY if state["alpha"] else None
        progress_btn.icon_color = (ft.Colors.PRIMARY if state["progress"]
                                   else None)
        if state["alpha"]:
            body.controls = [tile(c, o) for c, o in
                             sorted(items, key=lambda t: alpha_key(t[0]))]
        elif state["progress"]:
            body.controls = [tile(c, o) for c, o in
                             sorted(items,
                                    key=lambda t: (box_of(t[0], all_progress),
                                                   -_wrong_of(t[0])))]
        elif grouped:
            names = origin_names(store)
            groups: dict[str, list] = {}
            for c, o in items:
                groups.setdefault(names.get(c.id, "Unbekannte Liste"),
                                  []).append((c, o))
            rows: list[ft.Control] = []
            for name, group in groups.items():
                rows.append(group_heading(name))
                rows += [tile(c, o) for c, o in group]
            body.controls = rows
        else:
            body.controls = [tile(c, o) for c, o in items]

    def toggle_alpha(e):
        state["alpha"] = not state["alpha"]
        state["progress"] = False
        rebuild()
        nav.page.update()

    def toggle_progress(e):
        state["progress"] = not state["progress"]
        state["alpha"] = False
        rebuild()
        nav.page.update()

    alpha_btn.on_click = toggle_alpha
    progress_btn.on_click = toggle_progress
    rebuild()
    return [alpha_btn, progress_btn], body


def setup_view(nav, store: ContentStore, progress: ProgressStore,
               preselect_id: str | None = None) -> ft.Control:
    s = load_declension_settings()
    lists = filter_level(
        sorted(store.lists.values(),
               key=lambda l: (l.chapter is None, l.chapter or 0, l.name)),
        load_app_settings().level)
    selections = store.selections_of()
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
    info_text = ft.Text("", size=sz(13))
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
        allow_empty_selection=True,  # sonst rote Flet-Meldung beim Abwählen
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
        allow_empty_selection=True,
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
    sw_case = ft.Switch(label="Groß-/Kleinschreibung tolerieren (nur Nomen)",
                        value=s.case_tolerant)
    error_text = ft.Text("", color=ft.Colors.ERROR)

    def refresh_info(e=None):
        cards = store.cards_for(dd_list.value)
        nouns = decl.declinable_nouns(cards)
        info_text.value = f"{len(nouns)} deklinierbare Nomen in dieser Liste"
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

        def noun_tile(c, n) -> ft.Control:
            acc = decl.decline(n, "acc", "sg")
            gen = decl.decline(n, "gen", "sg")
            sub = " · ".join(
                f"{CASE_NAMES[case]}: {decl.ARTICLES[(case, 'sg')][n.gender]} {f}"
                for case, f in (("acc", acc), ("gen", gen)) if f
            ) or "nur Plural"
            return ft.ListTile(
                dense=True,
                title=ft.Row([ft.Text(c.front, expand=1), ft.Text(c.back, expand=1)],
                             spacing=12),
                subtitle=ft.Text(sub, size=sz(12)),
            )

        sort_btns, word_rows = _grouped_word_rows(
            nav, store, settings.list_id, nouns, noun_tile,
            all_progress=progress.all())
        rows: list[ft.Control] = [
            _preview_header(nav, store, progress,
                            f"{store.name_for(settings.list_id)} — "
                            f"{len(nouns)} Nomen", settings.list_id,
                            extra=sort_btns),
            word_rows,
        ]
        nav.go(f"Wörter ({len(nouns)})",
               ft.Column(rows, spacing=4, scroll=ft.ScrollMode.AUTO))

    def start(e):
        settings = current_settings()
        if settings is None:
            return
        tasks = decl.generate_tasks(store.cards_for(settings.list_id), settings)
        if not tasks:
            error_text.value = "Keine passenden Aufgaben für diese Auswahl gefunden."
            if settings.cases == ["nom"] and settings.numbers == ["sg"]:
                # Nominativ Singular steht schon in der Aufgabe und wird
                # nie abgefragt — diese Kombination ist immer leer
                error_text.value = ("Nominativ wird nur im Plural abgefragt — "
                                    "bitte Plural dazuwählen.")
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

    def edit_list(e):
        from mathainoa1.ui.views.manager import open_source_editor
        if dd_list.value:
            open_source_editor(nav, store, progress, dd_list.value)

    root = ft.Column(
        [
            # Lautsprecher (Auto-Vorlesen) oben rechts wie in der Übung;
            # gespeichert wie die anderen Einstellungen (app_settings.json)
            ft.Row([ft.Container(dd_list, expand=True),
                    ft.IconButton(icon=ft.Icons.EDIT_OUTLINED,
                                  tooltip="Liste bearbeiten",
                                  on_click=edit_list),
                    autoplay_button(nav.page)],
                   spacing=8,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([ft.TextButton("Neue Auswahlliste erstellen…",
                                  icon=ft.Icons.PLAYLIST_ADD, on_click=new_selection)]),
            info_text,
            ft.Divider(),
            ft.Row([seg_mode, tf_count], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            seg_direction,
            seg_cases,
            seg_numbers,
            sw_repeat, sw_accent, sw_case,
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
    # Beim Zurückkehren aus dem Editor die Nomen-Zählung auffrischen
    root.on_reappear = refresh_info
    return root


def adjective_setup_view(nav, store: ContentStore, progress: ProgressStore,
                         preselect_id: str | None = None) -> ft.Control:
    """Adjektivtraining: dekliniert werden nur kuratierte Adjektiv↔Nomen-
    Verbindungen (combos_view). Trainierbar sind normale Listen (es zählen
    ihre Adjektive) und eigene Adjektiv-Auswahllisten (nur hier sichtbar)."""
    s = load_adjective_settings()
    app_settings = load_app_settings()
    combos_mode = app_settings.adjective_combos_mode
    lists = filter_level(
        sorted(store.lists.values(),
               key=lambda l: (l.chapter is None, l.chapter or 0, l.name)),
        app_settings.level)
    selections = store.selections_of("adjektive")
    if not lists and not selections:
        return ft.Text("Keine Vokabellisten gefunden.")
    valid_ids = {l.id for l in lists} | {x.id for x in selections}
    if preselect_id and preselect_id in valid_ids:
        s.list_id = preselect_id
    if s.list_id not in valid_ids:
        s.list_id = lists[0].id if lists else selections[0].id

    dd_list = ft.Dropdown(
        label="Liste",
        value=s.list_id,
        options=[ft.DropdownOption(key=l.id, text=l.name) for l in lists]
        + [ft.DropdownOption(key=x.id, text=f"★ {x.name}") for x in selections],
    )
    info_text = ft.Text("", size=sz(13))
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
        allow_empty_selection=True,
        show_selected_icon=True,
        selected=[c for c in s.cases if c in CASE_NAMES] or ["acc"],
        segments=[
            ft.Segment(value="nom", label=ft.Text("Nominativ (Pl.)")),
            ft.Segment(value="acc", label=ft.Text("Akkusativ")),
            ft.Segment(value="gen", label=ft.Text("Genitiv")),
        ],
    )
    seg_numbers = ft.SegmentedButton(
        allow_multiple_selection=True,
        allow_empty_selection=True,
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
    sw_case = ft.Switch(label="Groß-/Kleinschreibung tolerieren (nur Nomen)",
                        value=s.case_tolerant)
    error_text = ft.Text("", color=ft.Colors.ERROR)

    def adj_items():
        return decl.usable_adjective_cards(store.cards_for(dd_list.value))

    def refresh_info(e=None):
        items = adj_items()
        pairs, blocked = load_combos()
        keys = {combo_key(a.word) for _, a in items}
        if combos_mode == "blacklist":
            n = sum(len(v) for k, v in blocked.items() if k in keys)
            info_text.value = f"{len(items)} Adjektive · {n} Ausnahmen"
        else:
            n = sum(len(v) for k, v in pairs.items() if k in keys)
            info_text.value = (f"{len(items)} Adjektive · "
                               f"{n} aktivierte Verbindungen")
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
            repeat_errors=sw_repeat.value,
            accent_tolerant=sw_accent.value,
            case_tolerant=sw_case.value,
            list_id=dd_list.value,
        )

    def new_selection(e):
        from mathainoa1.ui.views.manager import selection_editor

        def on_saved(sel):
            nav.stack[-2] = ("Adjektivtraining",
                             adjective_setup_view(nav, store, progress,
                                                  preselect_id=sel.id))
            nav.back()

        # kind="adjektive": die Liste erscheint nur im Adjektivtraining
        nav.go("Neue Adjektiv-Auswahlliste",
               selection_editor(nav, store,
                                SelectionList(name="", kind="adjektive"),
                                on_saved, progress))

    def open_combos(e):
        title = ("Ausnahmen: Adjektiv ↔ Nomen"
                 if combos_mode == "blacklist" else "Adjektiv ↔ Nomen")
        nav.go(title, combos_view(nav, store, dd_list.value, combos_mode))

    def _prune_against_all() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
        """Combos laden und tote Verbindungen entfernen (Wort weg = weg)."""
        pairs, blocked = load_combos()
        all_cards = store.all_cards()
        valid_adj = {combo_key(a.word)
                     for _, a in decl.usable_adjective_cards(all_cards)}
        valid_nouns = {combo_key(n.word)
                       for _, n in decl.declinable_nouns(all_cards)}
        if prune_combos(pairs, blocked, valid_adj, valid_nouns):
            save_combos(pairs, blocked)
        return pairs, blocked

    def noun_pool(list_id) -> tuple[list, bool]:
        """Blacklisting-Nomenquelle: Nomen der gewählten Liste — hat sie
        keine (reine Adjektivliste), alle Nomen der App (True = Fallback)."""
        nouns = decl.declinable_nouns(store.cards_for(list_id))
        if nouns:
            return nouns, False
        return decl.declinable_nouns(store.all_cards()), True

    def build_tasks(st: DeclensionSettings, items, pairs, blocked,
                    notify: bool = False):
        if combos_mode == "blacklist":
            nouns, fallback = noun_pool(st.list_id)
            if fallback and notify and nouns:
                nav.page.show_dialog(ft.SnackBar(ft.Text(
                    "Die Liste enthält keine Nomen — kombiniert wird mit "
                    "allen Nomen der App."),
                    duration=ft.Duration(milliseconds=1500)))
            return decl.generate_adjective_tasks(
                items, nouns, blocked, st, mode="blacklist")
        return decl.generate_adjective_tasks(
            items, decl.declinable_nouns(store.all_cards()), pairs, st)

    def make_tasks(st: DeclensionSettings):
        pairs, blocked = load_combos()
        return build_tasks(
            st, decl.usable_adjective_cards(store.cards_for(st.list_id)),
            pairs, blocked)

    def start(e):
        settings = current_settings()
        if settings is None:
            return
        items = adj_items()
        if not items:
            error_text.value = "Keine Adjektive in dieser Auswahl."
            nav.page.update()
            return
        pairs, blocked = _prune_against_all()
        tasks = build_tasks(settings, items, pairs, blocked, notify=True)
        if not tasks:
            if settings.cases == ["nom"] and settings.numbers == ["sg"]:
                error_text.value = ("Nominativ wird nur im Plural abgefragt — "
                                    "bitte Plural dazuwählen.")
            elif combos_mode == "blacklist":
                error_text.value = (
                    "Keine Aufgaben — alle Kombinationen sind als "
                    "Ausnahme ausgeschlossen (oder es gibt keine Nomen).")
            else:
                error_text.value = (
                    "Keine Aufgaben — bitte zuerst über „Verbindungen "
                    "festlegen…“ Nomen für die Adjektive aktivieren.")
            nav.page.update()
            return
        save_adjective_settings(settings)
        session = _make_session(tasks, settings)
        nav.go("Adjektivtraining", run_view(
            nav, store, session, title="Adjektivtraining",
            make_tasks=make_tasks))

    def edit_list(e):
        from mathainoa1.ui.views.manager import open_source_editor
        if dd_list.value:
            open_source_editor(nav, store, progress, dd_list.value)

    if combos_mode == "blacklist":
        combos_label, combos_icon = "Ausnahmen festlegen…", ft.Icons.LINK_OFF
        hint = ("Abgefragt werden alle Adjektiv↔Nomen-Kombinationen der "
                "Liste — außer den festgelegten Ausnahmen (gelten "
                "listenübergreifend).")
    else:
        combos_label, combos_icon = "Verbindungen festlegen…", ft.Icons.LINK
        hint = ("Abgefragt werden nur aktivierte Adjektiv↔Nomen-"
                "Verbindungen (gelten listenübergreifend).")

    root = ft.Column(
        [
            ft.Row([ft.Container(dd_list, expand=True),
                    ft.IconButton(icon=ft.Icons.EDIT_OUTLINED,
                                  tooltip="Liste bearbeiten",
                                  on_click=edit_list),
                    autoplay_button(nav.page)],
                   spacing=8,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([ft.TextButton("Neue Adjektiv-Auswahlliste erstellen…",
                                  icon=ft.Icons.PLAYLIST_ADD,
                                  on_click=new_selection)]),
            ft.Row([ft.TextButton(combos_label,
                                  icon=combos_icon, on_click=open_combos)]),
            info_text,
            ft.Text(hint, size=sz(13), italic=True),
            ft.Divider(),
            ft.Row([seg_mode, tf_count], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            seg_direction,
            seg_cases,
            seg_numbers,
            sw_repeat, sw_accent, sw_case,
            error_text,
            ft.Row(
                [
                    ft.FilledButton("Training starten", icon=ft.Icons.PLAY_ARROW,
                                    on_click=start),
                ],
                spacing=8, wrap=True,
            ),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )
    # Beim Zurückkehren (Verbindungen/Editor) die Zählerzeile auffrischen
    root.on_reappear = refresh_info
    return root


def combos_view(nav, store: ContentStore, source_id: str | None = None,
                mode: str = "whitelist") -> ft.Control:
    """Kuration der Adjektiv↔Nomen-Verbindungen: Adjektiv wählen, Listen
    durchblättern, Nomen antippen. Whitelisting aktiviert Verbindungen,
    Blacklisting sperrt Ausnahmen. Wortbasiert — eine Verbindung gilt
    überall, egal aus welcher Liste die Karten stammen. source_id: nur
    die Adjektive dieser Liste stehen zur Auswahl (None = alle)."""
    page = nav.page
    blacklist = mode == "blacklist"
    pairs, blocked = load_combos()
    active_dict = blocked if blacklist else pairs
    all_cards = store.all_cards()
    adj_cards = (store.cards_for(source_id) if source_id else all_cards)
    by_key: dict[str, tuple] = {}
    for c, a in decl.usable_adjective_cards(adj_cards):
        by_key.setdefault(combo_key(a.word), (c, a))
    if not by_key:
        return ft.Text("Keine Adjektive in der gewählten Liste gefunden.")
    # tote Verbindungen gleich aufräumen (Gültigkeit ist app-weit)
    valid_adj = {combo_key(a.word)
                 for _, a in decl.usable_adjective_cards(all_cards)}
    valid_nouns = {combo_key(n.word)
                   for _, n in decl.declinable_nouns(all_cards)}
    if prune_combos(pairs, blocked, valid_adj, valid_nouns):
        save_combos(pairs, blocked)

    adj_sorted = sorted(by_key.items(), key=lambda kv: kv[0])
    dd_adj = ft.Dropdown(
        label="Adjektiv",
        value=adj_sorted[0][0],
        options=[ft.DropdownOption(
            key=k, text=f"{a.word} — {a.meaning}" if a.meaning else a.word)
            for k, (_c, a) in adj_sorted],
    )
    lists = filter_level(
        sorted(store.lists.values(),
               key=lambda l: (l.chapter is None, l.chapter or 0, l.name)),
        load_app_settings().level)
    selections = store.selections_of()
    noun_list_ids = {l.id for l in lists} | {x.id for x in selections}
    dd_list = ft.Dropdown(
        label="Nomen aus Liste",
        # die Trainingsliste vorwählen, wenn sie Nomen liefern kann
        value=(source_id if source_id in noun_list_ids
               else lists[0].id if lists
               else (selections[0].id if selections else None)),
        options=[ft.DropdownOption(key=l.id, text=l.name) for l in lists]
        + [ft.DropdownOption(key=x.id, text=f"★ {x.name}") for x in selections],
    )
    count_text = ft.Text("", size=sz(13))
    body = ft.Column(spacing=0)

    def current_adj():
        return by_key[dd_adj.value][1]

    def nouns_for_list() -> list[tuple]:
        seen: set[str] = set()
        result = []
        for c, n in decl.declinable_nouns(store.cards_for(dd_list.value)):
            key = combo_key(n.word)
            if key in seen:
                continue
            seen.add(key)
            result.append((key, c, n))
        return result

    def toggle(noun_key: str):
        akey = combo_key(current_adj().word)
        active = active_dict.setdefault(akey, set())
        if noun_key in active:
            active.discard(noun_key)
            if not active:
                del active_dict[akey]
        else:
            active.add(noun_key)
        save_combos(pairs, blocked)
        refresh()

    def set_all(on: bool):
        akey = combo_key(current_adj().word)
        keys = {k for k, _c, _n in nouns_for_list()}
        if on:
            active_dict.setdefault(akey, set()).update(keys)
        else:
            active = active_dict.get(akey)
            if active:
                active -= keys
                if not active:
                    del active_dict[akey]
        save_combos(pairs, blocked)
        refresh()

    def refresh(e=None):
        adj = current_adj()
        akey = combo_key(adj.word)
        active = active_dict.get(akey, set())
        tiles: list[ft.Control] = []
        for key, c, n in nouns_for_list():
            on = key in active
            base_number = "pl" if n.plural_only else "sg"
            art = decl.ARTICLES[("nom", base_number)][n.gender]
            phrase = (f"{art} "
                      f"{decl.decline_adjective(adj, n.gender, 'nom', base_number)} "
                      f"{n.word}")
            if blacklist:
                leading = ft.Icon(
                    ft.Icons.BLOCK if on else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
                    color=ft.Colors.ERROR if on else None)
                bgcolor = ft.Colors.ERROR_CONTAINER if on else None
            else:
                leading = ft.Icon(
                    ft.Icons.CHECK_BOX if on
                    else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
                    color=ft.Colors.PRIMARY if on else None)
                bgcolor = ft.Colors.PRIMARY_CONTAINER if on else None
            tiles.append(ft.ListTile(
                # key je Zustand: harter Austausch statt träger Animation
                # (gleiches Muster wie die Mehrfachauswahl der Verwaltung)
                key=f"combo-{c.id}-{int(on)}",
                dense=True,
                leading=leading,
                title=ft.Row([ft.Text(c.front, expand=1),
                              ft.Text(c.back, expand=1)], spacing=8),
                subtitle=ft.Text(phrase, size=sz(12)),
                bgcolor=bgcolor,
                on_click=lambda e, k=key: toggle(k),
            ))
        if blacklist:
            count_text.value = (f"{len(active)} Ausnahmen für „{adj.word}“ "
                                "gesperrt (über alle Listen)")
        else:
            count_text.value = (f"{len(active)} Verbindungen für „{adj.word}“ "
                                "aktiv (über alle Listen)")
        body.controls = tiles or [ft.Text(
            "Keine deklinierbaren Nomen in dieser Liste.", italic=True)]
        page.update()

    # Flet-0.85-Dropdowns feuern on_select (on_change existiert nicht)
    dd_adj.on_select = refresh
    dd_list.on_select = refresh
    refresh()
    if blacklist:
        intro = ("Antippen sperrt/entsperrt ein Nomen für das gewählte "
                 "Adjektiv — gesperrte Kombinationen (Ausnahmen) werden "
                 "im Adjektivtraining nicht abgefragt.")
        all_on, all_off = "Alle sperren", "Alle freigeben"
    else:
        intro = ("Antippen aktiviert/deaktiviert ein Nomen für das "
                 "gewählte Adjektiv — nur aktivierte Verbindungen "
                 "werden im Adjektivtraining abgefragt.")
        all_on, all_off = "Alle an", "Alle aus"
    return ft.Column(
        [
            ft.Text(intro, size=sz(13), italic=True),
            dd_adj,
            ft.Row([ft.Container(dd_list, expand=True),
                    ft.TextButton(all_on,
                                  on_click=lambda e: set_all(True)),
                    ft.TextButton(all_off,
                                  on_click=lambda e: set_all(False))],
                   spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            count_text,
            body,
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def conjugation_setup_view(nav, store: ContentStore, progress: ProgressStore,
                           preselect_id: str | None = None) -> ft.Control:
    s = load_conjugation_settings()
    lists = filter_level(
        sorted(store.lists.values(),
               key=lambda l: (l.chapter is None, l.chapter or 0, l.name)),
        load_app_settings().level)
    selections = store.selections_of()
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
    info_text = ft.Text("", size=sz(13))
    seg_mode = ft.SegmentedButton(
        selected=[s.mode],
        segments=[
            ft.Segment(value="flashcard", label=ft.Text("Karteikarte"),
                       icon=ft.Icons.STYLE),
            ft.Segment(value="typing", label=ft.Text("Schreiben"),
                       icon=ft.Icons.KEYBOARD),
        ],
    )
    # Vorgabe: griechisches Lemma (leichter) oder deutscher Infinitiv.
    # Bei Griechisch entfällt die 1. Person Singular Präsens — sie ist
    # als Lemma ja schon zu sehen.
    seg_direction = ft.SegmentedButton(
        selected=[s.direction if s.direction in ("gr", "de") else "de"],
        segments=[
            ft.Segment(value="gr", label=ft.Text("Griechisch"),
                       icon=ft.Icons.TRANSLATE),
            ft.Segment(value="de", label=ft.Text("Deutsch"),
                       icon=ft.Icons.PSYCHOLOGY),
        ],
    )
    seg_tenses = ft.SegmentedButton(
        allow_multiple_selection=True,
        allow_empty_selection=True,  # sonst rote Flet-Meldung beim Abwählen
        show_selected_icon=True,
        selected=[t for t in s.tenses if t in conj.TENSES] or ["present"],
        segments=[
            ft.Segment(value="present", label=ft.Text("Präsens")),
            ft.Segment(value="future", label=ft.Text("Futur (θα)")),
        ],
    )
    seg_persons = ft.SegmentedButton(
        allow_multiple_selection=True,
        allow_empty_selection=True,
        show_selected_icon=True,
        selected=[str(p) for p in s.persons if p in conj.PERSONS] or ["1", "2", "3"],
        segments=[
            ft.Segment(value="1", label=ft.Text("1. Pers.")),
            # 2. Pl. ist zugleich die höfliche Anrede ("Sie")
            ft.Segment(value="2", label=ft.Text("2. Pers.")),
            ft.Segment(value="3", label=ft.Text("3. Pers.")),
        ],
    )
    seg_numbers = ft.SegmentedButton(
        allow_multiple_selection=True,
        allow_empty_selection=True,
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
        dir_sel = multi_values(seg_direction)
        return ConjugationSettings(
            mode=mode_sel[0] if mode_sel else "typing",
            direction=dir_sel[0] if dir_sel else "de",
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
        def verb_tile(c, v) -> ft.Control:
            return ft.ListTile(
                dense=True,
                title=ft.Row([ft.Text(c.front, expand=1), ft.Text(c.back, expand=1)],
                             spacing=12),
                subtitle=ft.Text(_verb_sample(v), size=sz(12)),
            )

        sort_btns, word_rows = _grouped_word_rows(
            nav, store, settings.list_id, verbs, verb_tile,
            all_progress=progress.all())
        rows: list[ft.Control] = [
            _preview_header(nav, store, progress,
                            f"{store.name_for(settings.list_id)} — "
                            f"{len(verbs)} Verben", settings.list_id,
                            extra=sort_btns),
            word_rows,
        ]
        nav.go(f"Verben ({len(verbs)})",
               ft.Column(rows, spacing=4, scroll=ft.ScrollMode.AUTO))

    def start(e):
        settings = current_settings()
        if settings is None:
            return
        tasks = conj.generate_tasks(store.cards_for(settings.list_id), settings)
        if not tasks:
            if settings.tenses == ["future"]:
                error_text.value = (
                    "Keine Verben mit 2. Stamm in dieser Liste — Futur "
                    "braucht das Feld „2. Stamm“ in der Vokabelverwaltung.")
            elif (settings.direction == "gr" and settings.persons == [1]
                    and settings.numbers == ["sg"]):
                error_text.value = (
                    "Bei griechischer Vorgabe wird die 1. Person Singular "
                    "Präsens nicht abgefragt — sie steht ja schon da. "
                    "Bitte weitere Personen/Zahlen wählen.")
            else:
                error_text.value = ("Keine passenden Aufgaben für diese "
                                    "Auswahl gefunden.")
            nav.page.update()
            return
        save_conjugation_settings(settings)
        session = _make_session(tasks, settings)
        nav.go("Verbtraining", run_view(
            nav, store, session, title="Verbtraining",
            make_tasks=lambda s: conj.generate_tasks(store.cards_for(s.list_id), s)))

    def edit_list(e):
        from mathainoa1.ui.views.manager import open_source_editor
        if dd_list.value:
            open_source_editor(nav, store, progress, dd_list.value)

    root = ft.Column(
        [
            # Lautsprecher (Auto-Vorlesen) oben rechts wie in der Übung;
            # gespeichert wie die anderen Einstellungen (app_settings.json)
            ft.Row([ft.Container(dd_list, expand=True),
                    ft.IconButton(icon=ft.Icons.EDIT_OUTLINED,
                                  tooltip="Liste bearbeiten",
                                  on_click=edit_list),
                    autoplay_button(nav.page)],
                   spacing=8,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([ft.TextButton("Neue Auswahlliste erstellen…",
                                  icon=ft.Icons.PLAYLIST_ADD, on_click=new_selection)]),
            info_text,
            ft.Divider(),
            ft.Row([seg_mode, tf_count], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            seg_direction,
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
    # Beim Zurückkehren aus dem Editor die Verb-Zählung auffrischen
    root.on_reappear = refresh_info
    return root


def run_view(nav, store: ContentStore, session: DeclensionSession,
             title: str, make_tasks) -> ft.Control:
    """Trainingsrunde — gemeinsam für Deklination und Konjugation.

    make_tasks(settings) erzeugt die Aufgaben für "Neue Runde".
    Die aufgedeckte Lösungsform (task.expected, z.B. "θα γράψετε" oder
    "τους μικρούς δρόμους") lässt sich anhören — die Sprachausgabe spricht
    auch gebeugte Formen, nicht nur die Grundform.
    """
    progress_label = ft.Text("", size=sz(13))
    round_label = ft.Text("", size=sz(13), color=ft.Colors.PRIMARY)
    prompt = ft.Text("", size=sz(28), weight=ft.FontWeight.BOLD,
                     text_align=ft.TextAlign.CENTER)
    task_label = ft.Text("", size=sz(16), color=ft.Colors.PRIMARY,
                         weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    meaning = ft.Text("", size=sz(14), italic=True, text_align=ft.TextAlign.CENTER)
    # Notizen/Hinweise der Karte — wie im Vokabeltrainer: vor der Antwort
    # nur die sichtbare Seite, nach dem Aufdecken beide Seiten
    notes_col = ft.Column(spacing=8,
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    answer = ft.Text("", size=sz(22), text_align=ft.TextAlign.CENTER)
    # Bei deutscher Vorgabe steht das griechische Wort nirgends — nach dem
    # Aufdecken die Grundform (Lemma/Nominativ) mit einblenden
    base_form = ft.Text("", size=sz(14), italic=True,
                        text_align=ft.TextAlign.CENTER)
    feedback = ft.Text("", size=sz(16), weight=ft.FontWeight.BOLD)
    # Bei falscher Antwort: rotes Kreuz + Label + Augensymbol; Klick blendet
    # die eigene Antwort darunter ein, das Label wird „Meine Antwort:" und
    # das Auge verschwindet
    own_answer = ft.Text("", size=sz(14), italic=True, color=ft.Colors.ERROR,
                         text_align=ft.TextAlign.CENTER, visible=False)
    wrong_label = ft.Text("Meine Antwort anzeigen", color=ft.Colors.ERROR)
    wrong_eye = ft.Icon(ft.Icons.VISIBILITY_OUTLINED, color=ft.Colors.ERROR,
                        size=sz(18))
    btn_wrong = ft.TextButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.CLOSE, color=ft.Colors.ERROR, size=sz(18)),
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
        shown["task"] = task
        done = len(session.answers)
        total = done + len(session.queue)
        progress_label.value = f"Aufgabe {done + 1} von {total}"
        round_label.value = "Fehlerrunde" if session.in_repeat_round else ""
        prompt.value = task.prompt
        task_label.value = f"→ {task.label}"
        meaning.value = task.meaning
        answer.value = ""
        base_form.value = ""
        session_answer["text"] = ""
        # Griechische Vorgabe: das Wort ist sichtbar, Anhören/Wort-Info
        # sofort erlaubt; die Beugungstabelle enthielte aber die Lösung
        # und kommt erst mit dem Aufdecken
        gr_visible = session.settings.direction == "gr"
        btn_word_play.visible = gr_visible
        word_state["forms"] = False
        update_word_details_button(
            btn_word, forms=False,
            info=gr_visible and etymology_for(task.card) is not None)
        refresh_notes(revealed=False)
        feedback.value = ""
        btn_wrong.visible = False
        wrong_label.value = "Meine Antwort anzeigen"
        wrong_eye.visible = True
        own_answer.visible = False
        own_answer.value = ""
        # Futur: das "θα" ist offensichtlich und steht schon vor dem
        # Antwortfeld — getippt wird nur die Verbform (zählt auch so,
        # die Varianten ohne θα sind ohnehin gültig)
        tf_answer.prefix = (
            ft.Text("θα ", size=sz(16))
            if getattr(task, "tense", None) == "future" else None)
        if session.settings.mode == "flashcard":
            action_area.controls = [ft.FilledButton("Zeigen", icon=ft.Icons.VISIBILITY,
                                                    on_click=reveal)]
        else:
            tf_answer.value = ""
            action_area.controls = typing_controls(tf_answer, check)
        hide_empty_texts(meaning, answer, base_form, feedback)
        nav.page.update()
        if session.settings.mode == "typing":
            focus_answer()

    # Die aktuell angezeigte Aufgabe — session.current kann schon weiter sein
    shown: dict = {"task": None}

    def speak_text() -> str:
        """Was der Lautsprecher spricht: die aufgedeckte Lösung, sonst
        die griechische Vorgabe (bei deutscher Vorgabe erst nach dem
        Aufdecken sichtbar)."""
        if session_answer["text"]:
            return session_answer["text"]
        return shown["task"].prompt if shown["task"] else ""

    # Symbolzeile wie im Vokabeltrainer unter der Aufgabe: Anhören,
    # Wort-Info/Beugungsformen (ein gemeinsames Symbol), Notizen bearbeiten.
    # Die Beugungstabelle bleibt bis zum Aufdecken gesperrt (word_state),
    # sie enthielte sonst die Lösung.
    btn_word_play = speaker_button(nav.page, speak_text)
    word_state = {"forms": False}

    def show_details(e):
        task = shown["task"]
        if task is None:
            return
        show_word_details(nav.page, task.card,
                          with_forms=word_state["forms"])

    btn_word = ft.IconButton(ft.Icons.INFO_OUTLINE, visible=False,
                             on_click=show_details)

    def edit_notes(e):
        task = shown["task"]
        if task is None:
            return
        edit_notes_dialog(nav.page, store, task.card,
                          on_saved=lambda: refresh_notes(
                              revealed=bool(answer.value)))

    btn_edit = ft.IconButton(ft.Icons.EDIT_NOTE,
                             tooltip="Hinweise/Notizen bearbeiten",
                             on_click=edit_notes)
    icons_row = ft.Row([btn_word_play, btn_word, btn_edit],
                       alignment=ft.MainAxisAlignment.CENTER, spacing=0)

    def refresh_notes(revealed: bool):
        task = shown["task"]
        if task is None:
            return
        card = task.card
        prompt_side = "gr" if session.settings.direction == "gr" else "de"
        sides = ["gr", "de"] if revealed else [prompt_side]

        def note_row(icon: str, text: str) -> ft.Row:
            return ft.Row(
                [ft.Icon(icon, size=sz(16), color=ft.Colors.PRIMARY),
                 ft.Text(text, size=sz(14), italic=True, expand=True)],
                spacing=6, vertical_alignment=ft.CrossAxisAlignment.START,
            )

        rows = []
        for side in sides:
            if card.notes_for(side):
                rows.append(note_row(ft.Icons.STICKY_NOTE_2_OUTLINED,
                                     card.notes_for(side)))
            if card.hints_for(side):
                rows.append(note_row(ft.Icons.LIGHTBULB_OUTLINE,
                                     card.hints_for(side)))
        notes_col.controls = rows
        nav.page.update()

    # Die zuletzt aufgedeckte Lösung — session.current kann schon weiter sein
    session_answer = {"text": "", "card": None}

    def solution_shown(task):
        # Die griechische Lösungsform ist jetzt sichtbar
        session_answer["text"] = task.expected
        session_answer["card"] = task.card
        btn_word_play.visible = True
        word_state["forms"] = has_word_forms(task.card)
        update_word_details_button(
            btn_word, forms=word_state["forms"],
            info=etymology_for(task.card) is not None)
        if session.settings.direction == "de":
            # Grundform mit anzeigen — bei deutscher Vorgabe stünde sie
            # sonst nirgends (z.B. "μένω" zu "μένετε")
            base_form.value = f"Grundform: {task.card.with_plural(task.card.front)}"
        hide_empty_texts(meaning, answer, base_form, feedback)
        refresh_notes(revealed=True)
        maybe_autoplay(nav.page, task.expected)

    def reveal(e):
        task = session.current
        answer.value = task.expected
        solution_shown(task)
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
            kinds = [almost_kind(x, given)
                     for x in [task.expected] + task.variants
                     if check_greek(x, given) == Result.ALMOST]
            kind = ("accent" if "accent" in kinds
                    else "sigma" if "sigma" in kinds else "both")
            feedback.value = almost_feedback(
                kind, session.settings.accent_tolerant)
            feedback.color = ft.Colors.ORANGE
            action_area.controls = [weiter]
        elif result == Result.CASE:
            feedback.value = "Fast — Groß-/Kleinschreibung beachten"
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
        solution_shown(task)
        nav.page.update()

    show_task()
    return ft.Column(
        [
            ft.Row([progress_label, round_label,
                    autoplay_button(nav.page)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            seg_mode,
            ft.Container(prompt, padding=ft.Padding.only(top=8)),
            task_label, meaning,
            notes_col,
            icons_row,
            answer, base_form,
            feedback, btn_wrong, own_answer,
            action_area,
        ],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )


def result_view(nav, store: ContentStore, session: DeclensionSession,
                title: str, make_tasks) -> ft.Control:
    stats = session.stats()
    # Bei deutscher Vorgabe die Grundform mit auflisten — sie steht sonst
    # nirgends in der Zeile
    de_direction = session.settings.direction == "de"
    wrong_items = [
        ft.ListTile(
            title=ft.Text(f"{t.prompt} → {t.expected}"),
            subtitle=ft.Text(" · ".join(
                x for x in (t.label, t.meaning,
                            f"Grundform: {t.card.front}" if de_direction
                            else "") if x)),
            leading=ft.Icon(ft.Icons.CLOSE, color=ft.Colors.ERROR),
        )
        for t in stats["wrong_tasks"]
    ]
    # Darunter auch die richtig gelösten Aufgaben der Runde zeigen
    correct_items = [
        ft.ListTile(
            title=ft.Text(f"{a.task.prompt} → {a.task.expected}"),
            subtitle=ft.Text(" · ".join(
                x for x in (a.task.label, a.task.meaning) if x)),
            leading=ft.Icon(ft.Icons.CHECK, color=ft.Colors.GREEN),
        )
        for a in session.answers[: session.total_first_round]
        if session.counts_correct(a.result)
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
                    size=sz(24), weight=ft.FontWeight.BOLD),
            ft.ProgressBar(value=stats["correct"] / max(1, stats["total"])),
            ft.Text("Falsche Aufgaben:" if wrong_items else "Alles richtig — μπράβο! 🎉"),
            *wrong_items,
            *([ft.Text("Richtig:")] if correct_items and wrong_items else []),
            *correct_items,
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
