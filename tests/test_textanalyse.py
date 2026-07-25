"""Tests für das Textanalyse-Feature: Parser, Import, Reimport, Index."""

import json

import pytest

from mathainoa1.models import VocabCard, VocabList
from mathainoa1.storage import textanalyse as ta
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.storage.settings import AppSettings, save_app_settings

SAMPLE = {
    "schema_version": 1,
    "title": "Σεισμός στην Αθήνα",
    "date": "2026-07-20",
    "original_text": "Χθες έγινε σεισμός στην Αθήνα.",
    "translation": "Gestern gab es ein Erdbeben in Athen.",
    "segments": [
        {"gr": "Χθες έγινε", "de": "gestern geschah",
         "note": "Aorist, 3. Sg."},
        {"gr": "σεισμός", "de": "ein Erdbeben"},
    ],
    "vocab": [
        {"front": "ο σεισμός", "back": "Erdbeben", "article": "ο",
         "plural": "-οί", "word_type": "Nomen",
         "forms": "gen_sg=του σεισμού"},
        {"front": "γράφω", "back": "schreiben", "word_type": "Verb",
         "stem2": "γράψ-", "aorist_passive": "γραφτ-",
         "participle": "γραμμένος"},
    ],
    "phrases": [
        {"gr": "έγινε σεισμός", "de": "es gab ein Erdbeben",
         "note": "unpersönlich"},
    ],
    "etymology": [
        {"word": "ο σεισμός",
         "breakdown": [{"element": "σει-", "meaning": "schütteln"}],
         "total": "das Schütteln → Erdbeben",
         "semantics": "Vom altgriechischen σείω.",
         "cognates": {
             "identical": [{"word": "σείω", "meaning": "schütteln"}],
             "related": [{"word": "το σείσμα", "meaning": "Erschütterung"}],
             "german_latin": [{"word": "seismisch", "meaning": "Lehnwort"}],
         },
         "synonyms": [{"word": "η δόνηση", "nuance": "auch technisch"}],
         "extra_vocab": [
             {"front": "η δόνηση", "back": "Erschütterung", "article": "η",
              "word_type": "Nomen"},
             # Dublette gegen das Hauptvokabular — muss übersprungen werden
             {"front": "ο σεισμός", "back": "Erdbeben", "article": "ο",
              "word_type": "Nomen"},
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
    astore = ta.AnalysisStore(ta.analyses_dir(), store)
    yield store, astore
    ta.invalidate_cache()


def _import(astore, data=SAMPLE):
    return astore.import_analysis(json.dumps(data, ensure_ascii=False))


# --- Parser -----------------------------------------------------------------

def test_parse_valid():
    a = ta.parse_analysis(json.dumps(SAMPLE, ensure_ascii=False))
    assert a.title == "Σεισμός στην Αθήνα"
    assert len(a.segments) == 2 and a.segments[1].note == ""
    assert len(a.etymology) == 1
    assert a.etymology[0].cognates["identical"][0]["word"] == "σείω"


def test_parse_errors():
    with pytest.raises(ValueError):
        ta.parse_analysis("kein json")
    with pytest.raises(ValueError):
        ta.parse_analysis("[1, 2]")
    with pytest.raises(ValueError):  # Pflichtfeld title fehlt
        ta.parse_analysis(json.dumps({"original_text": "x"}))


def test_word_key_ignores_article_accents_and_brackets():
    assert ta.word_key("ο σεισμός") == ta.word_key("σεισμος")
    assert ta.word_key("και / κι") == ta.word_key("καί")
    assert ta.word_key("η λαϊκή (αγορά)") == ta.word_key("λαικη")


# --- Import -----------------------------------------------------------------

def test_import_creates_lists_and_cards(env):
    store, astore = env
    analysis, stats = _import(astore)
    assert stats["created"] is True
    assert analysis.id  # aus dem Titel erzeugt
    main = store.lists[analysis.vocab_list_id]
    etym = store.lists[analysis.etym_list_id]
    assert main.name == "Σεισμός στην Αθήνα – Vokabeln"
    assert etym.name == "Σεισμός στην Αθήνα – Etymologie"
    noun, verb = main.cards
    assert noun.article == "ο" and noun.front == "ο σεισμός"
    assert noun.forms == {"gen_sg": "του σεισμού"}
    assert verb.stem2 == "γράψ-" and verb.aorist_passive == "γραφτ-"
    assert verb.participle == "γραμμένος"
    # Dublette (ο σεισμός) wurde übersprungen, nur η δόνηση bleibt
    assert [c.front for c in etym.cards] == ["η δόνηση"]


def test_reimport_keeps_ids_and_progress(env, tmp_path):
    store, astore = env
    analysis, _ = _import(astore)
    main = store.lists[analysis.vocab_list_id]
    noun_id = main.cards[0].id
    progress = ProgressStore(tmp_path / "p.db")
    try:
        progress.record(noun_id, correct=True)
        corrected = json.loads(json.dumps(SAMPLE))
        corrected["id"] = analysis.id
        corrected["vocab"][0]["back"] = "Erdbeben / Beben"
        analysis2, stats = _import(astore, corrected)
        assert analysis2.id == analysis.id
        assert stats["created"] is False and stats["changed"] == 1
        main2 = store.lists[analysis2.vocab_list_id]
        assert main2.cards[0].id == noun_id  # Lernstand bleibt an der Karte
        assert main2.cards[0].back == "Erdbeben / Beben"
        assert progress.get(noun_id).correct == 1
    finally:
        progress.close()


def test_reimport_matches_by_title_without_id(env):
    store, astore = env
    analysis, _ = _import(astore)
    again = json.loads(json.dumps(SAMPLE))  # ohne id, gleicher Titel
    analysis2, stats = _import(astore, again)
    assert analysis2.id == analysis.id and stats["created"] is False
    assert len(astore.analyses) == 1


def test_reimport_adds_and_removes_cards(env):
    store, astore = env
    analysis, _ = _import(astore)
    corrected = json.loads(json.dumps(SAMPLE))
    corrected["id"] = analysis.id
    corrected["vocab"] = [corrected["vocab"][0],  # Verb entfernt
                          {"front": "η θάλασσα", "back": "Meer",
                           "article": "η", "word_type": "Nomen"}]
    _, stats = _import(astore, corrected)
    assert stats["new"] == 1 and stats["removed"] == 1
    fronts = [c.front for c in store.lists[analysis.vocab_list_id].cards]
    assert fronts == ["ο σεισμός", "η θάλασσα"]


def test_reimport_lemma_fix_heuristic(env):
    """Korrigiertes Lemma bei gleicher Bedeutung+Worttyp behält die Karte."""
    store, astore = env
    analysis, _ = _import(astore)
    old_id = store.lists[analysis.vocab_list_id].cards[1].id
    corrected = json.loads(json.dumps(SAMPLE))
    corrected["id"] = analysis.id
    corrected["vocab"][1]["front"] = "γράφομαι"  # anderes Lemma, gleiche Rückseite
    _, stats = _import(astore, corrected)
    cards = store.lists[analysis.vocab_list_id].cards
    assert stats["new"] == 0 and stats["removed"] == 0
    assert cards[1].id == old_id and cards[1].front == "γράφομαι"


def test_reimport_renames_lists_on_title_change(env):
    store, astore = env
    analysis, _ = _import(astore)
    corrected = json.loads(json.dumps(SAMPLE))
    corrected["id"] = analysis.id
    corrected["title"] = "Neuer Titel"
    _import(astore, corrected)
    assert store.lists[analysis.vocab_list_id].name == "Neuer Titel – Vokabeln"


# --- Etymologie-Index / Feature-Schalter ------------------------------------

def _enable_feature():
    s = AppSettings()
    s.enabled_features = [ta.FEATURE_KEY]
    save_app_settings(s)
    ta.invalidate_cache()


def test_etymology_lookup(env):
    store, astore = env
    _import(astore)
    _enable_feature()
    card = VocabCard(front="ο σεισμός", back="Erdbeben")
    entry = ta.etymology_for(card)
    assert entry is not None and entry.total == "das Schütteln → Erdbeben"
    # akzent-/artikelunabhängig
    assert ta.etymology_for(VocabCard(front="σεισμος", back="x")) is entry
    # Zusatzwort findet den Eintrag seines Analyseworts
    assert ta.etymology_for(VocabCard(front="η δόνηση", back="x")) is entry
    assert ta.etymology_for(VocabCard(front="άσχετο", back="x")) is None


def test_etymology_disabled_returns_none(env):
    store, astore = env
    _import(astore)
    save_app_settings(AppSettings())  # Feature nicht aktiviert
    ta.invalidate_cache()
    assert ta.etymology_for(VocabCard(front="ο σεισμός", back="x")) is None


# --- Löschen ----------------------------------------------------------------

def test_delete_analysis(env):
    store, astore = env
    analysis, _ = _import(astore)
    list_ids = (analysis.vocab_list_id, analysis.etym_list_id)
    astore.delete_analysis(analysis.id, delete_lists=False)
    assert analysis.id not in astore.analyses
    assert all(i in store.lists for i in list_ids)  # Listen blieben

    analysis2, _ = _import(astore)
    astore.delete_analysis(analysis2.id, delete_lists=True)
    assert all(i not in store.lists
               for i in (analysis2.vocab_list_id, analysis2.etym_list_id))
