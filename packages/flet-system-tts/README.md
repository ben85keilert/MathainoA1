# flet-system-tts

Flet-Erweiterung für Μαθαίνω: spricht Text über die **Systemstimme des
Geräts** — auf Android/iOS über die System-TTS-Engine (z.B. Google-TTS),
auf Windows über SAPI, auf macOS über AVSpeech. Dart-Seite wrappt
[flutter_tts](https://pub.dev/packages/flutter_tts).

Alles läuft lokal auf dem Gerät; es werden keine Daten übertragen.
Linux wird von flutter_tts nicht unterstützt — die App nutzt dort den
Google-Modus (gTTS) als Ausweichweg.

**Im Browser** (Web-Fassung) spricht nicht flutter_tts, sondern
`lib/src/web_speech_web.dart` direkt über die Web Speech API
(`window.speechSynthesis`); die Gründe stehen im Kopf der Datei. Die Stimme
kommt vom Betriebssystem. Gemessen am 26.11.2026 unter Linux: Firefox 160
findet die griechische espeak-ng-Stimme (über speech-dispatcher, erst
einige Sekunden nach dem Laden der Seite); Chrome 157 kennt ohne den
Startschalter `--enable-speech-dispatcher` nur seine Google-Stimmen,
darunter keine griechische.

Wichtig: Der vorgebaute Flet-Client von `flet run` / `flet run --android`
enthält diese Erweiterung **nicht** — die Systemstimme funktioniert nur in
per `flet build` gebauten Apps (APK/Desktop-Build).

## Verwendung

```python
import flet as ft
from flet_system_tts import SystemTts

svc = SystemTts()  # language="el-GR" ist Standard
page.services.append(svc)
page.update()

await svc.speak("ο δρόμος")            # blockiert bis zum Ende
await svc.speak("ο δρόμος", rate=0.65) # langsam (zum Nachsprechen)
await svc.stop()
```
