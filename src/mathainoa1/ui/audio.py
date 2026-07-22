"""Sprachausgabe in der UI: Systemstimme des Geräts, komplett offline.

Gesprochen wird über storage/tts.py (pyttsx3). Das blockierende
speak() läuft in einem Thread (asyncio.to_thread); ein neuer Text
bricht die laufende Wiedergabe ab und verdrängt noch wartende.
"""

from __future__ import annotations

import asyncio

import flet as ft

from mathainoa1.storage.settings import load_app_settings, save_app_settings
from mathainoa1.storage.tts import SystemTts, TtsError, speakable

# Ein gemeinsames Engine-Objekt für alle Buttons
_tts: SystemTts | None = None
# Zähler der Abspielwünsche: nur der jüngste darf noch sprechen
_gen = 0


def system_tts() -> SystemTts:
    global _tts
    if _tts is None:
        _tts = SystemTts()
    return _tts


def play_text(page: ft.Page, text: str, slow: bool = False,
              notify_errors: bool = True) -> None:
    """Spricht einen griechischen Text; sync aufrufbar aus jedem on_click.

    slow=True verlangsamt das Sprechtempo (zum Nachsprechen). Fehler
    (keine griechische Stimme, Engine nicht verfügbar) zeigen eine
    SnackBar, außer notify_errors=False (Auto-Play soll lautlos
    scheitern).
    """
    spoken = speakable(text)
    if not spoken:
        return

    async def run():
        global _gen
        _gen += 1
        my = _gen
        tts = system_tts()
        tts.stop()

        def work():
            if my != _gen:
                return  # inzwischen kam ein neuerer Text — nicht mehr sprechen
            tts.speak(spoken, slow)

        try:
            await asyncio.to_thread(work)
        except TtsError as exc:
            if notify_errors:
                page.show_dialog(ft.SnackBar(ft.Text(str(exc))))

    page.run_task(run)


def maybe_autoplay(page: ft.Page, text: str) -> None:
    """Spricht den Text automatisch, wenn Auto-Play an ist — lautlos bei
    Fehlern (eine fehlende Stimme soll nicht jede Karte eine Meldung
    zeigen lassen)."""
    if autoplay_enabled():
        play_text(page, text, notify_errors=False)


_autoplay: bool | None = None


def autoplay_enabled() -> bool:
    """Auto-Play-Einstellung, gecacht — nicht bei jeder Karte die JSON lesen."""
    global _autoplay
    if _autoplay is None:
        _autoplay = load_app_settings().autoplay_audio
    return _autoplay


def set_autoplay(value: bool) -> None:
    global _autoplay
    _autoplay = value
    s = load_app_settings()
    s.autoplay_audio = value
    save_app_settings(s)


def autoplay_button(page: ft.Page) -> ft.IconButton:
    """Umschalter „Griechisch automatisch vorlesen“ für die Trainings-Views."""
    def apply_icon(btn: ft.IconButton):
        on = autoplay_enabled()
        btn.icon = ft.Icons.VOLUME_UP if on else ft.Icons.VOLUME_OFF
        btn.icon_color = ft.Colors.PRIMARY if on else None
        btn.tooltip = ("Automatisch vorlesen: an" if on
                       else "Automatisch vorlesen: aus")

    def toggle(e):
        set_autoplay(not autoplay_enabled())
        apply_icon(e.control)
        page.update()

    btn = ft.IconButton(on_click=toggle)
    apply_icon(btn)
    return btn
