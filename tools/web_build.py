"""Web-Fassung bauen — die App als statische Seite (Flutter zeichnet, Python
läuft über Pyodide im Browser).

    python tools/web_build.py --basis /            # Wurzel einer Adresse — und lokal
    python tools/web_build.py --basis /<ordner>/   # Unterordner eines Servers

Ergebnis: dist/web/ — ein Ordner mit index.html, den jeder Webserver
ausliefern kann, und darin stand.json (Version, Commit, Basisadresse).
Lokal ansehen: flet serve dist/web (nur mit --basis /).
Braucht flet-cli im selben Python (pip install flet-cli, Version wie flet).

Die Basisadresse ist der Pfad, unter dem index.html im Browser steht. Sie
ist fest in den Build eingebaut: Zieht die Seite um, wird neu gebaut.

Die Buchlisten sind NICHT im Build (data/vocab ist leer, private/ ist
ausgeschlossen): Was hier entsteht, darf öffentlich liegen. Inhalte kommen
im Browser verschlüsselt dazu (privates Repo mathaino-inhalte, web/bauen.py).

Was dieses Skript über `flet build web` hinaus tut — jeder Punkt hat in
der Probe vom 25.11.2026 gefehlt oder stammt aus der trainingsapp
(scripts/web_bauen.py), wo er einmal gefehlt hat:

1. --no-cdn: sonst lädt die Seite Pyodide von jsdelivr und Schriften von
   Google — bei jedem Besuch eine Anfrage an fremde Server.
2. Adressen mit „#“ (--route-url-strategy hash): Ein statischer Server
   kennt die Ansichten nicht.
3. Ausschlüsse fürs App-Archiv (WEB_EXCLUDE, WEB_CLEANUP): `flet build`
   packt den ganzen Projektordner ein. requirements.txt MUSS draußen bleiben — Flets
   Python-Worker liest sie im Browser und scheitert an der Zeile
   ./packages/flet-system-tts; die Seite bliebe beim Ladebild stehen.
4. Pyodide-Pakete einlegen (PYODIDE_PACKAGES): sqlite3 ist in Pyodide ein
   eigenes Paket und liegt mit --no-cdn nicht im Build — ohne es scheitert
   `import sqlite3` (storage/progress.py). Geladen wird es beim Start über
   [tool.flet.web] dependencies in pyproject.toml; cryptography (scrypt
   fürs Inhaltspaket) erst bei Bedarf. Die Dateien kommen beim
   BAUEN von jsdelivr, mit der Prüfsumme aus Pyodides pyodide-lock.json,
   und liegen dann auf dem eigenen Server.
   Ebenso die Ersatzschriften (FONTS): Ohne sie fragt Flutter eine
   fehlende Schrift in Dauerschleife an.
5. Inline-Skripte der index.html nach start-<n>.js: Eine strenge
   Content-Security-Policy (script-src 'self') blockiert sie sonst.
6. Das App-Archiv gegen das Repository prüfen: Außerhalb der Pakete darf
   nur liegen, was versioniert ist — sonst wandern Notizen und Daten
   dieses Rechners auf den Server (so in der Probe: temp.md).
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "web"

# Zusätzlich zu [tool.flet.app] exclude aus pyproject.toml — nur fürs Web.
# Die APK bleibt, wie sie ist. ACHTUNG: Ausschlüsse sind exakte Pfade
# relativ zum Projektordner, keine Muster (serious_python,
# package_command.dart: excludeList.contains(relativer Pfad)) — ein Eintrag
# wie "*.pdf" bewirkt nichts. Muster gehören nach WEB_CLEANUP.
WEB_EXCLUDE = [
    "requirements.txt",
    "requirements-dev.txt",
    "dist",
    "build",
    "CLAUDE.md",
    "README.md",
    "handbuch.md",
    "DATENSCHUTZ.md",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
]

# Muster (Globs), die nach dem Kopieren aus dem App-Ordner gelöscht werden
# (--cleanup-app-files); --cleanup-app räumt dazu __pycache__ weg.
WEB_CLEANUP = ["temp*", "**.pdf"]

# Pyodide-Pakete, die neben Pyodide liegen müssen (pyodide/), samt allem,
# was sie selbst brauchen. sqlite3 lädt die Seite beim Start
# ([tool.flet.web] dependencies). cryptography lädt sie erst, wenn jemand
# das verschlüsselte Inhaltspaket öffnet (ui/web_content.py): Dem Python
# im Browser fehlt hashlib.scrypt — auch mit Pyodides hashlib-Paket,
# gemessen am 25.11.2026 —, cryptography rechnet dasselbe.
PYODIDE_PACKAGES: tuple[str, ...] = ("sqlite3", "cryptography")
PYODIDE_SOURCE = "https://cdn.jsdelivr.net/pyodide/v{version}/full/{file}"
PYODIDE_CACHE = ROOT / "build" / "web-pyodide"

# Ersatzschriften, die die App im Browser braucht: Pfad unter assets/fonts/
# (so fragt Flutter sie an), Quelle, SHA-256. Fehlt Flutter ein Zeichen —
# der Pfeil „→“ steht nicht in der mitgelieferten Roboto, die App benutzt
# ihn an über 100 Stellen —, fragt es eine Noto-Schrift an; mit --no-cdn
# unter assets/fonts/, wo flet sie nicht ablegt. Die Anfrage scheitert und
# wiederholt sich (trainingsapp, gemessen: über 1400 Anfragen je Minute und
# Tab). Geladen beim BAUEN, nicht beim Besuch. SIL Open Font License.
# Braucht die App ein Zeichen aus einer weiteren Schrift, nennt die Konsole
# des Browsers die Datei (404 unter assets/fonts/…) — hier eintragen.
FONTS: tuple[tuple[str, str, str], ...] = (
    ("notosanssymbols/v43/"
     "rP2up3q65FkAtHfwd-eIS2brbDN6gxP34F9jRRCe4W3gfQ8gb_VFRkzrbQ.woff2",
     "https://fonts.gstatic.com/s/notosanssymbols/v43/"
     "rP2up3q65FkAtHfwd-eIS2brbDN6gxP34F9jRRCe4W3gfQ8gb_VFRkzrbQ.woff2",
     "08202e258ea583254c036cff46a7077bb5af4f82c41a6c0a6775f6e44d99f1aa"),
)

APP_ARCHIVE = Path("assets") / "app" / "app.zip"
# Was im Archiv außerhalb der Pakete unversioniert sein darf
ARCHIVE_ALLOWED = (".gitkeep",)

_SCRIPT = re.compile(r"<script(?P<attr>[^>]*)>(?P<body>.*?)</script>", re.S)
_FOREIGN = re.compile(r'(?:src|href)="https?://|Url: "https?://')
NO_CDN = 'noCdn: "True"'
HASH_ROUTES = 'routeUrlStrategy: "hash"'


def check_base(base: str) -> str:
    """Die Basisadresse: beginnt und endet mit „/“, sonst nur Buchstaben,
    Ziffern, - und _."""
    if not re.fullmatch(r"/(?:[A-Za-z0-9_-]+/)*", base):
        raise ValueError("Die Basisadresse beginnt und endet mit „/“ "
                         f"(/ oder /<ordner>/), nicht {base!r}")
    return base


def excludes() -> list[str]:
    """Ausschlüsse aus pyproject.toml plus die fürs Web."""
    with (ROOT / "pyproject.toml").open("rb") as f:
        own = tomllib.load(f)["tool"]["flet"]["app"]["exclude"]
    return list(dict.fromkeys([*own, *WEB_EXCLUDE]))


def move_inline_scripts(folder: Path) -> int:
    """Inline-Skripte der index.html nach start-<n>.js; liefert ihre Zahl.
    Reihenfolge und Zeitpunkt bleiben; Skripte mit src bleiben unberührt."""
    index = folder / "index.html"
    n = 0

    def replace(m: re.Match[str]) -> str:
        nonlocal n
        attr, body = m.group("attr"), m.group("body")
        if "src=" in attr or not body.strip():
            return m.group(0)
        n += 1
        name = f"start-{n}.js"
        (folder / name).write_text(body.strip() + "\n", encoding="utf-8")
        return f'<script{attr} src="{name}"></script>'

    index.write_text(_SCRIPT.sub(replace, index.read_text(encoding="utf-8")),
                     encoding="utf-8")
    return n


def fetch(source: str, sha256: str, cache: Path = PYODIDE_CACHE) -> Path:
    """Eine Datei aus der Ablage — oder einmal laden, mit geprüfter
    Prüfsumme."""
    file = cache / sha256
    if not file.is_file():
        if not source.startswith("https://"):
            raise ValueError(f"Nur über https: {source}")
        cache.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(source, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != sha256:
            raise ValueError(f"Prüfsumme stimmt nicht: {source}")
        file.write_bytes(data)
    elif hashlib.sha256(file.read_bytes()).hexdigest() != sha256:
        raise ValueError(f"Prüfsumme der abgelegten Datei stimmt nicht: {file}")
    return file


def add_fonts(folder: Path, cache: Path = PYODIDE_CACHE) -> int:
    """Die Ersatzschriften dorthin, wo Flutter sie sucht; liefert ihre Zahl."""
    for path, source, sha256 in FONTS:
        target = folder / "assets" / "fonts" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fetch(source, sha256, cache), target)
    return len(FONTS)


def font_findings(folder: Path) -> list[str]:
    return [f"Ersatzschrift fehlt: assets/fonts/{path}"
            for path, _source, _sha in FONTS
            if not (folder / "assets" / "fonts" / path).is_file()]


def pyodide_files(folder: Path,
                  names: tuple[str, ...] = PYODIDE_PACKAGES
                  ) -> list[tuple[str, str]]:
    """(Dateiname, SHA-256) der Pakete und von allem, was sie brauchen —
    aus pyodide/pyodide-lock.json des Web-Ordners."""
    lock = folder / "pyodide" / "pyodide-lock.json"
    try:
        packages = json.loads(lock.read_text(encoding="utf-8"))["packages"]
    except (OSError, ValueError, KeyError) as exc:
        raise ValueError(f"{lock} fehlt oder ist unlesbar") from exc
    todo, seen, files = list(names), set(), []
    while todo:
        name = todo.pop(0)
        if name in seen:
            continue
        seen.add(name)
        if name not in packages:
            raise ValueError(f"Pyodide kennt das Paket „{name}“ nicht ({lock})")
        files.append((str(packages[name]["file_name"]),
                      str(packages[name]["sha256"])))
        todo.extend(packages[name].get("depends") or [])
    return files


def add_pyodide_packages(folder: Path, cache: Path = PYODIDE_CACHE) -> int:
    """Die Pakete neben Pyodide legen; liefert ihre Zahl."""
    files = pyodide_files(folder)
    version = json.loads((folder / "pyodide" / "package.json")
                         .read_text(encoding="utf-8"))["version"]
    for name, sha256 in files:
        target = folder / "pyodide" / name
        if (target.is_file()
                and hashlib.sha256(target.read_bytes()).hexdigest() == sha256):
            continue
        source = PYODIDE_SOURCE.format(version=version, file=name)
        shutil.copyfile(fetch(source, sha256, cache), target)
    return len(files)


def pyodide_findings(folder: Path) -> list[str]:
    try:
        files = pyodide_files(folder)
    except ValueError as exc:
        return [f"Pyodide-Pakete nicht prüfbar: {exc}"]
    found = []
    for name, sha256 in files:
        file = folder / "pyodide" / name
        if not file.is_file():
            found.append(f"Pyodide-Paket fehlt: pyodide/{name}")
        elif hashlib.sha256(file.read_bytes()).hexdigest() != sha256:
            found.append(f"Pyodide-Paket mit falscher Prüfsumme: pyodide/{name}")
    return found


def _git(*args: str) -> str | None:
    """Ausgabe eines git-Befehls — None, wenn er scheitert."""
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                             text=True, check=False)
    except OSError:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def tracked_files() -> set[str] | None:
    """Die versionierten Dateien des Repos — None ohne git."""
    out = _git("ls-files", "-z")
    return None if out is None else {n for n in out.split("\0") if n}


def archive_findings(archive: Path, tracked: set[str] | None) -> list[str]:
    """Liegt im App-Archiv nur, was im Repository steht?

    Außerhalb von __pypackages__/ muss jede Datei versioniert sein (.pyc
    zählt als ihr .py), keine darf requirements*.txt heißen (Punkt 3 im
    Kopf), und kein Name darf mit einem Punkt beginnen (außer .gitkeep).
    Ohne git lässt sich das nicht prüfen — das ist selbst ein Befund.
    """
    if not archive.is_file():
        return [f"{archive} fehlt"]
    with zipfile.ZipFile(archive) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
    own = [n for n in names if not n.startswith("__pypackages__/")]
    foreign, found = [], []
    for name in own:
        base = name.rsplit("/", 1)[-1]
        if base in ARCHIVE_ALLOWED:
            continue
        if re.fullmatch(r"requirements.*\.txt", base):
            found.append(f"{name} liegt im App-Archiv — der Python-Teil der "
                         "Seite startet damit nicht")
            continue
        if any(part.startswith(".") for part in name.split("/")):
            foreign.append(name)
            continue
        if tracked is None:
            continue
        source = name[:-1] if name.endswith(".pyc") else name
        if source not in tracked:
            foreign.append(name)
    if foreign:
        show = ", ".join(foreign[:5]) + (
            f" … und {len(foreign) - 5} weitere" if len(foreign) > 5 else "")
        found.append(f"Im App-Archiv liegen {len(foreign)} Datei(en), die "
                     f"nicht im Repository stehen: {show}")
    if tracked is None:
        found.append("Das App-Archiv ließ sich nicht gegen das Repository "
                     "prüfen (kein git)")
    return found


def _start_page(folder: Path) -> str:
    parts = [folder / "index.html", *sorted(folder.glob("start-*.js"))]
    return "\n".join(p.read_text(encoding="utf-8") for p in parts if p.is_file())


def findings(folder: Path) -> list[str]:
    """Was an einem fertigen Web-Ordner nicht stimmt (leer = in Ordnung)."""
    index = folder / "index.html"
    if not index.is_file():
        return [f"{index} fehlt"]
    found = []
    for m in _SCRIPT.finditer(index.read_text(encoding="utf-8")):
        if "src=" not in m.group("attr") and m.group("body").strip():
            found.append("index.html enthält ein Inline-Skript — eine strenge "
                         "CSP blockiert es")
            break
    text = _start_page(folder)
    if NO_CDN not in text:
        found.append("Die Seite ist nicht mit --no-cdn gebaut")
    if foreign := _FOREIGN.search(text):
        found.append(f"Die Seite nennt eine fremde Adresse: {foreign.group(0)}…")
    if HASH_ROUTES not in text:
        found.append("Die App baut ihre Adressen nicht mit „#“ "
                     "(--route-url-strategy hash)")
    found += pyodide_findings(folder)
    found += font_findings(folder)
    found += archive_findings(folder / APP_ARCHIVE, tracked_files())
    return found


def version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as f:
        return str(tomllib.load(f)["project"]["version"])


def state(base: str, folder: Path) -> dict[str, object]:
    """Woraus dieser Build entstand — das Upload-Skript liest es.

    sauber: keine Änderungen an versionierten Dateien; gepusht: der Commit
    liegt auf einem Zweig des Servers. Nur beides zusammen lässt sich aus
    dem Repository wiederherstellen.
    """
    return {
        "version": version(),
        "commit": _git("rev-parse", "HEAD") or "",
        # Scheitert git, gilt der Stand als nicht sauber — nie umgekehrt.
        "sauber": _git("status", "--porcelain", "--untracked-files=no") == "",
        "gepusht": bool(_git("branch", "-r", "--contains", "HEAD")),
        "basis": base,
        "ohne_cdn": NO_CDN in _start_page(folder)
        and _FOREIGN.search(_start_page(folder)) is None,
        "archiv_geprueft": archive_findings(folder / APP_ARCHIVE,
                                            tracked_files()) == [],
        "gebaut": datetime.datetime.now().astimezone()
        .isoformat(timespec="seconds"),
    }


def finish(folder: Path, base: str) -> dict[str, object]:
    """Punkte 4–6 aus dem Kopf, dann stand.json — und die Prüfung."""
    n = move_inline_scripts(folder)
    k = add_pyodide_packages(folder)
    m = add_fonts(folder)
    values = state(base, folder)
    (folder / "stand.json").write_text(
        json.dumps(values, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(f"Nachbearbeitet: {n} Inline-Skripte ausgelagert, "
          f"{k} Pyodide-Paket(e) und {m} Ersatzschrift(en) eingelegt")
    if found := findings(folder):
        sys.exit("Der Web-Ordner ist nicht in Ordnung:\n  - "
                 + "\n  - ".join(found))
    if not (values["sauber"] and values["gepusht"]):
        print("Hinweis: nicht aus einem sauberen, gepushten Stand gebaut — "
              "nur zum Ausprobieren")
    return values


def flet_command() -> str:
    """Das flet neben diesem Python (venv), sonst das aus dem Suchpfad."""
    beside = Path(sys.executable).parent / "flet"
    return str(beside) if beside.is_file() else "flet"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Web-Fassung der App bauen (statische Seite)")
    parser.add_argument("--basis", required=True,
                        help="Pfad, unter dem die Seite im Browser steht: "
                             "/ (Wurzel, auch lokal) oder /<ordner>/")
    parser.add_argument("--ausgabe", type=Path, default=OUTPUT,
                        help="Zielordner (dist/web)")
    parser.add_argument("--nur-nachbearbeiten", action="store_true",
                        help="nicht bauen: einen vorhandenen Ordner "
                             "nachbearbeiten und prüfen")
    args = parser.parse_args()
    try:
        base = check_base(args.basis)
    except ValueError as exc:
        sys.exit(str(exc))
    output: Path = args.ausgabe.resolve()

    if not args.nur_nachbearbeiten:
        command = [flet_command(), "build", "web", "--no-cdn", "--yes",
                   "--no-rich-output", "--route-url-strategy", "hash",
                   "--base-url", base, "-o", str(output),
                   "--cleanup-app", "--cleanup-app-files", *WEB_CLEANUP,
                   "--exclude", *excludes()]
        print(f"Baue Web-Fassung {version()} für {base}")
        subprocess.run(command, cwd=ROOT, check=True)

    finish(output, base)
    size = sum(f.stat().st_size for f in output.rglob("*") if f.is_file()) / 1e6
    print(f"Fertig: {output} ({size:.0f} MB)")


if __name__ == "__main__":
    main()
