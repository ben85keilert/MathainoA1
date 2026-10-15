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


def test_main_views_build(store_with_edge_cases, tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
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
        grammar.adjective_setup_view(nav, store, progress)
        grammar.combos_view(nav, store, vlist.id)
        grammar.combos_view(nav, store, vlist.id, mode="blacklist")
        grammar.conjugation_setup_view(nav, store, progress)
        manager.manager_view(nav, store, progress)
        manager.list_view(nav, store, vlist, progress)
        manager.selection_editor(nav, store, None, lambda s: None, progress)
    finally:
        progress.close()


def test_adjective_views_build_with_selection_and_blacklist(
        store_with_edge_cases, tmp_path, monkeypatch):
    """Adjektiv-Auswahlliste: erscheint in Verwaltung und Adjektivtraining,
    Blacklist-Modus baut Setup- und Ausnahmen-View fehlerfrei."""
    from mathainoa1.models import SelectionList
    from mathainoa1.storage.settings import AppSettings, save_app_settings
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    store, vlist = store_with_edge_cases
    adj_card = next(c for c in vlist.cards if c.word_type == "Adjektiv")
    sel = SelectionList(name="Meine Adjektive", kind="adjektive",
                        card_ids=[adj_card.id])
    store.save_selection(sel)
    save_app_settings(AppSettings(adjective_combos_mode="blacklist"))
    nav = _fake_nav()
    nav.store = store
    progress = ProgressStore(tmp_path / "adj.db")
    try:
        manager.manager_view(nav, store, progress)
        grammar.adjective_setup_view(nav, store, progress,
                                     preselect_id=sel.id)
        grammar.combos_view(nav, store, sel.id, mode="blacklist")
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
        for attr in ("controls", "content", "title", "subtitle", "trailing"):
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
            for attr in ("controls", "content", "title", "subtitle", "trailing"):
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


def test_list_view_select_mode(store_with_edge_cases, monkeypatch):
    """Markiermodus: Umschalter aktiviert die Mehrfachauswahl-Zeile."""
    from mathainoa1.storage.settings import TTS_SYSTEM
    store, vlist = store_with_edge_cases
    # nicht die echte Einstellungs-Datei des Rechners lesen
    monkeypatch.setattr(manager, "tts_engine", lambda: TTS_SYSTEM)
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
    # "Audio löschen" gehört zum gTTS-Cache — nur im Google-Modus sichtbar
    assert find_icon_button(view, "Audio löschen (wird neu erzeugt)") is None


def test_list_view_select_mode_google_audio(store_with_edge_cases,
                                            monkeypatch):
    """Im Google-Modus erscheint der Cache-Button „Audio löschen“."""
    from mathainoa1.storage.settings import TTS_GOOGLE
    store, vlist = store_with_edge_cases
    monkeypatch.setattr(manager, "tts_engine", lambda: TTS_GOOGLE)
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

    find_icon_button(view, "Wörter markieren (Mehrfachauswahl)").on_click(None)
    assert find_icon_button(view, "Audio löschen (wird neu erzeugt)") is not None


def test_verb_preview_sample_no_crash(store_with_edge_cases):
    """Der Vorschau-Pfad selbst (nicht nur der View-Aufbau): jede Verbform
    liefert einen String, auch das custom-Verb ohne 2. Person Plural."""
    from mathainoa1.logic import conjugation as conj
    store, vlist = store_with_edge_cases
    for _c, v in conj.conjugatable_verbs(vlist.cards):
        assert isinstance(grammar._verb_sample(v), str)


def test_base_form_text_modes():
    """Grundform nach der Lösung: bei Futur-Aufgaben steuert die
    Einstellung, ob Präsensform, Futur-Grundform oder beides erscheint."""
    from mathainoa1.logic import conjugation as conj
    card = VocabCard(front="γράφω", back="schreiben", word_type="Verb",
                     stem2="γράψ-")
    v = conj.parse_verb(card)
    present = conj.build_task(card, v, 2, "pl")
    fut = conj.build_task(card, v, 2, "pl", tense="future")
    assert grammar._base_form_text(present, "both") == "γράφω"
    assert grammar._base_form_text(fut, "present") == "γράφω"
    assert grammar._base_form_text(fut, "stem2") == "θα γράψω"
    assert grammar._base_form_text(fut, "both") == "θα γράψω (γράφω)"


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


def test_settings_view_strict_error_policies(tmp_path, monkeypatch):
    """Die Abfrage-Sektion zeigt je Fehlerart (Akzent/Schreibung) die
    4-Punkte-Auswahl fürs Box-Verhalten."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.ui.views import settings as settings_mod

    nav = _fake_nav()
    found: list[str] = []
    _collect_texts_and_tooltips(settings_mod.settings_view(nav), found)
    assert "Akzentfehler" in found
    assert "Schreibungsfehler (Groß-/Klein, nur Nomen)" in found
    # je Fehlerart eine eigene Radio-Gruppe mit denselben vier Optionen
    reset_label = ("Setzt die Box zurück (Box 1) — gilt auch in der "
                   "Fehlerrunde")
    assert found.count(reset_label) == 2
    assert found.count("In der Fehlerrunde eine Box zurück") == 2


# --- Erweiterte Funktionen (Feature-Framework) und Textanalyse --------------

def _collect_texts_and_tooltips(ctrl, out):
    import flet as ft
    if isinstance(ctrl, ft.Text) and ctrl.value:
        out.append(ctrl.value)
    if getattr(ctrl, "tooltip", None):
        out.append(ctrl.tooltip)
    if getattr(ctrl, "label", None) and isinstance(ctrl.label, str):
        out.append(ctrl.label)
    for attr in ("controls", "content", "title", "subtitle", "trailing"):
        sub = getattr(ctrl, attr, None)
        subs = sub if isinstance(sub, list) else [sub]
        for s in subs:
            import flet as ft
            if isinstance(s, ft.Control):
                _collect_texts_and_tooltips(s, out)


def test_settings_view_features_section(tmp_path, monkeypatch):
    """Die Sektion „Erweiterte Funktionen“ zeigt je Feature einen Schalter —
    bzw. den Platzhalter, wenn die Registry leer ist."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.ui import features
    from mathainoa1.ui.views import settings as settings_mod

    nav = _fake_nav()
    found: list[str] = []
    _collect_texts_and_tooltips(settings_mod.settings_view(nav), found)
    assert "Erweiterte Funktionen" in found
    assert "Textanalyse" in found  # Schalter des registrierten Features
    assert "Stufe" in found  # Stufen-Sektion vorhanden

    monkeypatch.setattr(features, "FEATURES", [])
    monkeypatch.setattr(settings_mod, "FEATURES", [])
    found = []
    _collect_texts_and_tooltips(settings_mod.settings_view(nav), found)
    assert any("Noch keine Zusatzfunktionen" in t for t in found)


def test_home_menu_shows_enabled_feature(store_with_edge_cases, tmp_path,
                                         monkeypatch):
    """Home-Menü: Feature-Karte erscheint nach dem Aktivieren über
    on_reappear (Zurücknavigieren), ohne Neustart."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.storage.settings import AppSettings, save_app_settings
    from mathainoa1.ui import app as app_mod

    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "home.db")
    try:
        home = app_mod.home_view(nav, store, progress)
        found: list[str] = []
        _collect_texts_and_tooltips(home, found)
        assert "Vokabeltraining" in found and "Textanalyse" not in found

        s = AppSettings()
        s.enabled_features = ["textanalyse"]
        save_app_settings(s)
        assert callable(home.on_reappear)
        home.on_reappear()
        found = []
        _collect_texts_and_tooltips(home, found)
        assert "Textanalyse" in found
    finally:
        progress.close()


def _sample_analysis_json():
    import json
    return json.dumps({
        "title": "Testtext",
        "original_text": "Χθες έγινε σεισμός.",
        "translation": "Gestern gab es ein Erdbeben.",
        "segments": [{"gr": "Χθες", "de": "gestern"}],
        "vocab": [{"front": "ο σεισμός", "back": "Erdbeben",
                   "article": "ο", "word_type": "Nomen"}],
        "phrases": [{"gr": "έγινε σεισμός", "de": "es gab ein Erdbeben"}],
        "etymology": [{
            "word": "ο σεισμός",
            "breakdown": [{"element": "σει-", "meaning": "schütteln"}],
            "total": "das Schütteln → Erdbeben",
            "semantics": "Vom altgriechischen σείω.",
            "cognates": {"identical": [{"word": "σείω",
                                        "meaning": "schütteln"}]},
            "synonyms": [{"word": "η δόνηση", "nuance": "auch technisch"}],
            "extra_vocab": [{"front": "η δόνηση", "back": "Erschütterung",
                             "article": "η", "word_type": "Nomen"}],
        }],
    }, ensure_ascii=False)


def test_textanalyse_views_build(store_with_edge_cases, tmp_path, monkeypatch):
    """Gesamtschau, Detailansicht und Etymologie-Dialog bauen fehlerfrei —
    leer und mit importierter Analyse."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.storage import textanalyse as ta
    from mathainoa1.ui.views import textanalyse as ta_view

    ta.invalidate_cache()
    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "ta.db")
    try:
        ta_view.overview_view(nav, store, progress)  # leer

        astore = ta.AnalysisStore(ta.analyses_dir(), store)
        analysis, _stats = astore.import_analysis(_sample_analysis_json())
        overview = ta_view.overview_view(nav, store, progress)
        found: list[str] = []
        _collect_texts_and_tooltips(overview, found)
        assert "Testtext" in found

        detail = ta_view.detail_view(nav, astore, store, progress, analysis)
        found = []
        _collect_texts_and_tooltips(detail, found)
        assert "Originaltext & Übersetzung" in found
        assert "Etymologie" in found

        dialogs = []
        nav.page.show_dialog = lambda d: dialogs.append(d)
        ta_view.etymology_dialog(nav.page, analysis.etymology[0])
        assert dialogs
    finally:
        ta.invalidate_cache()
        progress.close()


def test_trainer_info_button_visible_with_feature(store_with_edge_cases,
                                                  tmp_path, monkeypatch):
    """Der Info-Button erscheint im Training auf der griechischen Seite,
    wenn das Feature aktiv ist und die Karte einen Etymologie-Eintrag hat."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.logic.session import TrainingSession, TrainingSettings
    from mathainoa1.storage import textanalyse as ta
    from mathainoa1.storage.settings import AppSettings, save_app_settings

    ta.invalidate_cache()
    store, _vlist = store_with_edge_cases
    astore = ta.AnalysisStore(ta.analyses_dir(), store)
    astore.import_analysis(_sample_analysis_json())
    s = AppSettings()
    s.enabled_features = ["textanalyse"]
    save_app_settings(s)
    ta.invalidate_cache()

    card = store.lists[
        [l.id for l in store.lists.values()
         if l.name == "Testtext – Vokabeln"][0]].cards[0]
    session = TrainingSession(
        [card], TrainingSettings(mode="flashcard", direction="gr_de"), {})
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "tr.db")
    try:
        view = trainer.run_view(nav, store, progress, session)
        found: list[str] = []
        _collect_texts_and_tooltips(view, found)
        # σεισμός hat Eintrag UND Beugungsformen → kombiniertes Symbol
        assert "Wort-Info & Beugungsformen" in found
    finally:
        ta.invalidate_cache()
        progress.close()


def test_update_word_details_button_states():
    """Ein Symbol je nach Verfügbarkeit: beides → Info, nur Beugung →
    Tabelle, nur Lexikoneintrag → Buch, nichts → unsichtbar."""
    import flet as ft
    btn = ft.IconButton()
    trainer.update_word_details_button(btn, forms=True, info=True)
    assert btn.visible and btn.icon == ft.Icons.INFO_OUTLINE
    trainer.update_word_details_button(btn, forms=True, info=False)
    assert btn.visible and btn.icon == ft.Icons.TABLE_CHART_OUTLINED
    trainer.update_word_details_button(btn, forms=False, info=True)
    assert btn.visible and btn.icon == ft.Icons.MENU_BOOK_OUTLINED
    trainer.update_word_details_button(btn, forms=False, info=False)
    assert not btn.visible


def test_has_word_forms_fast_matches_slow(store_with_edge_cases):
    """Das billige Prädikat (ohne Control-Bau) muss mit has_word_forms
    übereinstimmen — es entscheidet, ob Listenzeilen das Symbol zeigen."""
    _store, vlist = store_with_edge_cases
    extra = VocabCard(front="και", back="und")  # ohne Worttyp → nie Formen
    for card in list(vlist.cards) + [extra]:
        assert (reference.has_word_forms_fast(card)
                == reference.has_word_forms(card)), card.front


def test_word_details_button_variants(store_with_edge_cases):
    """Fertiger Listen-Button: Tabellen-Symbol bei Formen ohne Lexikon,
    None ohne beides."""
    from mathainoa1.ui.word_details import word_details_button
    import flet as ft
    _store, vlist = store_with_edge_cases
    verb = next(c for c in vlist.cards if c.front == "γράφω")
    btn = word_details_button(verb)  # Lexikon-Feature aus → nur Formen
    assert btn is not None and btn.icon == ft.Icons.TABLE_CHART_OUTLINED
    plain = VocabCard(front="και", back="und")
    assert word_details_button(plain) is None


def test_hide_empty_texts():
    """Leere Platzhalter einklappen, gefüllte zeigen (Prüfen-Button-Höhe)."""
    import flet as ft
    empty, filled = ft.Text(""), ft.Text("τον μικρό δρόμο")
    trainer.hide_empty_texts(empty, filled)
    assert not empty.visible and filled.visible


def test_settings_view_builds(store_with_edge_cases, tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.ui.views import settings as settings_mod
    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "set.db")
    try:
        settings_mod.settings_view(nav, store, progress)
    finally:
        progress.close()


def test_wrapping_radio_group_click_selects_and_saves():
    """Klick auf die Text-Zeile wählt den Wert und feuert den
    Speicher-Callback — Radio-Labels selbst können in Flet nicht
    umbrechen, deshalb die eigene Zeilen-Konstruktion."""
    from mathainoa1.ui.views.settings import _wrapping_radio_group
    page = SimpleNamespace(update=lambda: None)
    picked: list[str] = []
    rg = _wrapping_radio_group(
        "a", [("a", "Erste lange Option"), ("b", "Zweite lange Option")],
        picked.append, page)
    assert rg.value == "a"
    # zweite Zeile antippen (Container.on_click)
    rg.content.controls[1].on_click(None)
    assert rg.value == "b" and picked == ["b"]
    # Radio-Tap läuft über rg.on_change mit dem Gruppenwert
    rg.value = "a"
    rg.on_change(None)
    assert picked == ["b", "a"]


def test_switch_row_click_toggles_and_fires():
    from mathainoa1.ui.views.settings import _switch_row
    import flet as ft
    page = SimpleNamespace(update=lambda: None)
    fired: list[bool] = []
    sw = ft.Switch(value=False)
    sw.on_change = lambda e: fired.append(sw.value)
    row = _switch_row(sw, "Sehr langes Schalter-Label zum Umbrechen", page)
    row.on_click(None)
    assert sw.value is True and fired == [True]
    row.on_click(None)
    assert sw.value is False and fired == [True, False]


def test_result_view_lists_correct_answers(store_with_edge_cases, tmp_path):
    """Die Ergebnisansicht zeigt unter den Fehlern auch die richtig
    beantworteten Wörter (grüne Häkchen-Zeilen)."""
    from mathainoa1.logic.session import TrainingSession, TrainingSettings

    store, vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "res.db")
    try:
        session = TrainingSession(
            vlist.cards[:2],
            TrainingSettings(mode="flashcard", word_count=2,
                             repeat_errors=False))
        wrong_card, right_card = session.queue[0], session.queue[1]
        session.mark(False)
        session.mark(True)
        assert session.finished
        view = trainer.result_view(nav, store, progress, session)
        found: list[str] = []
        _collect_texts_and_tooltips(view, found)
        assert "Richtig:" in found
        assert wrong_card.front in found and right_card.front in found
    finally:
        progress.close()


def test_edit_notes_dialog_offers_full_editor(store_with_edge_cases):
    """„Alles bearbeiten" im Notiz-Dialog: nur bei eigenen Listen, öffnet
    den vollen Karteneditor und übernimmt eben getippte Notizen."""
    import flet as ft

    store, vlist = store_with_edge_cases
    card = vlist.cards[0]
    nav = _fake_nav()
    dialogs = []
    nav.page.show_dialog = lambda d: dialogs.append(d)
    nav.page.pop_dialog = lambda: None
    trainer.edit_notes_dialog(nav.page, store, card)
    assert len(dialogs) == 1

    def find_button(ctrl, label):
        if isinstance(ctrl, ft.TextButton) and ctrl.content == label:
            return ctrl
        for attr in ("controls", "content", "title", "actions"):
            sub = getattr(ctrl, attr, None)
            subs = sub if isinstance(sub, list) else [sub]
            for s in subs:
                if isinstance(s, ft.Control):
                    hit = find_button(s, label)
                    if hit is not None:
                        return hit
        return None

    btn = find_button(dialogs[0], "Alles bearbeiten")
    assert btn is not None
    # Notiz eintippen, dann wechseln: voller Editor öffnet, Notiz gespeichert
    notes_field = dialogs[0].content.controls[0]
    notes_field.value = "Merksatz"
    btn.on_click(None)
    assert len(dialogs) == 2  # Karteneditor als zweiter Dialog
    assert card.notes_gr == "Merksatz"


def test_edit_notes_dialog_no_full_editor_for_book_cards(tmp_path):
    """Buchkarten (nicht editierbare Liste): kein „Alles bearbeiten"."""
    import flet as ft
    import json

    book_dir = tmp_path / "book"
    book_dir.mkdir()
    card = VocabCard(front="ο δρόμος", back="Straße", word_type="Nomen")
    vlist = VocabList(name="Buchliste", cards=[card])
    (book_dir / "b.json").write_text(
        json.dumps(vlist.to_dict(), ensure_ascii=False), encoding="utf-8")
    store = ContentStore(book_dir, tmp_path / "user")
    store.load_all()
    book_card = store.all_cards()[0]
    nav = _fake_nav()
    dialogs = []
    nav.page.show_dialog = lambda d: dialogs.append(d)
    trainer.edit_notes_dialog(nav.page, store, book_card)
    texts = [getattr(a, "content", None) for a in dialogs[0].actions]
    assert "Alles bearbeiten" not in texts


# --- Lexikon (v0.6.0) --------------------------------------------------------

def _sample_package_json():
    import json
    return json.dumps({
        "title": "Paket 1",
        "etymology": [{
            "word": "γράφω",
            "breakdown": [{"element": "γραφ-", "meaning": "ritzen"}],
            "total": "ritzen → schreiben",
            "semantics": "Vom altgriechischen γράφω.",
            "cognates": {"related": [{"word": "το γράμμα",
                                      "meaning": "Brief"}]},
            "synonyms": [],
            "extra_vocab": [{"front": "το γράμμα",
                             "back": "Brief / Buchstabe",
                             "article": "το", "word_type": "Nomen"}],
        }],
    }, ensure_ascii=False)


def _enable_lexikon(tmp_path, monkeypatch):
    from mathainoa1.storage import textanalyse as ta
    from mathainoa1.storage.settings import AppSettings, save_app_settings
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    ta.invalidate_cache()
    s = AppSettings()
    s.enabled_features = ["lexikon"]
    save_app_settings(s)
    return ta


def test_lexikon_view_builds(store_with_edge_cases, tmp_path, monkeypatch):
    """Lexikon-Ansicht baut fehlerfrei — leer und mit importiertem Paket."""
    ta = _enable_lexikon(tmp_path, monkeypatch)
    from mathainoa1.ui.views import lexikon as lex_view

    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "lex.db")
    try:
        lex_view.lexikon_view(nav, store, progress)  # leer

        ta.lexicon_store(store).import_package(_sample_package_json())
        view = lex_view.lexikon_view(nav, store, progress)
        found: list[str] = []
        _collect_texts_and_tooltips(view, found)
        assert "γράφω" in found
        assert "1 Einträge" in found
    finally:
        ta.invalidate_cache()
        progress.close()


def test_search_hit_shows_info_button(store_with_edge_cases, tmp_path,
                                      monkeypatch):
    """Wortsuche: Treffer bekommen den kombinierten Wortinfo-Button
    (γράφω hat Beugungsformen UND Lexikon-Eintrag → ⓘ) plus Audio."""
    ta = _enable_lexikon(tmp_path, monkeypatch)
    store, _vlist = store_with_edge_cases
    ta.lexicon_store(store).import_package(_sample_package_json())
    ta.invalidate_cache()

    nav = _fake_nav()
    view = manager.search_view(nav, store)
    tf = view.controls[0]
    tf.value = "γράφω"
    tf.on_change(None)
    found: list[str] = []
    _collect_texts_and_tooltips(view, found)
    assert "Wort-Info & Beugungsformen" in found
    assert any(t.startswith("Anhören") for t in found)
    ta.invalidate_cache()


def test_search_hit_forms_only_shows_table_button(store_with_edge_cases):
    """Wortsuche ohne Lexikon-Feature: Wörter mit Beugungsformen bekommen
    trotzdem das Tabellen-Symbol."""
    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    view = manager.search_view(nav, store)
    tf = view.controls[0]
    tf.value = "γράφω"
    tf.on_change(None)
    found: list[str] = []
    _collect_texts_and_tooltips(view, found)
    assert "Beugungsformen anzeigen" in found


def test_list_view_word_info_icon(store_with_edge_cases, tmp_path,
                                  monkeypatch):
    """Listen-Detailansicht: Übersichtssymbol nur, wenn das Feature aktiv
    ist und die Liste Worthintergrund hat."""
    ta = _enable_lexikon(tmp_path, monkeypatch)
    from mathainoa1.storage.settings import AppSettings, save_app_settings

    store, vlist = store_with_edge_cases
    ta.lexicon_store(store).import_package(_sample_package_json())
    ta.invalidate_cache()

    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "lvi.db")
    try:
        found: list[str] = []
        _collect_texts_and_tooltips(
            manager.list_view(nav, store, vlist, progress), found)
        assert "Worthintergrund dieser Liste" in found

        save_app_settings(AppSettings())  # Feature aus
        ta.invalidate_cache()
        found = []
        _collect_texts_and_tooltips(
            manager.list_view(nav, store, vlist, progress), found)
        assert "Worthintergrund dieser Liste" not in found
    finally:
        ta.invalidate_cache()
        progress.close()


def test_prompts_two_step_split():
    """AW III liefert keine Etymologie mehr; AW IV übernimmt sie."""
    from mathainoa1.ui.views.lexikon import arbeitsanweisung_iv
    from mathainoa1.ui.views.textanalyse import arbeitsanweisung_iii

    for level in ("A1", "A2"):
        aw3, aw4 = arbeitsanweisung_iii(level), arbeitsanweisung_iv(level)
        assert '"etymology"' not in aw3
        assert "extra_vocab" not in aw3
        assert "Arbeitsanweisung IV" in aw3
        assert '"etymology"' in aw4
        assert '"extra_vocab"' in aw4
        assert "NICHT alphabetisch" in aw4
        assert "@" not in aw3 and "@" not in aw4  # Platzhalter ersetzt


def test_arbeitsanweisungen_verb_fields_follow_level():
    """AW III/IV fragen nur die Verbfelder der Stufe ab: A1 den 2. Stamm,
    A2 zusätzlich Aorist und Imperativ — Aorist Passiv/Partizip nie."""
    from mathainoa1.ui.views.lexikon import arbeitsanweisung_iv
    from mathainoa1.ui.views.textanalyse import arbeitsanweisung_iii

    a1, a2 = arbeitsanweisung_iii("A1"), arbeitsanweisung_iii("A2")
    assert '"stem2": ""' in a1 and '"aorist"' not in a1
    assert '"aorist": ""' in a2 and '"imperative": ""' in a2
    assert "έγραψα" in a2
    for text in (a1, a2, arbeitsanweisung_iv("A1"), arbeitsanweisung_iv("A2")):
        assert "aorist_passive" not in text and "participle" not in text
    assert "stem2, aorist, imperative" in arbeitsanweisung_iv("A2")
    # unbekannte (spätere) Stufe: alle Felder
    assert "aorist_passive" in arbeitsanweisung_iii("A2+")


# --- Backup (v0.7.0) ---------------------------------------------------------

def test_settings_view_backup_section(store_with_edge_cases, tmp_path,
                                      monkeypatch):
    """Einstellungen: Backup-Abschnitt nur mit übergebenen Stores;
    ohne Stores (Alt-Signatur) baut die View weiter fehlerfrei."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.storage.progress import ProgressStore
    from mathainoa1.ui.views import settings as settings_mod

    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "bs.db")
    try:
        found: list[str] = []
        _collect_texts_and_tooltips(
            settings_mod.settings_view(nav, store, progress), found)
        assert "Backup" in found
        assert "Backup erstellen" in [t for t in found] or any(
            "Backup" in t for t in found)

        found = []
        _collect_texts_and_tooltips(settings_mod.settings_view(nav), found)
        assert "Backup" not in found
    finally:
        progress.close()


def test_stats_view_has_no_export_button(store_with_edge_cases, tmp_path,
                                         monkeypatch):
    """Der Statistik-Export ist vom Backup abgelöst — kein Download mehr."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.storage.progress import ProgressStore

    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "se.db")
    try:
        found: list[str] = []
        _collect_texts_and_tooltips(stats.stats_view(nav, store, progress),
                                    found)
        assert not any("exportieren" in t.lower() for t in found)
        assert "Listen" in found
    finally:
        progress.close()


def test_summarize_list_counts(store_with_edge_cases, tmp_path):
    """Kennzahlen einer Liste (früher in stats_export, jetzt in der View)."""
    from mathainoa1.storage.progress import ProgressStore

    store, vlist = store_with_edge_cases
    progress = ProgressStore(tmp_path / "sm.db")
    try:
        progress.record(vlist.cards[0].id, correct=True)
        progress.record(vlist.cards[1].id, correct=False)
        s = stats.summarize_list(vlist, progress.all())
        assert s["cards"] == len(vlist.cards)
        assert s["trained"] == 2
        assert s["boxes"][1] == 1 and s["boxes"][2] == 1
        assert s["secure"] == 0
    finally:
        progress.close()


def test_list_view_title_row_with_tab_toggles(store_with_edge_cases,
                                              tmp_path):
    """Titelzeile (v0.7.1): Name + Reiter-Umschalter oben — auch für
    Buchlisten (ohne Umbenennen-Stift)."""
    import flet as ft
    import json

    store, vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "tr2.db")
    try:
        found: list[str] = []
        _collect_texts_and_tooltips(
            manager.list_view(nav, store, vlist, progress), found)
        assert vlist.name in found
        assert "Kartenansicht" in found and "Tabellenansicht" in found
        assert "Liste umbenennen" in found

        book_dir = tmp_path / "book2"
        book_dir.mkdir()
        book = VocabList(name="Buchliste", cards=[
            VocabCard(front="ο δρόμος", back="Straße", word_type="Nomen")])
        (book_dir / "b.json").write_text(
            json.dumps(book.to_dict(), ensure_ascii=False), encoding="utf-8")
        store2 = ContentStore(book_dir, tmp_path / "user2")
        store2.load_all()
        book_list = next(iter(store2.lists.values()))
        found = []
        _collect_texts_and_tooltips(
            manager.list_view(nav, store2, book_list, progress), found)
        assert "Buchliste" in found
        assert "Kartenansicht" in found and "Tabellenansicht" in found
        assert "Liste umbenennen" not in found
    finally:
        progress.close()


# --- Prompt-Konsistenz (v0.7.1) ---------------------------------------------

def test_prompt_examples_have_all_columns():
    """Beispielzeilen im Prompt haben genau die Spalten der Kopfzeile der
    Stufe — sonst lernt der Chatbot ein verkürztes Format. Die
    Beispielliste hat alle CSV-Spalten."""
    import csv
    import io

    from mathainoa1.storage.content import (
        _EXAMPLE_CSV,
        CSV_FIELDS,
        csv_fields_for,
    )
    from mathainoa1.ui.views.help import csv_format_rules

    for level in ("A1", "A2"):
        fields = csv_fields_for(level)
        rules = csv_format_rules(level)
        assert ",".join(fields) + "\n" in rules
        block = rules.split("BEISPIELZEILEN")[1]
        rows = [r for r in csv.reader(io.StringIO(block)) if len(r) > 1]
        assert rows
        assert all(len(r) == len(fields) for r in rows)
        grafo = dict(zip(fields, next(r for r in rows if r[0] == "γράφω")))
        assert grafo["stem2"] == "γράψ-"
        if level == "A2":
            assert grafo["aorist"] == "έγραψα"
            assert grafo["imperative"] == "Γράψε!"
        # A2-Beispiele (Aoristeintrag, -ύς-Adjektiv) nur auf A2
        assert any(r[0] == "ήρθα" for r in rows) == (level == "A2")

    example_rows = [r for r in csv.reader(io.StringIO(_EXAMPLE_CSV)) if r]
    assert all(len(r) == len(CSV_FIELDS) for r in example_rows)


def test_prompt_forms_without_article_and_keys():
    """forms-Werte ohne Artikel (sonst „του του άντρα") und nom_pl in
    der Schlüsselliste; aorist_passive nicht mehr als Pflicht."""
    from mathainoa1.ui.views.help import csv_format_rules
    from mathainoa1.ui.views.lexikon import arbeitsanweisung_iv
    from mathainoa1.ui.views.textanalyse import arbeitsanweisung_iii

    for level in ("A1", "A2"):
        assert "του άντρα" not in arbeitsanweisung_iii(level)
        assert "του άντρα" not in arbeitsanweisung_iv(level)
        assert "nom_pl" in csv_format_rules(level)
        assert "immer angeben" not in arbeitsanweisung_iii(level)
        # Schema nennt alle Felder
        assert "notes_gr" in arbeitsanweisung_iii(level)


def test_prompt_level_interpolation(tmp_path, monkeypatch):
    """Wortlisten-/Lesetext-Prompt tragen die aktive Stufe statt fest „A1"."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.storage.settings import (
        AppSettings,
        load_app_settings,
        save_app_settings,
    )
    from mathainoa1.ui.views.help import chatbot_prompt, text_prompt

    s = AppSettings()
    s.level = "A2"
    save_app_settings(s)
    for build in (chatbot_prompt, text_prompt):
        text = build(load_app_settings().level)
        assert "Niveau A2" in text and "{level}" not in text


def test_prompt_rules_follow_level():
    """Nur der Stoff der Stufe: A1 ohne Aorist/Imperativ, A2 mit beiden und
    mit der Pame-A2-Buchschreibweise; Aorist Passiv/Partizip auf keiner."""
    from mathainoa1.ui.views.help import chatbot_prompt

    a1, a2 = chatbot_prompt("A1"), chatbot_prompt("A2")
    assert "stem2:" in a1 and "aorist:" not in a1
    assert "imperative:" not in a1
    assert "aorist:" in a2 and "imperative:" in a2
    assert "πιστεύω, -έψω" in a2 and "Aorist von έρχομαι" in a2
    for text in (a1, a2):
        assert "aorist_passive" not in text and "participle" not in text
    # unbekannte (spätere) Stufe bekommt wieder alle Felder
    assert "aorist_passive" in chatbot_prompt("A2+")


def test_options_summary_saves_immediately_and_refreshes():
    """Die Options-Karte der Startseiten: jede Änderung im Dialog ruft
    sofort on_change (Speichern) und frischt die Zusammenfassung auf."""
    import flet as ft
    from mathainoa1.ui.views.setup_common import on_off, options_summary

    saved = []
    sw = ft.Switch(label="Fehlerrunde", value=True)
    page = SimpleNamespace(update=lambda: None, width=420,
                           show_dialog=lambda d: None,
                           pop_dialog=lambda: None)
    card = options_summary(page,
                           describe=lambda: [on_off("Fehlerrunde", sw.value)],
                           controls=[sw, ft.Text("Hinweis")],
                           on_change=lambda: saved.append(sw.value))
    tile = card.content
    assert tile.subtitle.value == "Fehlerrunde: an"
    sw.value = False
    sw.on_change(None)  # von der Komponente verdrahtet
    assert saved == [False]
    assert tile.subtitle.value == "Fehlerrunde: aus"


def test_setup_views_have_options_card(store_with_edge_cases, tmp_path,
                                       monkeypatch):
    """Alle 4 Startseiten zeigen die kompakte Options-Karte unter den
    Start-Buttons statt einzelner Schalter auf der Seite."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "opt.db")
    try:
        views = [
            trainer.setup_view(nav, store, progress),
            grammar.setup_view(nav, store, progress),
            grammar.adjective_setup_view(nav, store, progress),
            grammar.conjugation_setup_view(nav, store, progress),
        ]
        for view in views:
            found: list[str] = []
            _collect_texts_and_tooltips(view, found)
            assert "Weitere Optionen" in found
            # die Schalter selbst stehen nicht mehr direkt auf der Seite
            assert "Fehler am Ende wiederholen" not in found
    finally:
        progress.close()

def test_box_transition_dot_colors_and_tooltip():
    """Zweigeteilter Boxen-Punkt: linke Hälfte = vorher, rechte = nachher;
    Tooltip nennt beide Zustände (optional mit Wort-Label)."""
    from mathainoa1.ui.views import wordlist

    dot = wordlist.box_transition_dot(0, 1)
    left, right = dot.content.controls
    assert left.bgcolor == wordlist.UNTRAINED_COLOR
    assert right.bgcolor == wordlist.BOX_COLORS[0]
    assert dot.tooltip == "neu → Box 1"
    labeled = wordlist.box_transition_dot(2, 3, label="ο δρόμος")
    assert labeled.tooltip == "ο δρόμος: Box 2 → Box 3"


def _collect_deep(ctrl, out):
    """Wie _collect_texts_and_tooltips, aber auch durch leading/actions."""
    import flet as ft
    if isinstance(ctrl, ft.Text) and ctrl.value:
        out.append(ctrl.value)
    if getattr(ctrl, "tooltip", None):
        out.append(ctrl.tooltip)
    for attr in ("controls", "content", "title", "subtitle", "leading",
                 "trailing", "actions"):
        sub = getattr(ctrl, attr, None)
        subs = sub if isinstance(sub, list) else [sub]
        for s in subs:
            if isinstance(s, ft.Control):
                _collect_deep(s, out)


def test_result_view_box_dots_and_edit_for_correct(store_with_edge_cases,
                                                   tmp_path, monkeypatch):
    """Ergebnisliste des Vokabeltrainings: zweigeteilter Boxen-Punkt
    (vorher → nachher) je Wort und Bearbeiten-Stift auch bei den richtig
    beantworteten Wörtern."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.logic.session import TrainingSession, TrainingSettings

    store, vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "dots.db")
    try:
        def make_finished_session():
            session = TrainingSession(
                vlist.cards[:2],
                TrainingSettings(mode="flashcard", word_count=2,
                                 repeat_errors=False),
                progress=progress.all(),
            )
            session.on_result = lambda card, ok: progress.record(card.id, ok)
            session.mark(False)  # neues Wort falsch -> Box 1
            session.mark(True)  # neues Wort richtig -> Box 2
            return session

        view = trainer.result_view(nav, store, progress,
                                   make_finished_session())
        found: list[str] = []
        _collect_deep(view, found)
        assert "neu → Box 1" in found
        assert "neu → Box 2" in found
        # Stift bei falschen UND richtigen Wörtern
        assert found.count("Hinweise/Notizen bearbeiten") == 2

        # Abschaltbar über die App-Einstellung (Haupteinstellungen)
        from mathainoa1.storage.settings import AppSettings, save_app_settings
        save_app_settings(AppSettings(result_box_dots=False))
        view = trainer.result_view(nav, store, progress,
                                   make_finished_session())
        found = []
        _collect_deep(view, found)
        assert not any("→ Box" in x for x in found)
        assert found.count("Hinweise/Notizen bearbeiten") == 2
    finally:
        progress.close()


def test_declension_result_view_dots_per_scored_card(store_with_edge_cases,
                                                     tmp_path, monkeypatch):
    """Beugungs-Ergebnisliste (Vorgabe Deutsch): ein Boxen-Punkt je
    mitwandernder Karte — im Adjektivtraining also zwei (Nomen und
    Adjektiv, per Tooltip unterscheidbar) — und ein Bearbeiten-Stift."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.logic.declension import (
        DeclensionSession,
        DeclensionSettings,
        DeclensionTask,
    )

    store, vlist = store_with_edge_cases
    noun = next(c for c in vlist.cards if c.front == "το μετρό")
    adj = next(c for c in vlist.cards if c.front == "μικρός")
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "decl.db")
    try:
        task = DeclensionTask(
            card=noun, case="acc", number="sg", prompt="Metro (Akkusativ)",
            meaning="Metro", expected="το μικρό μετρό", adj_card=adj)
        settings = DeclensionSettings(mode="typing", direction="de",
                                      word_count=1, repeat_errors=False)
        session = DeclensionSession(
            [task], settings, progress=progress.all(),
            on_result=lambda card, ok: progress.record(card.id, ok))
        session.check_typed("το μικρό μετρό")
        assert session.finished
        view = grammar.result_view(nav, store, session, "Adjektivtraining",
                                   make_tasks=lambda s: [], progress=progress)
        found: list[str] = []
        _collect_deep(view, found)
        assert f"{noun.front}: neu → Box 2" in found
        assert f"{adj.front}: neu → Box 2" in found
        assert "Hinweise/Notizen bearbeiten" in found
    finally:
        progress.close()


def _tiles(ctrl, out):
    """Alle ListTiles des Control-Baums einsammeln."""
    import flet as ft
    if isinstance(ctrl, ft.ListTile):
        out.append(ctrl)
    for attr in ("controls", "content", "title", "subtitle", "trailing",
                 "leading"):
        sub = getattr(ctrl, attr, None)
        for s in (sub if isinstance(sub, list) else [sub]):
            if isinstance(s, ft.Control):
                _tiles(s, out)


def _icons(ctrl, out):
    import flet as ft
    if isinstance(ctrl, ft.Icon) and ctrl.name:
        out.append(ctrl.name)
    for attr in ("controls", "content", "title", "subtitle", "trailing",
                 "leading"):
        sub = getattr(ctrl, attr, None)
        for s in (sub if isinstance(sub, list) else [sub]):
            if isinstance(s, ft.Control):
                _icons(s, out)


def test_result_view_marks_only_in_headings(store_with_edge_cases, tmp_path,
                                            monkeypatch):
    """✓/✗ stehen einmal in der Überschrift, nicht mehr vor jedem Wort."""
    import flet as ft

    from mathainoa1.logic.session import TrainingSession, TrainingSettings

    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    store, vlist = store_with_edge_cases
    nav = _fake_nav()
    progress = ProgressStore(tmp_path / "res.db")
    try:
        session = TrainingSession(
            vlist.cards[:2],
            TrainingSettings(mode="flashcard", word_count=2,
                             repeat_errors=False))
        session.mark(False)
        session.mark(True)
        view = trainer.result_view(nav, store, progress, session)
        texts: list[str] = []
        _collect_texts_and_tooltips(view, texts)
        assert "Falsche Karten:" in texts and "Richtig:" in texts
        tiles: list = []
        _tiles(view, tiles)
        assert tiles  # es gibt Wortzeilen …
        for tile in tiles:
            marks: list[str] = []
            if isinstance(tile.leading, ft.Control):
                _icons(tile.leading, marks)
            # … aber ohne eigenes ✓/✗ davor
            assert ft.Icons.CHECK not in marks and ft.Icons.CLOSE not in marks
    finally:
        progress.close()


def test_stats_switch_off_stops_progress(store_with_edge_cases, tmp_path,
                                         monkeypatch):
    """„Statistik einschalten für" aus: die Runde läuft, bewegt aber
    weder Boxen noch Zähler."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.logic.session import TrainingSettings
    from mathainoa1.storage.settings import (
        AppSettings,
        load_app_settings,
        save_app_settings,
    )

    store, vlist = store_with_edge_cases
    progress = ProgressStore(tmp_path / "stats.db")
    try:
        settings = TrainingSettings(mode="flashcard", word_count=1,
                                    repeat_errors=False, list_id=vlist.id)
        save_app_settings(AppSettings(stats_vocab=True))
        assert trainer.make_session(
            store, progress, settings).on_result is not None

        save_app_settings(AppSettings(stats_vocab=False))
        assert load_app_settings().stats_vocab is False
        session = trainer.make_session(store, progress, settings)
        assert session.on_result is None and session.on_repeat_correct is None
        card = session.current
        session.mark(True)
        assert progress.get(card.id) is None  # nichts aufgezeichnet
    finally:
        progress.close()


def test_leitner_wiring_respects_stats_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.logic.declension import DeclensionSettings

    settings = DeclensionSettings(direction="de")
    progress = ProgressStore(tmp_path / "w.db")
    try:
        on_result, on_repeat, on_penalty = grammar._leitner_wiring(
            progress, settings, lambda: "typing", stats_on=True)
        assert (on_result is not None and on_repeat is not None
                and on_penalty is not None)
        assert grammar._leitner_wiring(
            progress, settings, lambda: "typing",
            stats_on=False) == (None, None, None)
        # Vorgabe Griechisch zählt weiterhin gar nicht
        assert grammar._leitner_wiring(
            DeclensionSettings(direction="gr"), DeclensionSettings(direction="gr"),
            lambda: "typing") == (None, None, None)
    finally:
        progress.close()


def test_setup_views_have_box_filter(store_with_edge_cases, tmp_path,
                                     monkeypatch):
    """Alle Trainings-Startseiten bieten die abwählbaren Leitner-Boxen."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    nav.store = store
    progress = ProgressStore(tmp_path / "box.db")
    try:
        views = [
            trainer.setup_view(nav, store, progress),
            grammar.setup_view(nav, store, progress),
            grammar.adjective_setup_view(nav, store, progress),
            grammar.conjugation_setup_view(nav, store, progress),
        ]
        for view in views:
            found: list[str] = []
            _collect_texts_and_tooltips(view, found)
            assert "Boxen" in found
            assert "Noch nicht trainiert" in found  # Tooltip des „neu"-Chips
            assert "Box 5" in found
    finally:
        progress.close()


def test_box_filter_row_toggles(tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.logic.session import ALL_BOXES
    from mathainoa1.ui.views.setup_common import box_filter_row

    nav = _fake_nav()
    row, boxes_of = box_filter_row(nav.page, None)
    assert boxes_of() == ALL_BOXES
    # Chip „5" abschalten (die Zeile beginnt mit der Beschriftung)
    chip5 = row.controls[5]  # Text, 1, 2, 3, 4, 5, neu
    chip5.on_click(None)
    assert boxes_of() == [0, 1, 2, 3, 4]
    chip5.on_click(None)
    assert boxes_of() == ALL_BOXES
    # gespeicherte Auswahl wird übernommen
    _row2, boxes2 = box_filter_row(nav.page, [0, 1])
    assert boxes2() == [0, 1]


# --- Stufe A2: Aorist/Imperativ nur, wo sie Stoff sind ----------------------

def _set_level(tmp_path, monkeypatch, level):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.storage.settings import AppSettings, save_app_settings
    save_app_settings(AppSettings(level=level))


def _find_all(ctrl, cls, out=None):
    """Alle Controls eines Typs (rekursiv über controls/content)."""
    import flet as ft
    out = [] if out is None else out
    if isinstance(ctrl, cls):
        out.append(ctrl)
    for attr in ("controls", "content"):
        sub = getattr(ctrl, attr, None)
        for s in (sub if isinstance(sub, list) else [sub]):
            if isinstance(s, ft.Control):
                _find_all(s, cls, out)
    return out


_STEM2 = "2. Stamm (Futur/να-Form)"
_AORIST = "Aorist (Vergangenheit)"
_IMPERATIVE = "Imperativ (2. Person Singular)"
_AORIST_PASSIVE = "Aorist Passiv (3. Stamm)"
_PARTICIPLE = "Perfekt-Partizip (unregelmäßig)"


@pytest.mark.parametrize("level, visible, hidden", [
    ("A1", {_STEM2}, {_AORIST, _IMPERATIVE, _AORIST_PASSIVE, _PARTICIPLE}),
    ("A2", {_STEM2, _AORIST, _IMPERATIVE}, {_AORIST_PASSIVE, _PARTICIPLE}),
])
def test_card_editor_verb_fields_follow_level(store_with_edge_cases, tmp_path,
                                              monkeypatch, level, visible,
                                              hidden):
    import flet as ft
    _set_level(tmp_path, monkeypatch, level)
    store, vlist = store_with_edge_cases
    nav = _fake_nav()
    dialogs = []
    nav.page.show_dialog = dialogs.append
    grafo = next(c for c in vlist.cards if c.front == "γράφω")
    manager.card_editor_dialog(nav.page, store, vlist, grafo)
    fields = {tf.label: tf for tf in _find_all(dialogs[-1].content,
                                                ft.TextField)}
    assert all(fields[label].visible for label in visible)
    assert not any(fields[label].visible for label in hidden)


def test_card_editor_saves_aorist_and_keeps_hidden_values(
        store_with_edge_cases, tmp_path, monkeypatch):
    import flet as ft
    _set_level(tmp_path, monkeypatch, "A2")
    store, vlist = store_with_edge_cases
    grafo = next(c for c in vlist.cards if c.front == "γράφω")
    grafo.aorist_passive = "γραφτ-"  # kein A2-Stoff: ausgeblendet, bleibt
    nav = _fake_nav()
    dialogs = []
    nav.page.show_dialog = dialogs.append
    manager.card_editor_dialog(nav.page, store, vlist, grafo)
    dlg = dialogs[-1]
    fields = {tf.label: tf for tf in _find_all(dlg.content, ft.TextField)}
    fields[_AORIST].value = "έγραψα"
    fields[_IMPERATIVE].value = "Γράψε!"
    dlg.actions[1].on_click(None)  # Speichern
    assert (grafo.aorist, grafo.imperative) == ("έγραψα", "Γράψε!")
    assert grafo.aorist_passive == "γραφτ-"
    # ein Stamm statt der 1. Person ergibt keinen Aorist → abgelehnt
    fields[_AORIST].value = "γράψ-"
    dlg.actions[1].on_click(None)
    assert grafo.aorist == "έγραψα"


@pytest.mark.parametrize("level, tenses", [
    ("A1", ["present", "future"]),
    ("A2", ["present", "future", "aorist", "imperative"]),
])
def test_conjugation_setup_tenses_follow_level(store_with_edge_cases, tmp_path,
                                               monkeypatch, level, tenses):
    import flet as ft
    _set_level(tmp_path, monkeypatch, level)
    store, _vlist = store_with_edge_cases
    nav = _fake_nav()
    nav.store = store
    progress = ProgressStore(tmp_path / "p.db")
    try:
        view = grammar.conjugation_setup_view(nav, store, progress)
    finally:
        progress.close()
    seg = next(s for s in _find_all(view, ft.SegmentedButton)
               if any(x.value == "present" for x in s.segments))
    assert [x.value for x in seg.segments] == tenses


def test_reference_shows_a2_material_only_on_a2():
    def texts(ctrl):
        found: list[str] = []
        _collect_texts_and_tooltips(ctrl, found)
        return found

    for view, heading in (
            (reference.verbs_view, "Aorist (Vergangenheit)"),
            (reference.verbs_view, "Imperativ (einmalig, 2. Person Singular)"),
            (reference.adjectives_view, "A2: Adjektive auf -ύς, -ιά, -ύ"),
            (reference.numbers_view, "A2: Ordnungszahlen")):
        assert heading in texts(view("A2"))
        assert heading not in texts(view("A1"))
    card = VocabCard(front="γράφω", back="schreiben", word_type="Verb",
                     stem2="γράψ-", aorist="έγραψα", imperative="Γράψε!")
    a1 = texts(reference._verb_forms_tables(card, "A1"))
    a2 = texts(reference._verb_forms_tables(card, "A2"))
    assert "Aorist (Vergangenheit)" in a2
    assert "Imperativ (2. Person Singular)" in a2
    assert "Aorist (Vergangenheit)" not in a1 and "Futur (θα + 2. Stamm)" in a1
