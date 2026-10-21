# Μαθαίνω — Griechisch A1/A2

[![Tests](https://github.com/ben85keilert/MathainoA1/actions/workflows/tests.yml/badge.svg)](https://github.com/ben85keilert/MathainoA1/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Lern-App für Griechisch (Niveau A1 und A2, als Stufen strikt getrennt
umschaltbar) — Vokabeltraining
(Karteikarten oder Tippen) sowie Grammatiktrainer für Deklination und
Konjugation (ab A2 mit Aorist und Imperativ). Gebaut mit [Flet](https://flet.dev).

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
tools/        # Release-, Icon- und Lexikon-Werkzeuge
.claude/skills/lexikon/  # Claude-Code-Skill für Lexikonpakete
```

## Release bauen (APK)

Der Workflow [`release.yml`](.github/workflows/release.yml) baut bei
einem Versions-Tag (`v*`) oder manuell (workflow_dispatch) die APK
(nur für `arm64-v8a`, also Pixel & Co. — andere Architekturen werden
nicht gebraucht und würden die Datei fast verdoppeln), lädt sie als
Workflow-Artefakt hoch und legt beim Tag-Push ein GitHub-Release an. Der Tag muss zur Version in `pyproject.toml` passen.
Das AAB (App Bundle für Google Play) wird derzeit **nicht** gebaut —
gebraucht wird nur die APK zum Sideload. Der versionCode wird trotzdem
weiter aus der Version berechnet, damit ein späterer Play-Upload direkt
passt; zum Wiederbeleben genügt ein `flet build aab`-Schritt im
Workflow (im Kopfkommentar der Datei beschrieben).
Am einfachsten übernimmt das Release-Skript alles auf einmal
(Version in `pyproject.toml` + `__init__.py` setzen, committen, taggen,
pushen). Es läuft nur auf `main` mit sauberem Arbeitsverzeichnis — auch
eine nicht versionierte Datei lässt es abbrechen (`git status`):

```bash
python tools/release.py 0.9.5
```

### Von Hand releasen

Dieselben Schritte ohne Skript (Beispiel 0.9.4 → 0.9.5). Die
Reihenfolge ist wichtig: erst die Version committen, dann genau diesen
Commit taggen — erst der Tag-Push startet den Release-Build.

```bash
# 1. Version an beiden Stellen setzen (im Editor oder per sed):
#    pyproject.toml              version = "0.9.5"
#    src/mathainoa1/__init__.py  __version__ = "0.9.5"
sed -i 's/^version = ".*"/version = "0.9.5"/' pyproject.toml
sed -i 's/^__version__ = ".*"/__version__ = "0.9.5"/' src/mathainoa1/__init__.py
git diff                       # nur die beiden Versionszeilen geändert?

# 2. Version committen und pushen (startet nur die Tests)
git add pyproject.toml src/mathainoa1/__init__.py
git commit -m "Version 0.9.5"
git push origin main

# 3. Diesen Commit taggen und den Tag pushen — startet den Release-Build
git tag -a v0.9.5 -m "Version 0.9.5"
git push origin v0.9.5

# 4. Build verfolgen (dauert einige Minuten)
gh run list --workflow release.yml --limit 3
gh run watch <run-id>
gh run view <run-id> --json conclusion   # das verlässliche Ergebnis
```

Ein Testbuild ohne Release (APK nur als Workflow-Artefakt) geht ohne
Tag: `gh workflow run release.yml --ref main`. Ändert ein Push Dateien
unter `.github/workflows/`, braucht der HTTPS-Push ein Token mit
`workflow`-Scope — sonst per SSH pushen:
`git push git@github.com:ben85keilert/MathainoA1.git main v0.9.5`.

**Kein Release über die GitHub-Oberfläche anlegen und keinen Tag ohne
passenden „Version x.y.z“-Commit setzen.** Ein solcher Tag lässt den
Workflow sofort mit „Tag vX passt nicht zu pyproject-Version Y“
abbrechen; ein von Hand angelegtes Release steht dann leer (ohne APK)
in der Liste. Ist das doch einmal passiert: Version nachziehen und den
Tag auf den neuen Commit umsetzen (`git push origin :refs/tags/vX` —
dann neu taggen und pushen), der Workflow hängt die Dateien
anschließend an das bestehende Release.

### In-App-Update-Check (Sideload-Provisorium)

Die App prüft beim Start (höchstens einmal täglich, still bei Fehlern)
das neueste GitHub-Release und bietet bei einer neueren Version den
APK-Download an; zusätzlich gibt es in der Hilfe „Nach Updates suchen“
(`storage/updates.py` + `ui/updates.py`). Releases **ohne** APK-Datei
werden übersprungen — ein noch laufender oder gescheiterter Build soll
kein Update melden, das sich nicht installieren lässt. Da alle CI-Builds denselben
Signierschlüssel tragen, installiert Android die neue APK über die
bestehende App — Lernstand und Listen bleiben erhalten.
Voraussetzung: das Repository ist öffentlich (die ungetokente
GitHub-API liefert für private Repos 404 — der Check schlägt dann
einfach still fehl).

### Play-Store-Veröffentlichung (Checkliste)

Vorerst nicht aktuell — der Workflow baut nur die APK. Für einen
Play-Upload muss zuerst der AAB-Schritt wieder in `release.yml`
(siehe oben).

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

## Lexikonpakete (Claude-Code-Skill)

Lexikonpakete (Etymologie-Pakete nach Arbeitsanweisung IV) zu
Vokabellisten erzeugt und prüft das Claude-Code-Skill **`/lexikon`**
([`.claude/skills/lexikon/`](.claude/skills/lexikon/SKILL.md)), z.B.
`/lexikon erstellen private/pame-a2/lexikon kap05` oder
`/lexikon prüfen private/pame-a2/lexikon kap01`. Es kennt drei Modi
(erstellen, prüfen, nachbessern) und hält den KI-Aufwand klein: Alles
Mechanische prüft [`tools/lexikon.py`](tools/lexikon.py) (Schema,
Vollständigkeit, Schreibweise, von der App gebildete Formen, Importtest),
Agenten schreiben Inhalte und prüfen gezielte Auszüge, Korrekturen laufen
als Patches. Die Inhaltsregeln stehen in
[`regeln.md`](.claude/skills/lexikon/regeln.md). Arbeitsordner und Pakete
liegen wie die Listen unter `private/`.

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
