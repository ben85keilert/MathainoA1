"""Statistik: Fortschritt pro Liste, Boxen-Verteilung, Problemwörter.

Klick auf eine Liste öffnet die Wortansicht: alle Wörter mit Farbpunkt
ihrer Box, oben Filter-Chips zum An-/Abwählen einzelner Boxen.
"""

from __future__ import annotations

import flet as ft

from mathainoa1.models import VocabList
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.progress import MAX_BOX, CardProgress, ProgressStore
from mathainoa1.ui.views.wordlist import BOX_COLORS, word_list_panel


def stats_view(nav, store: ContentStore, progress: ProgressStore) -> ft.Control:
    all_progress = progress.all()

    def reset_list(vlist) -> None:
        def do_reset(e):
            progress.reset([c.id for c in vlist.cards])
            nav.page.pop_dialog()
            # Ansicht mit frischen Daten neu aufbauen
            nav.stack[-1] = ("Statistik", stats_view(nav, store, progress))
            nav._show()

        nav.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Statistik zurücksetzen?"),
            content=ft.Text(
                f"Der Lernstand aller {len(vlist.cards)} Karten von "
                f"„{vlist.name}“ wird gelöscht — sie gelten danach wieder "
                "als neu. Das lässt sich nicht rückgängig machen."),
            actions=[
                ft.TextButton("Abbrechen",
                              on_click=lambda e: nav.page.pop_dialog()),
                ft.FilledButton("Zurücksetzen", on_click=do_reset),
            ],
        ))

    def list_block(vlist) -> ft.Control:
        boxes = {i: 0 for i in range(1, MAX_BOX + 1)}
        seen = 0
        for c in vlist.cards:
            p = all_progress.get(c.id)
            if p and p.seen:
                seen += 1
                boxes[p.box] += 1
        learned = boxes[MAX_BOX - 1] + boxes[MAX_BOX]
        box_row = ft.Row(
            [ft.Container(
                ft.Text(str(boxes[i]), size=12, color=ft.Colors.WHITE),
                bgcolor=BOX_COLORS[i - 1], border_radius=6,
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            ) for i in range(1, MAX_BOX + 1)],
            spacing=6, wrap=True,
        )
        return ft.Card(
            content=ft.Container(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(vlist.name, weight=ft.FontWeight.BOLD,
                                        expand=True),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE, icon_size=18,
                                    tooltip="Statistik dieser Liste zurücksetzen",
                                    on_click=lambda e, l=vlist: reset_list(l),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(f"{seen} von {len(vlist.cards)} Karten trainiert, "
                                f"{learned} sicher (Box 4–5)", size=13),
                        ft.ProgressBar(value=seen / max(1, len(vlist.cards))),
                        box_row,
                    ],
                    spacing=8,
                ),
                padding=12,
                ink=True,
                on_click=lambda e, l=vlist: nav.go(
                    l.name, list_words_view(nav, l, all_progress)),
            )
        )

    lists = sorted(store.lists.values(),
                   key=lambda l: (l.chapter is None, l.chapter or 0, l.name))
    blocks = [list_block(l) for l in lists]

    # Problemwörter: am häufigsten falsch beantwortete Karten
    by_id = {c.id: c for l in lists for c in l.cards}
    problems = sorted(
        (p for p in all_progress.values() if p.wrong > 0 and p.card_id in by_id),
        key=lambda p: (-p.wrong, p.box),
    )[:10]
    problem_tiles = [
        ft.ListTile(
            leading=ft.Icon(ft.Icons.PRIORITY_HIGH, color=ft.Colors.ERROR),
            title=ft.Text(by_id[p.card_id].front),
            subtitle=ft.Text(by_id[p.card_id].back),
            trailing=ft.Text(f"{p.wrong}× falsch\nBox {p.box}", size=12,
                             text_align=ft.TextAlign.RIGHT),
        )
        for p in problems
    ]

    controls: list[ft.Control] = blocks
    if problem_tiles:
        controls += [ft.Divider(),
                     ft.Text("Problemwörter", size=18, weight=ft.FontWeight.BOLD),
                     *problem_tiles]
    elif not any(p.seen for p in all_progress.values()):
        controls.append(ft.Text("Noch keine Trainingsdaten — starte eine Runde!"))

    return ft.Column(controls, spacing=10, scroll=ft.ScrollMode.AUTO)


def list_words_view(nav, vlist: VocabList,
                    all_progress: dict[str, CardProgress]) -> ft.Control:
    """Wörter einer Liste: gemeinsames Panel mit Farbpunkt und Filtern."""
    return word_list_panel(nav.page, vlist.cards, all_progress)
