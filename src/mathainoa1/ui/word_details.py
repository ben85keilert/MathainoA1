"""Kombinierter Wortinfo-Button: Beugungsformen + Lexikoneintrag.

Ein Symbol mit drei Zuständen — beides vorhanden → ⓘ, nur Beugung →
Tabellensymbol, nur Lexikon → Buchsymbol. Wird von Trainern, Wortlisten,
Wortsuche, Ergebnis- und Statistikansichten geteilt. Liegt bewusst in
ui/ (nicht ui/views/), damit wordlist/manager/grammar es ohne
Import-Zirkel nutzen können; die Textanalyse-Dialoge bleiben
Lazy-Imports (Feature-Modul).
"""

from __future__ import annotations

import flet as ft

from mathainoa1.storage.textanalyse import etymology_for
from mathainoa1.ui.scale import sz
from mathainoa1.ui.views.reference import (
    has_word_forms_fast,
    show_word_forms,
    word_forms_content,
)


def update_word_details_button(btn: ft.IconButton, forms: bool,
                               info: bool) -> None:
    """Ein Symbol für Wort-Info und Beugungsformen — je nach Verfügbarkeit:
    beides → Info-Symbol, nur Beugung → Tabellensymbol (wie Nomen-/
    Verbtraining), nur Lexikoneintrag → Buchsymbol des Lexikons."""
    btn.visible = forms or info
    if forms and info:
        btn.icon = ft.Icons.INFO_OUTLINE
        btn.tooltip = "Wort-Info & Beugungsformen"
    elif forms:
        btn.icon = ft.Icons.TABLE_CHART_OUTLINED
        btn.tooltip = "Beugungsformen anzeigen"
    elif info:
        btn.icon = ft.Icons.MENU_BOOK_OUTLINED
        btn.tooltip = "Wortherkunft & Synonyme"


def show_word_details(page: ft.Page, card, with_forms: bool = True) -> None:
    """Wort-Info und/oder Beugungsformen als Dialog — gibt es beides,
    steht die Beugungstabelle unter dem Lexikoneintrag, getrennt durch
    einen Querbalken. with_forms=False, solange die Tabelle die Lösung
    verraten würde (deutsche Vorgabe vor dem Aufdecken)."""
    entry = etymology_for(card)
    forms = word_forms_content(card) if with_forms else None
    if forms is None and entry is None:
        return
    if entry is None:
        show_word_forms(page, card)
        return
    if forms is None:
        # Lazy-Import: das Feature-Modul nur laden, wenn es gebraucht wird
        from mathainoa1.ui.views.textanalyse import etymology_dialog
        etymology_dialog(page, entry)
        return
    from mathainoa1.ui.views.textanalyse import render_etymology
    w = getattr(page, "width", None) or 420
    h = getattr(page, "height", None) or 700
    page.show_dialog(ft.AlertDialog(
        title=ft.Text(card.with_plural(card.front), size=sz(16)),
        inset_padding=ft.Padding.all(12),
        content=ft.Column(
            render_etymology(entry, with_title=False)
            + [ft.Divider(thickness=2),
               ft.Text("Beugungsformen", size=sz(16), weight=ft.FontWeight.BOLD),
               forms],
            scroll=ft.ScrollMode.AUTO, width=w, height=h - 180,
        ),
        actions=[ft.TextButton("Schließen",
                               on_click=lambda e: page.pop_dialog())],
    ))


def word_details_button(card, *, icon_size: int | None = None,
                        ) -> ft.IconButton | None:
    """Fertiger kombinierter Button für Listenzeilen — None, wenn es
    weder Beugungsformen noch einen Lexikoneintrag gibt (dann gar kein
    Symbol anbieten). Öffnet show_word_details über die Seite des
    geklickten Controls."""
    forms = has_word_forms_fast(card)
    info = etymology_for(card) is not None
    if not (forms or info):
        return None
    btn = ft.IconButton(
        on_click=lambda e: show_word_details(e.control.page, card))
    if icon_size is not None:
        btn.icon_size = sz(icon_size)
    update_word_details_button(btn, forms, info)
    return btn
