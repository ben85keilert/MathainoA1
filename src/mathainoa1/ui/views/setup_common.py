"""Gemeinsamer Baustein der Trainings-Startseiten: kompakte Optionszeile.

Die selteneren Optionen (Schalter wie Fehlerrunde/Toleranzen) stehen
nicht mehr einzeln auf der Startseite, sondern kompakt zusammengefasst
unter den Start-Buttons; Tippen öffnet einen Dialog mit den Controls.
Jede Änderung dort speichert sofort (on_change des Aufrufers) und
aktualisiert die Zusammenfassung — nicht erst beim Trainingsstart.
"""

from __future__ import annotations

from typing import Callable, Sequence

import flet as ft

from mathainoa1.ui.scale import sz


def options_summary(page: ft.Page,
                    describe: Callable[[], list[str]],
                    controls: Sequence[ft.Control],
                    on_change: Callable[[], None],
                    title: str = "Weitere Optionen") -> ft.Control:
    """Kompakte Options-Karte: Zusammenfassung + Bearbeiten im Dialog.

    describe() liefert je Option eine Kurzbeschreibung des aktuellen
    Werts (z.B. "Fehlerrunde: an"). controls sind die Options-Controls —
    sie LEBEN im Dialog; bei jedem on_change eines Controls wird erst
    on_change() des Aufrufers gerufen (sofort speichern), dann die
    Zusammenfassung aufgefrischt. Controls ohne on_change-Feld (z.B.
    Beschriftungs-Texte) werden einfach mit angezeigt.
    """
    summary = ft.Text(" · ".join(describe()), size=sz(13))

    def refresh() -> None:
        summary.value = " · ".join(describe())

    def changed(e) -> None:
        on_change()
        refresh()
        page.update()

    for c in controls:
        if hasattr(c, "on_change"):
            c.on_change = changed

    def open_dialog(e) -> None:
        w = getattr(page, "width", None) or 420
        page.show_dialog(ft.AlertDialog(
            title=ft.Text(title, size=sz(16)),
            content=ft.Column(list(controls), tight=True, spacing=8,
                              scroll=ft.ScrollMode.AUTO, width=w),
            actions=[ft.TextButton(
                "Schließen", on_click=lambda e: page.pop_dialog())],
        ))

    return ft.Card(content=ft.ListTile(
        leading=ft.Icon(ft.Icons.TUNE, color=ft.Colors.PRIMARY),
        title=ft.Text(title, size=sz(14), weight=ft.FontWeight.BOLD),
        subtitle=summary,
        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
        on_click=open_dialog,
    ))


def on_off(label: str, value: bool) -> str:
    """Kurzform "Label: an/aus" für describe()-Listen."""
    return f"{label}: {'an' if value else 'aus'}"
