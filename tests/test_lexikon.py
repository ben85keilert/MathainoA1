"""Tests für das zentrale Lexikon: Paket-Parser, wortweiser Merge,
Zusatzwörter-Liste, Auswahllisten, Index-Vorrang, Gap-Export."""

import json

import pytest

from mathainoa1.models import VocabCard
from mathainoa1.storage import textanalyse as ta
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.settings import AppSettings, save_app_settings

PACKAGE = {
    "title": "Alltag 1",
    "etymology": [
        {"word": "ο σεισμός",
         "breakdown": [{"element": "σει-", "meaning": "schütteln"}],
         "total": "das Schütteln → Erdbeben",
         "semantics": "Vom altgriechischen σείω.",
         "cognates": {
             "related": [{"word": "το σείσμα", "meaning": "Erschütterung"}],
         },
         "synonyms": [{"word": "η δόνηση", "nuance": "auch technisch"}],
         "extra_vocab": [
             {"front": "η δόνηση", "back": "Erschütterung", "article": "η",
              "word_type": "Nomen"},
             # Ursprungswort selbst darf nie in die Zusatzliste rutschen
             {"front": "ο σεισμός", "back": "Erdbeben", "article": "ο",
              "word_type": "Nomen"},
         ]},
        {"word": "γράφω",
         "total": "ritzen → schreiben",
         "extra_vocab": [
             {"front": "το γράμμα", "back": "Brief, Buchstabe",
              "article": "το", "word_type": "Nomen"},
         ]},
    ],
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolierte Umgebung: App-Daten unter tmp_path, leerer Cache."""
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    ta.invalidate_cache()
    store = ContentStore(tmp_path / "book", tmp_path / "user")
    store.load_all()
    yield store, ta.lexicon_store(store)
    ta.invalidate_cache()


def _import(lex, data=PACKAGE):
    return lex.import_package(json.dumps(data, ensure_ascii=False))


def _enable(*keys):
    s = AppSettings()
    s.enabled_features = list(keys)
    save_app_settings(s)
    ta.invalidate_cache()


# --- Parser -----------------------------------------------------------------

def test_parse_package():
    title, entries = ta.parse_lexicon_package(
        json.dumps(PACKAGE, ensure_ascii=False))
    assert title == "Alltag 1"
    assert [e.word for e in entries] == ["ο σεισμός", "γράφω"]


def test_parse_package_accepts_full_analysis():
    # komplette Analyse-Datei: nur etymology wird übernommen
    data = {"title": "Text", "original_text": "…", "vocab": [],
            "etymology": PACKAGE["etymology"]}
    _title, entries = ta.parse_lexicon_package(json.dumps(data))
    assert len(entries) == 2


def test_parse_package_errors():
    with pytest.raises(ValueError, match="JSON"):
        ta.parse_lexicon_package("kein json")
    with pytest.raises(ValueError, match="JSON-Objekt"):
        ta.parse_lexicon_package("[1, 2]")
    with pytest.raises(ValueError, match="etymology"):
        ta.parse_lexicon_package(json.dumps({"title": "leer"}))


# --- Merge & Listen ---------------------------------------------------------

def test_import_merges_entries_and_builds_lists(env):
    store, lex = env
    stats = _import(lex)
    assert stats["new"] == 2 and stats["updated"] == 0
    # Zusatzliste: Ursprungswörter ausgefiltert, Bündelreihenfolge
    vlist = store.lists[lex.extra_list_id]
    assert vlist.name == "Lexikon – Zusatzwörter"
    assert [c.front for c in vlist.cards] == ["η δόνηση", "το γράμμα"]
    assert stats["extra_new"] == 2
    # pro Paket eine Auswahlliste mit Referenzen auf genau diese Karten
    sel = next(iter(store.selections.values()))
    assert sel.name == "Lexikon: Alltag 1"
    assert sel.card_ids == [c.id for c in vlist.cards]
    assert stats["selection"] == sel.name


def test_reimport_replaces_entry_and_keeps_card_ids(env):
    store, lex = env
    _import(lex)
    old_ids = [c.id for c in store.lists[lex.extra_list_id].cards]
    fixed = json.loads(json.dumps(PACKAGE))
    fixed["etymology"][0]["total"] = "korrigiert"
    fixed["etymology"][0]["extra_vocab"][0]["back"] = "Vibration"
    stats = _import(lex, fixed)
    # wortweiser Merge: Einträge ersetzt, nichts doppelt
    assert stats["new"] == 0 and stats["updated"] == 2
    assert len(lex.entries) == 2
    assert lex.entries[0].total == "korrigiert"
    vlist = store.lists[lex.extra_list_id]
    # additiv: keine Karte verloren, IDs (Lernstand) erhalten
    assert [c.id for c in vlist.cards] == old_ids
    assert vlist.cards[0].back == "Vibration"
    assert stats["extra_updated"] == 1 and stats["extra_new"] == 0


def test_import_survives_deleted_extra_list(env):
    store, lex = env
    _import(lex)
    store.delete_user_list(lex.extra_list_id)
    stats = _import(lex)
    assert stats["extra_new"] == 2
    assert store.lists[lex.extra_list_id].name == "Lexikon – Zusatzwörter"


def test_extra_list_rename_survives_reimport(env):
    store, lex = env
    _import(lex)
    vlist = store.lists[lex.extra_list_id]
    vlist.name = "Meine Bonuswörter"
    store.save_user_list(vlist)
    _import(lex)
    assert store.lists[lex.extra_list_id].name == "Meine Bonuswörter"


def test_lexicon_roundtrip(env):
    store, lex = env
    _import(lex)
    fresh = ta.lexicon_store(store)
    assert [e.word for e in fresh.entries] == ["ο σεισμός", "γράφω"]
    assert fresh.extra_list_id == lex.extra_list_id


def test_delete_entry(env):
    _store, lex = env
    _import(lex)
    assert lex.delete_entry("ο σεισμός") is True
    assert [e.word for e in lex.entries] == ["γράφω"]
    assert lex.delete_entry("ο σεισμός") is False
    fresh = ta.lexicon_store(_store)
    assert [e.word for e in fresh.entries] == ["γράφω"]


# --- Index, Schalter, Gap-Export --------------------------------------------

def test_index_lexicon_wins_over_legacy_analysis(env):
    store, lex = env
    astore = ta.AnalysisStore(ta.analyses_dir(), store)
    astore.import_analysis(json.dumps({
        "title": "Alt", "original_text": "x",
        "vocab": [{"front": "ο σεισμός", "back": "Erdbeben"}],
        "etymology": [{"word": "ο σεισμός", "total": "alt"}],
    }))
    _import(lex)
    _enable(ta.LEXIKON_KEY)
    entry = ta.etymology_for(VocabCard(front="ο σεισμός", back="Erdbeben"))
    assert entry is not None and entry.total == "das Schütteln → Erdbeben"


def test_feature_enabled_by_either_switch(env):
    _store, lex = env
    _import(lex)
    card = VocabCard(front="γράφω", back="schreiben")
    _enable()
    assert ta.etymology_for(card) is None
    for key in (ta.FEATURE_KEY, ta.LEXIKON_KEY):
        _enable(key)
        assert ta.etymology_for(card) is not None


def test_extra_vocab_points_to_origin_entry(env):
    _store, lex = env
    _import(lex)
    _enable(ta.LEXIKON_KEY)
    entry = ta.etymology_for(VocabCard(front="το γράμμα", back="Brief"))
    assert entry is not None and entry.word == "γράφω"


def test_missing_cards(env):
    _store, lex = env
    _import(lex)
    covered = VocabCard(front="ο σεισμός", back="Erdbeben")
    extra = VocabCard(front="η δόνηση", back="Erschütterung")
    gap = VocabCard(front="το ψωμί", back="Brot")
    assert ta.missing_cards([covered, extra, gap]) == [gap]
