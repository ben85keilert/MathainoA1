"""Sprachausgabe in der UI: zwei Wege, umschaltbar in den Einstellungen.

- Systemstimme (Standard, TTS_SYSTEM): die flet-system-tts-Erweiterung
  spricht über die Stimme des Geräts — offline, keine Datenübertragung.
  Im vorgebauten Dev-Client (flet run / flet run --android) ist die
  Erweiterung nicht enthalten; dann erscheint ein Hinweis mit dem Tipp,
  auf den Google-Weg umzuschalten.
- Google (TTS_GOOGLE): MP3 aus dem gTTS-Cache (storage/tts.py) über
  flet-audio abspielen — Cache-Treffer sofort und offline, sonst wird
  die MP3 im Hintergrund von Google geholt (braucht Internet).
"""

from __future__ import annotations

import asyncio

import flet as ft

from mathainoa1.storage.settings import (
    TTS_GOOGLE,
    TTS_SYSTEM,
    load_app_settings,
    save_app_settings,
    tts_cache_dir,
)
from mathainoa1.storage.tts import SLOW_FACTOR, TtsCache, TtsFetchError, speakable

try:
    import flet_audio as fa
except ImportError:  # Paket fehlt (z.B. Test-Umgebung)
    fa = None

try:
    from flet_system_tts import SystemTts
except ImportError:  # Erweiterung fehlt (Dev-Client, Test-Umgebung)
    SystemTts = None

NO_SYSTEM_TTS_HINT = (
    "Systemstimme nicht verfügbar — griechisches Sprachpaket installieren "
    "oder in den Einstellungen auf „Google (online)“ umschalten."
)

_cache: TtsCache | None = None
# Texte, deren gTTS-Abruf gerade läuft — schützt vor Doppel-Taps
_fetching: set[str] = set()


def tts_cache() -> TtsCache:
    global _cache
    if _cache is None:
        _cache = TtsCache(tts_cache_dir())
    return _cache


# --- Weg 1: Systemstimme (flet-system-tts) ---------------------------------

def _system_service(page: ft.Page):
    """Den SystemTts-Service der Seite liefern (einmalig einhängen) —
    oder None, wenn die Erweiterung nicht installiert ist."""
    if SystemTts is None:
        return None
    for s in page.services:
        if isinstance(s, SystemTts):
            return s
    svc = SystemTts()
    page.services.append(svc)
    page.update()
    return svc


async def _speak_system(page: ft.Page, text: str, slow: bool,
                        notify_errors: bool) -> None:
    svc = _system_service(page)
    if svc is None:
        if notify_errors:
            page.show_dialog(ft.SnackBar(ft.Text(NO_SYSTEM_TTS_HINT)))
        return
    try:
        await svc.speak(text, rate=SLOW_FACTOR if slow else 1.0)
    except Exception:
        # Sprachpaket fehlt oder Engine-Fehler — gleicher Ausweg
        if notify_errors:
            page.show_dialog(ft.SnackBar(ft.Text(NO_SYSTEM_TTS_HINT)))


# --- Weg 2: Google (gTTS-Cache + flet-audio) -------------------------------

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


async def _speak_google(page: ft.Page, text: str, slow: bool,
                        notify_errors: bool) -> None:
    if fa is None:
        return
    if text in _fetching:
        return
    cache = tts_cache()
    if not cache.has(text):
        _fetching.add(text)
        try:
            await asyncio.to_thread(cache.fetch, text)
        except TtsFetchError:
            if notify_errors:
                page.show_dialog(ft.SnackBar(ft.Text(
                    "Kein Internet — Audio nicht verfügbar.")))
            return
        finally:
            _fetching.discard(text)
    # file://-URL (nicht rohe Bytes, nicht nackter Pfad): das
    # audioplayers-Plugin reicht den src-String direkt an GStreamers
    # playbin (uri=...) weiter, das eine gültige URI *mit Schema*
    # verlangt. as_uri() liefert "file:///..." — gültig auf Desktop
    # und Android. Wiedergabe per autoplay statt play(), siehe
    # _install_autoplay().
    uri = cache.path_for(text).as_uri()
    _install_autoplay(page, uri, SLOW_FACTOR if slow else 1.0)


# --- gemeinsame API für alle Views -----------------------------------------

def play_text(page: ft.Page, text: str, slow: bool = False,
              notify_errors: bool = True) -> None:
    """Spricht einen griechischen Text; sync aufrufbar aus jedem on_click.

    Der Weg (Systemstimme oder Google) kommt aus den App-Einstellungen.
    slow=True verlangsamt die Wiedergabe (zum Nachsprechen). Fehler zeigen
    eine SnackBar, außer notify_errors=False (Auto-Play soll lautlos
    scheitern).
    """
    spoken = speakable(text)
    if not spoken:
        return

    async def run():
        if tts_engine() == TTS_GOOGLE:
            await _speak_google(page, spoken, slow, notify_errors)
        else:
            await _speak_system(page, spoken, slow, notify_errors)

    page.run_task(run)


def maybe_autoplay(page: ft.Page, text: str) -> None:
    """Spricht den Text automatisch, wenn Auto-Play an ist — lautlos bei
    Fehlern (offline oder fehlende Stimme soll nicht jede Karte eine
    Meldung zeigen)."""
    if autoplay_enabled():
        play_text(page, text, notify_errors=False)


# --- Einstellungen (gecacht — nicht bei jeder Karte die JSON lesen) --------

_autoplay: bool | None = None
_engine: str | None = None


def autoplay_enabled() -> bool:
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


def tts_engine() -> str:
    global _engine
    if _engine is None:
        _engine = load_app_settings().tts_engine
    return _engine


def set_tts_engine(value: str) -> None:
    global _engine
    _engine = value
    s = load_app_settings()
    s.tts_engine = value
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
