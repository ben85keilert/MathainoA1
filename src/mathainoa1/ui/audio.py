"""Wiedergabe der Wort-Audiodateien: ein gemeinsamer Player für alle Buttons.

Einziges Modul mit flet-audio-Kontakt. Der Import ist abgesichert, damit die
App (und pytest) auch ohne installiertes flet-audio funktioniert — die
Play-Buttons erscheinen dann schlicht nicht, weil AudioStore leer bleibt
bzw. play_card nichts tut.
"""

from __future__ import annotations

import flet as ft

from mathainoa1.storage.audio import AudioStore
from mathainoa1.storage.settings import (
    audio_dir,
    load_app_settings,
    save_app_settings,
)

try:
    import flet_audio as fa
except ImportError:  # Paket fehlt (z.B. Test-Umgebung)
    fa = None

# Langsam-Wiedergabe zum Nachsprechen; audioplayers erlaubt 0.5–2.0
SLOW_RATE = 0.65

_store: AudioStore | None = None


def audio_store() -> AudioStore:
    global _store
    if _store is None:
        _store = AudioStore(audio_dir())
    return _store


def _player(page: ft.Page):
    """Den gemeinsamen Audio-Service finden oder anlegen —
    dasselbe Muster wie beim FilePicker in manager_view."""
    for s in page.services:
        if isinstance(s, fa.Audio):
            return s
    p = fa.Audio(release_mode=fa.ReleaseMode.STOP)
    page.services.append(p)
    page.update()
    return p


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


def maybe_autoplay(page: ft.Page, card_id: str) -> None:
    """Spielt das Karten-Audio ab, wenn Auto-Play an ist und Audio existiert."""
    if autoplay_enabled() and audio_store().has_audio(card_id):
        play_card(page, card_id)


def play_card(page: ft.Page, card_id: str, slow: bool = False) -> None:
    """Spielt das Audio einer Karte ab; sync aufrufbar aus jedem on_click.

    slow=True verlangsamt die Wiedergabe (zum Nachsprechen) — dieselbe
    Datei, nur mit reduzierter playback_rate.
    """
    if fa is None:
        return
    path = audio_store().path_for(card_id)
    if path is None:
        return

    async def run():
        player = _player(page)
        # Bytes statt Dateipfad: funktioniert unabhängig davon, ob die
        # Plattform app_data_dir()-Pfade als Audioquelle akzeptiert
        player.src = path.read_bytes()
        player.playback_rate = SLOW_RATE if slow else 1.0
        page.update()
        await player.play()

    page.run_task(run)
