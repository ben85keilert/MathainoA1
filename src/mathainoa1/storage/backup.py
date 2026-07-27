"""Backup: Export/Import der Nutzerdaten als eine ZIP-Datei.

Kategorieweise wählbar (PARTS): Vokabeln, Lernfortschritt, Notizen,
Textanalysen, Lexikon, Einstellungen. Der Lernfortschritt referenziert
Karten-IDs und ist deshalb nur zusammen mit den Vokabeln erlaubt.

Aufbau der ZIP: die Original-Dateien relativ zu app_data_dir() (z.B.
vocab/<id>.json), dazu generiert manifest.json (Schema, Kategorien,
Zähler) und progress.json (Lernstand als Zeilen — die SQLite-Datei wird
nie kopiert, weil die App eine offene Verbindung hält; siehe
ProgressStore.export_rows/replace_all). manifest.json liegt im
ZIP-Wurzelverzeichnis und wird beim Restore nie nach vocab/ geschrieben —
ContentStore.load_all würde dort jede fremde Datei als Liste parsen.

Restore ersetzt genau die im Manifest genannten Kategorien und lässt
alles andere unangetastet. Es wird erst vollständig validiert (Schema,
Kategorien, Pfad-Whitelist, Zip-Slip-Abwehr), dann gelöscht/geschrieben.
"""

from __future__ import annotations

import datetime
import io
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Iterator

from mathainoa1.storage import textanalyse
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.storage.settings import app_data_dir

BACKUP_SCHEMA = 1
MANIFEST_NAME = "manifest.json"
PROGRESS_NAME = "progress.json"

# Kategorien in Anzeige-Reihenfolge: (Schlüssel, deutsches Label)
PARTS: list[tuple[str, str]] = [
    ("vocab", "Vokabeln & Auswahllisten"),
    ("progress", "Lernfortschritt"),
    ("notes", "Notizen"),
    ("textanalyse", "Textanalysen"),
    ("lexikon", "Lexikon"),
    ("settings", "Einstellungen"),
]

# Pfad-Whitelist je Kategorie, relativ zu app_data_dir()
_PART_DIRS = {
    "vocab": ("vocab/",),
    "textanalyse": ("features/textanalyse/",),
    "lexikon": ("features/lexikon/",),
}
_PART_FILES = {
    "notes": ("notes.json",),
    "settings": ("app_settings.json", "training_settings.json",
                 "declension_settings.json", "conjugation_settings.json"),
}


def part_label(key: str) -> str:
    return next((label for k, label in PARTS if k == key), key)


def suggested_filename() -> str:
    return f"mathaino-backup-{datetime.date.today().isoformat()}.zip"


def _app_version() -> str:
    try:
        from importlib.metadata import version
        return version("mathainoa1")
    except Exception:
        return ""


def _iter_part_files(base: Path, part: str) -> Iterator[str]:
    """Vorhandene Dateien einer Kategorie als POSIX-Pfade relativ zu base
    (transiente *.tmp-Dateien ausgenommen)."""
    for prefix in _PART_DIRS.get(part, ()):
        directory = base / prefix
        if not directory.exists():
            continue
        for p in sorted(directory.rglob("*")):
            if p.is_file() and p.suffix != ".tmp":
                yield p.relative_to(base).as_posix()
    for name in _PART_FILES.get(part, ()):
        if (base / name).is_file():
            yield name


def _member_part(name: str) -> str | None:
    """Zu welcher Kategorie gehört ein ZIP-Member? None = fremd."""
    if name == PROGRESS_NAME:
        return "progress"
    for part, prefixes in _PART_DIRS.items():
        if any(name.startswith(p) for p in prefixes):
            return part
    for part, files in _PART_FILES.items():
        if name in files:
            return part
    return None


def _unsafe_path(name: str) -> bool:
    if name.startswith("/") or "\\" in name or ":" in name:
        return True
    return ".." in PurePosixPath(name).parts


def _validate_parts(parts: list[str]) -> list[str]:
    known = [k for k, _ in PARTS]
    chosen = [k for k in known if k in parts]  # feste Reihenfolge
    if not chosen:
        raise ValueError("Bitte mindestens eine Kategorie wählen.")
    if "progress" in chosen and "vocab" not in chosen:
        raise ValueError("Der Lernfortschritt gehört zu den Karten-IDs der "
                         "Vokabeln — er kann nur zusammen mit "
                         "„Vokabeln & Auswahllisten“ gesichert werden.")
    return chosen


def create_backup(progress: ProgressStore, parts: list[str]) -> bytes:
    chosen = _validate_parts(parts)
    base = app_data_dir()
    counts: dict[str, int] = {}
    buf = io.BytesIO()

    def writestr(name: str, data) -> None:
        # Fester Zeitstempel statt Datei-mtime: Android liefert teils
        # mtimes vor 1980, an denen zipfile mit "ZIP does not support
        # timestamps before 1980" scheitert. Der Inhalt zählt, nicht
        # das Datum (das steht im Manifest).
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for part in chosen:
            if part == "progress":
                rows = progress.export_rows()
                writestr(PROGRESS_NAME,
                         json.dumps(rows, ensure_ascii=False, indent=1))
                counts[part] = len(rows)
                continue
            n = 0
            for rel in _iter_part_files(base, part):
                writestr(rel, (base / rel).read_bytes())
                n += 1
            counts[part] = n
        manifest = {
            "backup_schema": BACKUP_SCHEMA,
            "app_version": _app_version(),
            "created": datetime.date.today().isoformat(),
            "parts": chosen,
            "counts": counts,
        }
        writestr(MANIFEST_NAME,
                 json.dumps(manifest, ensure_ascii=False, indent=2))
    return buf.getvalue()


def read_manifest(data: bytes) -> dict:
    """Manifest einer Backup-Datei lesen und grundvalidieren — für den
    Warn-Dialog vor dem Restore. ValueError mit deutscher Meldung."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError("Das ist keine gültige Backup-Datei "
                         "(ZIP erwartet).") from exc
    with zf:
        if MANIFEST_NAME not in zf.namelist():
            raise ValueError("In der Datei fehlt das manifest.json — "
                             "kein Mathaino-Backup?")
        try:
            manifest = json.loads(zf.read(MANIFEST_NAME).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Das manifest.json im Backup ist nicht "
                             "lesbar.") from exc
    if (not isinstance(manifest, dict)
            or manifest.get("backup_schema") != BACKUP_SCHEMA):
        raise ValueError("Unbekanntes Backup-Format — die Datei stammt "
                         "aus einer neueren App-Version?")
    known = [k for k, _ in PARTS]
    parts = manifest.get("parts")
    if (not isinstance(parts, list) or not parts
            or any(p not in known for p in parts)):
        raise ValueError("Das Backup nennt unbekannte Kategorien.")
    if "progress" in parts and "vocab" not in parts:
        raise ValueError("Das Backup enthält Lernfortschritt ohne "
                         "Vokabeln — inkonsistente Datei.")
    return manifest


def restore_backup(data: bytes, store: ContentStore,
                   progress: ProgressStore) -> dict:
    """Ersetzt die im Backup enthaltenen Kategorien auf diesem Gerät.

    Rückgabe: {"parts": [...], "counts": {kategorie: anzahl}}.
    """
    manifest = read_manifest(data)
    parts = _validate_parts(manifest["parts"])
    base = app_data_dir()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = [n for n in zf.namelist()
                 if n != MANIFEST_NAME and not n.endswith("/")]
        # Erst komplett validieren, dann löschen
        for name in names:
            if _unsafe_path(name):
                raise ValueError(f"Unzulässiger Pfad im Backup: {name}")
            part = _member_part(name)
            if part is None or part not in parts:
                raise ValueError(f"Unerwartete Datei im Backup: {name}")
        rows: list = []
        if "progress" in parts:
            if PROGRESS_NAME not in names:
                raise ValueError("Im Backup fehlt das progress.json.")
            try:
                rows = json.loads(zf.read(PROGRESS_NAME).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError("Das progress.json im Backup ist nicht "
                                 "lesbar.") from exc
            if not isinstance(rows, list):
                raise ValueError("Das progress.json im Backup hat ein "
                                 "unerwartetes Format.")
        counts: dict[str, int] = {}
        for part in parts:
            if part == "progress":
                counts[part] = progress.replace_all(
                    [r for r in rows if isinstance(r, dict)])
                continue
            for rel in list(_iter_part_files(base, part)):
                (base / rel).unlink(missing_ok=True)
            n = 0
            for name in names:
                if name == PROGRESS_NAME or _member_part(name) != part:
                    continue
                target = base / PurePosixPath(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))
                n += 1
            counts[part] = n
    store.load_all()
    textanalyse.invalidate_cache()
    return {"parts": parts, "counts": counts}
