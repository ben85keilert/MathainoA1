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
