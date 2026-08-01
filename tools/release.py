#!/usr/bin/env python3
"""Release auf Knopfdruck: Version setzen, committen, taggen, pushen.

    python tools/release.py 0.8.2

Setzt die Version in pyproject.toml und src/mathainoa1/__init__.py,
committet als "Version 0.8.2", taggt v0.8.2 und pusht beides — die CI
(.github/workflows/release.yml) baut daraus APK + AAB und legt das
GitHub-Release an, das der In-App-Update-Check findet.

Sicherheitsnetz: läuft nur auf main mit sauberem Arbeitsverzeichnis,
die neue Version muss größer als die bisherige sein, der Tag darf noch
nicht existieren.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Datei -> Muster der Versionszeile (Gruppen: Präfix, Version, Suffix)
VERSION_LINES = {
    ROOT / "pyproject.toml": r'^(version = ")([^"]+)(")',
    ROOT / "src" / "mathainoa1" / "__init__.py":
        r'^(__version__ = ")([^"]+)(")',
}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def as_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in version.split("."))


def main() -> int:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        print(__doc__)
        return 2
    new = sys.argv[1]

    if git("status", "--porcelain"):
        print("Arbeitsverzeichnis nicht sauber — bitte erst committen "
              "oder stashen (git status).")
        return 1
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        print(f"Bitte von main aus releasen (aktuell: {branch}).")
        return 1
    if f"v{new}" in git("tag", "--list", f"v{new}"):
        print(f"Tag v{new} existiert schon.")
        return 1

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(VERSION_LINES[ROOT / "pyproject.toml"], pyproject, re.M)
    if not m:
        print("Versionszeile in pyproject.toml nicht gefunden.")
        return 1
    old = m.group(2)
    if as_tuple(new) <= as_tuple(old):
        print(f"Neue Version {new} muss größer sein als bisherige {old}.")
        return 1

    for path, pattern in VERSION_LINES.items():
        text = path.read_text(encoding="utf-8")
        new_text, count = re.subn(
            pattern, lambda mm: mm.group(1) + new + mm.group(3),
            text, count=1, flags=re.M)
        if count != 1:
            print(f"Versionszeile in {path.name} nicht gefunden.")
            return 1
        path.write_text(new_text, encoding="utf-8")

    git("commit", "-am", f"Version {new}")
    # Annotierter Tag + expliziter Push: "--follow-tags" würde
    # leichtgewichtige Tags stillschweigend NICHT mitpushen
    git("tag", "-a", f"v{new}", "-m", f"Version {new}")
    git("push", "origin", "main", f"v{new}")
    print(f"{old} -> {new}: getaggt und gepusht. Die CI baut jetzt — "
          "Fortschritt: https://github.com/ben85keilert/MathainoA1/actions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
