"""Tests für die Notizen-Persistenz und den Aufbau der Notizen-View."""

from types import SimpleNamespace

from mathainoa1.storage.notes import Note, NotesData, load_notes, save_notes


def test_roundtrip_greek(tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    data = NotesData(
        draft="δικηγόρος δικηγόρος δικηγόρος",
        notes=[Note(title="Anwalt üben", text="10× δικηγόρος",
                    created="2026-07-21T10:15:00")],
    )
    save_notes(data)
    loaded = load_notes()
    assert loaded.draft == data.draft
    assert len(loaded.notes) == 1
    assert loaded.notes[0].title == "Anwalt üben"
    assert loaded.notes[0].text == "10× δικηγόρος"
    assert loaded.notes[0].created == "2026-07-21T10:15:00"


def test_missing_file_returns_default(tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    data = load_notes()
    assert data.draft == ""
    assert data.notes == []


def test_corrupt_file_returns_default(tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    (tmp_path / "notes.json").write_text("{kaputt", encoding="utf-8")
    data = load_notes()
    assert data.draft == ""
    assert data.notes == []


def test_unknown_keys_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    (tmp_path / "notes.json").write_text(
        '{"draft": "x", "zukunft": 1,'
        ' "notes": [{"title": "t", "text": "y", "farbe": "rot"}]}',
        encoding="utf-8")
    data = load_notes()
    assert data.draft == "x"
    assert data.notes[0].title == "t"
    assert data.notes[0].created == ""


def test_notes_view_builds(tmp_path, monkeypatch):
    """Headless-Smoke-Test wie in test_views: View baut ohne Fenster."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    save_notes(NotesData(draft="entwurf", notes=[
        Note(title="A", text="a", created="2026-07-21T10:15:00")]))
    from mathainoa1.ui.views.notes import notes_view

    page = SimpleNamespace(
        update=lambda: None, run_task=lambda f: None, services=[],
        show_dialog=lambda d: None, pop_dialog=lambda: None, width=420,
        views=[SimpleNamespace(can_pop=True, on_confirm_pop=None)],
    )
    nav = SimpleNamespace(page=page, stack=[("x", None)],
                          go=lambda t, c: None, back=lambda e=None: None)
    view = notes_view(nav)
    assert view is not None
    # Schreibfeld ganz oben, mit Entwurf vorbelegt und Autofokus
    tf = view.controls[0]
    assert tf.value == "entwurf"
    assert tf.autofocus is True
