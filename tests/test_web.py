"""Tests für das Web-Profil (web.py): was in der Web-Fassung anders ist.
Jede Funktion aus web.WEB_OFF hat hier einen Test, der den Web-Zweig
durchläuft."""

from types import SimpleNamespace

import pytest

from mathainoa1 import web
from mathainoa1.storage.settings import TTS_GOOGLE, TTS_SYSTEM


@pytest.fixture
def browser(monkeypatch, tmp_path):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    monkeypatch.setenv("MATHAINO_WEB", "1")


def test_ausserhalb_des_browsers_ist_alles_an(monkeypatch):
    monkeypatch.delenv("MATHAINO_WEB", raising=False)
    assert not web.in_browser()
    assert all(web.active(name) for name in web.WEB_OFF)


def test_im_browser_ist_das_profil_aus(browser):
    assert web.in_browser()
    assert not any(web.active(name) for name in web.WEB_OFF)
    assert web.active("irgendwas_anderes")


def test_getestete_funktionen_sind_vollstaendig():
    """Kommt eine Funktion in WEB_OFF dazu, braucht sie hier einen Test."""
    assert set(web.WEB_OFF) == {"update_check", "tts_google"}


def test_kein_update_check_im_browser(browser, monkeypatch):
    from mathainoa1.storage import updates
    from mathainoa1.ui import updates as ui_updates

    def boom(*a, **kw):
        raise AssertionError("im Browser darf nichts geprüft werden")

    monkeypatch.setattr(updates, "downgrade_notice", boom)
    monkeypatch.setattr(updates, "auto_check", boom)
    page = SimpleNamespace(run_task=boom, show_dialog=boom)
    ui_updates.startup_checks(page)


def test_sprachausgabe_im_browser_nur_systemstimme(browser, monkeypatch):
    from mathainoa1.ui import audio
    monkeypatch.setattr(audio, "_engine", TTS_GOOGLE)
    assert audio.tts_engine() == TTS_SYSTEM
    monkeypatch.delenv("MATHAINO_WEB")
    assert audio.tts_engine() == TTS_GOOGLE


def test_einstellungen_zeigen_speicher_nur_mit_browserspeicher(browser):
    import flet as ft

    from mathainoa1.storage import browser_storage as bs
    from mathainoa1.ui.views import settings as settings_mod

    page = SimpleNamespace(services=[], update=lambda: None,
                           show_dialog=lambda d: None,
                           pop_dialog=lambda: None)
    nav = SimpleNamespace(page=page, go=lambda *a: None, browser_storage=None)
    ohne = len(settings_mod.settings_view(nav).controls)
    nav.browser_storage = bs.BrowserStorage(None, None, state=bs.ON)
    assert len(settings_mod.settings_view(nav).controls) == ohne + 1
    view = settings_mod.settings_category_view(nav, "browser")
    assert isinstance(view, ft.Column)
    texts = [c.value for c in view.controls if isinstance(c, ft.Text)]
    assert bs.TEXTS[bs.ON] in texts
    # Sprachausgabe: im Browser ohne die Wahl „Google (online)“
    tts = settings_mod.settings_category_view(nav, "sprachausgabe")
    assert not any(isinstance(c, ft.RadioGroup) for c in tts.controls)


def test_einstieg_ist_ausserhalb_von_pyodide_main():
    from mathainoa1.ui import app
    assert app.entry() is app.main


# --- Sperrseite (ui/web_content.py) ---

def _web_nav():
    page = SimpleNamespace(update=lambda: None, show_dialog=lambda d: None,
                           pop_dialog=lambda: None, services=[])
    shown = []
    nav = SimpleNamespace(page=page, stack=[], appbar=SimpleNamespace(visible=True),
                          go=lambda title, view: shown.append(view))
    return nav, shown


def _texts(control):
    import flet as ft
    found = []
    stack = [control]
    while stack:
        c = stack.pop()
        if isinstance(c, ft.Text):
            found.append(c.value)
        stack += list(getattr(c, "controls", None) or [])
        if getattr(c, "content", None) is not None:
            stack.append(c.content)
    return found


def _server(hinweis=""):
    import json

    from mathainoa1.storage import content_package as cp
    liste = {"id": "t1", "name": "T", "book": "A2", "editable": True,
             "cards": [{"id": "t1-1", "front": "γράφω", "back": "schreiben"}]}
    stand = {"version": cp.content_version([liste], []), "hinweis": hinweis}
    files = {cp.STAND_URL: json.dumps(stand).encode(),
             cp.PACKAGE_URL: cp.pack([liste], [], "K7QM9XA2")}

    async def fetch(path):
        return (200, files[path]) if path in files else (404, b"")

    return fetch


def test_ohne_code_zeigt_die_seite_nur_die_sperre(browser, tmp_path):
    import asyncio

    import flet as ft

    from mathainoa1.storage.content import ContentStore
    from mathainoa1.ui.web_content import WebContent

    store = ContentStore(tmp_path / "book", tmp_path / "vocab")
    store.load_all()
    nav, shown = _web_nav()
    opened = []
    wc = WebContent(nav, store, lambda: opened.append(True),
                    fetch=_server("Private Seite, kleiner Kreis."))
    asyncio.run(wc.start())
    assert opened == [] and nav.appbar.visible is False
    gate = shown[-1]
    texts = _texts(gate)
    assert "Private Seite, kleiner Kreis." in texts  # Infotext des Betreibers

    def controls(c):
        out, stack = [], [c]
        while stack:
            x = stack.pop()
            out.append(x)
            stack += list(getattr(x, "controls", None) or [])
            if getattr(x, "content", None) is not None:
                stack.append(x.content)
        return out

    # ein Feld für den Code, ein Knopf — kein „Später“, kein Weg vorbei
    assert sum(isinstance(c, ft.TextField) for c in controls(gate)) == 1
    buttons = [c for c in controls(gate)
               if isinstance(c, (ft.TextButton, ft.FilledButton,
                                 ft.OutlinedButton))]
    assert len(buttons) == 1


def test_ohne_inhaltspaket_oeffnet_sich_die_app(browser, tmp_path):
    import asyncio

    from mathainoa1.storage.content import ContentStore
    from mathainoa1.ui.web_content import WebContent

    async def leer(path):
        return 404, b""

    store = ContentStore(tmp_path / "book", tmp_path / "vocab")
    store.load_all()
    nav, shown = _web_nav()
    opened = []
    asyncio.run(WebContent(nav, store, lambda: opened.append(True),
                           fetch=leer).start())
    assert opened == [True]


def test_ohne_netz_und_ohne_code_bleibt_die_seite_zu(browser, tmp_path):
    import asyncio

    from mathainoa1.storage.content import ContentStore
    from mathainoa1.ui.web_content import WebContent

    async def kaputt(path):
        raise OSError("kein Netz")

    store = ContentStore(tmp_path / "book", tmp_path / "vocab")
    store.load_all()
    nav, shown = _web_nav()
    opened = []
    asyncio.run(WebContent(nav, store, lambda: opened.append(True),
                           fetch=kaputt).start())
    assert opened == []
    assert any("nicht erreichbar" in (t or "") for t in _texts(shown[-1]))
