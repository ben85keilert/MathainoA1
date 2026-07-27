"""Tests für das Backup: kategorieweiser Export/Import als ZIP."""

import io
import json
import zipfile

import pytest

from mathainoa1.models import SelectionList, VocabCard, VocabList
from mathainoa1.storage import backup
from mathainoa1.storage import textanalyse as ta
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.notes import Note, NotesData, load_notes, save_notes
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.storage.settings import (
    AppSettings,
    app_data_dir,
    book_vocab_dir,
    load_app_settings,
    save_app_settings,
    user_vocab_dir,
)

ALL_PARTS = [k for k, _ in backup.PARTS]


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Echte app_data_dir()-Pfade unter tmp_path — backup.py arbeitet
    direkt auf app_data_dir(), nicht auf beliebigen Store-Pfaden."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    ta.invalidate_cache()
    store = ContentStore(book_vocab_dir(), user_vocab_dir())
    store.load_all()
    progress = ProgressStore(app_data_dir() / "progress.db")
    yield store, progress
    progress.close()
    ta.invalidate_cache()


def _populate(store, progress):
    """Alle Kategorien mit Beispieldaten füllen; gibt die Liste zurück."""
    cards = [VocabCard(front="γράφω", back="schreiben", word_type="Verb"),
             VocabCard(front="το ψωμί", back="Brot", article="το",
                       word_type="Nomen")]
    vlist = VocabList(name="Meine Liste", cards=cards)
    store.save_user_list(vlist)
    store.save_selection(SelectionList(name="Stern", card_ids=[cards[0].id]))
    save_notes(NotesData(draft="Entwurf", notes=[
        Note(title="Merke", text="σ vs ς", created="2026-01-01T10:00:00")]))
    s = AppSettings()
    s.level = "A2"
    s.enabled_features = ["lexikon"]
    save_app_settings(s)
    astore = ta.AnalysisStore(ta.analyses_dir(), store)
    astore.import_analysis(json.dumps({
        "title": "Text", "original_text": "α",
        "vocab": [{"front": "ο σεισμός", "back": "Erdbeben"}]}))
    ta.lexicon_store(store).import_package(json.dumps({
        "title": "P1", "etymology": [{"word": "γράφω", "total": "ritzen"}]}))
    progress.record(cards[0].id, correct=True)
    progress.record(cards[1].id, correct=False)
    return vlist


def test_full_roundtrip(env):
    store, progress = env
    vlist = _populate(store, progress)
    card_id = vlist.cards[0].id
    box_before = progress.get(card_id).box
    data = backup.create_backup(progress, ALL_PARTS)

    # Gerät „verwüsten": Daten löschen/ändern
    store.delete_user_list(vlist.id)
    for sel_id in list(store.selections):
        store.delete_selection(sel_id)
    progress.replace_all([])
    save_notes(NotesData())
    save_app_settings(AppSettings())
    (app_data_dir() / "features" / "lexikon" / "lexikon.json").unlink()

    result = backup.restore_backup(data, store, progress)
    assert set(result["parts"]) == set(ALL_PARTS)
    restored = store.lists[vlist.id]
    assert [c.id for c in restored.cards] == [c.id for c in vlist.cards]
    assert len(store.selections) == 1
    assert progress.get(card_id).box == box_before
    notes = load_notes()
    assert notes.draft == "Entwurf" and notes.notes[0].title == "Merke"
    assert load_app_settings().level == "A2"
    assert ta.lexicon_store(store).entries[0].word == "γράφω"
    # Analyse-Datei wieder da
    assert list(ta.analyses_dir().glob("*.json"))


def test_partial_restore_leaves_other_parts_alone(env):
    store, progress = env
    vlist = _populate(store, progress)
    data = backup.create_backup(progress, ["vocab", "progress"])

    save_notes(NotesData(draft="NEU"))
    s = AppSettings()
    s.level = "A1"
    save_app_settings(s)
    store.delete_user_list(vlist.id)
    progress.replace_all([])

    result = backup.restore_backup(data, store, progress)
    assert result["parts"] == ["vocab", "progress"]
    assert vlist.id in store.lists  # Vokabeln zurück
    assert progress.get(vlist.cards[0].id) is not None
    # Nicht enthaltene Kategorien unangetastet
    assert load_notes().draft == "NEU"
    assert load_app_settings().level == "A1"


def test_settings_only_backup(env):
    store, progress = env
    vlist = _populate(store, progress)
    data = backup.create_backup(progress, ["settings"])
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
    assert all(n == backup.MANIFEST_NAME or n in backup._PART_FILES["settings"]
               for n in names)
    backup.restore_backup(data, store, progress)
    assert vlist.id in store.lists  # Vokabeln blieben unangetastet


def test_progress_requires_vocab(env):
    _store, progress = env
    with pytest.raises(ValueError, match="Vokabeln"):
        backup.create_backup(progress, ["progress"])
    with pytest.raises(ValueError, match="Kategorie"):
        backup.create_backup(progress, [])


def test_manifest_progress_without_vocab_rejected(env):
    store, progress = env
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(backup.MANIFEST_NAME, json.dumps({
            "backup_schema": backup.BACKUP_SCHEMA, "parts": ["progress"]}))
        zf.writestr(backup.PROGRESS_NAME, "[]")
    with pytest.raises(ValueError, match="Vokabeln"):
        backup.restore_backup(buf.getvalue(), store, progress)


def test_excludes_tts_and_tmp(env):
    store, progress = env
    _populate(store, progress)
    tts = app_data_dir() / "tts"
    tts.mkdir()
    (tts / "abc.mp3").write_bytes(b"mp3")
    (user_vocab_dir() / "kaputt.tmp").write_text("x", encoding="utf-8")
    data = backup.create_backup(progress, ALL_PARTS)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
    assert not any(n.startswith("tts/") or n.endswith(".tmp") for n in names)


def test_invalid_backups_leave_data_untouched(env):
    store, progress = env
    vlist = _populate(store, progress)

    with pytest.raises(ValueError, match="ZIP"):
        backup.restore_backup(b"kein zip", store, progress)

    buf = io.BytesIO()  # ZIP ohne Manifest
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("vocab/x.json", "{}")
    with pytest.raises(ValueError, match="manifest"):
        backup.restore_backup(buf.getvalue(), store, progress)

    def evil_zip(member: str) -> bytes:
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as zf:
            zf.writestr(backup.MANIFEST_NAME, json.dumps({
                "backup_schema": backup.BACKUP_SCHEMA, "parts": ["vocab"]}))
            zf.writestr(member, "{}")
        return b.getvalue()

    with pytest.raises(ValueError, match="Unzulässiger Pfad"):
        backup.restore_backup(evil_zip("vocab/../../evil.json"),
                              store, progress)
    with pytest.raises(ValueError, match="Unerwartete Datei"):
        backup.restore_backup(evil_zip("hack.json"), store, progress)
    with pytest.raises(ValueError, match="Unerwartete Datei"):
        # Kategorie nicht im Manifest deklariert
        backup.restore_backup(evil_zip("notes.json"), store, progress)

    # Gerätedaten unangetastet
    store.load_all()
    assert vlist.id in store.lists
    assert progress.get(vlist.cards[0].id) is not None


def test_unknown_schema_rejected(env):
    store, progress = env
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(backup.MANIFEST_NAME, json.dumps({
            "backup_schema": 99, "parts": ["notes"]}))
    with pytest.raises(ValueError, match="Format"):
        backup.restore_backup(buf.getvalue(), store, progress)


def test_progress_replace_all_roundtrip(env):
    _store, progress = env
    progress.record("abc123", correct=True)
    progress.record("def456", correct=False)
    rows = progress.export_rows()
    progress.replace_all([])
    assert progress.get("abc123") is None
    assert progress.replace_all(rows) == 2
    p = progress.get("abc123")
    assert p is not None and p.box == 2 and p.correct == 1


def test_restore_after_full_wipe_new_device(env, tmp_path):
    """Ernstfall Gerätewechsel: leeres app_data_dir → Restore."""
    store, progress = env
    vlist = _populate(store, progress)
    data = backup.create_backup(progress, ALL_PARTS)

    # „Neues Gerät": alle Nutzerdateien weg, DB leer
    import shutil
    shutil.rmtree(user_vocab_dir())
    shutil.rmtree(app_data_dir() / "features")
    (app_data_dir() / "notes.json").unlink()
    progress.replace_all([])
    store.load_all()
    assert not store.lists

    backup.restore_backup(data, store, progress)
    assert vlist.id in store.lists
    assert load_notes().notes
    assert ta.lexicon_store(store).entries
    assert progress.get(vlist.cards[0].id) is not None


def test_create_backup_survives_pre_1980_mtimes(env):
    """Android-Bug: Datei-mtimes vor 1980 dürfen den Export nicht brechen
    (fester ZIP-Zeitstempel statt Datei-Datum)."""
    import os

    store, progress = env
    vlist = _populate(store, progress)
    for p in user_vocab_dir().rglob("*.json"):
        os.utime(p, (0, 0))  # Epoche 1970 — vor der ZIP-Untergrenze 1980
    data = backup.create_backup(progress, ALL_PARTS)

    store.delete_user_list(vlist.id)
    backup.restore_backup(data, store, progress)
    assert vlist.id in store.lists
