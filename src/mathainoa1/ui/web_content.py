"""Web-Fassung: das Inhaltspaket vom Server holen und mit dem Code öffnen.

Die Logik (Standdatei, Paket, Entschlüsseln, Übernehmen) steht in
storage/content_package.py; hier nur die Flet-Anbindung und der Netzweg
des Browsers. Geladen wird ausschließlich vom eigenen Server (relative
Adressen) — die Seite fragt nie eine fremde Adresse.
"""

from __future__ import annotations

import flet as ft

from mathainoa1.storage import content_package as cp
from mathainoa1.storage.settings import load_app_settings, save_app_settings
from mathainoa1.ui.scale import sz


async def browser_fetch(path: str) -> tuple[int, bytes]:
    """`fetch` des Browsers — nur in Pyodide. Ohne Zwischenspeicher, damit
    eine neue Standdatei sofort gesehen wird."""
    from urllib.parse import urljoin

    import js
    from pyodide.http import pyfetch

    response = await pyfetch(urljoin(str(js.location.href), path),
                             cache="no-store")
    if response.status != 200:
        return response.status, b""
    return response.status, await response.bytes()


class WebContent:
    """Beim Start und auf Knopfdruck: nachsehen, laden, nach dem Code
    fragen, übernehmen."""

    def __init__(self, nav, store, fetch=browser_fetch):
        self.nav = nav
        self.page = nav.page
        self.updater = cp.Updater(fetch, store)

    async def check(self, announce: bool = False) -> str:
        """announce: auch „nichts Neues“ melden (Knopf in den
        Einstellungen); beim Start bleibt das still."""
        result = await self.updater.check()
        if result == cp.NEED_CODE:
            self.ask_code()
        elif result == cp.UPDATED:
            self._done()
        elif announce:
            self._snack("Die Inhalte sind auf dem neuesten Stand."
                        if result == cp.CURRENT
                        else "Auf dem Server liegen keine Inhalte "
                             "(oder er ist nicht erreichbar).")
        return result

    def ask_code(self) -> None:
        page = self.page
        field = ft.TextField(label="Code", autofocus=True, max_length=12,
                             capitalization=ft.TextCapitalization.CHARACTERS,
                             hint_text="z.B. K7QM-9XA2")
        error = ft.Text("", color=ft.Colors.ERROR, size=sz(13))
        intro = ("Der bisherige Code gilt nicht mehr. Für die neuen Inhalte "
                 "brauchst du den neuen Code — was du schon hast, bleibt."
                 if self.updater.had_code else
                 "Die Vokabellisten dieser Seite sind mit einem Code "
                 "geschützt. Du hast ihn zusammen mit der Adresse bekommen.")

        async def submit(e=None):
            code = cp.normalize_code(field.value or "")
            if code is None:
                error.value = ("Ein Code hat 8 Zeichen: Buchstaben und "
                               "Ziffern, ohne 0, O, 1 und I.")
                page.update()
                return
            error.value = "Wird geöffnet …"
            button.disabled = True
            page.update()
            try:
                self.updater.open(code)
            except cp.NotPossible:
                error.value = "Dieser Browser kann das Paket nicht öffnen."
            except cp.WrongCode as exc:
                error.value = str(exc)
            else:
                page.pop_dialog()
                self._done()
                return
            button.disabled = False
            page.update()

        field.on_submit = submit
        button = ft.FilledButton("Öffnen", on_click=submit)
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Code eingeben"),
            content=ft.Column([ft.Text(intro, size=sz(14)), field, error],
                              tight=True, spacing=10, width=360),
            actions=[ft.TextButton("Später",
                                   on_click=lambda e: page.pop_dialog()),
                     button],
        ))

    def _done(self) -> None:
        stats = self.updater.stats
        # Beim ersten Öffnen das Lexikon einschalten, wenn das Paket eines
        # mitbringt — sonst fände es niemand (Standard: aus)
        if stats.get("lexikon") and not self.updater.had_code:
            settings = load_app_settings()
            if "lexikon" not in settings.enabled_features:
                settings.enabled_features.append("lexikon")
                save_app_settings(settings)
        self.updater.had_code = True
        self.nav._show()  # Hauptmenü frisch aufbauen (Lexikon-Karte)
        text = f"Inhalte geladen: {stats.get('lists', 0)} Listen"
        if stats.get("lexikon"):
            text += f", {stats['lexikon']} Lexikoneinträge"
        self._snack(text + ". Die Stufe (A1/A2) wählst du in den "
                           "Einstellungen.")

    def _snack(self, text: str) -> None:
        self.page.show_dialog(ft.SnackBar(ft.Text(text)))
