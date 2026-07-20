"""Sprachausgabe per gTTS (Google-Translate-TTS) mit lokalem Cache.

Die App erzeugt Audio on-the-fly: Beim ersten Abspielen eines Texts wird
die MP3 über gTTS geholt (Internet nötig, ~1 s) und lokal gecacht —
danach spielt sie sofort und offline. Cache-Schlüssel ist ein Hash des
gesprochenen Texts: Textänderungen erzeugen automatisch neues Audio,
veraltetes Audio kann es nicht geben.
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from pathlib import Path

try:
    from gtts import gTTS
except ImportError:  # Paket fehlt (z.B. Test-Umgebung)
    gTTS = None

LANG = "el"


class TtsFetchError(Exception):
    """Abruf fehlgeschlagen — meist kein Internet oder Google drosselt."""


def speakable(text: str) -> str:
    """Sprechbare Form eines Kartentexts.

    - erste "/"-Alternative ("και / κι" -> "και")
    - Klammern im Wort auffüllen ("αγαπ(ά)ω" -> "αγαπάω")
    - freistehende Klammerzusätze streichen ("η Ένωση (ΕΕ)" -> "η Ένωση")
    """
    t = text.split("/")[0]
    t = re.sub(r"(?<=\S)\(([^)]*)\)", r"\1", t)
    t = re.sub(r"\s*\([^)]*\)", "", t)
    return " ".join(t.split())


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", " ".join(text.split()))


class TtsCache:
    """MP3-Cache, Dateiname = SHA1 des normalisierten Texts."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    def path_for(self, text: str) -> Path:
        key = hashlib.sha1(_normalize(text).encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.mp3"

    def has(self, text: str) -> bool:
        return self.path_for(text).exists()

    def fetch(self, text: str) -> Path:
        """Holt die MP3 (blockierend!) und legt sie atomar in den Cache.

        Gibt den Pfad zurück; wirft TtsFetchError bei jedem Fehler.
        Aus der UI immer über asyncio.to_thread aufrufen.
        """
        target = self.path_for(text)
        if target.exists():
            return target
        if gTTS is None:
            raise TtsFetchError("gTTS ist nicht installiert.")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        try:
            gTTS(_normalize(text), lang=LANG).save(str(tmp))
            os.replace(tmp, target)
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            raise TtsFetchError(str(exc)) from exc
        return target
