"""Persistenz der Trainings-Defaults und App-Datenpfade."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from mathainoa1.logic.conjugation import ConjugationSettings
from mathainoa1.logic.declension import DeclensionSettings
from mathainoa1.logic.session import TrainingSettings

# Sprachausgabe-Wege (AppSettings.tts_engine)
TTS_SYSTEM = "system"  # Systemstimme des Geräts (flet-system-tts, offline)
TTS_GOOGLE = "google"  # gTTS-MP3 von Google-Servern, lokal gecacht


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
    # Box 5 nur über das Beugungstraining (Nomen/Adjektiv/Verb, Vorgabe
    # Deutsch) — alle übrigen Obergrenzen rücken eine Box nach unten
    # (siehe storage/progress.max_box_for_mode). Standard aus.
    top_box_needs_inflection: bool = False
    # Wort-Audio automatisch abspielen, sobald im Training die
    # griechische Seite sichtbar wird (Umschalter in den Trainings-Views)
    autoplay_audio: bool = False
    # Sprachausgabe-Weg: TTS_SYSTEM = Systemstimme des Geräts (offline,
    # keine Übertragung), TTS_GOOGLE = gTTS online holen + lokal cachen
    # (für Geräte ohne griechische Systemstimme, z.B. Linux)
    tts_engine: str = TTS_SYSTEM
    # Prüfen beim Schreiben: False = "Prüfen"-Button mittig unter dem
    # Antwortfeld (Standard), True = rundes Häkchen rechts daneben
    check_beside_field: bool = False
    # Sichtbare Stufe: "A1" | "A2". A2 zeigt auch A1-Listen; Listen ohne
    # Stufe (book=None, alle eigenen) sind immer sichtbar.
    level: str = "A1"
    # Eingeschaltete erweiterte Funktionen (Schlüssel aus ui/features.FEATURES).
    # Unbekannte Schlüssel (z.B. entfernte Features) werden ignoriert.
    enabled_features: list[str] = field(default_factory=list)
    # Fehlerrunde: wohin wandert ein Wort, das in der ersten Runde falsch
    # (→ Box 1) und in der Fehlerrunde richtig beantwortet wurde?
    # "none" = keine Verbesserung (bleibt Box 1), "box2" = immer Box 2,
    # "original" = zurück in die ursprüngliche Box, "step_down" = eine Box
    # unter der ursprünglichen, mindestens Box 2 (Standard)
    repeat_round_box_policy: str = "step_down"
    # Doppeltipp-Fenster (Sekunden) für "langsam abspielen" auf dem
    # Lautsprecher der Wortlisten (zusätzlich zum langen Drücken)
    slow_double_tap_seconds: float = 0.5
    # Reihenfolge der Hauptmenü-Kacheln (Keys aus ui/app.CORE_TILES bzw.
    # Feature-Keys); leer = Standardreihenfolge. Unbekannte Keys werden
    # ignoriert, fehlende hängen sich hinten an.
    menu_order: list[str] = field(default_factory=list)
    # Adjektivtraining: "whitelist" = nur explizit festgelegte
    # Adjektiv↔Nomen-Verbindungen werden abgefragt (Standard);
    # "blacklist" = alle Kombinationen außer festgelegten Ausnahmen
    adjective_combos_mode: str = "whitelist"
    # App-weiter Zoomfaktor (1.0 = 100 %); geklemmt wird beim Anwenden
    # in ui/scale.py, hier bleibt der Rohwert
    ui_scale: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AppSettings":
        known = {f for f in cls.__dataclass_fields__}
        data = {k: v for k, v in d.items() if k in known}
        # Migration der alten 3-stufigen Einstellung repeat_round_promotion
        if "repeat_round_box_policy" not in data and "repeat_round_promotion" in d:
            data["repeat_round_box_policy"] = {
                "off": "none", "on": "original", "auto": "step_down",
            }.get(d["repeat_round_promotion"], "step_down")
        return cls(**data)


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
    """MP3-Cache des Google-Wegs, nach Text-Hash benannt (storage/tts.py)."""
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


def load_adjective_settings() -> DeclensionSettings:
    """Defaults des Adjektivtrainings (eigene Datei, gleiches Schema wie
    die Deklinations-Einstellungen)."""
    path = app_data_dir() / "adjective_settings.json"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return DeclensionSettings.from_dict(json.load(f))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return DeclensionSettings()


def save_adjective_settings(settings: DeclensionSettings) -> None:
    path = app_data_dir() / "adjective_settings.json"
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
