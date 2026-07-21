"""App-Gerüst: Startseite mit Navigation zu den Modi.

Navigation ist bewusst einfach gehalten: ein Inhalts-Container,
dessen Inhalt beim Navigieren ausgetauscht wird.
"""

from __future__ import annotations

import flet as ft

from mathainoa1 import APP_NAME
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.storage.settings import (
    app_data_dir,
    book_vocab_dir,
    load_app_settings,
    user_vocab_dir,
)
from mathainoa1.ui.views import grammar, manager, stats, trainer
from mathainoa1.ui.views.settings import apply_app_theme, settings_view


class Navigator:
    """Tauscht den Seiteninhalt aus und pflegt einen Zurück-Stapel."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.store: ContentStore | None = None  # in main() gesetzt (für Hilfe)
        self.stack: list[tuple[str, ft.Control]] = []
        from mathainoa1.ui.views.reference import reference_menu_button
        self.appbar = ft.AppBar(
            title=ft.Text(APP_NAME),
            actions=[
                ft.IconButton(ft.Icons.STICKY_NOTE_2_OUTLINED, tooltip="Notizen",
                              on_click=self._open_notes),
                reference_menu_button(self),
                ft.IconButton(ft.Icons.HELP_OUTLINE, tooltip="Hilfe",
                              on_click=self._open_help),
            ],
        )
        # oben 8px extra, damit schwebende Feld-Labels nicht abgeschnitten werden;
        # SafeArea hält den Inhalt von der Android-Systemleiste unten frei
        self.body = ft.Container(
            expand=True,
            padding=ft.Padding.only(left=16, right=16, top=8, bottom=8),
        )
        page.appbar = self.appbar
        page.add(ft.SafeArea(self.body, expand=True))
        # Android-Zurück-Taste an unseren Stapel koppeln: solange es eine
        # Unterseite gibt, navigiert sie zurück statt die App zu beenden
        root = page.views[0]
        root.can_pop = False

        async def confirm_pop(e):
            if len(self.stack) > 1:
                self.back()
                await root.confirm_pop(False)
            else:
                await root.confirm_pop(True)  # Startseite: App verlassen

        root.on_confirm_pop = confirm_pop

    def go(self, title: str, content: ft.Control) -> None:
        self.stack.append((title, content))
        self._show()

    def _open_help(self, e=None) -> None:
        from mathainoa1.ui.views.help import help_view
        if self.stack and self.stack[-1][0] == "Hilfe":
            return  # Hilfe ist schon offen
        self.go("Hilfe", help_view(self, self.store))

    def _open_notes(self, e=None) -> None:
        from mathainoa1.ui.views.notes import notes_view
        if self.stack and self.stack[-1][0] == "Notizen":
            return  # Notizen sind schon offen
        self.go("Notizen", notes_view(self))

    def back(self, e=None) -> None:
        if len(self.stack) > 1:
            self.stack.pop()
            self._show()

    def _show(self) -> None:
        title, content = self.stack[-1]
        self.appbar.title = ft.Text(title)
        self.appbar.leading = (
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=self.back)
            if len(self.stack) > 1 else None
        )
        self.body.content = content
        self.page.update()


def home_view(nav: Navigator, store: ContentStore, progress: ProgressStore) -> ft.Control:
    def item(icon, title, subtitle, builder=None):
        return ft.Card(
            content=ft.ListTile(
                leading=ft.Icon(icon, size=32),
                title=ft.Text(title, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(subtitle),
                on_click=(lambda e: nav.go(title, builder(nav))) if builder else None,
            ),
            opacity=1.0 if builder else 0.55,
        )

    menu = ft.Column(
        [
            item(ft.Icons.STYLE, "Vokabeltraining",
                 "Karteikarten oder Tippen, nach Liste und Worttyp",
                 lambda n: trainer.setup_view(n, store, progress)),
            item(ft.Icons.TABLE_CHART, "Nomentraining",
                 "Nomen und Adjektive: Plural, Akkusativ und Genitiv",
                 lambda n: grammar.setup_view(n, store, progress)),
            item(ft.Icons.SYNC_ALT, "Verbtraining",
                 "Verben im Präsens: vom deutschen Infinitiv zur Form",
                 lambda n: grammar.conjugation_setup_view(n, store, progress)),
            item(ft.Icons.EDIT_NOTE, "Vokabelverwaltung",
                 "Eigene Listen anlegen, importieren, exportieren",
                 lambda n: manager.manager_view(n, store, progress)),
            item(ft.Icons.INSIGHTS, "Statistik",
                 "Fortschritt und Problemwörter",
                 lambda n: stats.stats_view(n, store, progress)),
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
    )
    # Rundes Zahnrad unten rechts öffnet die Einstellungen
    settings_fab = ft.FloatingActionButton(
        icon=ft.Icons.SETTINGS, mini=True, bottom=16, right=16,
        tooltip="Einstellungen",
        on_click=lambda e: nav.go("Einstellungen", settings_view(nav)),
    )
    return ft.Stack([menu, settings_fab], expand=True)


def main(page: ft.Page) -> None:
    page.title = APP_NAME
    page.window.width = 420
    page.window.height = 780
    apply_app_theme(page, load_app_settings())
    store = ContentStore(book_vocab_dir(), user_vocab_dir())
    store.load_all()
    progress = ProgressStore(app_data_dir() / "progress.db")
    nav = Navigator(page)
    nav.store = store
    nav.go(APP_NAME, home_view(nav, store, progress))
