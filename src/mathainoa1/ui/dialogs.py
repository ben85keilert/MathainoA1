"""Geteilte Dialoge der Views (bewusst ohne Import anderer View-Module)."""

from __future__ import annotations

import flet as ft
from mathainoa1.ui.scale import sz


def plaintext_dialog(page: ft.Page, title: str, text: str) -> None:
    """Exporttext anzeigen: markierbar plus Kopieren-Button.

    Wird von Vokabelverwaltung und Statistik-Export genutzt.
    """
    clipboard = ft.Clipboard()
    page.services.append(clipboard)

    def copy(e):
        async def do():
            await clipboard.set(text)
        page.run_task(do)
        page.pop_dialog()
        page.show_dialog(ft.SnackBar(ft.Text(
            "Export in die Zwischenablage kopiert.")))

    page.show_dialog(ft.AlertDialog(
        title=ft.Text(title, size=sz(16)),
        content=ft.Column(
            [ft.Text(text, size=sz(12), selectable=True)],
            scroll=ft.ScrollMode.AUTO, width=420, height=440,
        ),
        actions=[
            ft.TextButton("Kopieren", icon=ft.Icons.COPY, on_click=copy),
            ft.TextButton("Schließen",
                          on_click=lambda e: page.pop_dialog()),
        ],
    ))
