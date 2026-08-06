"""Update-Dialog und Update-Checks (Start + Hilfe → „Nach Updates suchen").

Die eigentliche Logik (GitHub-API, Drosselung, Versionsvergleich) liegt in
storage/updates.py; hier nur die Flet-Anbindung.
"""

from __future__ import annotations

import asyncio

import flet as ft

from mathainoa1 import __version__
from mathainoa1.storage import updates
from mathainoa1.ui.scale import sz


def show_update_dialog(page: ft.Page, info: updates.UpdateInfo) -> None:
    # Direktlink zur APK, sonst die Release-Seite (dort liegt sie auch)
    url = info.apk_url or info.page_url

    def download(e):
        async def run():
            await ft.UrlLauncher().launch_url(url)
        page.run_task(run)
        page.pop_dialog()

    body: list[ft.Control] = [
        ft.Text(f"Version {info.version} ist verfügbar "
                f"(installiert: {__version__}).", size=sz(14)),
        ft.Text("Die APK wird im Browser heruntergeladen und über die "
                "bestehende App installiert — Lernstand und Listen "
                "bleiben erhalten.", size=sz(13)),
    ]
    if info.notes:
        body += [ft.Divider(),
                 ft.Text(info.notes, size=sz(12), selectable=True)]
    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Update verfügbar"),
        content=ft.Column(body, tight=True, spacing=8, width=380,
                          scroll=ft.ScrollMode.AUTO),
        actions=[ft.TextButton("Später",
                               on_click=lambda e: page.pop_dialog()),
                 ft.FilledButton("Herunterladen", icon=ft.Icons.DOWNLOAD,
                                 on_click=download)],
    ))


def startup_checks(page: ft.Page) -> None:
    """Beim App-Start: Downgrade-Hinweis + stiller Update-Check.

    Der Update-Check läuft im Hintergrund (max. 1×/Tag) und meldet sich
    nur, wenn es wirklich ein Update gibt — sonst passiert nichts.
    """
    notice = updates.downgrade_notice()
    if notice:
        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Ältere App-Version"),
            content=ft.Text(notice, size=sz(14)),
            actions=[ft.TextButton("Verstanden",
                                   on_click=lambda e: page.pop_dialog())],
        ))

    async def run():
        info = await asyncio.to_thread(updates.auto_check)
        if info is not None:
            show_update_dialog(page, info)
    page.run_task(run)


def manual_check(page: ft.Page) -> None:
    """Update-Check auf Knopfdruck, mit Rückmeldung in jedem Fall."""
    async def run():
        try:
            info = await asyncio.to_thread(updates.fetch_latest)
        except (OSError, ValueError):
            page.show_dialog(ft.SnackBar(ft.Text(
                "Update-Check fehlgeschlagen — bitte die "
                "Internetverbindung prüfen.")))
            return
        if updates.is_installable_update(info):
            show_update_dialog(page, info)
        elif (updates.parse_version(info.version)
                > updates.parse_version(__version__)):
            # Release ist da, die APK aber noch nicht (Build läuft oder
            # ist gescheitert) — ehrlicher als „auf dem neuesten Stand"
            page.show_dialog(ft.SnackBar(ft.Text(
                f"Version {info.version} ist angekündigt, aber noch ohne "
                "installierbare Datei — bitte später noch einmal "
                "versuchen.")))
        else:
            page.show_dialog(ft.SnackBar(ft.Text(
                f"Du bist auf dem neuesten Stand ({__version__}).")))
    page.run_task(run)
