import pytest

from mathainoa1.storage import tts
from mathainoa1.storage.tts import TtsCache, TtsFetchError, speakable


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
