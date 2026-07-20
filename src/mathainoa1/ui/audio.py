"""Sprachausgabe in der UI: ein gemeinsamer Player für alle Buttons.

Wiedergabe läuft über den gTTS-Cache (storage/tts.py): Cache-Treffer
spielen sofort und offline, sonst wird die MP3 im Hintergrund geholt
(braucht Internet) und danach abgespielt.

Einziges Modul mit flet-audio-Kontakt. Der Import ist abgesichert, damit
die App (und pytest) auch ohne installiertes flet-audio funktioniert —
Abspielen tut dann schlicht nichts.
"""

from __future__ import annotations

import asyncio

import flet as ft

from mathainoa1.storage.settings import (
    load_app_settings,
    save_app_settings,
    tts_cache_dir,
)
from mathainoa1.storage.tts import TtsCache, TtsFetchError, speakable

try:
    import flet_audio as fa
except ImportError:  # Paket fehlt (z.B. Test-Umgebung)
    fa = None

# Langsam-Wiedergabe zum Nachsprechen; audioplayers erlaubt 0.5–2.0
SLOW_RATE = 0.65

_cache: TtsCache | None = None
# Texte, deren Abruf gerade läuft — schützt vor Doppel-Taps
_fetching: set[str] = set()


def tts_cache() -> TtsCache:
    global _cache
    if _cache is None:
        _cache = TtsCache(tts_cache_dir())
    return _cache


def _install_autoplay(page: ft.Page, uri: str, rate: float):
    """Frisches Audio-Control mit src+autoplay einhängen und altes entfernen.

    Workaround für den flet-audio-Regressionsbug ab 0.82 (flet-Issue #6265):
    ein separater `await player.play()` auf ein bestehendes Control lädt die
    Quelle nie ("on_loaded" feuert nicht) und läuft in den 30-s-Timeout
    "Future not completed" — reproduzierbar auf Desktop UND Android. Ein neu
    erzeugtes Audio mit `src`/`playback_rate` schon im Konstruktor plus
    `autoplay=True` spielt beim Einhängen selbst ab, ohne den kaputten
    play()-Aufruf. Laut flet-Doku wird autoplay auf Desktop und Mobile
    unterstützt (nur Web-Chrome/Edge nicht). Weil autoplay nur beim Anlegen
    auslöst, wird pro Wiedergabe ein neues Control gesetzt und das alte
    entfernt (sonst sammeln sie sich an)."""
    for s in [s for s in page.services if isinstance(s, fa.Audio)]:
        page.services.remove(s)
    p = fa.Audio(src=uri, playback_rate=rate, autoplay=True,
                 release_mode=fa.ReleaseMode.RELEASE)
    page.services.append(p)
    page.update()
    return p


def play_text(page: ft.Page, text: str, slow: bool = False,
              notify_errors: bool = True) -> None:
    """Spricht einen griechischen Text; sync aufrufbar aus jedem on_click.

    Cache-Treffer spielen sofort; sonst wird die MP3 erst im Hintergrund
    geholt (gTTS, braucht Internet). slow=True verlangsamt die Wiedergabe
    (zum Nachsprechen) — dieselbe Datei, nur mit reduzierter playback_rate.
    Fehler (offline, Drosselung) zeigen eine SnackBar, außer
    notify_errors=False (Auto-Play soll lautlos scheitern).
    """
    if fa is None:
        return
    spoken = speakable(text)
    if not spoken:
        return

    async def run():
        if spoken in _fetching:
            return
        cache = tts_cache()
        if not cache.has(spoken):
            _fetching.add(spoken)
            try:
                await asyncio.to_thread(cache.fetch, spoken)
            except TtsFetchError:
                if notify_errors:
                    page.show_dialog(ft.SnackBar(ft.Text(
                        "Kein Internet — Audio nicht verfügbar.")))
                return
            finally:
                _fetching.discard(spoken)
        # file://-URL (nicht rohe Bytes, nicht nackter Pfad): das
        # audioplayers-Plugin reicht den src-String direkt an GStreamers
        # playbin (uri=...) weiter, das eine gültige URI *mit Schema*
        # verlangt. as_uri() liefert "file:///..." — gültig auf Desktop
        # und Android. Wiedergabe per autoplay statt play(), siehe
        # _install_autoplay().
        uri = cache.path_for(spoken).as_uri()
        _install_autoplay(page, uri, SLOW_RATE if slow else 1.0)

    page.run_task(run)


def maybe_autoplay(page: ft.Page, text: str) -> None:
    """Spricht den Text automatisch, wenn Auto-Play an ist — lautlos bei
    Fehlern (offline soll nicht jede Karte eine Meldung zeigen)."""
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
