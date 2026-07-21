"""Notizen: Schreibfeld zum Kritzeln/Tippüben plus gespeicherte Einträge.

Der Entwurf wird bei jedem Tastendruck auf Platte gesichert und überlebt
so Zurück-Navigation und App-Neustart; Speichern-Dialog vergibt eine
Pflicht-Überschrift und legt den Text als Eintrag unter dem Feld ab.
"""

from __future__ import annotations

import flet as ft

from mathainoa1.storage.notes import Note, load_notes, now_iso, save_notes


def _save_note_dialog(page: ft.Page, data, tf_draft: ft.TextField,
                      on_saved) -> None:
    """Fragt die Überschrift ab und archiviert den Schreibfeld-Inhalt."""
    tf_title = ft.TextField(label="Überschrift", autofocus=True)

    def save(e):
        title = (tf_title.value or "").strip()
        if not title:
            tf_title.error_text = "Überschrift darf nicht leer sein."
            page.update()
            return
        data.notes.insert(0, Note(title=title, text=tf_draft.value or "",
                                  created=now_iso()))
        data.draft = ""
        save_notes(data)
        tf_draft.value = ""
        page.pop_dialog()
        on_saved()
        tf_draft.focus()

    tf_title.on_submit = save
    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Notiz speichern"),
        content=tf_title,
        actions=[ft.TextButton("Abbrechen", on_click=lambda e: page.pop_dialog()),
                 ft.FilledButton("Speichern", on_click=save)],
    ))


def _edit_note_dialog(page: ft.Page, data, note: Note, on_saved) -> None:
    """Überschrift und Text einer gespeicherten Notiz nachträglich ändern."""
    tf_title = ft.TextField(label="Überschrift", value=note.title)
    tf_text = ft.TextField(label="Text", value=note.text,
                           multiline=True, min_lines=4, max_lines=10)

    def save(e):
        title = (tf_title.value or "").strip()
        if not title:
            tf_title.error_text = "Überschrift darf nicht leer sein."
            page.update()
            return
        note.title = title
        note.text = tf_text.value or ""
        save_notes(data)
        page.pop_dialog()
        on_saved()

    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Notiz bearbeiten"),
        content=ft.Column([tf_title, tf_text], tight=True, spacing=12,
                          width=400, scroll=ft.ScrollMode.AUTO),
        actions=[ft.TextButton("Abbrechen", on_click=lambda e: page.pop_dialog()),
                 ft.FilledButton("Speichern", on_click=save)],
    ))


def _confirm_delete_dialog(page: ft.Page, data, note: Note,
                           on_deleted) -> None:
    def delete(e):
        if note in data.notes:
            data.notes.remove(note)
            save_notes(data)
        page.pop_dialog()
        on_deleted()

    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Wirklich alles löschen?"),
        content=ft.Text(f"Notiz „{note.title}“ wird endgültig gelöscht."),
        actions=[ft.TextButton("Abbrechen", on_click=lambda e: page.pop_dialog()),
                 ft.FilledButton("Löschen", on_click=delete)],
    ))


def _short_date(created: str) -> str:
    # "2026-07-21T10:15:00" -> "21.07.2026"
    try:
        y, m, d = created[:10].split("-")
        return f"{d}.{m}.{y}"
    except ValueError:
        return created


def notes_view(nav) -> ft.Control:
    page = nav.page
    data = load_notes()

    tf = ft.TextField(
        label="Schreibfeld",
        value=data.draft,
        multiline=True,
        min_lines=6,
        max_lines=10,
        autofocus=True,
    )

    def on_draft_change(e):
        data.draft = tf.value or ""
        save_notes(data)

    tf.on_change = on_draft_change

    notes_header = ft.Text("Gespeicherte Notizen", size=16,
                           weight=ft.FontWeight.BOLD, visible=False)
    notes_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

    def note_tile(note: Note) -> ft.Control:
        return ft.Container(
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=8,
            padding=8,
            content=ft.Column([
                ft.Row([
                    ft.Text(note.title, weight=ft.FontWeight.BOLD, expand=True),
                    ft.Text(_short_date(note.created), size=12,
                            color=ft.Colors.OUTLINE),
                    ft.IconButton(
                        ft.Icons.EDIT_OUTLINED, tooltip="Notiz bearbeiten",
                        on_click=lambda e, n=note: _edit_note_dialog(
                            page, data, n, refresh),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE, tooltip="Notiz löschen",
                        on_click=lambda e, n=note: _confirm_delete_dialog(
                            page, data, n, refresh),
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(note.text, size=14, selectable=True),
            ], spacing=4),
        )

    def refresh():
        notes_header.visible = bool(data.notes)
        notes_col.controls = [note_tile(n) for n in data.notes]
        page.update()

    def clear_field(e):
        # bewusst ohne Rückfrage: Leeren gehört zum Tippüben-Workflow
        tf.value = ""
        data.draft = ""
        save_notes(data)
        page.update()
        tf.focus()

    def save_note(e):
        if not (tf.value or "").strip():
            page.show_dialog(ft.SnackBar(ft.Text("Nichts zu speichern.")))
            return
        _save_note_dialog(page, data, tf, refresh)

    buttons = ft.Row([
        ft.OutlinedButton("Leeren", icon=ft.Icons.BACKSPACE_OUTLINED,
                          on_click=clear_field),
        ft.FilledButton("Speichern", icon=ft.Icons.SAVE, on_click=save_note),
    ], spacing=8)

    # Erstbefüllung ohne page.update() (View ist noch nicht auf der Seite)
    notes_header.visible = bool(data.notes)
    notes_col.controls = [note_tile(n) for n in data.notes]

    return ft.Column(
        [tf, buttons, notes_header, notes_col],
        spacing=8,
        expand=True,
    )
