"""App-weiter Zoomfaktor für Schriftgrößen (Einstellung „Zoom").

Flet kennt keinen echten Zoom (Transform-Scale ist reine Malerei ohne
Layout-Wirkung), deshalb skaliert die App ihre Schriftgrößen selbst:
alle size=/icon_size=-Angaben der UI laufen durch sz(). Der Faktor
kommt aus AppSettings.ui_scale und wird von apply_app_theme() über
set_ui_scale() gesetzt — geklemmt wird nur hier, die Einstellung
selbst bleibt roh gespeichert. Ohne set_ui_scale() gilt 1.0 (Tests,
Headless).

Bewusst ohne Imports aus ui/ oder storage/ — jedes UI-Modul importiert
sz(), Importzyklen darf es hier nicht geben.
"""

from __future__ import annotations

MIN_SCALE = 0.7
MAX_SCALE = 1.5

_scale = 1.0


def set_ui_scale(factor) -> None:
    """Faktor übernehmen; ungültige Werte fallen auf 1.0, gültige werden
    auf [MIN_SCALE, MAX_SCALE] geklemmt."""
    global _scale
    try:
        f = float(factor)
    except (TypeError, ValueError):
        f = 1.0
    _scale = min(MAX_SCALE, max(MIN_SCALE, f))


def get_ui_scale() -> float:
    return _scale


def sz(n: float) -> int:
    """Skalierte Schrift-/Symbolgröße (ganzzahlig, mindestens 1)."""
    return max(1, round(n * _scale))
