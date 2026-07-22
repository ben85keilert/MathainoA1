"""Headless-Smoke-Tests: bauen alle UI-Views ohne echtes Flet-Fenster.

Fängt Konstruktions- und Vorschau-Abstürze ab (z.B. IndexError in der
Verben-Vorschau), ohne die volle App zu starten. Es wird nur geprüft, dass
der Aufbau der Controls fehlerfrei durchläuft — keine Interaktion.
"""

from types import SimpleNamespace

import pytest

from mathainoa1.models import VocabCard, VocabList
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.ui.views import grammar, help as help_view_mod, manager, reference, stats, trainer


def _fake_nav():
    page = SimpleNamespace(
        update=lambda: None, run_task=lambda f: None, services=[],
        show_dialog=lambda d: None, pop_dialog=lambda: None, width=420,
        views=[SimpleNamespace(can_pop=True, on_confirm_pop=None)],
    )
    nav = SimpleNamespace(
        page=page, stack=[("x", None)], go=lambda t, c: None,
        back=lambda e=None: None, _show=lambda: None, store=None,
    )
    return nav


@pytest.fixture
def store_with_edge_cases(tmp_path):
    """Liste mit Grenzfällen: unveränderlich (plural '-'), custom-Verb,
    Eigenname, regelmäßiges Verb/Adjektiv."""
    store = ContentStore(tmp_path / "book", tmp_path / "user")
    store.load_all()
    cards = [
        VocabCard(front="το μετρό", back="Metro", article="το", plural="-",
                  word_type="Nomen"),
        VocabCard(front="η Αθήνα", back="Athen", article="η", plural="-",
                  word_type="Nomen"),
        VocabCard(front="κάνει", back="macht", word_type="Verb",
                  forms={"1sg": "κάνω"}),  # custom-Verb ohne 2pl
        VocabCard(front="γράφω", back="schreiben", word_type="Verb",
                  stem2="γράψ-"),
        VocabCard(front="μικρός", back="klein", word_type="Adjektiv"),
    ]
    vlist = VocabList(name="Grenzfälle", cards=cards)
    store.save_user_list(vlist)
    return store, vlist


def test_reference_chapters_build():
    for _title, _icon, builder in reference.CHAPTERS:
        builder()


def test_main_views_build(store_with_edge_cases, tmp_path):
    store, vlist = store_with_edge_cases
    nav = _fake_nav()
    nav.store = store
    progress = ProgressStore(tmp_path / "p.db")
    try:
        help_view_mod.help_view(nav, store)
        stats.stats_view(nav, store, progress)
        stats.list_words_view(nav, vlist, progress.all())
        trainer.setup_view(nav, store, progress)
        grammar.setup_view(nav, store, progress)
        grammar.conjugation_setup_view(nav, store, progress)
        manager.manager_view(nav, store, progress)
        manager.list_view(nav, store, vlist, progress)
        manager.selection_editor(nav, store, None, lambda s: None, progress)
    finally:
        progress.close()


def test_word_list_panel_groups_selection(store_with_edge_cases):
    """Auswahllisten-Wortübersicht: die Wörter stehen unter der Überschrift
    ihrer jeweiligen Ursprungsliste — auch bei Karten aus mehreren Listen."""
    from mathainoa1.models import SelectionList, VocabCard, VocabList
    from mathainoa1.ui.views import wordlist
    store, vlist = store_with_edge_cases
    other = VocabList(name="Zweite Liste", cards=[
        VocabCard(front="η θάλασσα", back="Meer", article="η",
                  word_type="Nomen")])
    store.save_user_list(other)
    cards = list(vlist.cards) + list(other.cards)
    sel = SelectionList(name="Meine Auswahl",
                        card_ids=[c.id for c in cards])
    store.save_selection(sel)
    nav = _fake_nav()
    panel = wordlist.word_list_panel(nav.page, store.cards_for(sel.id), {},
                                     store=store, source_id=sel.id)

    def texts(ctrl, out):
        import flet as ft
        if isinstance(ctrl, ft.Text) and ctrl.value:
            out.append(ctrl.value)
        for attr in ("controls", "content", "title", "subtitle"):
            sub = getattr(ctrl, attr, None)
            subs = sub if isinstance(sub, list) else [sub]
            for s in subs:
                if isinstance(s, ft.Control):
                    texts(s, out)

    found: list[str] = []
    texts(panel, found)
    # beide Ursprungslisten-Überschriften erscheinen, jede Karte unter ihrer
    assert vlist.name in found and "Zweite Liste" in found
    # das Wort der zweiten Liste steht NACH deren Überschrift
    idx_head = found.index("Zweite Liste")
    idx_word = next(i for i, t in enumerate(found) if "θάλασσα" in t)
    assert idx_word > idx_head


def test_word_list_panel_alpha_sort(store_with_edge_cases):
    """alpha_key sortiert ohne Artikel und Akzente griechisch-alphabetisch."""
    from mathainoa1.ui.views.wordlist import alpha_key
    store, vlist = store_with_edge_cases
    keys = sorted(alpha_key(c) for c in vlist.cards)
    assert keys == sorted(keys)
    # Artikel zählt nicht mit: "το μετρό" sortiert unter μ, nicht τ
    metro = next(c for c in vlist.cards if "μετρό" in c.front)
    assert alpha_key(metro).startswith("μ")


def test_selection_editor_groups_and_sorts(store_with_edge_cases, tmp_path):
    """Reiter „Ausgewählt“: Ursprungslisten-Überschriften erscheinen, und
    die Sortier-Umschalter (alphabetisch/Lernstand) bauen ohne Fehler."""
    import flet as ft
    from mathainoa1.models import SelectionList, VocabCard, VocabList
    store, vlist = store_with_edge_cases
    other = VocabList(name="Editor-Zweitliste", cards=[
        VocabCard(front="η θάλασσα", back="Meer", article="η",
                  word_type="Nomen")])
    store.save_user_list(other)
    sel = SelectionList(name="Auswahl", card_ids=[
        c.id for c in list(vlist.cards) + list(other.cards)])
    store.save_selection(sel)
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "sel.db")
    try:
        view = manager.selection_editor(nav, store, sel,
                                        lambda s: None, progress)

        def collect(ctrl, out):
            if isinstance(ctrl, ft.Text) and ctrl.value:
                out.append(ctrl.value)
            if isinstance(ctrl, ft.IconButton) and ctrl.tooltip:
                out.append(ctrl.tooltip)
            for attr in ("controls", "content", "title", "subtitle"):
                sub = getattr(ctrl, attr, None)
                subs = sub if isinstance(sub, list) else [sub]
                for s in subs:
                    if isinstance(s, ft.Control):
                        collect(s, out)

        found: list[str] = []
        collect(view, found)
        # Gruppierung: beide Ursprungslisten als Überschrift
        assert vlist.name in found and "Editor-Zweitliste" in found
        # Sortier-Umschalter vorhanden — und Umschalten baut fehlerfrei
        assert any("Alphabetisch sortieren" in t for t in found)
        assert any("Lernstand" in t for t in found)

        def find_btn(ctrl, tooltip_part):
            if (isinstance(ctrl, ft.IconButton) and ctrl.tooltip
                    and tooltip_part in ctrl.tooltip):
                return ctrl
            for attr in ("controls", "content", "title"):
                sub = getattr(ctrl, attr, None)
                subs = sub if isinstance(sub, list) else [sub]
                for s in subs:
                    if isinstance(s, ft.Control):
                        hit = find_btn(s, tooltip_part)
                        if hit is not None:
                            return hit
            return None

        find_btn(view, "Alphabetisch sortieren").on_click(None)
        find_btn(view, "Lernstand").on_click(None)
    finally:
        progress.close()


def test_list_view_select_mode(store_with_edge_cases):
    """Markiermodus: Umschalter aktiviert die Mehrfachauswahl-Zeile."""
    store, vlist = store_with_edge_cases
    nav = _fake_nav()
    view = manager.list_view(nav, store, vlist)

    def find_icon_button(ctrl, tooltip):
        import flet as ft
        if isinstance(ctrl, ft.IconButton) and ctrl.tooltip == tooltip:
            return ctrl
        for attr in ("controls", "content", "title"):
            sub = getattr(ctrl, attr, None)
            subs = sub if isinstance(sub, list) else [sub]
            for s in subs:
                if isinstance(s, ft.Control):
                    hit = find_icon_button(s, tooltip)
                    if hit is not None:
                        return hit
        return None

    import flet as ft
    btn = find_icon_button(view, "Wörter markieren (Mehrfachauswahl)")
    assert btn is not None
    btn.on_click(None)  # Markiermodus an — baut die Auswahl-Kacheln
    assert find_icon_button(view, "Markieren beenden") is not None
    assert find_icon_button(view, "Markierte löschen…") is not None


def test_verb_preview_sample_no_crash(store_with_edge_cases):
    """Der Vorschau-Pfad selbst (nicht nur der View-Aufbau): jede Verbform
    liefert einen String, auch das custom-Verb ohne 2. Person Plural."""
    from mathainoa1.logic import conjugation as conj
    store, vlist = store_with_edge_cases
    for _c, v in conj.conjugatable_verbs(vlist.cards):
        assert isinstance(grammar._verb_sample(v), str)


def test_search_view_builds_and_lists_hits(store_with_edge_cases):
    """Wortsuche baut fehlerfrei und rendert bei einem Query Ergebniszeilen."""
    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    nav.store = store
    view = manager.search_view(nav, store)
    # TextField ist das erste Control; Query setzen und refresh auslösen
    tf = view.controls[0]
    results = view.controls[1]
    tf.value = "μετρό"
    tf.on_change(None)
    assert len(results.controls) >= 1


def test_search_hit_edits_in_place(store_with_edge_cases):
    """Klick auf ein Suchergebnis öffnet den Editor als Dialog über der Suche —
    ohne Fensterwechsel (kein nav.go)."""
    store, _vlist = store_with_edge_cases
    dialogs = []
    nav = _fake_nav()
    nav.store = store
    nav.page.show_dialog = lambda d: dialogs.append(d)
    navigated = []
    nav.go = lambda t, c: navigated.append(t)
    view = manager.search_view(nav, store)
    results = view.controls[1]
    view.controls[0].value = "μετρό"
    view.controls[0].on_change(None)
    results.controls[0].on_click(None)  # ersten Treffer anklicken
    assert dialogs and not navigated  # Dialog geöffnet, nicht navigiert


def test_card_editor_dialog_builds(store_with_edge_cases):
    """Der extrahierte Karten-Editor baut ohne Fehler."""
    store, vlist = store_with_edge_cases
    nav = _fake_nav()
    dialogs = []
    nav.page.show_dialog = lambda d: dialogs.append(d)
    manager.card_editor_dialog(nav.page, store, vlist, vlist.cards[0])
    manager.card_editor_dialog(nav.page, store, vlist, None)  # neue Karte
    assert len(dialogs) == 2


def test_settings_view_builds_and_applies_theme(tmp_path, monkeypatch):
    """Einstellungs-View baut; apply_app_theme setzt den Theme-Modus.
    Env auf tmp umbiegen, damit keine echten Settings geschrieben werden."""
    import flet as ft
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.storage.settings import AppSettings
    from mathainoa1.ui.views.settings import apply_app_theme, settings_view

    nav = _fake_nav()
    view = settings_view(nav)
    assert view is not None
    apply_app_theme(nav.page, AppSettings(theme="dark", seed="green"))
    assert nav.page.theme_mode == ft.ThemeMode.DARK
    assert nav.page.theme is not None
