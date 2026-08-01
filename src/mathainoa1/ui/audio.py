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
import re
import time

import flet as ft

from mathainoa1.storage.settings import (
    TTS_GOOGLE,
    TTS_SYSTEM,
    load_app_settings,
    save_app_settings,
    tts_cache_dir,
)
from mathainoa1.storage.tts import SLOW_FACTOR, TtsCache, TtsFetchError, speakable
from mathainoa1.ui.scale import sz

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

def play_text(page: ft.Page, text: str, slow: bool | None = None,
              notify_errors: bool = True) -> None:
    """Spricht einen griechischen Text; sync aufrufbar aus jedem on_click.

    Der Weg (Systemstimme oder Google) kommt aus den App-Einstellungen.
    slow=None folgt dem app-weiten Langsam-Modus (slow_mode); True/False
    erzwingt ein Tempo. Fehler zeigen eine SnackBar, außer
    notify_errors=False (Auto-Play soll lautlos scheitern).
    """
    if slow is None:
        slow = _slow_mode
    spoken = speakable(text)
    if not spoken:
        return

    async def run():
        if tts_engine() == TTS_GOOGLE:
            await _speak_google(page, spoken, slow, notify_errors)
        else:
            await _speak_system(page, spoken, slow, notify_errors)

    page.run_task(run)


def play_long_text(page: ft.Page, text: str, slow: bool | None = None,
                   notify_errors: bool = True) -> None:
    """Spricht einen längeren Fließtext (z.B. Originaltext einer
    Textanalyse) — ohne die speakable()-Kürzungen von play_text, die für
    Vokabel-Vorderseiten gedacht sind (Abschneiden an "/", Klammern).

    Die Systemstimme spricht beliebig lange Texte; gTTS zerlegt lange
    Texte intern selbst und liefert eine MP3, die im Cache landet
    (erste Wiedergabe dauert dann etwas).
    """
    if slow is None:
        slow = _slow_mode
    spoken = re.sub(r"\s+", " ", text or "").strip()
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
    Meldung zeigen). Folgt dem Langsam-Modus."""
    if autoplay_enabled():
        play_text(page, text, notify_errors=False)


# --- Langsam-Modus (Sitzung, nicht persistiert) ----------------------------
#
# Gedrückthalten eines Lautsprechers schaltet app-weit auf langsame
# Wiedergabe um (SLOW_FACTOR), erneutes Gedrückthalten zurück auf normal.
# Bewusst nicht gespeichert: die App startet immer im Normaltempo.

_slow_mode: bool = False

SPEAKER_TOOLTIP = "Anhören — Doppeltipp oder lang drücken: langsam an/aus"

# Schildkröte = langsame Wiedergabe (zum Nachsprechen); es gibt kein
# passendes Material-Icon, daher als Emoji-Text in Buttons/Symbolen
TURTLE = "🐢"


def slow_mode() -> bool:
    return _slow_mode


def toggle_slow_mode(page: ft.Page) -> bool:
    global _slow_mode
    _slow_mode = not _slow_mode
    page.show_dialog(ft.SnackBar(ft.Text(
        "Langsame Wiedergabe an — nochmal lange drücken für normal."
        if _slow_mode else "Normale Wiedergabe.")))
    return _slow_mode


def speaker_button(page: ft.Page | None, text_provider,
                   long_text: bool = False,
                   icon_size: int | None = None,
                   icon_color: str | None = None) -> ft.GestureDetector:
    """Einheitlicher Lautsprecher: Tippen = anhören im aktuellen Tempo,
    Gedrückthalten ODER Doppeltipp (Zeitfenster in den Einstellungen) =
    Langsam-Modus umschalten und sofort im neuen Tempo abspielen
    (hörbares Feedback). Im Langsam-Modus wird das Symbol zur
    Schildkröte 🐢.

    text_provider ist eine Funktion, damit der Text zur Abspielzeit
    aktuell ist (Trainer wechselt die Karte unter dem Button weg). Das
    Symbol zeigt den Modus beim Aufbau und nach eigenem Umschalten;
    andere, bereits gebaute Lautsprecher wechseln nicht mit um — dafür
    gibt es die SnackBar von toggle_slow_mode.

    page darf None sein (Listenzeilen, die vor dem Einhängen gebaut
    werden) — die Seite kommt zur Event-Zeit aus e.control.page.
    """
    play = play_long_text if long_text else play_text

    def symbol() -> ft.Control:
        if _slow_mode:
            return ft.Text(TURTLE, size=icon_size or sz(20))
        return ft.Icon(ft.Icons.VOLUME_UP, size=icon_size, color=icon_color)

    holder = ft.Container(symbol(), padding=8, tooltip=SPEAKER_TOOLTIP)
    last_tap = {"t": 0.0}

    def event_page(e) -> ft.Page | None:
        ctl = getattr(e, "control", None)
        return (ctl.page if ctl is not None else None) or page

    def toggle(e):
        pg = event_page(e)
        toggle_slow_mode(pg)
        holder.content = symbol()
        play(pg, text_provider())
        pg.update()

    def on_tap(e):
        now = time.monotonic()
        if now - last_tap["t"] <= slow_tap_seconds():
            last_tap["t"] = 0.0
            toggle(e)
        else:
            last_tap["t"] = now
            play(event_page(e), text_provider())

    return ft.GestureDetector(
        content=holder,
        on_tap=on_tap,
        on_long_press_start=toggle,
    )


# --- Einstellungen (gecacht — nicht bei jeder Karte die JSON lesen) --------

_autoplay: bool | None = None
_engine: str | None = None
_slow_tap: float | None = None


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


def slow_tap_seconds() -> float:
    global _slow_tap
    if _slow_tap is None:
        _slow_tap = load_app_settings().slow_double_tap_seconds
    return _slow_tap


def set_slow_tap_seconds(value: float) -> None:
    global _slow_tap
    _slow_tap = value
    s = load_app_settings()
    s.slow_double_tap_seconds = value
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
