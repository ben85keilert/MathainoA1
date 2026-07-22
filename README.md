# Μαθαίνω — Griechisch A1

[![Tests](https://github.com/ben85keilert/MathainoA1/actions/workflows/tests.yml/badge.svg)](https://github.com/ben85keilert/MathainoA1/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Lern-App für Griechisch (Niveau A1) — Vokabeltraining
(Karteikarten oder Tippen) sowie Grammatiktrainer für Deklination und
Konjugation. Gebaut mit [Flet](https://flet.dev).

Details zum Lern- und Statistik-System (Leitner-Boxen, was in die
Statistik einfließt) stehen im [Handbuch](handbuch.md).

## Voraussetzungen

- Python >= 3.12
- Sprachausgabe: standardmäßig spricht die **Systemstimme des Geräts**
  (eigene Flet-Extension [`packages/flet-system-tts`](packages/flet-system-tts)
  um flutter_tts) — sie funktioniert nur in per `flet build` gebauten
  Apps und nicht unter Linux. Im Dev-Betrieb (`flet run`) bzw. auf
  Geräten ohne griechische Stimme in den App-Einstellungen auf
  „Google (online)“ umschalten (gTTS + lokaler Cache).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt
# oder ohne Dev-/Testabhängigkeiten:
pip install -r requirements.txt
```

Hinweis: `pip install -e .` funktioniert **nicht** — die lokale
Extension `flet-system-tts` ist für pip nur über den relativen Pfad in
den requirements-Dateien auflösbar (`flet build` nutzt stattdessen
`[tool.uv.sources]` aus `pyproject.toml`). Immer aus dem
Repo-Stammverzeichnis installieren.

## Starten

```bash
python main.py
# oder, für Hot-Reload während der Entwicklung:
flet run
# Live-Vorschau auf einem Android-Gerät (Flet-App aus dem Play Store nötig):
flet run --android
```

Die vorgebauten Dev-Clients von `flet run` / `flet run --android`
enthalten die `flet-system-tts`-Extension **nicht** — die Systemstimme
lässt sich nur in einer per `flet build apk` gebauten App testen. Im
Dev-Betrieb dafür in den App-Einstellungen die Sprachausgabe auf
„Google (online)“ stellen.

**Windows-Hinweis:** Die `.venv`-Aktivierungsskripte setzen `PYTHONUTF8=1`,
da `flet run --android` sonst beim Anzeigen des QR-Codes/Links mit
`UnicodeEncodeError` abstürzt (Windows-Konsolen laufen standardmäßig mit
`cp1252`). Wird die `.venv` neu angelegt, geht diese Einstellung verloren —
dann `set PYTHONUTF8=1` (cmd) bzw. `$env:PYTHONUTF8=1` (PowerShell) vor dem
Befehl setzen oder die venv-Skripte erneut anpassen.

**VPN-Hinweis:** Ein aktives VPN (z.B. ProtonVPN) macht `flet run --android`
unbrauchbar: Flet ermittelt die IP für Link/QR-Code über die ausgehende
Route und erwischt dabei die VPN-Tunnel-Adresse (z.B. `10.2.x.x`), die das
Handy im WLAN nicht erreichen kann. Vor dem Start das VPN trennen — oder
per Split-Tunneling Python/Flet vom Tunnel ausnehmen.

## Tests

```bash
pytest
```

## Projektstruktur

```
src/mathainoa1/
  logic/      # Kernlogik: Antwortprüfung, Konjugation, Deklination, Session-Ablauf
  storage/    # Persistenz: Vokabel-/Inhaltsverwaltung, Lernfortschritt, Einstellungen
  ui/         # Flet-Oberfläche (App-Shell und Views)
data/vocab/   # Vokabellisten je Kapitel (JSON)
tests/        # pytest-Tests
```

## Release bauen (APK + AAB)

Der Workflow [`release.yml`](.github/workflows/release.yml) baut bei
einem Versions-Tag (`v*`) oder manuell (workflow_dispatch) APK und AAB,
lädt beide als Workflow-Artefakte hoch und legt beim Tag-Push ein
GitHub-Release an. Der Tag muss zur Version in `pyproject.toml` passen:

```bash
git tag v0.3.0
git push --tags
```

### Play-Store-Veröffentlichung (Checkliste)

- **Datenschutzerklärung**: In der Play Console eine öffentlich
  erreichbare URL hinterlegen — z.B. die GitHub-Ansicht von
  [DATENSCHUTZ.md](DATENSCHUTZ.md).
- **Datensicherheits-Formular**: Es werden keine Nutzerdaten erhoben;
  im optionalen Google-Modus der Sprachausgabe wird der Wort-Text (mit
  IP-Adresse) an Google übertragen — als optionale Weitergabe
  deklarieren (siehe [Datenschutz](#datenschutz)).
- **Zielgruppe**: nicht an Kinder gerichtet (Lern-App für Erwachsene).

## Vokabellisten

Die App wird **ohne Vokabellisten ausgeliefert** — eigene Listen kommen
per Import (CSV/JSON-Datei oder „Als Text importieren") in die App; die
passenden Chatbot-Prompts stehen in der App-Hilfe. Lokale Listen liegen
im gitignorierten Ordner `private/` und kommen nie ins Repository.

## Datenschutz

Die App erhebt keine Daten: kein Konto, kein Tracking, keine
Analyse-Dienste. Lernfortschritt, Notizen, Listen und Einstellungen
liegen ausschließlich lokal auf dem Gerät. Die Sprachausgabe nutzt
standardmäßig die Systemstimme des Geräts (offline, keine
Übertragung); nur der optional wählbare Google-Modus überträgt beim
Laden eines Worts den Text und die IP-Adresse an Google und cacht das
Audio danach lokal. Details in der
[Datenschutzerklärung](DATENSCHUTZ.md).

## Lizenz

MIT, siehe [LICENSE](LICENSE) — gilt für den Quellcode; Vokabelinhalte
sind nicht Teil dieses Repositorys.
