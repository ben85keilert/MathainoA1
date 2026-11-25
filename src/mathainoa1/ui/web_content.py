"""Web-Fassung: das Inhaltspaket vom Server holen und mit dem Code öffnen —
und die App geschlossen halten, solange das nicht gelungen ist.

Die Logik (Standdatei, Paket, Entschlüsseln, Übernehmen, „bleibt zu?“)
steht in storage/content_package.py; hier nur die Flet-Anbindung und der
Netzweg des Browsers. Geladen wird ausschließlich vom eigenen Server
(relative Adressen) — die Seite fragt nie eine fremde Adresse.

Die Sperrseite ist kein Zugangsschutz des Servers: Der liefert nur Dateien
aus, und der Quelltext der App ist öffentlich. Geschützt sind die Inhalte
— sie sind verschlüsselt. Die Sperrseite sorgt dafür, dass die Seite ohne
Code zu nichts zu gebrauchen ist.
"""

from __future__ import annotations

import flet as ft

from mathainoa1 import APP_NAME
from mathainoa1.storage import content_package as cp
from mathainoa1.storage.settings import load_app_settings, save_app_settings
from mathainoa1.ui.scale import sz

# Steht auf der Sperrseite, wenn die Standdatei des Servers keinen eigenen
# Infotext mitbringt ("hinweis")
DEFAULT_NOTICE = (
    "Diese Seite ist eine Lern-App für Griechisch. Sie arbeitet vollständig "
    "in deinem Browser: Lernstand, Vokabellisten, Notizen, Einstellungen und "
    "der Code bleiben auf diesem Gerät und werden an keinen Server gesendet. "
    "Löscht der Browser seine Websitedaten, ist alles weg."
)


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


async def load_scrypt() -> None:
    """Dem Python im Browser fehlt hashlib.scrypt: cryptography nachladen —
    vom eigenen Server (tools/web_build.py legt es neben Pyodide), und erst,
    wenn wirklich ein Paket zu öffnen ist. Scheitert das, meldet es der
    nächste Schritt als NotPossible."""
    if cp.scrypt_available():
        return
    try:
        import pyodide_js
        await pyodide_js.loadPackage("cryptography")
    except Exception:  # noqa: BLE001 — nicht im Browser, Paket fehlt
        pass


class WebContent:
    """Beim Start und auf Knopfdruck: nachsehen, laden, öffnen — oder die
    Sperrseite zeigen. open_app() baut das Hauptmenü (ui/app.py)."""

    def __init__(self, nav, store, open_app, fetch=browser_fetch):
        self.nav = nav
        self.page = nav.page
        self.open_app = open_app
        self.updater = cp.Updater(fetch, store, prepare=load_scrypt)

    # --- Ablauf ---

    async def start(self) -> str:
        """Beim Laden der Seite: erst prüfen, dann App oder Sperrseite."""
        result = await self.updater.check()
        if self.updater.locked:
            self._lock()
        else:
            self.open_app()
            if result == cp.UPDATED:
                self._announce_update()
        return result

    async def check(self, announce: bool = False) -> str:
        """Bei offener App (Knopf in den Einstellungen): nach Neuem sehen.
        Wurde der Code inzwischen gesperrt, schließt sich die App."""
        result = await self.updater.check()
        if self.updater.locked:
            self._lock()
        elif result == cp.UPDATED:
            self._announce_update()
        elif announce:
            self._snack({
                cp.CURRENT: "Die Inhalte sind auf dem neuesten Stand.",
                cp.NOTHING: "Auf dem Server liegen keine Inhalte.",
            }.get(result, "Der Server ist gerade nicht erreichbar."))
        return result

    def _lock(self) -> None:
        self.nav.appbar.visible = False
        self.nav.stack.clear()
        self.nav.go(APP_NAME, self.gate_view())

    # --- Ansichten ---

    def loading_view(self) -> ft.Control:
        return ft.Column(
            [ft.ProgressRing(), ft.Text("Μαθαίνω wird geladen …")],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)

    def gate_view(self) -> ft.Control:
        """Die Sperrseite: Infotext und Code-Eingabe. Kein „Später“ — ohne
        Code gibt es hier nichts zu sehen."""
        page, up = self.page, self.updater
        head = [
            ft.Text("Μαθαίνω", size=sz(28), weight=ft.FontWeight.BOLD),
            ft.Text(up.notice or DEFAULT_NOTICE, size=sz(14)),
            ft.Divider(),
        ]
        if up.result == cp.UNREACHABLE:
            async def retry(e=None):
                await self.start()

            return self._frame(head + [
                ft.Text("Die Inhalte dieser Seite sind gerade nicht "
                        "erreichbar. Prüfe die Internetverbindung und "
                        "versuche es noch einmal.", size=sz(14)),
                ft.FilledButton("Erneut versuchen", icon=ft.Icons.REFRESH,
                                on_click=retry),
            ])

        field = ft.TextField(label="Code", autofocus=True, max_length=12,
                             capitalization=ft.TextCapitalization.CHARACTERS,
                             hint_text="z.B. K7QM-9XA2")
        error = ft.Text("", color=ft.Colors.ERROR, size=sz(13))
        intro = ("Dein bisheriger Code gilt nicht mehr. Mit dem neuen Code "
                 "geht es weiter — dein Lernstand ist noch da."
                 if up.had_code else
                 "Diese Seite öffnet sich mit einem Code. Du hast ihn "
                 "zusammen mit der Adresse bekommen.")

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
            first = not up.had_code
            try:
                await load_scrypt()
                up.open(code)
            except cp.NotPossible:
                error.value = "Dieser Browser kann die Inhalte nicht öffnen."
            except cp.WrongCode as exc:
                error.value = str(exc)
            else:
                self._opened(first)
                return
            button.disabled = False
            page.update()
            await field.focus()  # gleich neu tippen können

        field.on_submit = submit
        button = ft.FilledButton("Öffnen", icon=ft.Icons.LOCK_OPEN,
                                 on_click=submit)
        return self._frame(head + [ft.Text(intro, size=sz(14)), field,
                                   error, button])

    @staticmethod
    def _frame(controls: list[ft.Control]) -> ft.Control:
        return ft.Column(
            [ft.Container(ft.Column(controls, spacing=14, tight=True),
                          padding=ft.Padding.only(top=32), width=420)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO, expand=True)

    # --- nach dem Öffnen ---

    def _opened(self, first: bool) -> None:
        # Beim ersten Öffnen das Lexikon einschalten, wenn das Paket eines
        # mitbringt — sonst fände es niemand (Standard: aus)
        if first and self.updater.stats.get("lexikon"):
            settings = load_app_settings()
            if "lexikon" not in settings.enabled_features:
                settings.enabled_features.append("lexikon")
                save_app_settings(settings)
        self.open_app()
        self._announce_update(first)

    def _announce_update(self, first: bool = False) -> None:
        stats = self.updater.stats
        text = (f"Inhalte {'geladen' if first else 'aktualisiert'}: "
                f"{stats.get('lists', 0)} Listen")
        if stats.get("lexikon"):
            text += f", {stats['lexikon']} Lexikoneinträge"
        if first:
            text += ". Die Stufe (A1/A2) wählst du in den Einstellungen"
        self._snack(text + ".")

    def _snack(self, text: str) -> None:
        self.page.show_dialog(ft.SnackBar(ft.Text(text)))
