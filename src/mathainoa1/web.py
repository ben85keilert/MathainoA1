"""Web-Profil: was die Web-Fassung anders hält als die App.

Die Web-Fassung ist dieselbe App als statische Seite (`flet build web`,
Python läuft über Pyodide im Browser; gebaut mit tools/web_build.py). Ein
Server liefert nur Dateien aus — er rechnet nichts und speichert nichts.

Dies ist die EINE Stelle, an der steht, was im Browser aus ist. Ansichten
fragen `active("…")`, statt selbst die Plattform zu prüfen.
"""

from __future__ import annotations

import os
import sys

# Funktionen, die es im Browser nicht gibt — mit Grund:
WEB_OFF: dict[str, str] = {
    # fragt GitHub nach einer neuen APK; eine Seite braucht kein Update,
    # und urllib hat im Browser-Python keinen Netzweg
    "update_check": "Eine Seite ist immer auf dem Stand des Servers.",
    # gTTS holt MP3 von Google-Servern (Anfrage an fremde Server) über
    # urllib in einem Thread — beides geht im Browser nicht
    "tts_google": "Im Browser spricht nur die Stimme des Geräts.",
}


def in_browser() -> bool:
    """Läuft Python im Browser (Pyodide)? Für Tests und die Vorschau am
    Rechner lässt sich das Web-Profil mit MATHAINO_WEB=1 einschalten."""
    return sys.platform == "emscripten" or os.environ.get("MATHAINO_WEB") == "1"


def active(feature: str) -> bool:
    """Ob eine Funktion hier zur Verfügung steht (außerhalb des Browsers
    immer)."""
    return not (in_browser() and feature in WEB_OFF)
