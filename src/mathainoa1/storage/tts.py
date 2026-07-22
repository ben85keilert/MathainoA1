"""Sprachausgabe über die Systemstimme des Geräts (pyttsx3).

Kein Clouddienst, kein Internet: Der Text wird von der auf dem Gerät
installierten Sprachausgabe gesprochen (Windows: SAPI, macOS:
NSSpeechSynthesizer, Linux: eSpeak/speech-dispatcher). Es verlassen
keine Daten das Gerät. Voraussetzung ist eine installierte griechische
Stimme — sie wird beim ersten Sprechen automatisch gesucht.
"""

from __future__ import annotations

import re
import threading
import unicodedata

try:
    import pyttsx3
except ImportError:  # Paket fehlt (z.B. Test-Umgebung oder Android)
    pyttsx3 = None

# Langsam-Faktor zum Nachsprechen, relativ zur Normalgeschwindigkeit
SLOW_FACTOR = 0.65

NO_VOICE_HINT = (
    "Keine griechische Stimme installiert. Windows: Einstellungen → "
    "Zeit und Sprache → Sprache → „Ελληνικά“ mit Text-in-Sprache "
    "hinzufügen."
)


class TtsError(Exception):
    """Sprechen fehlgeschlagen — Engine fehlt oder keine griechische Stimme."""


def speakable(text: str) -> str:
    """Sprechbare Form eines Kartentexts.

    - Ein-Wort-Alternativen am Anfang: erste Variante plus Rest
      ("ο / η συνταξιούχος" -> "ο συνταξιούχος", "και / κι" -> "και")
    - sonst erste "/"-Alternative ("τα λέμε / γεια" -> "τα λέμε")
    - Klammern im Wort auffüllen ("αγαπ(ά)ω" -> "αγαπάω")
    - freistehende Klammerzusätze streichen ("η Ένωση (ΕΕ)" -> "η Ένωση")
    """
    t = text.strip()
    # "ο / η συνταξιούχος": die "/"-Gruppe besteht aus einzelnen Wörtern,
    # der gemeinsame Rest gehört zu jeder Variante — erste Variante nehmen,
    # Rest behalten (der alte split("/") ließe nur "ο" übrig)
    m = re.match(r"^(\S+)(?:\s*/\s*\S+)+(\s.*)?$", t)
    if m:
        t = m.group(1) + (m.group(2) or "")
    else:
        t = t.split("/")[0]
    t = re.sub(r"(?<=\S)\(([^)]*)\)", r"\1", t)
    t = re.sub(r"\s*\([^)]*\)", "", t)
    return " ".join(t.split())


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", " ".join(text.split()))


def _voice_languages(voice) -> list[str]:
    """Sprachcodes einer Stimme, treiberunabhängig normalisiert.

    eSpeak liefert Bytes mit Prioritäts-Präfix (b"\\x05el"), SAPI oft gar
    nichts, macOS Strings wie "el_GR" — alles auf Kleinbuchstaben ohne
    Steuerzeichen bringen, damit startswith("el") überall greift.
    """
    out = []
    for lang in getattr(voice, "languages", None) or []:
        if isinstance(lang, (bytes, bytearray)):
            lang = lang.decode("utf-8", "ignore")
        out.append(re.sub(r"[^a-z0-9_-]", "", str(lang).lower()))
    return out


def find_greek_voice(voices) -> str | None:
    """ID der ersten griechischen Stimme — oder None, wenn keine da ist."""
    for v in voices:
        if any(lang.startswith("el") or "greek" in lang
               for lang in _voice_languages(v)):
            return v.id
    for v in voices:
        # SAPI nennt die Sprache nur in Name/ID ("Microsoft Stefanos -
        # Greek (Greece)", "...TTS_MS_EL-GR_..."), eSpeak teils nur "el"
        text = f"{getattr(v, 'name', '')} {v.id}".lower()
        if ("greek" in text or "ελλην" in text
                or re.search(r"(^|[^a-z])el([-_]gr)?([^a-z]|$)", text)):
            return v.id
    return None


class SystemTts:
    """Kapselt die pyttsx3-Engine: Stimmwahl, Tempo, serialisiertes Sprechen.

    speak() blockiert bis zum Ende der Wiedergabe — aus der UI immer über
    asyncio.to_thread aufrufen. Ein Lock verhindert überlappende Aufrufe;
    stop() bricht eine laufende Wiedergabe von außen ab.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._engine = None
        self._rate: int = 0  # Normaltempo der Engine (Wörter/Minute)

    def _ensure_engine(self):
        if pyttsx3 is None:
            raise TtsError("Sprachausgabe auf diesem Gerät nicht verfügbar.")
        if self._engine is None:
            try:
                engine = pyttsx3.init()
                voice = find_greek_voice(engine.getProperty("voices") or [])
            except Exception as exc:
                raise TtsError(
                    f"Sprachausgabe nicht verfügbar: {exc}") from exc
            if voice is None:
                raise TtsError(NO_VOICE_HINT)
            engine.setProperty("voice", voice)
            self._rate = int(engine.getProperty("rate") or 200)
            self._engine = engine
        return self._engine

    def speak(self, text: str, slow: bool = False) -> None:
        """Spricht blockierend; wirft TtsError bei jedem Fehler."""
        with self._lock:
            engine = self._ensure_engine()
            try:
                rate = self._rate * (SLOW_FACTOR if slow else 1.0)
                engine.setProperty("rate", int(rate))
                engine.say(_normalize(text))
                engine.runAndWait()
            except Exception as exc:
                # kaputte Engine verwerfen — der nächste Aufruf
                # initialisiert frisch statt dauerhaft stumm zu bleiben
                self._engine = None
                raise TtsError(str(exc)) from exc

    def stop(self) -> None:
        """Bricht die laufende Wiedergabe ab (neuer Text gewinnt)."""
        engine = self._engine
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass
