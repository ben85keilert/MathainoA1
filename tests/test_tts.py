import asyncio
from types import SimpleNamespace

import pytest

from mathainoa1.storage import tts
from mathainoa1.storage.settings import TTS_GOOGLE, TTS_SYSTEM, AppSettings
from mathainoa1.storage.tts import SLOW_FACTOR, TtsCache, TtsFetchError, speakable
from mathainoa1.ui import audio


def test_speakable_alternatives_and_parens():
    # erste "/"-Alternative
    assert speakable("και / κι") == "και"
    assert speakable("τρεις / τρία") == "τρεις"
    # Klammern im Wort werden aufgefüllt
    assert speakable("αγαπ(ά)ω") == "αγαπάω"
    # freistehende Klammerzusätze entfallen
    assert speakable("η Ένωση (ΕΕ)") == "η Ένωση"
    assert speakable("η λαϊκή (αγορά)") == "η λαϊκή"
    # Normalfall bleibt unverändert
    assert speakable("ο δρόμος") == "ο δρόμος"
    assert speakable("  ο   δρόμος  ") == "ο δρόμος"
    assert speakable("") == ""


def test_speakable_article_variants():
    # Ein-Wort-Alternativen am Anfang: erste Variante + gemeinsamer Rest —
    # früher blieb nur "ο" übrig und das Audio war kaputt
    assert speakable("ο / η συνταξιούχος") == "ο συνταξιούχος"
    assert speakable("ο/η συνταξιούχος") == "ο συνταξιούχος"
    assert speakable("ο / η / το ίδιος") == "ο ίδιος"
    # Verb-Varianten ohne Rest: erste Form
    assert speakable("αγαπάω / αγαπώ") == "αγαπάω"
    # mehrwortige erste Alternative bleibt beim alten Verhalten
    assert speakable("τα λέμε / γεια σου") == "τα λέμε"


# --- Google-Weg: MP3-Cache -------------------------------------------------

def test_path_for_stable_and_normalized(tmp_path):
    cache = TtsCache(tmp_path)
    p1 = cache.path_for("ο δρόμος")
    assert p1 == cache.path_for("ο δρόμος")  # stabil
    assert p1 == cache.path_for("  ο  δρόμος ")  # Whitespace normalisiert
    assert p1 != cache.path_for("η γυναίκα")
    assert p1.suffix == ".mp3" and p1.parent == tmp_path
    assert not cache.has("ο δρόμος")
    p1.write_bytes(b"mp3")
    assert cache.has("ο δρόμος")


class FakeGTTS:
    """Ersatz für gtts.gTTS in Tests — schreibt Fake-MP3-Bytes."""

    calls: list[str] = []
    fail = False

    def __init__(self, text, lang="el"):
        self.text = text
        FakeGTTS.calls.append(text)

    def save(self, path):
        if FakeGTTS.fail:
            raise RuntimeError("kein Netz")
        with open(path, "wb") as f:
            f.write(b"ID3fake-" + self.text.encode())


@pytest.fixture
def fake_gtts(monkeypatch):
    FakeGTTS.calls = []
    FakeGTTS.fail = False
    monkeypatch.setattr(tts, "gTTS", FakeGTTS)
    return FakeGTTS


def test_fetch_writes_and_caches(tmp_path, fake_gtts):
    cache = TtsCache(tmp_path / "tts")
    p = cache.fetch("ο δρόμος")
    assert p.read_bytes().startswith(b"ID3fake-")
    assert cache.has("ο δρόμος")
    # zweiter Abruf trifft den Cache — kein weiterer gTTS-Aufruf
    cache.fetch("ο δρόμος")
    assert fake_gtts.calls == ["ο δρόμος"]


def test_fetch_error_leaves_no_leftovers(tmp_path, fake_gtts):
    fake_gtts.fail = True
    cache = TtsCache(tmp_path)
    with pytest.raises(TtsFetchError):
        cache.fetch("ο δρόμος")
    assert not cache.has("ο δρόμος")
    assert list(tmp_path.glob("*.tmp")) == []  # atomar: kein Rest


def test_fetch_without_gtts_package(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "gTTS", None)
    with pytest.raises(TtsFetchError):
        TtsCache(tmp_path).fetch("ο δρόμος")


# --- Engine-Weiche ---------------------------------------------------------

def test_app_settings_engine_roundtrip():
    s = AppSettings(tts_engine=TTS_GOOGLE)
    assert AppSettings.from_dict(s.to_dict()).tts_engine == TTS_GOOGLE
    # Standard ist die Systemstimme
    assert AppSettings().tts_engine == TTS_SYSTEM


class FakePage:
    """Minimale Page: führt run_task-Coroutinen sofort aus und sammelt
    angezeigte Dialoge (SnackBars)."""

    def __init__(self):
        self.services = []
        self.dialogs = []

    def run_task(self, f):
        asyncio.run(f())

    def show_dialog(self, d):
        self.dialogs.append(d)

    def update(self):
        pass


@pytest.fixture
def engine_setter(monkeypatch):
    """Setzt den Engine-Cache in ui.audio direkt (keine Settings-Datei)."""
    def set_engine(value):
        monkeypatch.setattr(audio, "_engine", value)
    yield set_engine
    monkeypatch.setattr(audio, "_engine", None)


def _record(calls, name):
    async def rec(page, text, slow, notify_errors):
        calls.append((name, text, slow, notify_errors))
    return rec


def test_play_text_routes_by_engine(monkeypatch, engine_setter):
    calls = []
    monkeypatch.setattr(audio, "_speak_system", _record(calls, "system"))
    monkeypatch.setattr(audio, "_speak_google", _record(calls, "google"))
    page = FakePage()

    engine_setter(TTS_SYSTEM)
    audio.play_text(page, "ο δρόμος", slow=True)
    engine_setter(TTS_GOOGLE)
    audio.play_text(page, "αγαπ(ά)ω")

    # speakable wird vor dem Sprechen angewandt
    assert calls == [("system", "ο δρόμος", True, True),
                     ("google", "αγαπάω", False, True)]


def test_play_text_empty_text_is_noop(monkeypatch, engine_setter):
    calls = []
    monkeypatch.setattr(audio, "_speak_system", _record(calls, "system"))
    engine_setter(TTS_SYSTEM)
    page = FakePage()
    audio.play_text(page, "(ΕΕ)")  # speakable("(ΕΕ)") == ""
    assert calls == []


def test_system_engine_without_extension_shows_hint(monkeypatch, engine_setter):
    # Erweiterung nicht installiert (Dev-Client): Hinweis statt Absturz
    monkeypatch.setattr(audio, "SystemTts", None)
    engine_setter(TTS_SYSTEM)
    page = FakePage()
    audio.play_text(page, "ο δρόμος")
    assert len(page.dialogs) == 1
    # lautlos bei Auto-Play
    audio.play_text(page, "ο δρόμος", notify_errors=False)
    assert len(page.dialogs) == 1


class FakeSystemTts:
    """Ersatz für flet_system_tts.SystemTts."""

    def __init__(self):
        self.spoken: list[tuple[str, float]] = []
        self.fail = False

    async def speak(self, text, rate=1.0):
        if self.fail:
            raise Exception("language_not_available: el-GR")
        self.spoken.append((text, rate))


def test_system_engine_speaks_via_service(monkeypatch, engine_setter):
    svc = FakeSystemTts()
    monkeypatch.setattr(audio, "SystemTts", FakeSystemTts)
    monkeypatch.setattr(audio, "_system_service", lambda page: svc)
    engine_setter(TTS_SYSTEM)
    page = FakePage()
    audio.play_text(page, "ο δρόμος")
    audio.play_text(page, "ο δρόμος", slow=True)
    assert svc.spoken == [("ο δρόμος", 1.0), ("ο δρόμος", SLOW_FACTOR)]
    assert page.dialogs == []


def test_system_engine_speak_error_shows_hint(monkeypatch, engine_setter):
    svc = FakeSystemTts()
    svc.fail = True
    monkeypatch.setattr(audio, "SystemTts", FakeSystemTts)
    monkeypatch.setattr(audio, "_system_service", lambda page: svc)
    engine_setter(TTS_SYSTEM)
    page = FakePage()
    audio.play_text(page, "ο δρόμος")
    assert len(page.dialogs) == 1


def test_google_engine_uses_cache(monkeypatch, engine_setter, tmp_path,
                                  fake_gtts):
    # flet_audio durch Recorder ersetzen — _install_autoplay soll das
    # Audio-Control mit file://-URI und Rate einhängen
    installed = []
    monkeypatch.setattr(audio, "_install_autoplay",
                        lambda page, uri, rate: installed.append((uri, rate)))
    monkeypatch.setattr(audio, "fa", object())  # "installiert"
    monkeypatch.setattr(audio, "_cache", TtsCache(tmp_path / "tts"))
    engine_setter(TTS_GOOGLE)
    page = FakePage()
    audio.play_text(page, "ο δρόμος", slow=True)
    assert fake_gtts.calls == ["ο δρόμος"]
    assert len(installed) == 1
    uri, rate = installed[0]
    assert uri.startswith("file://") and uri.endswith(".mp3")
    assert rate == SLOW_FACTOR


def test_google_engine_offline_shows_hint(monkeypatch, engine_setter,
                                          tmp_path, fake_gtts):
    fake_gtts.fail = True
    monkeypatch.setattr(audio, "fa", object())
    monkeypatch.setattr(audio, "_cache", TtsCache(tmp_path / "tts"))
    engine_setter(TTS_GOOGLE)
    page = FakePage()
    audio.play_text(page, "ο δρόμος")
    assert len(page.dialogs) == 1
