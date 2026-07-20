"""Persistenz der Trainings-Defaults und App-Datenpfade."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from mathainoa1.logic.conjugation import ConjugationSettings
from mathainoa1.logic.declension import DeclensionSettings
from mathainoa1.logic.session import TrainingSettings


@dataclass
class AppSettings:
    """App-weite Einstellungen (Zahnrad-Menü), getrennt von den
    Trainings-Defaults."""

    theme: str = "system"  # "light" | "dark" | "system"
    seed: str = "blue"  # Akzentfarbe, Schlüssel aus ui/views/settings.SEED_COLORS
    # Strenger Fehler (Akzent/Groß-Klein, wenn Toleranz aus) setzt die Box
    # auf 1 statt sie unverändert zu lassen
    accent_resets_box: bool = False
    case_resets_box: bool = False
    # Beschränkungen durch die Abfragemodi (Standard an):
    # Box 4+5 nur über D->G; Box 5 nur über getipptes D->G
    high_boxes_need_production: bool = True
    top_box_needs_typing: bool = True
    # Wort-Audio automatisch abspielen, sobald im Training die
    # griechische Seite sichtbar wird (Umschalter in den Trainings-Views)
    autoplay_audio: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AppSettings":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def app_data_dir() -> Path:
    """Schreibbares App-Datenverzeichnis (Fortschritt, eigene Listen).

    In der gepackten App setzt Flet FLET_APP_STORAGE_DATA. Ohne das Env
    (Desktop) das übliche Nutzerverzeichnis — und falls auch das nicht
    beschreibbar ist, lieber ein Temp-Verzeichnis als ein Absturz.
    """
    env = os.environ.get("FLET_APP_STORAGE_DATA")
    if env:
        return Path(env)
    local = Path.home() / ".local" / "share" / "mathainoa1"
    try:
        local.mkdir(parents=True, exist_ok=True)
        return local
    except OSError:
        return Path(tempfile.gettempdir()) / "mathainoa1"


def user_vocab_dir() -> Path:
    return app_data_dir() / "vocab"


def tts_cache_dir() -> Path:
    """MP3-Cache der Sprachausgabe, nach Text-Hash benannt (storage/tts.py)."""
    return app_data_dir() / "tts"


def book_vocab_dir() -> Path:
    """Mitgelieferte Buchlisten: Assets der gepackten App oder Repo-Ordner."""
    assets = os.environ.get("FLET_ASSETS_DIR")
    if assets and (Path(assets) / "vocab").exists():
        return Path(assets) / "vocab"
    return Path(__file__).resolve().parents[3] / "data" / "vocab"


def load_default_settings() -> TrainingSettings:
    path = app_data_dir() / "training_settings.json"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return TrainingSettings.from_dict(json.load(f))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return TrainingSettings()


def save_default_settings(settings: TrainingSettings) -> None:
    path = app_data_dir() / "training_settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)


def load_declension_settings() -> DeclensionSettings:
    path = app_data_dir() / "declension_settings.json"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return DeclensionSettings.from_dict(json.load(f))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return DeclensionSettings()


def save_declension_settings(settings: DeclensionSettings) -> None:
    path = app_data_dir() / "declension_settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)


def load_conjugation_settings() -> ConjugationSettings:
    path = app_data_dir() / "conjugation_settings.json"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return ConjugationSettings.from_dict(json.load(f))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return ConjugationSettings()


def save_conjugation_settings(settings: ConjugationSettings) -> None:
    path = app_data_dir() / "conjugation_settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)


def load_app_settings() -> AppSettings:
    path = app_data_dir() / "app_settings.json"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return AppSettings.from_dict(json.load(f))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return AppSettings()


def save_app_settings(settings: AppSettings) -> None:
    path = app_data_dir() / "app_settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)
