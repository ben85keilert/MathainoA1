"""Python-Seite der Erweiterung: ein Service nach dem Muster von
flet_audio.Audio. Methodenaufrufe laufen über _invoke_method zur
Dart-Seite (flutter/flet_system_tts), die flutter_tts anspricht."""

import flet as ft


@ft.control("SystemTts")
class SystemTts(ft.Service):
    """Spricht Text über die System-Sprachausgabe des Geräts.

    In page.services einhängen; danach speak()/stop() aufrufen.
    Wirft eine Exception, wenn die eingestellte Sprache auf dem Gerät
    nicht verfügbar ist (Meldung enthält "language_not_available").
    """

    language: str = "el-GR"
    """BCP-47-Sprachcode der Stimme (Standard: Neugriechisch)."""

    async def speak(self, text: str, rate: float = 1.0) -> None:
        """Spricht text und wartet bis zum Ende der Wiedergabe.

        rate: 1.0 = Normaltempo, kleiner = langsamer (z.B. 0.65 zum
        Nachsprechen). Eine bereits laufende Wiedergabe wird abgebrochen.
        """
        await self._invoke_method("speak", {"text": text, "rate": rate})

    async def stop(self) -> None:
        """Bricht die laufende Wiedergabe ab."""
        await self._invoke_method("stop")

    async def is_language_available(self) -> bool:
        """Ob das Gerät eine Stimme für `language` installiert hat."""
        return bool(await self._invoke_method("is_language_available"))
