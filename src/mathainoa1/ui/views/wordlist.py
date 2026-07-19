"""Gemeinsame Wortlisten-Bausteine: Kartenzeilen und Filter-Panel.

Wird von Vokabelverwaltung, Statistik und Trainer-Vorschau geteilt, damit
alle Kartenansichten gleich aussehen: zwei Spalten (Griechisch | Deutsch),
links optional der Farbpunkt der Leitner-Box. Importiert bewusst keine
anderen View-Module (vermeidet Import-Zirkel).
"""

from __future__ import annotations

import flet as ft

from mathainoa1.models import WORD_TYPES, VocabCard
from mathainoa1.storage.progress import MAX_BOX, CardProgress

BOX_COLORS = [ft.Colors.RED, ft.Colors.ORANGE, ft.Colors.AMBER,
              ft.Colors.LIGHT_GREEN, ft.Colors.GREEN]
UNTRAINED_COLOR = ft.Colors.GREY


def box_color(box: int) -> str:
    """Farbe einer Box; Box 0 = noch nicht trainiert."""
    return BOX_COLORS[box - 1] if box else UNTRAINED_COLOR


def box_of(card: VocabCard, all_progress: dict[str, CardProgress]) -> int:
    """Leitner-Box einer Karte; 0 = noch nicht trainiert."""
    p = all_progress.get(card.id)
    return p.box if p and p.seen else 0


def box_chip_controls(active: set[int], on_toggle) -> list[ft.Control]:
    """Farbige Box-Umschalter (1–5 und „neu“) für Filterzeilen."""
    return [
        ft.Container(
            ft.Text("neu" if b == 0 else str(b), size=12, color=ft.Colors.WHITE),
            bgcolor=box_color(b), border_radius=6,
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            opacity=1.0 if b in active else 0.3,
            on_click=lambda e, b=b: on_toggle(b),
            tooltip=("Noch nicht trainiert" if b == 0 else f"Box {b}"),
        )
        for b in [1, 2, 3, 4, 5, 0]
    ]


def card_tiles(cards: list[VocabCard], on_click=None, on_delete=None,
               all_progress: dict[str, CardProgress] | None = None,
               ) -> list[ft.Control]:
    """Kartenzeilen: Griechisch und Deutsch nebeneinander in zwei Spalten,
    Hinweise/Notizen mit kleinem Abstand darunter.

    all_progress: Farbpunkt der Leitner-Box vorne (grau = untrainiert).
    """
    tiles = []
    for c in cards:
        extra = " · ".join(x for x in (c.notes_gr, c.notes_de, c.hints_gr, c.hints_de,
                                       "unregelmäßig" if (c.forms or c.stem2) else "") if x)
        leading = None
        if all_progress is not None:
            p = all_progress.get(c.id)
            box = p.box if p and p.seen else 0
            leading = ft.Icon(ft.Icons.CIRCLE, size=14, color=box_color(box))
        tiles.append(ft.ListTile(
            title=ft.Row(
                [
                    ft.Text(c.with_plural(c.front), expand=1),
                    ft.Text(c.back, expand=1),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            subtitle=ft.Container(
                ft.Text(extra, size=12),
                padding=ft.Padding.only(top=4),
            ) if extra else None,
            leading=leading,
            on_click=(lambda e, c=c: on_click(c)) if on_click else None,
            trailing=ft.IconButton(
                ft.Icons.DELETE_OUTLINE, tooltip="Löschen",
                on_click=lambda e, c=c: on_delete(c),
            ) if on_delete else None,
        ))
    return tiles


def drag_row(title: str | ft.Control, subtitle: str = "") -> ft.ListTile:
    """Zeile für den Sortiermodus: nur Inhalt + Drag-Griff (≡) rechts —
    keine Bearbeitung, man will ja sortieren."""
    return ft.ListTile(
        title=ft.Text(title) if isinstance(title, str) else title,
        subtitle=ft.Text(subtitle, size=12) if subtitle else None,
        trailing=ft.ReorderableDragHandle(
            content=ft.Icon(ft.Icons.DRAG_HANDLE),
        ),
    )


def word_list_panel(page: ft.Page, cards: list[VocabCard],
                    all_progress: dict[str, CardProgress],
                    on_click=None) -> ft.Control:
    """Wortliste mit Farbpunkt und Filtern: Box-Chips, Worttyp-Dropdown
    und Sortierung nach Lernstand (schlechteste zuerst)."""

    def box_of(c: VocabCard) -> int:
        p = all_progress.get(c.id)
        return p.box if p and p.seen else 0

    def wrong_of(c: VocabCard) -> int:
        p = all_progress.get(c.id)
        return p.wrong if p else 0

    counts = {b: 0 for b in range(0, MAX_BOX + 1)}
    for c in cards:
        counts[box_of(c)] += 1

    active: set[int] = set(range(0, MAX_BOX + 1))
    state = {"wtype": None, "sort_progress": False}
    chip_row = ft.Row(spacing=6, wrap=True)
    words_col = ft.Column(spacing=0)

    def toggle(box: int):
        if box in active:
            active.discard(box)
        else:
            active.add(box)
        refresh()

    present_types = [t for t in WORD_TYPES
                     if any(c.word_type == t for c in cards)]
    ALL = "Alle Worttypen"

    def select_type(e):
        state["wtype"] = None if dd_type.value == ALL else dd_type.value
        refresh()

    dd_type = ft.Dropdown(
        label="Worttyp", value=ALL, width=190,
        options=[ft.DropdownOption(key=ALL, text=ALL)]
        + [ft.DropdownOption(key=t, text=t) for t in present_types],
        # Achtung: Flet-0.85-Dropdowns feuern on_select (kein on_change)
        on_select=select_type,
    )

    def toggle_sort(e):
        state["sort_progress"] = not state["sort_progress"]
        sort_btn.icon_color = (ft.Colors.PRIMARY if state["sort_progress"]
                               else None)
        refresh()

    sort_btn = ft.IconButton(
        ft.Icons.SORT, tooltip="Nach Lernstand sortieren (schlechteste zuerst)",
        on_click=toggle_sort,
    )

    def refresh():
        chip_row.controls = [
            ft.Container(
                ft.Text(f"{counts[b]}" if b else f"neu {counts[b]}",
                        size=12, color=ft.Colors.WHITE),
                bgcolor=box_color(b), border_radius=6,
                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                opacity=1.0 if b in active else 0.3,
                on_click=lambda e, b=b: toggle(b),
                tooltip=("Noch nicht trainiert" if b == 0 else f"Box {b}"),
            )
            for b in [1, 2, 3, 4, 5, 0]
        ]
        shown = [c for c in cards
                 if box_of(c) in active
                 and (state["wtype"] is None or c.word_type == state["wtype"])]
        if state["sort_progress"]:
            shown.sort(key=lambda c: (box_of(c), -wrong_of(c)))
        words_col.controls = (
            card_tiles(shown, on_click=on_click, all_progress=all_progress)
            or [ft.Text("Keine Wörter für diese Auswahl.", italic=True)]
        )
        page.update()

    refresh()
    return ft.Column(
        [
            ft.Text("Boxen an-/abwählen:", size=13),
            chip_row,
            ft.Row([dd_type, sort_btn],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            words_col,
        ],
        spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
    )
