"""Tests für das Bau-Skript der Web-Fassung (tools/web_build.py) — die
Prüfungen, nicht der Build selbst."""

import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import web_build as wb  # noqa: E402


def archive(tmp_path, names):
    path = tmp_path / "app.zip"
    with zipfile.ZipFile(path, "w") as z:
        for name in names:
            z.writestr(name, "x")
    return path


TRACKED = {"main.py", "pyproject.toml", "src/mathainoa1/web.py"}


def test_archiv_mit_versionierten_dateien_ist_in_ordnung(tmp_path):
    a = archive(tmp_path, ["main.py", "src/mathainoa1/web.py",
                           "data/vocab/.gitkeep",
                           "__pypackages__/flet/x.py"])
    assert wb.archive_findings(a, TRACKED) == []


def test_archiv_meldet_notizen_dieses_rechners(tmp_path):
    a = archive(tmp_path, ["main.py", "temp.md"])
    found = wb.archive_findings(a, TRACKED)
    assert len(found) == 1 and "temp.md" in found[0]


def test_archiv_meldet_requirements(tmp_path):
    """requirements.txt im Archiv: Der Python-Teil der Seite startet nicht
    (Probe vom 25.11.2026)."""
    a = archive(tmp_path, ["main.py", "requirements.txt"])
    assert any("requirements.txt" in f for f in wb.archive_findings(a, TRACKED))


def test_archiv_meldet_punktdateien_und_fehlendes_git(tmp_path):
    a = archive(tmp_path, ["main.py", ".env"])
    assert any(".env" in f for f in wb.archive_findings(a, TRACKED))
    assert any("kein git" in f
               for f in wb.archive_findings(archive(tmp_path, ["main.py"]),
                                            None))
    assert wb.archive_findings(tmp_path / "fehlt.zip", TRACKED)


def test_basisadresse():
    assert wb.check_base("/") == "/"
    assert wb.check_base("/app/AbC-1_x/") == "/app/AbC-1_x/"
    for bad in ("app/x", "/app", "https://x/", "/a b/"):
        with pytest.raises(ValueError):
            wb.check_base(bad)


def test_inline_skripte_werden_ausgelagert(tmp_path):
    (tmp_path / "index.html").write_text(
        '<head><script>var a = 1;</script><script src="python.js"></script>'
        '<script id="s">function f() {}</script></head>', encoding="utf-8")
    assert wb.move_inline_scripts(tmp_path) == 2
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "var a" not in html and 'src="start-1.js"' in html
    assert '<script id="s" src="start-2.js">' in html
    assert (tmp_path / "start-1.js").read_text(encoding="utf-8") == "var a = 1;\n"


def test_ausschluesse_enthalten_die_der_app_und_requirements():
    ex = wb.excludes()
    assert {"private", "tests", "tools", "requirements.txt"} <= set(ex)
    # exakte Pfade, keine Muster — Muster stehen in WEB_CLEANUP
    assert not any("*" in e for e in wb.WEB_EXCLUDE)


def test_pyodide_pakete_samt_abhaengigkeiten(tmp_path):
    (tmp_path / "pyodide").mkdir()
    (tmp_path / "pyodide" / "pyodide-lock.json").write_text(json.dumps(
        {"packages": {
            "sqlite3": {"file_name": "sqlite3.whl", "sha256": "a", "depends": []},
            "cryptography": {"file_name": "cryptography.whl", "sha256": "b",
                        "depends": ["openssl"]},
            "openssl": {"file_name": "openssl.zip", "sha256": "c", "depends": []},
        }}), encoding="utf-8")
    assert wb.pyodide_files(tmp_path) == [("sqlite3.whl", "a"),
                                          ("cryptography.whl", "b"),
                                          ("openssl.zip", "c")]
    assert len(wb.pyodide_findings(tmp_path)) == 3  # noch nicht eingelegt
    with pytest.raises(ValueError):
        wb.pyodide_files(tmp_path, ("gibtsnicht",))


def test_web_abhaengigkeiten_stehen_in_pyproject():
    """Ohne den Eintrag lädt die Seite sqlite3 nicht und startet nicht."""
    import tomllib
    with (wb.ROOT / "pyproject.toml").open("rb") as f:
        deps = tomllib.load(f)["tool"]["flet"]["web"]["dependencies"]
    assert "sqlite3" in deps
    # Was die Seite beim Start lädt, muss neben Pyodide liegen — sonst käme
    # es von einem fremden Server oder gar nicht
    assert set(deps) <= set(wb.PYODIDE_PACKAGES)


def test_ersatzschriften_werden_eingelegt_und_vermisst(tmp_path):
    """Ohne die Schrift fragt Flutter sie in Dauerschleife an (Zeichen „→“)."""
    import hashlib
    assert len(wb.font_findings(tmp_path)) == len(wb.FONTS) >= 1
    cache = tmp_path / "cache"
    cache.mkdir()
    fake = []
    for path, source, _sha in wb.FONTS:
        data = path.encode()
        sha = hashlib.sha256(data).hexdigest()
        (cache / sha).write_bytes(data)
        fake.append((path, source, sha))
    old, wb.FONTS = wb.FONTS, tuple(fake)
    try:
        assert wb.add_fonts(tmp_path, cache) == len(fake)
        assert wb.font_findings(tmp_path) == []
    finally:
        wb.FONTS = old
    for _path, source, sha in wb.FONTS:
        assert source.startswith("https://") and len(sha) == 64
