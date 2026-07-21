"""Persistenz der Notizen: Schreibfeld-Entwurf und gespeicherte Einträge."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from mathainoa1.storage.settings import app_data_dir


@dataclass
class Note:
    """Eine gespeicherte Notiz mit Pflicht-Überschrift."""

    title: str
    text: str
    created: str = ""  # ISO-8601, z.B. "2026-07-21T10:15:00"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Note":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class NotesData:
    """Entwurf im Schreibfeld plus Liste der Notizen (neueste zuerst)."""

    draft: str = ""
    notes: list[Note] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"draft": self.draft, "notes": [n.to_dict() for n in self.notes]}

    @classmethod
    def from_dict(cls, d: dict) -> "NotesData":
        return cls(
            draft=str(d.get("draft", "")),
            notes=[Note.from_dict(n) for n in d.get("notes", [])
                   if isinstance(n, dict)],
        )


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _notes_path() -> Path:
    return app_data_dir() / "notes.json"


def load_notes() -> NotesData:
    path = _notes_path()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return NotesData.from_dict(json.load(f))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return NotesData()


def save_notes(data: NotesData) -> None:
    # Atomar schreiben (tmp + replace): der Entwurf wird bei jedem
    # Tastendruck gesichert, ein App-Kill mitten im Schreiben darf die
    # Datei mit allen Notizen nicht zerstören
    path = _notes_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data.to_dict(), f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
