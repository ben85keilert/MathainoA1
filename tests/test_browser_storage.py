"""Tests für den Speicher im Browser (storage/browser_storage.py) — mit
einem nachgebauten Zugang; der echte (PyodideAccess) läuft nur im Browser."""

import asyncio

import pytest

from mathainoa1.storage import browser_storage as bs


class FakeAccess:
    """Merkt sich, was der Speicher vom Browser verlangt."""

    def __init__(self, free=True, fail=None):
        self.free = free
        self.fail = fail  # Name der Methode, die scheitern soll
        self.calls: list = []

    def mount(self, path):
        self.calls.append(("mount", path))
        if self.fail == "mount":
            raise OSError("kein IDBFS")

    async def sync(self, load):
        self.calls.append(("sync", load))
        if self.fail == "sync":
            raise OSError("Speicher voll")

    async def lock(self, name):
        self.calls.append(("lock", name))
        return self.free

    async def remove(self, path):
        self.calls.append(("remove", path))
        if self.fail == "remove":
            raise OSError("blockiert")


def started(tmp_path, **kw):
    storage = bs.BrowserStorage(tmp_path, FakeAccess(**kw))
    asyncio.run(storage.start())
    return storage


def test_start_haengt_ein_sperrt_und_holt(tmp_path):
    s = started(tmp_path)
    assert s.state == bs.ON and s.active
    assert s.access.calls == [("mount", str(tmp_path)), ("lock", bs.LOCK),
                              ("sync", True)]
    assert s.existing is False and not s.changed()


def test_vorhandenes_wird_erkannt(tmp_path):
    (tmp_path / "progress.db").write_bytes(b"alt")
    assert started(tmp_path).existing is True


def test_speichert_nur_bei_aenderung(tmp_path):
    s = started(tmp_path)
    assert not s.changed()
    (tmp_path / "vocab").mkdir()
    (tmp_path / "vocab" / "a.json").write_text("{}", encoding="utf-8")
    assert s.changed()
    assert asyncio.run(s.save()) is True
    assert s.access.calls[-1] == ("sync", False)
    assert not s.changed()


def test_zweiter_tab_schreibt_nicht(tmp_path):
    s = started(tmp_path, free=False)
    assert s.state == bs.OTHER_TAB and not s.active
    (tmp_path / "x").write_text("x", encoding="utf-8")
    assert asyncio.run(s.save()) is False
    assert ("sync", False) not in s.access.calls


def test_browser_laesst_es_nicht_zu(tmp_path):
    s = started(tmp_path, fail="mount")
    assert s.state == bs.FAILED and "kein IDBFS" in s.error
    assert asyncio.run(s.save()) is False


def test_fehler_beim_schreiben_schaltet_ab(tmp_path):
    s = started(tmp_path)
    s.access.fail = "sync"
    (tmp_path / "x").write_text("x", encoding="utf-8")
    assert asyncio.run(s.save()) is False
    assert s.state == bs.FAILED


def test_loeschen_beendet_das_schreiben(tmp_path):
    s = started(tmp_path)
    asyncio.run(s.erase())
    assert s.state == bs.ERASED
    assert s.access.calls[-1] == ("remove", str(tmp_path))
    (tmp_path / "x").write_text("x", encoding="utf-8")
    assert asyncio.run(s.save()) is False


def test_gescheitertes_loeschen_laesst_den_zustand(tmp_path):
    s = started(tmp_path)
    s.access.fail = "remove"
    with pytest.raises(OSError):
        asyncio.run(s.erase())
    assert s.state == bs.ON


def test_takt_schreibt_nur_wenn_ruhig(tmp_path, monkeypatch):
    """Der Takt wartet, solange eine Transaktion offen ist."""
    monkeypatch.setattr(bs, "TICK_S", 0)
    s = started(tmp_path)
    (tmp_path / "x").write_text("x", encoding="utf-8")
    quiet = {"value": False}

    async def run():
        task = asyncio.ensure_future(s.tick(lambda: quiet["value"]))
        for _ in range(5):
            await asyncio.sleep(0)
        assert ("sync", False) not in s.access.calls
        quiet["value"] = True
        for _ in range(5):
            await asyncio.sleep(0)
        task.cancel()

    asyncio.run(run())
    assert ("sync", False) in s.access.calls


def test_jeder_zustand_hat_einen_text():
    for state in (bs.OFF, bs.ON, bs.OTHER_TAB, bs.ERASED, bs.FAILED):
        assert bs.TEXTS[state]
