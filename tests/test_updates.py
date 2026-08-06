"""Tests für den Update-Check (storage/updates.py)."""

import json
from datetime import date

import pytest

from mathainoa1 import __version__
from mathainoa1.storage import updates


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    return tmp_path


def test_parse_version():
    assert updates.parse_version("v0.9.1") == (0, 9, 1)
    assert updates.parse_version("0.10.0") == (0, 10, 0)
    assert updates.parse_version("1.2.3") > updates.parse_version("1.2.2")
    # zweistellige Teile: numerisch, nicht lexikografisch
    assert updates.parse_version("0.10.0") > updates.parse_version("0.9.9")
    assert updates.parse_version("") == (0,)
    assert updates.parse_version("Kaputt") == (0,)


def test_auto_check_meldet_neuere_version(env, monkeypatch):
    monkeypatch.setattr(updates, "fetch_latest", lambda: updates.UpdateInfo(
        version="99.0.0", notes="Neues", apk_url="https://x/app.apk"))
    info = updates.auto_check()
    assert info is not None and info.version == "99.0.0"


def test_auto_check_still_bei_aktueller_version(env, monkeypatch):
    monkeypatch.setattr(updates, "fetch_latest",
                        lambda: updates.UpdateInfo(version=__version__))
    assert updates.auto_check() is None


def test_auto_check_hoechstens_einmal_pro_tag(env, monkeypatch):
    calls = []

    def fake_fetch():
        calls.append(1)
        return updates.UpdateInfo(version="99.0.0",
                                  apk_url="https://x/app.apk")

    monkeypatch.setattr(updates, "fetch_latest", fake_fetch)
    assert updates.auto_check() is not None
    # zweiter Start am selben Tag: kein weiterer API-Aufruf
    assert updates.auto_check() is None
    assert len(calls) == 1
    state = json.loads((env / "update_check.json").read_text("utf-8"))
    assert state["last_check"] == date.today().isoformat()


def test_auto_check_still_bei_netzfehler(env, monkeypatch):
    def fail():
        raise OSError("kein Netz")

    monkeypatch.setattr(updates, "fetch_latest", fail)
    assert updates.auto_check() is None


def test_downgrade_notice(env):
    # Erster Start: Version wird gemerkt, kein Hinweis
    assert updates.downgrade_notice() is None
    state = json.loads((env / "update_check.json").read_text("utf-8"))
    assert state["max_version_run"] == __version__
    # Daten stammen aus einer neueren Version -> Hinweis bei jedem Start
    state["max_version_run"] = "99.0.0"
    (env / "update_check.json").write_text(
        json.dumps(state), encoding="utf-8")
    notice = updates.downgrade_notice()
    assert notice is not None and "99.0.0" in notice
    assert updates.downgrade_notice() is not None  # bleibt bestehen


def test_auto_check_ueberspringt_release_ohne_apk(env, monkeypatch):
    """Ein Release ohne APK ist noch nicht fertig (Build läuft oder ist
    gescheitert) — es zu melden führte nur zu einer Seite ohne Download."""
    monkeypatch.setattr(updates, "fetch_latest", lambda: updates.UpdateInfo(
        version="99.0.0", notes="Neues", apk_url=""))
    assert updates.auto_check() is None


def test_is_installable_update():
    neu_mit_apk = updates.UpdateInfo(version="99.0.0",
                                     apk_url="https://x/app.apk")
    neu_ohne_apk = updates.UpdateInfo(version="99.0.0")
    alt_mit_apk = updates.UpdateInfo(version="0.0.1",
                                     apk_url="https://x/app.apk")
    assert updates.is_installable_update(neu_mit_apk) is True
    assert updates.is_installable_update(neu_ohne_apk) is False
    assert updates.is_installable_update(alt_mit_apk) is False
    assert updates.is_installable_update(
        updates.UpdateInfo(version=__version__,
                           apk_url="https://x/app.apk")) is False
