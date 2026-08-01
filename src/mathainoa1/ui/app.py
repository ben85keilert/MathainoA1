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
from mathainoa1.ui.features import enabled_features
from mathainoa1.ui.updates import startup_checks
from mathainoa1.ui.views import grammar, manager, stats, trainer
from mathainoa1.ui.views.settings import apply_app_theme, settings_view
from mathainoa1.ui.scale import sz


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
                ft.IconButton(ft.Icons.SEARCH, tooltip="Wortsuche",
                              on_click=self._open_search),
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

    def _open_search(self, e=None) -> None:
        from mathainoa1.ui.views.manager import search_view
        if self.store is None or (self.stack
                                  and self.stack[-1][0] == "Wortsuche"):
            return  # Suche ist schon offen (oder Store noch nicht gesetzt)
        self.go("Wortsuche", search_view(self, self.store))

    def back(self, e=None) -> None:
        if len(self.stack) > 1:
            self.stack.pop()
            self._show()

    def _show(self) -> None:
        title, content = self.stack[-1]
        if len(self.stack) == 1:
            # Startseite: kurzer Titel + aktive Stufe (frisch gelesen —
            # _show läuft auch beim Zurückkehren aus den Einstellungen)
            title = f"Μαθαίνω – {load_app_settings().level}"
        self.appbar.title = ft.Text(title)
        self.appbar.leading = (
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=self.back)
            if len(self.stack) > 1 else None
        )
        self.body.content = content
        # Views mit on_reappear-Attribut frischen sich beim (Wieder-)
        # Anzeigen selbst auf — z.B. das Listenmenü nach dem Anlegen
        # einer Auswahlliste in einer Unterseite
        callback = getattr(content, "on_reappear", None)
        if callback:
            callback()
        self.page.update()


# Kern-Kacheln des Hauptmenüs in Standardreihenfolge: (key, icon, Titel,
# Untertitel). key ist stabil und wird in AppSettings.menu_order gespeichert.
CORE_TILES = [
    ("vokabeln", ft.Icons.STYLE, "Vokabeltraining",
     "Karteikarten oder Tippen, nach Liste und Worttyp"),
    ("statistik", ft.Icons.INSIGHTS, "Statistik",
     "Fortschritt und Problemwörter"),
    ("nomen", ft.Icons.TABLE_CHART, "Nomentraining",
     "Nomen deklinieren: Plural, Akkusativ und Genitiv"),
    ("verben", ft.Icons.SYNC_ALT, "Verbtraining",
     "Verben im Präsens: vom deutschen Infinitiv zur Form"),
    ("adjektive", ft.Icons.PALETTE_OUTLINED, "Adjektivtraining",
     "Adjektiv + Nomen deklinieren — mit eigenen Verbindungen"),
    ("verwaltung", ft.Icons.EDIT_NOTE, "Vokabelverwaltung",
     "Eigene Listen anlegen, importieren, exportieren"),
]


def menu_tiles_meta(app_settings) -> list[tuple[str, str, str]]:
    """(key, Titel, Icon) aller Kacheln in Standardreihenfolge, inkl.
    eingeschalteter Features — für den Sortier-Editor der Einstellungen."""
    metas = [(key, title, icon) for key, icon, title, _sub in CORE_TILES]
    metas += [(f.key, f.title, f.icon)
              for f in enabled_features(app_settings)]
    return metas


def ordered_menu_keys(default_keys: list[str],
                      saved: list[str]) -> list[str]:
    """Gespeicherte Reihenfolge anwenden: unbekannte gespeicherte Keys
    entfallen, neue (ungespeicherte) Kacheln hängen sich in
    Standardreihenfolge hinten an."""
    known = set(default_keys)
    order = [k for k in saved if k in known]
    return order + [k for k in default_keys if k not in order]


def home_view(nav: Navigator, store: ContentStore, progress: ProgressStore) -> ft.Control:
    def item(icon, title, subtitle, builder=None):
        return ft.Card(
            content=ft.ListTile(
                leading=ft.Icon(icon, size=sz(32)),
                title=ft.Text(title, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(subtitle),
                on_click=(lambda e: nav.go(title, builder(nav))) if builder else None,
            ),
            opacity=1.0 if builder else 0.55,
        )

    builders = {
        "vokabeln": lambda n: trainer.setup_view(n, store, progress),
        "statistik": lambda n: stats.stats_view(n, store, progress),
        "nomen": lambda n: grammar.setup_view(n, store, progress),
        "verben": lambda n: grammar.conjugation_setup_view(n, store, progress),
        "adjektive": lambda n: grammar.adjective_setup_view(n, store, progress),
        "verwaltung": lambda n: manager.manager_view(n, store, progress),
    }

    def build_menu() -> list[ft.Control]:
        app = load_app_settings()
        tiles = {key: item(icon, title, sub, builders[key])
                 for key, icon, title, sub in CORE_TILES}
        default_keys = [key for key, _i, _t, _s in CORE_TILES]
        for f in enabled_features(app):
            tiles[f.key] = item(f.icon, f.title, f.subtitle,
                                lambda n, f=f: f.build(n, store, progress))
            default_keys.append(f.key)
        return [tiles[k] for k in ordered_menu_keys(default_keys,
                                                    app.menu_order)]

    menu = ft.Column(build_menu(), spacing=8, scroll=ft.ScrollMode.AUTO)
    # Rundes Zahnrad unten rechts öffnet die Einstellungen
    settings_fab = ft.FloatingActionButton(
        icon=ft.Icons.SETTINGS, mini=True, bottom=16, right=16,
        tooltip="Einstellungen",
        on_click=lambda e: nav.go("Einstellungen",
                                  settings_view(nav, store, progress)),
    )
    root = ft.Stack([menu, settings_fab], expand=True)

    def refresh_menu():
        # In den Einstellungen umgeschaltete Features beim Zurücknavigieren
        # ein-/ausblenden (Navigator._show ruft on_reappear auf)
        menu.controls = build_menu()

    root.on_reappear = refresh_menu
    return root


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
    startup_checks(page)
