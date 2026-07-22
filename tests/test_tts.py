import pytest

from mathainoa1.storage import tts
from mathainoa1.storage.tts import (
    NO_VOICE_HINT,
    SLOW_FACTOR,
    SystemTts,
    TtsError,
    find_greek_voice,
    speakable,
)


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


class FakeVoice:
    def __init__(self, id, name="", languages=None):
        self.id = id
        self.name = name
        self.languages = languages or []


def test_find_greek_voice_by_languages():
    voices = [
        FakeVoice("v1", "Anna", ["de_DE"]),
        # eSpeak-Stil: Bytes mit Prioritäts-Präfix
        FakeVoice("v2", "greek", [b"\x05el"]),
    ]
    assert find_greek_voice(voices) == "v2"
    # macOS-Stil: Sprachcode als String
    assert find_greek_voice([FakeVoice("m1", "Melina", ["el_GR"])]) == "m1"


def test_find_greek_voice_by_name_or_id():
    # SAPI nennt die Sprache nur im Anzeigenamen/der Registry-ID
    sapi = FakeVoice(
        r"HKEY...\TTS_MS_EL-GR_STEFANOS_11.0",
        "Microsoft Stefanos - Greek (Greece)")
    assert find_greek_voice([FakeVoice("v1", "Microsoft Hedda - German"),
                             sapi]) == sapi.id
    # eSpeak-Kurzform: ID ist schlicht "el"
    assert find_greek_voice([FakeVoice("de"), FakeVoice("el")]) == "el"


def test_find_greek_voice_none_and_no_false_positives():
    # "Elsa"/"Elena" enthalten "el", sind aber keine griechischen Stimmen
    voices = [FakeVoice("v1", "Microsoft Elsa - Italian (Italy)"),
              FakeVoice("v2", "Elena", ["es_ES"])]
    assert find_greek_voice(voices) is None
    assert find_greek_voice([]) is None


class FakeEngine:
    """Ersatz für die pyttsx3-Engine in Tests."""

    def __init__(self, voices, rate=200, fail_on_say=False):
        self.voices = voices
        self.props = {"rate": rate}
        self.said: list[tuple[str, int]] = []
        self.fail_on_say = fail_on_say
        self.stopped = 0

    def getProperty(self, name):
        return self.voices if name == "voices" else self.props.get(name)

    def setProperty(self, name, value):
        self.props[name] = value

    def say(self, text):
        if self.fail_on_say:
            raise RuntimeError("Treiber kaputt")
        self.said.append((text, self.props["rate"]))

    def runAndWait(self):
        pass

    def stop(self):
        self.stopped += 1


class FakePyttsx3:
    """Ersatz für das pyttsx3-Modul: init() liefert vorbereitete Engines."""

    def __init__(self, *engines):
        self.engines = list(engines)
        self.inits = 0

    def init(self):
        self.inits += 1
        return self.engines.pop(0)


GREEK = FakeVoice("el", "greek", [b"\x05el"])


def test_speak_selects_voice_and_rates(monkeypatch):
    engine = FakeEngine([FakeVoice("de", "german"), GREEK], rate=200)
    fake = FakePyttsx3(engine)
    monkeypatch.setattr(tts, "pyttsx3", fake)
    t = SystemTts()
    t.speak("ο δρόμος")
    t.speak("η γυναίκα", slow=True)
    assert engine.props["voice"] == "el"
    assert engine.said == [("ο δρόμος", 200),
                           ("η γυναίκα", int(200 * SLOW_FACTOR))]
    # Engine wird wiederverwendet, nicht pro Aufruf neu erzeugt
    assert fake.inits == 1


def test_speak_without_greek_voice(monkeypatch):
    monkeypatch.setattr(
        tts, "pyttsx3", FakePyttsx3(FakeEngine([FakeVoice("de", "german")])))
    with pytest.raises(TtsError, match="griechische Stimme"):
        SystemTts().speak("ο δρόμος")
    assert "Ελληνικά" in NO_VOICE_HINT


def test_speak_without_pyttsx3(monkeypatch):
    monkeypatch.setattr(tts, "pyttsx3", None)
    with pytest.raises(TtsError):
        SystemTts().speak("ο δρόμος")


def test_broken_engine_reinitializes(monkeypatch):
    broken = FakeEngine([GREEK], fail_on_say=True)
    fresh = FakeEngine([GREEK])
    fake = FakePyttsx3(broken, fresh)
    monkeypatch.setattr(tts, "pyttsx3", fake)
    t = SystemTts()
    with pytest.raises(TtsError):
        t.speak("ο δρόμος")
    # kaputte Engine wurde verworfen — nächster Aufruf initialisiert neu
    t.speak("ο δρόμος")
    assert fake.inits == 2
    assert fresh.said == [("ο δρόμος", 200)]


def test_stop_without_engine_is_noop(monkeypatch):
    monkeypatch.setattr(tts, "pyttsx3", None)
    SystemTts().stop()  # darf nicht werfen
