"""Wort-Audio: Ablage und ZIP-Import der pro Karte erzeugten Dateien.

Jede Karte kann eine Audiodatei haben, benannt nach ihrer ID
(z.B. "3f2a9c81d0b4.mp3"). Die Dateien werden extern erzeugt (Chatbot/TTS,
siehe export_tts_text) und als ZIP importiert; die Zuordnung läuft allein
über die global eindeutige Karten-ID.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

AUDIO_EXTS = (".mp3", ".m4a", ".ogg", ".wav")


@dataclass
class AudioImportReport:
    """Ergebnis eines ZIP-Imports für den Report-Dialog."""

    imported: list[str] = field(default_factory=list)   # Karten-IDs
    unmatched: list[str] = field(default_factory=list)  # Dateien ohne Karte
    skipped: list[str] = field(default_factory=list)    # keine Audio-Endung


class AudioStore:
    """Verwaltet die Audiodateien flach unter einem Verzeichnis.

    Karten-IDs sind global eindeutig, daher braucht es keine Unterordner —
    das funktioniert für Buchlisten, eigene Listen und Auswahllisten gleich.
    """

    def __init__(self, audio_dir: Path):
        self.audio_dir = audio_dir

    def path_for(self, card_id: str) -> Path | None:
        for ext in AUDIO_EXTS:
            p = self.audio_dir / f"{card_id}{ext}"
            if p.exists():
                return p
        return None

    def has_audio(self, card_id: str) -> bool:
        return self.path_for(card_id) is not None

    def existing_ids(self) -> set[str]:
        """IDs aller vorhandenen Audiodateien — ein Verzeichnis-Scan statt
        stat() pro Karte, für lange Listenansichten."""
        if not self.audio_dir.exists():
            return set()
        return {p.stem for p in self.audio_dir.iterdir()
                if p.suffix.lower() in AUDIO_EXTS}

    def missing_ids(self, ids: Iterable[str]) -> list[str]:
        have = self.existing_ids()
        return [i for i in ids if i not in have]

    def import_zip(self, data: bytes, known_ids: set[str]) -> AudioImportReport:
        """Entpackt ein ZIP mit "<karten-id>.<ext>"-Dateien.

        Ordner im ZIP werden ignoriert (Zuordnung über den Dateinamen),
        ebenso versteckte Dateien und Nicht-Audio. Wirft zipfile.BadZipFile
        bei ungültigen Daten.
        """
        report = AudioImportReport()
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                stem, ext = Path(name).stem, Path(name).suffix.lower()
                if name.startswith(".") or ext not in AUDIO_EXTS:
                    report.skipped.append(name)
                    continue
                if stem not in known_ids:
                    report.unmatched.append(name)
                    continue
                # Re-Import mit anderer Endung: alte Datei ersetzen, sonst
                # gäbe es id.mp3 und id.ogg nebeneinander
                old = self.path_for(stem)
                target = self.audio_dir / f"{stem}{ext}"
                if old is not None and old != target:
                    old.unlink()
                target.write_bytes(zf.read(info))
                report.imported.append(stem)
        return report
