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
        assert "Wortherkunft & Synonyme" in found
    finally:
        ta.invalidate_cache()
        progress.close()


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
    """Wortsuche: Treffer mit Lexikon-Eintrag bekommen den ⓘ-Button."""
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
    assert "Wortherkunft & Synonyme" in found
    ta.invalidate_cache()


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
    from mathainoa1.ui.views.lexikon import ARBEITSANWEISUNG_IV
    from mathainoa1.ui.views.textanalyse import ARBEITSANWEISUNG_III

    assert '"etymology"' not in ARBEITSANWEISUNG_III
    assert "extra_vocab" not in ARBEITSANWEISUNG_III
    assert "Arbeitsanweisung IV" in ARBEITSANWEISUNG_III
    assert '"etymology"' in ARBEITSANWEISUNG_IV
    assert '"extra_vocab"' in ARBEITSANWEISUNG_IV
    assert "NICHT alphabetisch" in ARBEITSANWEISUNG_IV


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
    """Beispielzeilen in Prompt und Beispielliste: volle 13 Spalten —
    sonst lernt der Chatbot ein verkürztes Format (aorist_passive und
    participle fehlten positionsrichtig)."""
    import csv
    import io

    from mathainoa1.storage.content import _EXAMPLE_CSV, CSV_FIELDS
    from mathainoa1.ui.views.help import _CSV_FORMAT_RULES

    block = _CSV_FORMAT_RULES.split("BEISPIELZEILEN")[1]
    rows = [r for r in csv.reader(io.StringIO(block)) if len(r) > 1]
    assert rows
    assert all(len(r) == len(CSV_FIELDS) for r in rows)
    # γράφω zeigt jetzt auch aorist_passive und participle
    grafo = next(r for r in rows if r[0] == "γράφω")
    assert grafo[11] == "γραφτ-" and grafo[12] == "γραμμένος"

    example_rows = [r for r in csv.reader(io.StringIO(_EXAMPLE_CSV)) if r]
    assert all(len(r) == len(CSV_FIELDS) for r in example_rows)


def test_prompt_forms_without_article_and_keys():
    """forms-Werte ohne Artikel (sonst „του του άντρα") und nom_pl in
    der Schlüsselliste; aorist_passive nicht mehr als Pflicht."""
    from mathainoa1.ui.views.help import _CSV_FORMAT_RULES
    from mathainoa1.ui.views.lexikon import ARBEITSANWEISUNG_IV
    from mathainoa1.ui.views.textanalyse import ARBEITSANWEISUNG_III

    assert "του άντρα" not in ARBEITSANWEISUNG_III
    assert "του άντρα" not in ARBEITSANWEISUNG_IV
    assert "nom_pl" in _CSV_FORMAT_RULES
    assert "immer angeben" not in ARBEITSANWEISUNG_III
    assert "notes_gr" in ARBEITSANWEISUNG_III  # Schema nennt alle Felder


def test_prompt_level_interpolation(tmp_path, monkeypatch):
    """CHATBOT_/TEXT_PROMPT tragen die aktive Stufe statt fest „A1"."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    from mathainoa1.storage.settings import (
        AppSettings,
        load_app_settings,
        save_app_settings,
    )
    from mathainoa1.ui.views.help import CHATBOT_PROMPT, TEXT_PROMPT

    s = AppSettings()
    s.level = "A2"
    save_app_settings(s)
    for tpl in (CHATBOT_PROMPT, TEXT_PROMPT):
        text = tpl.format(level=load_app_settings().level)
        assert "Niveau A2" in text and "{level}" not in text
