import io
import zipfile

import pytest

from mathainoa1.storage.audio import AudioStore


def make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_path_for_and_has_audio(tmp_path):
    store = AudioStore(tmp_path)
    assert store.path_for("abc") is None
    assert not store.has_audio("abc")
    for i, ext in enumerate((".mp3", ".m4a", ".ogg", ".wav")):
        (tmp_path / f"id{i}{ext}").write_bytes(b"x")
        assert store.path_for(f"id{i}") == tmp_path / f"id{i}{ext}"
        assert store.has_audio(f"id{i}")


def test_existing_and_missing_ids(tmp_path):
    store = AudioStore(tmp_path)
    # Verzeichnis existiert noch nicht — kein Fehler
    assert store.existing_ids() == set()
    assert store.missing_ids(["a", "b"]) == ["a", "b"]
    (tmp_path / "a.mp3").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")  # kein Audio, zählt nicht
    assert store.existing_ids() == {"a"}
    assert store.missing_ids(["a", "b"]) == ["b"]


def test_import_zip_matching(tmp_path):
    store = AudioStore(tmp_path / "audio")
    data = make_zip({
        "id1.mp3": b"eins",
        "ordner/id2.mp3": b"zwei",       # Wrapper-Ordner: Basename zählt
        "fremd.mp3": b"drei",            # keine passende Karte
        ".DS_Store": b"junk",            # versteckt -> übersprungen
        "liesmich.txt": b"text",         # keine Audio-Endung
    })
    report = store.import_zip(data, known_ids={"id1", "id2"})
    assert sorted(report.imported) == ["id1", "id2"]
    assert report.unmatched == ["fremd.mp3"]
    assert sorted(report.skipped) == [".DS_Store", "liesmich.txt"]
    assert (tmp_path / "audio" / "id1.mp3").read_bytes() == b"eins"
    assert (tmp_path / "audio" / "id2.mp3").read_bytes() == b"zwei"
    assert not (tmp_path / "audio" / "fremd.mp3").exists()


def test_import_zip_replaces_other_extension(tmp_path):
    store = AudioStore(tmp_path)
    store.import_zip(make_zip({"id1.mp3": b"alt"}), known_ids={"id1"})
    store.import_zip(make_zip({"id1.ogg": b"neu"}), known_ids={"id1"})
    # kein id1.mp3 + id1.ogg nebeneinander
    assert not (tmp_path / "id1.mp3").exists()
    assert (tmp_path / "id1.ogg").read_bytes() == b"neu"
    assert store.path_for("id1") == tmp_path / "id1.ogg"


def test_import_zip_bad_data(tmp_path):
    store = AudioStore(tmp_path)
    with pytest.raises(zipfile.BadZipFile):
        store.import_zip(b"kein zip", known_ids=set())
