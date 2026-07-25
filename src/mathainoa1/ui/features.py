"""Registry der erweiterten Funktionen (Power-User-Features).

Features sind Zusatzfunktionen, die in den Einstellungen unter
„Erweiterte Funktionen" einzeln eingeschaltet werden (Standard: aus).
Eingeschaltete Features erscheinen als zusätzliche Karten im Hauptmenü.
Der Schalter gilt stufenübergreifend (A1 und A2 gemeinsam).

Ein neues Feature braucht nur einen Eintrag in FEATURES:
- key: stabiler Schlüssel, wird in AppSettings.enabled_features gespeichert
- build(nav, store, progress) -> ft.Control: baut die Feature-Startansicht,
  gleiche Signatur wie die bestehenden Views (nav.page für Dialoge nutzbar)
- Eigene Daten legt ein Feature unter app_data_dir()/features/<key>/ ab.
- Bringt ein Feature eigene Chatbot-Prompts mit (z.B. für Wortlisten-Import),
  müssen deren Spaltenangaben zur aktiven Stufe passen (AppSettings.level:
  A1 nutzt stem2, A2 zusätzlich aorist_passive/participle).

Schwere Importe gehören in die build-Funktion (Lazy-Import), damit die
Registry selbst billig bleibt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import flet as ft

from mathainoa1.storage.settings import AppSettings


@dataclass(frozen=True)
class Feature:
    key: str  # stabiler Schlüssel in AppSettings.enabled_features
    title: str  # Kartentitel auf der Startseite
    subtitle: str
    icon: str  # ft.Icons.*
    build: Callable  # build(nav, store, progress) -> ft.Control


def _build_textanalyse(nav, store, progress) -> ft.Control:
    from mathainoa1.ui.views.textanalyse import overview_view
    return overview_view(nav, store, progress)


FEATURES: list[Feature] = [
    Feature(
        key="textanalyse",
        title="Textanalyse",
        subtitle="Griechische Texte: Übersetzung, Wortliste, Etymologie",
        icon=ft.Icons.ARTICLE_OUTLINED,
        build=_build_textanalyse,
    ),
]


def enabled_features(settings: AppSettings) -> list[Feature]:
    """Die laut Einstellungen aktivierten Features in Registry-Reihenfolge."""
    return [f for f in FEATURES if f.key in settings.enabled_features]
