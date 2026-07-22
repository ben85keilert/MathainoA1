# flet-system-tts

Flet-Erweiterung für Μαθαίνω: spricht Text über die **Systemstimme des
Geräts** — auf Android/iOS über die System-TTS-Engine (z.B. Google-TTS),
auf Windows über SAPI, auf macOS über AVSpeech. Dart-Seite wrappt
[flutter_tts](https://pub.dev/packages/flutter_tts).

Alles läuft lokal auf dem Gerät; es werden keine Daten übertragen.
Linux wird von flutter_tts nicht unterstützt — die App nutzt dort den
Google-Modus (gTTS) als Ausweichweg.

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
