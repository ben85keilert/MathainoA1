"""Vokabelverwaltung: Listen-Übersicht, Karten-Editor, Import/Export.

Buchlisten sind sichtbar, aber nicht editierbar (ausgegraut, nur ansehen).
Eigene Listen werden mit Namen angelegt (manuell oder per Import).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import flet as ft

from mathainoa1.models import (
    NOUN_EDITOR_KEYS,
    WORD_TYPES,
    SelectionList,
    VocabCard,
    VocabList,
    forms_to_text,
    parse_stem2_text,
    parse_verb_forms_text,
    verb_forms_to_text,
)
from mathainoa1.storage import content
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.storage.tts import TtsFetchError, speakable
from mathainoa1.ui.audio import tts_cache
from mathainoa1.ui.views.trainer import edit_notes_dialog
from mathainoa1.ui.views.wordlist import (
    alpha_key,
    box_chip_controls,
    box_of,
    card_tiles,
    drag_row,
    group_heading,
    origin_names,
)

ARTICLES = ["", "ο", "η", "το", "οι", "τα"]


def rename_dialog(page: ft.Page, store: ContentStore, vlist: VocabList,
                  on_saved=None) -> None:
    """Dialog zum Umbenennen einer (editierbaren) Liste."""
    tf = ft.TextField(label="Name", value=vlist.name, autofocus=True)

    def save(e):
        if tf.value.strip():
            vlist.name = tf.value.strip()
            store.save_user_list(vlist)
            page.pop_dialog()
            if on_saved:
                on_saved()

    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Liste umbenennen"),
        content=tf,
        actions=[ft.TextButton("Abbrechen", on_click=lambda e: page.pop_dialog()),
                 ft.FilledButton("Speichern", on_click=save)],
    ))


def manager_view(nav, store: ContentStore,
                 progress: ProgressStore) -> ft.Control:
    page = nav.page
    picker = ft.FilePicker()
    if picker not in page.services:
        page.services.append(picker)
    body = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
    state = {"sort_mode": False}  # Listen-Reihenfolge per ↑/↓ ändern

    def toggle_sort(e):
        state["sort_mode"] = not state["sort_mode"]
        refresh()

    def reorder_lists(e):
        ids = [l.id for l in store.ordered_lists()]
        ids.insert(e.new_index, ids.pop(e.old_index))
        store.set_list_order(ids)
        refresh()

    def refresh():
        ordered = store.ordered_lists()
        sort_btn = ft.IconButton(
            icon=ft.Icons.CHECK if state["sort_mode"] else ft.Icons.SWAP_VERT,
            icon_color=ft.Colors.PRIMARY if state["sort_mode"] else None,
            tooltip=("Sortieren beenden" if state["sort_mode"]
                     else "Reihenfolge ändern"),
            on_click=toggle_sort,
        )
        rows: list[ft.Control] = [
            ft.Row([
                ft.FilledButton("Neue Liste", icon=ft.Icons.ADD, on_click=new_list_dialog),
                ft.FilledButton("Neue Auswahlliste", icon=ft.Icons.PLAYLIST_ADD,
                                on_click=new_selection),
                ft.OutlinedButton("Importieren", icon=ft.Icons.UPLOAD_FILE,
                                  on_click=import_file),
                ft.OutlinedButton("Als Text importieren", icon=ft.Icons.CONTENT_PASTE,
                                  on_click=import_text_dialog),
            ], spacing=8, wrap=True),
        ]
        if store.selections:
            rows.append(ft.Text("Auswahllisten", size=16, weight=ft.FontWeight.BOLD))
            for sel in sorted(store.selections.values(), key=lambda x: x.name):
                rows.append(selection_tile(sel))
        rows.append(ft.Row([
            ft.Text("Vokabellisten", size=16, weight=ft.FontWeight.BOLD,
                    expand=True),
            sort_btn,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER))
        if state["sort_mode"]:
            # Ziehen am ≡; die ReorderableListView scrollt selbst, die
            # Spalte darf dann nicht auch noch scrollen
            body.scroll = None
            rows.append(ft.ReorderableListView(
                controls=[drag_row(l.name, f"{len(l.cards)} Karten")
                          for l in ordered],
                show_default_drag_handles=False,
                on_reorder=reorder_lists,
                expand=True,
            ))
        else:
            body.scroll = ft.ScrollMode.AUTO
            for vlist in ordered:
                rows.append(list_tile(vlist))
        body.controls = rows
        page.update()

    def new_selection(e):
        nav.go("Neue Auswahlliste",
               selection_editor(nav, store, None, on_saved_selection, progress))

    def on_saved_selection(sel):
        nav.back()
        refresh()

    def selection_tile(sel: SelectionList) -> ft.Control:
        def delete(e, s=sel):
            def do(e):
                store.delete_selection(s.id)
                page.pop_dialog()
                refresh()
            page.show_dialog(ft.AlertDialog(
                title=ft.Text(f"„{s.name}“ löschen?"),
                content=ft.Text("Nur die Auswahl wird gelöscht, keine Vokabeln."),
                actions=[ft.TextButton("Abbrechen", on_click=lambda e: page.pop_dialog()),
                         ft.FilledButton("Löschen", on_click=do)],
            ))
        return ft.Card(
            content=ft.ListTile(
                leading=ft.Icon(ft.Icons.STAR_OUTLINE),
                title=ft.Text(sel.name),
                subtitle=ft.Text(f"Auswahl · {len(sel.card_ids)} Karten"),
                trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Löschen",
                                       on_click=delete),
                on_click=lambda e, s=sel: nav.go(
                    s.name, selection_editor(nav, store, s, on_saved_selection,
                                             progress)),
            )
        )

    def list_tile(vlist: VocabList) -> ft.Control:
        if vlist.editable:
            trailing = ft.PopupMenuButton(items=[
                ft.PopupMenuItem(content="Umbenennen", icon=ft.Icons.EDIT,
                                 on_click=lambda e, l=vlist: rename_dialog(
                                     page, store, l, on_saved=refresh)),
                ft.PopupMenuItem(content="Export JSON", icon=ft.Icons.DOWNLOAD,
                                 on_click=lambda e, l=vlist: export_list(l, "json")),
                ft.PopupMenuItem(content="Export CSV", icon=ft.Icons.DOWNLOAD,
                                 on_click=lambda e, l=vlist: export_list(l, "csv")),
                ft.PopupMenuItem(content="Audio vorbereiten",
                                 icon=ft.Icons.DOWNLOAD_FOR_OFFLINE,
                                 on_click=lambda e, l=vlist: prepare_audio_dialog(l)),
                ft.PopupMenuItem(content="Löschen", icon=ft.Icons.DELETE,
                                 on_click=lambda e, l=vlist: delete_dialog(l)),
            ])
        else:
            # Buchlisten: nicht editierbar, aber die Audio-Vorbereitung ist
            # auch für sie sinnvoll (Cache hängt nur am Text)
            trailing = ft.Row([
                ft.Icon(ft.Icons.LOCK_OUTLINE, tooltip="Buchliste (nicht editierbar)"),
                ft.PopupMenuButton(items=[
                    ft.PopupMenuItem(content="Audio vorbereiten",
                                     icon=ft.Icons.DOWNLOAD_FOR_OFFLINE,
                                     on_click=lambda e, l=vlist: prepare_audio_dialog(l)),
                ]),
            ], tight=True, spacing=0)
        return ft.Card(
            content=ft.ListTile(
                leading=ft.Icon(ft.Icons.LIST_ALT),
                title=ft.Text(vlist.name),
                subtitle=ft.Text(f"{len(vlist.cards)} Karten"),
                trailing=trailing,
                on_click=lambda e, l=vlist: nav.go(l.name, list_view(nav, store, l)),
            ),
            opacity=1.0 if vlist.editable else 0.55,
        )

    # --- Dialoge ---

    def close_dialog(e=None):
        page.pop_dialog()

    def new_list_dialog(e):
        tf_name = ft.TextField(label="Name", autofocus=True)
        def create(e):
            name = (tf_name.value or "").strip()
            if not name:
                return
            vlist = VocabList(name=name)
            store.save_user_list(vlist)
            close_dialog()
            refresh()
            nav.go(vlist.name, list_view(nav, store, vlist))
        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Neue Liste"),
            content=ft.Column([tf_name], tight=True, spacing=12),
            actions=[ft.TextButton("Abbrechen", on_click=close_dialog),
                     ft.FilledButton("Anlegen", on_click=create)],
        ))

    def delete_dialog(vlist: VocabList):
        def delete(e):
            store.delete_user_list(vlist.id)
            close_dialog()
            refresh()
        page.show_dialog(ft.AlertDialog(
            title=ft.Text(f"„{vlist.name}“ löschen?"),
            content=ft.Text(f"Die Liste mit {len(vlist.cards)} Karten wird endgültig gelöscht."),
            actions=[ft.TextButton("Abbrechen", on_click=close_dialog),
                     ft.FilledButton("Löschen", on_click=delete)],
        ))

    # --- Import / Export ---

    def import_text_dialog(e):
        """CSV/JSON als eingefügten Text importieren — für Chatbots, die
        keine Datei liefern können (Antwort einfach hineinkopieren)."""
        tf_name = ft.TextField(label="Name der Liste", autofocus=True)
        tf_text = ft.TextField(
            label="CSV- oder JSON-Text hier einfügen",
            multiline=True, min_lines=8, max_lines=14,
        )
        error = ft.Text("", color=ft.Colors.ERROR, size=13)

        def do_import(e):
            text = (tf_text.value or "").strip()
            name = (tf_name.value or "").strip() or "Import"
            if not text:
                error.value = "Bitte zuerst den Text einfügen."
                page.update()
                return
            try:
                if text.lstrip("﻿").startswith("{"):
                    vlist = content.import_json(text)
                    vlist.name = name
                else:
                    vlist = content.import_csv(name, text)
            except Exception:
                error.value = "Text konnte nicht gelesen werden — ist es CSV/JSON?"
                page.update()
                return
            if not vlist.cards:
                error.value = ("Keine Karten gefunden — fehlt die Kopfzeile "
                               "mit den Spaltennamen (front,back,…)?")
                page.update()
                return
            store.save_user_list(vlist)
            page.pop_dialog()
            refresh()

        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Als Text importieren"),
            content=ft.Column([tf_name, tf_text, error],
                              tight=True, spacing=10, width=420,
                              scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Abbrechen",
                                   on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Importieren", on_click=do_import)],
        ))

    async def import_file(e):
        files = await picker.pick_files(
            dialog_title="Liste importieren",
            allowed_extensions=["json", "csv"], with_data=True,
        )
        if not files:
            return
        f = files[0]
        data = f.bytes_data if hasattr(f, "bytes_data") else None
        if data is None and f.path:
            data = Path(f.path).read_bytes()
        if data is None:
            return
        text = data.decode("utf-8-sig")  # toleriert UTF-8 mit BOM (Excel & Co.)
        name = Path(f.name).stem
        if f.name.lower().endswith(".json"):
            vlist = content.import_json(text)
        else:
            vlist = content.import_csv(name, text)
        store.save_user_list(vlist)
        refresh()

    async def export_list(vlist: VocabList, fmt: str):
        text = content.export_json(vlist) if fmt == "json" else content.export_csv(vlist)
        await picker.save_file(
            dialog_title="Liste exportieren",
            file_name=f"{vlist.name}.{fmt}",
            allowed_extensions=[fmt],
            src_bytes=text.encode("utf-8"),
        )

    def prepare_audio_dialog(vlist: VocabList):
        """Lädt das Audio aller Wörter einer Liste vorab in den Cache —
        danach ist die Liste komplett offline anhörbar.

        Kleine Pause zwischen den Abrufen (Google drosselt sonst); nach
        3 Fehlern in Folge wird abgebrochen (offline nicht durch die
        ganze Liste laufen).
        """
        texts = list(dict.fromkeys(
            t for t in (speakable(c.front) for c in vlist.cards) if t))
        cache = tts_cache()
        todo = [t for t in texts if not cache.has(t)]
        already = len(texts) - len(todo)

        bar = ft.ProgressBar(value=0.0)
        status = ft.Text(f"{already} von {len(texts)} bereits vorhanden.",
                         size=13)
        btn_action = ft.TextButton("Abbrechen")
        state = {"cancel": False, "done": False}

        def close_or_cancel(e):
            if state["done"]:
                page.pop_dialog()
            else:
                state["cancel"] = True

        btn_action.on_click = close_or_cancel

        async def run():
            ok, errors, streak = 0, 0, 0
            for i, text in enumerate(todo):
                if state["cancel"] or streak >= 3:
                    break
                status.value = f"Lade {i + 1} von {len(todo)}: {text}"
                bar.value = i / max(1, len(todo))
                page.update()
                try:
                    await asyncio.to_thread(cache.fetch, text)
                    ok += 1
                    streak = 0
                except TtsFetchError:
                    errors += 1
                    streak += 1
                await asyncio.sleep(0.3)
            state["done"] = True
            bar.value = 1.0
            if streak >= 3:
                status.value = (f"Abgebrochen — kein Internet? "
                                f"{ok} neu geladen, {errors} Fehler.")
            elif state["cancel"]:
                status.value = f"Abgebrochen — {ok} neu geladen."
            else:
                status.value = (f"Fertig: {ok} neu geladen, "
                                f"{already + ok} von {len(texts)} im Cache"
                                + (f", {errors} Fehler." if errors else "."))
            btn_action.text = "Schließen"
            page.update()

        page.show_dialog(ft.AlertDialog(
            title=ft.Text(f"Audio vorbereiten — {vlist.name}"),
            content=ft.Column([bar, status], tight=True, spacing=12,
                              width=420),
            actions=[btn_action],
        ))
        if todo:
            page.run_task(run)
        else:
            state["done"] = True
            bar.value = 1.0
            status.value = f"Alle {len(texts)} Wörter sind schon im Cache."
            btn_action.text = "Schließen"

    refresh()
    # Rundes Such-Symbol unten links (unten rechts kollidiert mit den
    # Listen-Bearbeitungssymbolen); bleibt beim Scrollen fix
    search_fab = ft.FloatingActionButton(
        icon=ft.Icons.SEARCH, mini=True, bottom=16, left=16,
        tooltip="Wörter suchen",
        on_click=lambda e: nav.go("Wortsuche", search_view(nav, store)),
    )
    return ft.Stack([body, search_fab], expand=True)


def search_view(nav, store: ContentStore) -> ft.Control:
    """Wortsuche über alle Listen (Deutsch oder Griechisch)."""
    page = nav.page
    results = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    tf = ft.TextField(label="Suche (Deutsch oder Griechisch)", autofocus=True,
                      prefix_icon=ft.Icons.SEARCH)

    def open_hit(vlist: VocabList, card: VocabCard):
        # Editor als Dialog über der Suche öffnen — kein Fensterwechsel;
        # nach dem Speichern die Trefferliste aktualisieren
        open_card_editor(nav.page, store, vlist, card, on_saved=refresh)

    def refresh(e=None):
        query = (tf.value or "").strip()
        if not query:
            results.controls = [ft.Text("Tippe zum Suchen — es wird in allen "
                                        "Listen gesucht.", italic=True)]
            page.update()
            return
        hits = store.search_cards(query)
        if not hits:
            results.controls = [ft.Text("Keine Treffer.", italic=True)]
            page.update()
            return
        tiles = []
        for vlist, card, in_selections in hits:
            star = None
            if in_selections:
                star = ft.Icon(
                    ft.Icons.STAR, color=ft.Colors.AMBER, size=18,
                    tooltip="In Auswahlliste: " + ", ".join(in_selections))
            tiles.append(ft.ListTile(
                dense=True,
                title=ft.Row(
                    [ft.Text(card.with_plural(card.front), expand=1),
                     ft.Text(card.back, expand=1)],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                subtitle=ft.Text(vlist.name, size=12),
                trailing=star,
                on_click=lambda e, v=vlist, c=card: open_hit(v, c),
            ))
        results.controls = tiles
        page.update()

    tf.on_change = refresh
    refresh()
    return ft.Column([tf, results], spacing=10, expand=True)


def open_source_editor(nav, store: ContentStore, progress: ProgressStore,
                       source_id: str) -> None:
    """Öffnet den passenden Editor: Vokabelliste oder Auswahlliste.

    Aus der Trainings-Vorschau erreichbar; springt danach einfach zurück.
    """
    if source_id in store.lists:
        vlist = store.lists[source_id]
        nav.go(vlist.name, list_view(nav, store, vlist))
    elif source_id in store.selections:
        sel = store.selections[source_id]
        nav.go(sel.name, selection_editor(nav, store, sel,
                                          lambda s: nav.back(), progress))


def selection_editor(nav, store: ContentStore, selection: SelectionList | None,
                     on_saved, progress: ProgressStore) -> ft.Control:
    """Auswahlliste zusammenstellen: zwei Reiter (klick- und wischbar).

    Links "Auswählen": filtern und Karten antippen (farbig markiert).
    Rechts "Ausgewählt": Antippen markiert nur zum Entfernen; erst
    "Aktualisieren" wirft die markierten Karten wirklich raus.
    Speichern über den mitlaufenden Button unten rechts.
    """
    page = nav.page
    all_progress = progress.all()
    sel = selection or SelectionList(name="")
    selected_ids: set[str] = set(sel.card_ids)
    to_remove: set[str] = set()
    # unabhängige Box-Filter je Reiter (alle Boxen aktiv = nichts ausgeblendet)
    pick_boxes: set[int] = set(range(0, 6))
    sel_boxes: set[int] = set(range(0, 6))

    tf_name = ft.TextField(label="Name der Auswahlliste", value=sel.name)
    lists = sorted(store.lists.values(),
                   key=lambda l: (l.chapter is None, l.chapter or 0, l.name))
    dd_list = ft.Dropdown(
        label="Liste", value=lists[0].id,
        options=[ft.DropdownOption(key=l.id, text=l.name) for l in lists],
    )
    dd_type = ft.Dropdown(label="Worttyp", value="")
    dd_type_sel = ft.Dropdown(label="Worttyp", value="")
    # Sortierung im Reiter "Ausgewählt": ohne Umschalter gruppiert nach
    # Ursprungsliste, sonst alphabetisch bzw. nach Lernstand (wie in den
    # Wortübersichten)
    sel_sort = {"alpha": False, "progress": False}

    def toggle_sel_alpha(e):
        sel_sort["alpha"] = not sel_sort["alpha"]
        sel_sort["progress"] = False
        refresh()

    def toggle_sel_progress(e):
        sel_sort["progress"] = not sel_sort["progress"]
        sel_sort["alpha"] = False
        refresh()

    sel_alpha_btn = ft.IconButton(
        ft.Icons.SORT_BY_ALPHA,
        tooltip="Alphabetisch sortieren (über alle Ursprungslisten)",
        on_click=toggle_sel_alpha,
    )
    sel_progress_btn = ft.IconButton(
        ft.Icons.SORT,
        tooltip="Nach Lernstand sortieren (schlechteste zuerst)",
        on_click=toggle_sel_progress,
    )
    pick_box_row = ft.Row(spacing=6, wrap=True)
    sel_box_row = ft.Row(spacing=6, wrap=True)
    counter = ft.Text("", size=13, weight=ft.FontWeight.BOLD)
    error = ft.Text("", color=ft.Colors.ERROR, size=13)
    pick_col = ft.Column(spacing=0)
    selected_col = ft.Column(spacing=0)
    tab_selected = ft.Tab(label="Ausgewählt")
    btn_apply = ft.FilledButton("Aktualisieren", icon=ft.Icons.DELETE_SWEEP)

    def filtered() -> list[VocabCard]:
        cards = store.lists[dd_list.value].cards
        if dd_type.value:
            cards = [c for c in cards if c.word_type == dd_type.value]
        return [c for c in cards if box_of(c, all_progress) in pick_boxes]

    def selected_cards() -> list[VocabCard]:
        by_id = store.cards_by_id()
        return [by_id[cid] for l in store.lists.values() for cid in
                (c.id for c in l.cards) if cid in selected_ids and cid in by_id]

    def selected_filtered() -> list[VocabCard]:
        cards = selected_cards()
        if dd_type_sel.value:
            cards = [c for c in cards if c.word_type == dd_type_sel.value]
        return [c for c in cards if box_of(c, all_progress) in sel_boxes]

    def _type_options(cards: list[VocabCard], current: str) -> tuple[list, str]:
        types = [t for t in WORD_TYPES if any(c.word_type == t for c in cards)]
        opts = [ft.DropdownOption(key="", text="Alle Worttypen")] + [
            ft.DropdownOption(key=t, text=t) for t in types]
        return opts, ("" if current and current not in types else current)

    def refresh_filter_options():
        dd_type.options, dd_type.value = _type_options(
            store.lists[dd_list.value].cards, dd_type.value)
        dd_type_sel.options, dd_type_sel.value = _type_options(
            selected_cards(), dd_type_sel.value)

    def toggle_pick_box(b: int):
        pick_boxes.symmetric_difference_update({b})
        refresh()

    def toggle_sel_box(b: int):
        sel_boxes.symmetric_difference_update({b})
        refresh()

    def refresh(e=None):
        refresh_filter_options()
        pick_box_row.controls = box_chip_controls(pick_boxes, toggle_pick_box)
        sel_box_row.controls = box_chip_controls(sel_boxes, toggle_sel_box)
        counter.value = f"{len(selected_ids)} Karten ausgewählt"
        tab_selected.label = f"Ausgewählt ({len(selected_ids)})"
        # linker Reiter: Karten der gefilterten Liste antippen
        pick_col.controls = [
            ft.ListTile(
                dense=True,
                leading=ft.Icon(
                    ft.Icons.CHECK_CIRCLE if c.id in selected_ids
                    else ft.Icons.RADIO_BUTTON_UNCHECKED,
                    color=ft.Colors.PRIMARY if c.id in selected_ids else None,
                ),
                title=ft.Text(c.front),
                subtitle=ft.Text(c.back),
                selected=c.id in selected_ids,
                selected_tile_color=ft.Colors.PRIMARY_CONTAINER,
                on_click=lambda e, c=c: toggle(c),
            )
            for c in filtered()
        ]
        # rechter Reiter: bereits Ausgewählte, Antippen markiert zum
        # Entfernen. Ohne Sortier-Umschalter gruppiert nach Ursprungsliste
        # („Liste X“-Überschriften), sonst flach alphabetisch bzw. nach
        # Lernstand sortiert.
        def sel_tile(c: VocabCard) -> ft.Control:
            return ft.ListTile(
                dense=True,
                leading=ft.Icon(
                    ft.Icons.CANCEL if c.id in to_remove else ft.Icons.CHECK_CIRCLE,
                    color=ft.Colors.ERROR if c.id in to_remove else ft.Colors.PRIMARY,
                ),
                title=ft.Text(c.front),
                subtitle=ft.Text(c.back),
                opacity=0.5 if c.id in to_remove else 1.0,
                on_click=lambda e, c=c: mark_remove(c),
            )

        sel_alpha_btn.icon_color = (ft.Colors.PRIMARY if sel_sort["alpha"]
                                    else None)
        sel_progress_btn.icon_color = (ft.Colors.PRIMARY
                                       if sel_sort["progress"] else None)
        shown_sel = selected_filtered()
        if not shown_sel:
            selected_col.controls = [ft.Text(
                "Noch keine Karten ausgewählt." if not selected_ids
                else "Keine ausgewählten Karten für diesen Filter.",
                italic=True)]
        elif sel_sort["alpha"]:
            selected_col.controls = [
                sel_tile(c) for c in sorted(shown_sel, key=alpha_key)]
        elif sel_sort["progress"]:
            def wrong_of(c: VocabCard) -> int:
                p = all_progress.get(c.id)
                return p.wrong if p else 0
            selected_col.controls = [
                sel_tile(c) for c in sorted(
                    shown_sel,
                    key=lambda c: (box_of(c, all_progress), -wrong_of(c)))]
        else:
            names = origin_names(store)
            groups: dict[str, list[VocabCard]] = {}
            for c in shown_sel:
                groups.setdefault(names.get(c.id, "Unbekannte Liste"),
                                  []).append(c)
            rows: list[ft.Control] = []
            for name, group in groups.items():
                rows.append(group_heading(name))
                rows += [sel_tile(c) for c in group]
            selected_col.controls = rows
        btn_apply.content = (f"Aktualisieren ({len(to_remove)} entfernen)"
                             if to_remove else "Aktualisieren")
        btn_apply.disabled = not to_remove
        page.update()

    def toggle(card: VocabCard):
        if card.id in selected_ids:
            selected_ids.discard(card.id)
            to_remove.discard(card.id)
        else:
            selected_ids.add(card.id)
        refresh()

    def mark_remove(card: VocabCard):
        if card.id in to_remove:
            to_remove.discard(card.id)
        else:
            to_remove.add(card.id)
        refresh()

    def apply_removals(e):
        selected_ids.difference_update(to_remove)
        to_remove.clear()
        refresh()

    btn_apply.on_click = apply_removals

    def select_visible(select: bool):
        for c in filtered():
            if select:
                selected_ids.add(c.id)
            else:
                selected_ids.discard(c.id)
                to_remove.discard(c.id)
        refresh()

    def save(e):
        name = (tf_name.value or "").strip()
        if not name:
            error.value = "Bitte einen Namen eingeben."
            page.update()
            return
        # 0 Karten sind erlaubt — man darf eine Auswahl auch ganz leeren
        sel.name = name
        sel.card_ids = [c.id for c in selected_cards()]
        store.save_selection(sel)
        on_saved(sel)

    dd_list.on_select = refresh
    dd_type.on_select = refresh
    dd_type_sel.on_select = refresh
    refresh()

    pick_tab = ft.Column(
        [
            dd_list, ft.Row([dd_type], spacing=8, wrap=True),
            pick_box_row,
            ft.Row(
                [
                    ft.TextButton("Alle sichtbaren auswählen",
                                  on_click=lambda e: select_visible(True)),
                    ft.TextButton("Auswahl aufheben",
                                  on_click=lambda e: select_visible(False)),
                ],
                spacing=4, wrap=True,
            ),
            pick_col,
        ],
        spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
    )
    selected_tab = ft.Column(
        [
            ft.Row([ft.Container(dd_type_sel, expand=True),
                    sel_alpha_btn, sel_progress_btn],
                   spacing=4,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            sel_box_row,
            ft.Text("Antippen markiert zum Entfernen — wirksam erst mit "
                    "„Aktualisieren“.", size=13, italic=True),
            btn_apply,
            selected_col,
        ],
        spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
    )

    tabs = ft.Tabs(
        length=2,
        expand=True,
        content=ft.Column(
            [
                ft.TabBar(tabs=[ft.Tab(label="Auswählen", icon=ft.Icons.CHECKLIST),
                                tab_selected]),
                ft.TabBarView(expand=True, controls=[pick_tab, selected_tab]),
            ],
            expand=True,
        ),
    )
    # Speichern fest im (nicht scrollenden) Kopfbereich — unten würde die
    # Systemleiste den Button verdecken
    save_btn = ft.IconButton(
        icon=ft.Icons.SAVE, tooltip="Auswahlliste speichern", on_click=save,
        icon_size=28, style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY_CONTAINER),
    )
    return ft.Column(
        [
            ft.Row([ft.Container(tf_name, expand=True), save_btn], spacing=8),
            ft.Row([counter, error], spacing=16),
            tabs,
        ],
        spacing=10, expand=True,
    )


def card_editor_dialog(page, store, vlist, card: VocabCard | None, on_saved=None):
    """Karten-Editor: alle Felder sichtbar, Blättern zwischen Nachbar-
    karten mit Auto-Save, Undo, Schließen oben rechts."""
    state = {"card": card}  # None = neue, noch nicht gespeicherte Karte

    tf_front = ft.TextField(label="Vorderseite (Griechisch)", autofocus=True)
    tf_back = ft.TextField(label="Rückseite (Deutsch)")
    dd_type = ft.Dropdown(
        label="Worttyp", expand=True,
        options=[ft.DropdownOption(key=t, text=t) for t in WORD_TYPES],
    )
    dd_article = ft.Dropdown(
        label="Artikel", expand=True,
        options=[ft.DropdownOption(key=a, text=a or "–") for a in ARTICLES],
    )
    tf_plural = ft.TextField(label="Plural (z.B. -α, nur Anzeige)")
    tf_notes_gr = ft.TextField(label="Notiz (griechische Seite)")
    tf_notes_de = ft.TextField(label="Notiz (deutsche Seite)")
    tf_hints_gr = ft.TextField(label="Hinweis (griechische Seite)")
    tf_hints_de = ft.TextField(label="Hinweis (deutsche Seite)")
    # Unregelmäßige Formen, je Worttyp eigene Felder (nur bei Bedarf
    # ausfüllen — leer = regelbasierte Formen)
    noun_fields = {
        "gen_sg": ft.TextField(label="Genitiv Singular", hint_text="z.B. του άντρα"),
        "gen_pl": ft.TextField(label="Genitiv Plural", hint_text="z.B. των αντρών"),
        "acc_sg": ft.TextField(label="Akkusativ Singular", hint_text="z.B. τον άντρα"),
        "acc_pl": ft.TextField(label="Akkusativ Plural", hint_text="z.B. τους άντρες"),
    }
    noun_section = ft.Column(
        [ft.Text("Deklination (nur bei Unregelmäßigkeit)", size=13,
                 weight=ft.FontWeight.BOLD),
         *[noun_fields[k] for k in NOUN_EDITOR_KEYS]],
        spacing=10, visible=False,
    )
    tf_present = ft.TextField(
        label="Präsens (unregelmäßig)",
        hint_text="z.B. πάω, πας, πάει, πάμε, πάτε, πάνε",
        helper="6 Formen mit Komma (1sg–3pl), „-“ = regelmäßig, "
               "Varianten mit „/“. Leer = ganz regelmäßig.",
    )
    tf_stem2 = ft.TextField(
        label="2. Stamm (Futur/να-Form)",
        hint_text="z.B. γράψ- — oder 6 Formen mit Komma",
        helper="Stamm mit Akzent → θα γράψω; ohne Akzent → endbetont "
               "(κοιμηθ- → θα κοιμηθώ). Unregelmäßig: 6 Formen wie oben.",
    )
    verb_section = ft.Column(
        [ft.Text("Konjugation", size=13, weight=ft.FontWeight.BOLD),
         tf_present, tf_stem2],
        spacing=10, visible=False,
    )
    tf_fem = ft.TextField(label="Femininum (unregelmäßig)",
                          hint_text="z.B. γλυκιά")
    adj_section = ft.Column(
        [ft.Text("Deklination (nur bei Unregelmäßigkeit)", size=13,
                 weight=ft.FontWeight.BOLD),
         tf_fem],
        spacing=10, visible=False,
    )
    error = ft.Text("", color=ft.Colors.ERROR, size=13)
    pos_label = ft.Text("", size=13)

    def sync_type_fields(e=None):
        # Nur die zum Worttyp passenden Felder einblenden;
        # "Sonstiges" (unbestimmt) zeigt alle Felder
        wt = dd_type.value
        other = wt == "Sonstiges"
        dd_article.visible = wt == "Nomen" or other
        tf_plural.visible = wt == "Nomen" or other
        noun_section.visible = wt == "Nomen" or other
        verb_section.visible = wt == "Verb" or other
        adj_section.visible = wt == "Adjektiv" or other
        page.update()

    def on_article_select(e=None):
        if dd_article.value and dd_type.value == "Sonstiges":
            dd_type.value = "Nomen"
            sync_type_fields()

    dd_type.on_select = sync_type_fields
    dd_article.on_select = on_article_select

    def load(c: VocabCard | None):
        state["card"] = c
        tf_front.value = c.front if c else ""
        tf_back.value = c.back if c else ""
        dd_type.value = c.word_type if c else "Sonstiges"
        dd_article.value = (c.article or "") if c else ""
        tf_plural.value = c.plural if c else ""
        tf_notes_gr.value = c.notes_gr if c else ""
        tf_notes_de.value = c.notes_de if c else ""
        tf_hints_gr.value = c.hints_gr if c else ""
        tf_hints_de.value = c.hints_de if c else ""
        for key, tf in noun_fields.items():
            tf.value = c.forms.get(key, "") if c else ""
        tf_present.value = verb_forms_to_text(c.forms) if c else ""
        tf_stem2.value = c.stem2 if c else ""
        tf_fem.value = c.forms.get("fem", "") if c else ""
        error.value = ""
        if c is None:
            pos_label.value = f"neu ({len(vlist.cards) + 1})"
        else:
            pos_label.value = f"{vlist.cards.index(c) + 1}/{len(vlist.cards)}"
        sync_type_fields()

    def is_blank() -> bool:
        return not (tf_front.value or "").strip() and not (tf_back.value or "").strip()

    def collect_forms() -> tuple[dict[str, str], str]:
        """Formen und 2. Stamm je Worttyp aus den Feldern einsammeln.

        Worttyp-Wechsel räumt fremde Schlüssel auf (analog zum
        Artikel-Nulling). ValueError bei ungültiger Eingabe.
        """
        wt = dd_type.value
        if wt == "Nomen":
            forms = {k: v for k in NOUN_EDITOR_KEYS
                     if (v := (noun_fields[k].value or "").strip())}
            # nom_pl hat kein Editorfeld, bleibt aber erhalten (Altdaten)
            old = state["card"].forms if state["card"] else {}
            if old.get("nom_pl"):
                forms["nom_pl"] = old["nom_pl"]
            return forms, ""
        if wt == "Verb":
            return (parse_verb_forms_text(tf_present.value or ""),
                    parse_stem2_text(tf_stem2.value or ""))
        if wt == "Adjektiv":
            fem = (tf_fem.value or "").strip()
            return ({"fem": fem} if fem else {}), ""
        if wt == "Sonstiges":
            # alle Felder sichtbar -> auch alle Eingaben übernehmen
            forms = {k: v for k in NOUN_EDITOR_KEYS
                     if (v := (noun_fields[k].value or "").strip())}
            if (fem := (tf_fem.value or "").strip()):
                forms["fem"] = fem
            forms.update(parse_verb_forms_text(tf_present.value or ""))
            return forms, parse_stem2_text(tf_stem2.value or "")
        return {}, ""

    def apply_to(c: VocabCard) -> bool:
        front = (tf_front.value or "").strip()
        back = (tf_back.value or "").strip()
        if not front or not back:
            error.value = "Vorder- und Rückseite dürfen nicht leer sein."
            page.update()
            return False
        try:
            forms, stem2 = collect_forms()
        except ValueError as exc:
            error.value = str(exc)
            page.update()
            return False
        c.front = front
        c.back = back
        c.article = (dd_article.value or "").strip() or None
        if not dd_article.visible:
            c.article = None
        c.plural = (tf_plural.value or "").strip() if tf_plural.visible else ""
        c.word_type = dd_type.value or "Sonstiges"
        c.notes_gr = (tf_notes_gr.value or "").strip()
        c.notes_de = (tf_notes_de.value or "").strip()
        c.hints_gr = (tf_hints_gr.value or "").strip()
        c.hints_de = (tf_hints_de.value or "").strip()
        c.forms = forms
        c.stem2 = stem2
        c.chapter = vlist.chapter
        return True

    def save_current() -> bool:
        """Speichert die angezeigte Karte. Leere neue Karte = nichts zu tun."""
        if state["card"] is None:
            if is_blank():
                return True
            target = VocabCard(front="", back="")
            if not apply_to(target):
                return False
            vlist.cards.append(target)
            state["card"] = target
        elif not apply_to(state["card"]):
            return False
        store.save_user_list(vlist)
        on_saved and on_saved()
        load(state["card"])  # Positionsanzeige aktualisieren
        page.update()
        return True

    def go(delta: int):
        """Auto-Save, dann zur Nachbarkarte blättern."""
        if not save_current() or not vlist.cards:
            return
        if state["card"] is None:  # leere neue Karte -> von den Rändern her
            idx = len(vlist.cards) - 1 if delta < 0 else 0
        else:
            idx = (vlist.cards.index(state["card"]) + delta) % len(vlist.cards)
        load(vlist.cards[idx])
        page.update()

    def new_card(e):
        if save_current():
            load(None)
            page.update()

    def undo(e):
        load(state["card"])  # zurück auf den gespeicherten Stand
        page.update()

    def save_btn(e):
        save_current()

    def close(e):
        page.pop_dialog()
        on_saved and on_saved()

    tf_back.on_submit = lambda e: new_card(e)

    header = ft.Row(
        [
            ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Vorherige (speichert)",
                          on_click=lambda e: go(-1)),
            pos_label,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip="Nächste (speichert)",
                          on_click=lambda e: go(1)),
            ft.Container(expand=True),
            ft.IconButton(ft.Icons.CLOSE, tooltip="Schließen (ohne Speichern)",
                          on_click=close),
        ],
        spacing=0,
    )
    actions = [
        ft.IconButton(ft.Icons.UNDO, tooltip="Änderungen verwerfen", on_click=undo),
        ft.IconButton(ft.Icons.SAVE, tooltip="Speichern", on_click=save_btn),
        ft.IconButton(ft.Icons.ADD, tooltip="Speichern + neue Vokabel",
                      on_click=new_card),
    ]

    load(card)
    page.show_dialog(ft.AlertDialog(
        title=header,
        content=ft.Column(
            [tf_front, tf_back, error,
             ft.Row([dd_type, dd_article], spacing=8),
             tf_plural, noun_section, verb_section, adj_section,
             tf_notes_gr, tf_notes_de, tf_hints_gr, tf_hints_de],
            tight=True, spacing=10, scroll=ft.ScrollMode.AUTO, width=400,
        ),
        actions=actions,
    ))


def open_card_editor(page, store: ContentStore, vlist: VocabList,
                     card: VocabCard | None, on_saved=None) -> None:
    """Öffnet den passenden Karten-Dialog (schwebt über der aktuellen View):
    editierbare Liste → voller Editor, Buchliste → nur Notizen/Hinweise."""
    if vlist.editable:
        card_editor_dialog(page, store, vlist, card, on_saved=on_saved)
    else:
        edit_notes_dialog(page, store, card, on_saved=on_saved)


def list_view(nav, store: ContentStore, vlist: VocabList) -> ft.Control:
    page = nav.page
    cards_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
    table_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
    # Worttyp-Filter und Karten-Sortiermodus schließen sich aus: über die
    # Lücken ausgeblendeter Karten hinweg zu verschieben wäre verwirrend.
    # "tab": aktiver Reiter (0 = Karten, 1 = Tabelle)
    # "select_mode": Mehrfachauswahl für Massenaktionen (Löschen,
    # Verschieben, Kopieren, Audio löschen, zur Auswahlliste)
    view_state = {"sort_mode": False, "wtype": None, "tab": 0,
                  "select_mode": False}
    selected: set[str] = set()

    def open_card(c: VocabCard):
        open_card_editor(page, store, vlist, c, on_saved=refresh)

    def build_table() -> ft.Control:
        """Alle Werte jeder Karte als Tabelle — zum Prüfen nach einem Import.

        Kein horizontales Scrollen: Kopfzeile und Inhalt werden aus
        demselben Spaltenfenster gebaut und sind dadurch immer bündig.
        Mit ◀ ▶ blättert man spaltenweise — die gewählte Spalte beginnt
        direkt neben der ersten (Griechisch, fix bei ~30 % Breite).
        """
        w = getattr(page, "width", None) or 420
        first_w = max(120, 0.30 * w)
        cols = [("Deutsch", 150), ("Plural", 90), ("Artikel", 70),
                ("Typ", 100), ("Formen", 170), ("2. Stamm", 110),
                ("Hinweis GR", 130), ("Hinweis DE", 130),
                ("Notiz GR", 130), ("Notiz DE", 130)]
        max_k = len(cols) - 1
        k = min(max(view_state.get("col_offset", 0), 0), max_k)
        view_state["col_offset"] = k
        # so viele Spalten ab k, wie neben erste Spalte + Pfeile passen.
        # Breite Spalten (z.B. "Formen") werden auf den freien Platz
        # gestutzt — sonst würde die Kopfzeile überlaufen und die
        # ▶/◀-Pfeile aus dem Fenster schieben (Blättern bräche dann ab)
        avail = max(80, w - first_w - 104)
        visible: list[tuple[str, int]] = []
        used = 0
        for name, cw in cols[k:]:
            if visible and used + cw > avail:
                break
            cw = min(cw, avail)
            visible.append((name, cw))
            used += cw
        zebra = ft.Colors.SURFACE_CONTAINER_HIGHEST

        def cell(text: str, width: float, bold: bool = False) -> ft.Container:
            return ft.Container(
                ft.Text(text or "", size=13, max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        weight=ft.FontWeight.BOLD if bold else None),
                width=width,
                padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            )

        def turn(delta: int):
            def handler(e):
                view_state["col_offset"] = min(max(k + delta, 0), max_k)
                refresh()
            return handler

        # Pfeile in einer eigenen Zeile über der Kopfzeile: der Hinweistext
        # ist flexibel (expand) und macht Platz — die Pfeile können so auf
        # keiner Fensterbreite abgeschnitten werden (das Blättern blieb
        # sonst nach einigen Spalten stecken). Sobald die letzte Spalte
        # sichtbar ist, endet das Blättern — danach kommt ja nichts mehr.
        at_end = k + len(visible) - 1 >= max_k
        pager = ft.Row(
            [ft.Text("Antippen einer Zeile öffnet die Karte · "
                     "◀ ▶ blättert durch die Spalten.", size=12,
                     italic=True, expand=True),
             ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_size=20,
                           tooltip="Spalte zurück",
                           on_click=turn(-1), disabled=k == 0),
             ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_size=20,
                           tooltip="Nächste Spalte",
                           on_click=turn(1), disabled=at_end)],
            spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        header = ft.Row(
            [cell("Griechisch", first_w, bold=True)]
            + [cell(name, cw, bold=True) for name, cw in visible],
            spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        def values(c: VocabCard) -> tuple:
            return (c.back, c.plural, c.article or "", c.word_type,
                    forms_to_text(c.forms), c.stem2,
                    c.hints_gr, c.hints_de, c.notes_gr, c.notes_de)

        rows = []
        for i, c in enumerate(shown_cards()):
            vals = values(c)[k:k + len(visible)]
            rows.append(ft.Container(
                ft.Row([cell(c.front, first_w)]
                       + [cell(v, cw) for v, (_, cw) in zip(vals, visible)],
                       spacing=0,
                       vertical_alignment=ft.CrossAxisAlignment.START),
                bgcolor=zebra if i % 2 else None,
                on_click=lambda e, c=c: open_card(c),
            ))
        body = ft.Column(rows, scroll=ft.ScrollMode.AUTO, expand=True,
                         spacing=0)
        return ft.Column([pager, header, ft.Divider(height=1), body],
                         spacing=0, expand=True)


    def shown_cards() -> list[VocabCard]:
        """Karten nach Worttyp-Filter (im Sortiermodus immer alle)."""
        if view_state["sort_mode"] or view_state["wtype"] is None:
            return vlist.cards
        return [c for c in vlist.cards if c.word_type == view_state["wtype"]]

    def set_filter(wtype: str | None):
        view_state["wtype"] = wtype
        view_state["sort_mode"] = False  # entweder filtern oder sortieren
        refresh()

    def toggle_sort(e):
        view_state["sort_mode"] = not view_state["sort_mode"]
        view_state["wtype"] = None
        view_state["select_mode"] = False  # entweder sortieren oder markieren
        refresh()

    def toggle_select(e):
        view_state["select_mode"] = not view_state["select_mode"]
        view_state["sort_mode"] = False
        if not view_state["select_mode"]:
            selected.clear()
        refresh()

    filter_btn = ft.PopupMenuButton(icon=ft.Icons.FILTER_LIST,
                                    tooltip="Nach Worttyp filtern")
    sort_btn = ft.IconButton(on_click=toggle_sort)
    select_btn = ft.IconButton(ft.Icons.CHECKLIST, on_click=toggle_select)

    def refresh_header_buttons():
        present = [t for t in WORD_TYPES
                   if any(c.word_type == t for c in vlist.cards)]
        filter_btn.items = [
            ft.PopupMenuItem(content="Alle Worttypen",
                             on_click=lambda e: set_filter(None)),
        ] + [
            ft.PopupMenuItem(content=t,
                             on_click=lambda e, t=t: set_filter(t))
            for t in present
        ]
        filter_btn.icon_color = (ft.Colors.PRIMARY
                                 if view_state["wtype"] else None)
        sort_btn.icon = (ft.Icons.CHECK if view_state["sort_mode"]
                         else ft.Icons.SWAP_VERT)
        sort_btn.icon_color = (ft.Colors.PRIMARY
                               if view_state["sort_mode"] else None)
        # Sortieren geht nur in der Kartenansicht, nicht in der Tabelle
        sort_btn.disabled = view_state["tab"] != 0
        sort_btn.tooltip = ("Sortieren beenden" if view_state["sort_mode"]
                            else "Karten verschieben (nur Kartenansicht)")
        # Markiermodus ebenso nur in der Kartenansicht
        select_btn.icon = (ft.Icons.CHECK if view_state["select_mode"]
                           else ft.Icons.CHECKLIST)
        select_btn.icon_color = (ft.Colors.PRIMARY
                                 if view_state["select_mode"] else None)
        select_btn.disabled = view_state["tab"] != 0
        select_btn.tooltip = ("Markieren beenden" if view_state["select_mode"]
                              else "Wörter markieren (Mehrfachauswahl)")
        # im Sortiermodus ist der Tab-Wechsel gesperrt
        tab_bar.disabled = view_state["sort_mode"]

    def reorder_cards(e):
        card = vlist.cards.pop(e.old_index)
        vlist.cards.insert(e.new_index, card)
        store.save_user_list(vlist)
        refresh()

    def sort_view() -> ft.Control:
        return ft.ReorderableListView(
            controls=[
                drag_row(ft.Row(
                    [ft.Text(c.with_plural(c.front), expand=1),
                     ft.Text(c.back, expand=1)],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ))
                for c in vlist.cards
            ],
            show_default_drag_handles=False,
            on_reorder=reorder_cards,
            expand=True,
        )

    # --- Mehrfachauswahl (Massenaktionen) ---

    def snack(text: str):
        page.show_dialog(ft.SnackBar(ft.Text(text)))

    def selected_cards() -> list[VocabCard]:
        return [c for c in vlist.cards if c.id in selected]

    def toggle_selected(card: VocabCard):
        if card.id in selected:
            selected.discard(card.id)
        else:
            selected.add(card.id)
        refresh()

    def select_all(select: bool):
        if select:
            selected.update(c.id for c in shown_cards())
        else:
            selected.clear()
        refresh()

    def pick_list_dialog(title: str, targets: list[VocabList], on_pick):
        """Zielliste wählen (für Verschieben/Kopieren)."""
        dd = ft.Dropdown(
            label="Zielliste", value=targets[0].id,
            options=[ft.DropdownOption(key=l.id, text=l.name)
                     for l in targets],
        )

        def ok(e):
            page.pop_dialog()
            on_pick(dd.value)

        page.show_dialog(ft.AlertDialog(
            title=ft.Text(title),
            content=dd,
            actions=[ft.TextButton("Abbrechen",
                                   on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("OK", on_click=ok)],
        ))

    def delete_selected(e):
        cards = selected_cards()

        def do(e):
            for c in cards:
                vlist.cards.remove(c)
            store.save_user_list(vlist)
            selected.clear()
            page.pop_dialog()
            refresh()

        page.show_dialog(ft.AlertDialog(
            title=ft.Text(f"{len(cards)} Karten löschen?"),
            content=ft.Text("Die markierten Karten werden endgültig "
                            "aus dieser Liste gelöscht."),
            actions=[ft.TextButton("Abbrechen",
                                   on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Löschen", on_click=do)],
        ))

    def move_selected(e):
        targets = [l for l in store.ordered_lists()
                   if l.editable and l.id != vlist.id]
        if not targets:
            snack("Keine andere eigene Liste vorhanden.")
            return

        def do(target_id: str):
            target = store.lists[target_id]
            moving = selected_cards()
            for c in moving:
                vlist.cards.remove(c)
            target.cards.extend(moving)
            store.save_user_list(target)
            store.save_user_list(vlist)
            selected.clear()
            refresh()
            snack(f"{len(moving)} Karten nach „{target.name}“ verschoben.")

        pick_list_dialog(f"{len(selected)} Karten verschieben", targets, do)

    def copy_selected(e):
        targets = [l for l in store.ordered_lists()
                   if l.editable and l.id != vlist.id]
        if not targets:
            snack("Keine eigene Zielliste vorhanden — erst eine anlegen.")
            return

        def do(target_id: str):
            target = store.lists[target_id]
            n = 0
            for c in selected_cards():
                d = c.to_dict()
                d.pop("id", None)  # Kopie bekommt eine frische ID
                copy = VocabCard.from_dict(d)
                copy.source = "custom"
                target.cards.append(copy)
                n += 1
            store.save_user_list(target)
            refresh()
            snack(f"{n} Karten nach „{target.name}“ kopiert.")

        pick_list_dialog(f"{len(selected)} Karten kopieren", targets, do)

    def delete_audio_selected(e):
        # Gecachte MP3s der markierten Wörter löschen — beim nächsten
        # Abspielen wird frisches Audio geholt (so lässt sich kaputtes
        # Audio korrigieren)
        cache = tts_cache()
        n = 0
        for c in selected_cards():
            path = cache.path_for(speakable(c.front))
            if path.exists():
                path.unlink()
                n += 1
        snack(f"{n} Audio-Dateien gelöscht — beim nächsten Abspielen "
              "wird das Audio neu erzeugt.")

    def add_to_selection_selected(e):
        sels = sorted(store.selections.values(), key=lambda x: x.name)
        NEW = "__new__"
        dd = ft.Dropdown(
            label="Auswahlliste",
            value=(sels[0].id if sels else NEW),
            options=[ft.DropdownOption(key=x.id, text=x.name) for x in sels]
            + [ft.DropdownOption(key=NEW, text="➕ Neue Auswahlliste…")],
        )
        tf_name = ft.TextField(label="Name der neuen Auswahlliste",
                               visible=not sels)
        error = ft.Text("", color=ft.Colors.ERROR, size=13)

        def on_select(e=None):
            tf_name.visible = dd.value == NEW
            page.update()

        # Flet-0.85-Dropdowns feuern on_select (kein on_change)
        dd.on_select = on_select

        def ok(e):
            cards = selected_cards()
            if dd.value == NEW:
                name = (tf_name.value or "").strip()
                if not name:
                    error.value = "Bitte einen Namen eingeben."
                    page.update()
                    return
                sel = SelectionList(name=name,
                                    card_ids=[c.id for c in cards])
                store.save_selection(sel)
                page.pop_dialog()
                snack(f"Auswahlliste „{name}“ mit {len(cards)} "
                      "Karten angelegt.")
                return
            sel = store.selections[dd.value]
            new = [c.id for c in cards if c.id not in sel.card_ids]
            sel.card_ids.extend(new)
            store.save_selection(sel)
            page.pop_dialog()
            snack(f"{len(new)} Karten zu „{sel.name}“ hinzugefügt.")

        page.show_dialog(ft.AlertDialog(
            title=ft.Text(f"{len(selected)} Karten zur Auswahlliste"),
            content=ft.Column([dd, tf_name, error], tight=True, spacing=10),
            actions=[ft.TextButton("Abbrechen",
                                   on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Hinzufügen", on_click=ok)],
        ))

    def select_action_bar() -> ft.Control:
        none = not selected

        def act_btn(icon, tooltip, handler, disabled=False):
            return ft.IconButton(icon, tooltip=tooltip, on_click=handler,
                                 disabled=disabled or none)

        buttons = [
            act_btn(ft.Icons.PLAYLIST_ADD, "Zur Auswahlliste hinzufügen…",
                    add_to_selection_selected),
            act_btn(ft.Icons.VOLUME_OFF,
                    "Audio löschen (wird neu erzeugt)",
                    delete_audio_selected),
            act_btn(ft.Icons.CONTENT_COPY, "In andere Liste kopieren…",
                    copy_selected),
        ]
        if vlist.editable:
            buttons += [
                act_btn(ft.Icons.DRIVE_FILE_MOVE_OUTLINED,
                        "In andere Liste verschieben…", move_selected),
                act_btn(ft.Icons.DELETE_OUTLINE, "Markierte löschen…",
                        delete_selected),
            ]
        return ft.Column([
            ft.Row([
                ft.Text(f"{len(selected)} markiert", size=13,
                        weight=ft.FontWeight.BOLD),
                ft.TextButton("Alle", on_click=lambda e: select_all(True)),
                ft.TextButton("Keine", on_click=lambda e: select_all(False)),
            ], spacing=4, wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row(buttons, spacing=0, wrap=True),
        ], spacing=0)

    def select_tiles(cards: list[VocabCard]) -> list[ft.Control]:
        return [
            ft.ListTile(
                dense=True,
                leading=ft.Icon(
                    ft.Icons.CHECK_BOX if c.id in selected
                    else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
                    color=ft.Colors.PRIMARY if c.id in selected else None,
                ),
                title=ft.Row(
                    [ft.Text(c.with_plural(c.front), expand=1),
                     ft.Text(c.back, expand=1)],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                selected=c.id in selected,
                selected_tile_color=ft.Colors.PRIMARY_CONTAINER,
                on_click=lambda e, c=c: toggle_selected(c),
            )
            for c in cards
        ]

    def refresh():
        refresh_header_buttons()
        shown = shown_cards()
        rows: list[ft.Control] = []
        if view_state["sort_mode"]:
            # eigene Scroll-Logik der ReorderableListView — die Spalte
            # selbst darf dann nicht auch noch scrollen
            cards_col.scroll = None
            rows.append(ft.Text("Sortiermodus: Karten am ≡ ziehen.",
                                italic=True, size=13))
            rows.append(sort_view())
        elif view_state["select_mode"]:
            cards_col.scroll = ft.ScrollMode.AUTO
            rows.append(select_action_bar())
            if view_state["wtype"]:
                rows.append(ft.Text(f"Filter: {view_state['wtype']}",
                                    italic=True, size=13))
            rows += select_tiles(shown)
            if vlist.cards and not shown:
                rows.append(ft.Text("Keine Karten für diesen Worttyp.",
                                    italic=True))
        else:
            cards_col.scroll = ft.ScrollMode.AUTO
            if vlist.editable:
                rows.append(ft.FilledButton(
                    "Neue Vokabel", icon=ft.Icons.ADD,
                    on_click=lambda e: open_card_editor(
                        page, store, vlist, None, on_saved=refresh)))
            else:
                rows.append(ft.Text("Buchliste — Vokabeln fest, eigene Hinweise/Notizen "
                                    "per Antippen ergänzbar", italic=True, size=13))
            if view_state["wtype"]:
                rows.append(ft.Text(f"Filter: {view_state['wtype']}",
                                    italic=True, size=13))
            rows += card_tiles(
                shown,
                on_click=open_card,
                on_delete=(lambda c: delete_card(c)) if vlist.editable else None,
            )
            if vlist.cards and not shown:
                rows.append(ft.Text("Keine Karten für diesen Worttyp.",
                                    italic=True))
        if not vlist.cards:
            rows.append(ft.Text("Noch keine Karten in dieser Liste."))
        cards_col.controls = rows
        if shown:
            # die Tabelle scrollt selbst (fixe Kopfzeile) — die Spalte
            # darf dann nicht auch noch scrollen
            table_col.scroll = None
            table_col.controls = [build_table()]
        else:
            table_col.scroll = ft.ScrollMode.AUTO
            table_col.controls = [
                ft.Text("Keine Karten für diesen Worttyp." if vlist.cards
                        else "Noch keine Karten in dieser Liste.")]
        page.update()

    def delete_card(card: VocabCard):
        vlist.cards.remove(card)
        store.save_user_list(vlist)
        refresh()

    # Zwei Reiter: Kartenliste und Tabelle aller Werte; die TabBarView
    # lässt sich auch per Links-rechts-Wischen wechseln. Rechts neben den
    # Reitern: Worttyp-Filter und (bei eigenen Listen) der Sortiermodus —
    # die Zeile bleibt beim Scrollen sichtbar, nur die Tab-Inhalte scrollen.
    tab_bar = ft.TabBar(tabs=[
        ft.Tab(label="Karten", icon=ft.Icons.VIEW_AGENDA_OUTLINED),
        ft.Tab(label="Tabelle", icon=ft.Icons.TABLE_ROWS_OUTLINED),
    ])
    header_row = [ft.Container(tab_bar, expand=True), filter_btn, select_btn]
    if vlist.editable:
        header_row.append(sort_btn)

    def on_tab_change(e):
        view_state["tab"] = tabs.selected_index
        if view_state["sort_mode"] and view_state["tab"] != 0:
            # Sortiermodus: Tabelle gesperrt (auch gegen Wisch-Wechsel) —
            # erst den Sortiermodus beenden
            tabs.selected_index = 0
            view_state["tab"] = 0
        refresh_header_buttons()
        page.update()

    tabs = ft.Tabs(
        length=2,
        expand=True,
        on_change=on_tab_change,
        content=ft.Column(
            [
                ft.Row(header_row,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.TabBarView(expand=True, controls=[cards_col, table_col]),
            ],
            expand=True,
        ),
    )
    refresh()

    if not vlist.editable:
        return tabs

    # Listenname als anklickbare Überschrift: Klick öffnet Umbenennen
    name_text = ft.Text(vlist.name, size=16, weight=ft.FontWeight.BOLD,
                        expand=True)

    def after_rename():
        name_text.value = vlist.name
        nav.stack[-1] = (vlist.name, nav.stack[-1][1])  # AppBar-Titel mitziehen
        nav._show()

    name_header = ft.Container(
        ft.Row([name_text,
                ft.Icon(ft.Icons.EDIT_OUTLINED, size=18)],
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ink=True, border_radius=8,
        padding=ft.Padding.symmetric(horizontal=4, vertical=2),
        tooltip="Liste umbenennen",
        on_click=lambda e: rename_dialog(page, store, vlist,
                                         on_saved=after_rename),
    )
    return ft.Column([name_header, tabs], spacing=4, expand=True)
