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

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt
# oder ohne Dev-/Testabhängigkeiten:
pip install -r requirements.txt
```

Alternativ über die Projektdefinition selbst:

```bash
pip install -e ".[dev]"
```

## Starten

```bash
python main.py
# oder, für Hot-Reload während der Entwicklung:
flet run
# Live-Vorschau auf einem Android-Gerät (Flet-App aus dem Play Store nötig):
flet run --android
```

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

## Android-APK bauen

Der Workflow [`build-apk.yml`](.github/workflows/build-apk.yml) baut bei
jedem Push nach `main` sowie bei `v*`-Tags automatisch eine APK
(`flet build apk`) und lädt sie als Workflow-Artefakt hoch. Bei einem
Tag-Push wird zusätzlich ein GitHub-Release mit der APK angelegt:

```bash
git tag v0.1.0
git push --tags
```

## Vokabellisten

Die App wird **ohne Vokabellisten ausgeliefert** — eigene Listen kommen
per Import (CSV/JSON-Datei oder „Als Text importieren") in die App; die
passenden Chatbot-Prompts stehen in der App-Hilfe. Lokale Listen liegen
im gitignorierten Ordner `private/` und kommen nie ins Repository.

## Lizenz

MIT, siehe [LICENSE](LICENSE) — gilt für den Quellcode; Vokabelinhalte
sind nicht Teil dieses Repositorys.
