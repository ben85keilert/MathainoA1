"""Tests für den Statistik-Export (CSV/JSON) und die Stufen-Filterung."""

import csv
import io
import json

from mathainoa1.models import VocabCard, VocabList
from mathainoa1.storage.content import filter_level
from mathainoa1.storage.progress import ProgressStore
from mathainoa1.storage.settings import AppSettings
from mathainoa1.storage.stats_export import (
    STATS_FIELDS,
    stats_csv,
    stats_json,
    summarize_list,
)


def _setup(tmp_path):
    cards = [
        VocabCard(front="ο δρόμος", back="Straße", word_type="Nomen"),
        VocabCard(front="γράφω", back="schreiben", word_type="Verb"),
        VocabCard(front="εδώ", back="hier", word_type="Adverb"),
    ]
    vlist = VocabList(name="Testliste", cards=cards)
    progress = ProgressStore(tmp_path / "p.db")
    # Karte 0 viermal richtig -> Box 5 (sicher); Karte 1 einmal falsch
    for _ in range(4):
        progress.record(cards[0].id, correct=True)
    progress.record(cards[1].id, correct=False)
    return vlist, progress


def test_stats_csv_rows(tmp_path):
    vlist, progress = _setup(tmp_path)
    try:
        text = stats_csv([vlist], progress.all())
        rows = list(csv.DictReader(io.StringIO(text)))
        assert list(rows[0].keys()) == STATS_FIELDS
        assert len(rows) == 3  # auch die untrainierte Karte
        assert rows[0]["liste"] == "Testliste"
        assert rows[0]["box"] == "5" and rows[0]["correct"] == "4"
        assert rows[1]["box"] == "1" and rows[1]["wrong"] == "1"
        assert rows[1]["last_seen"] != ""
        untrained = rows[2]
        assert untrained["front"] == "εδώ"
        assert untrained["box"] == "" and untrained["last_seen"] == ""
    finally:
        progress.close()


def test_stats_json_summary(tmp_path):
    vlist, progress = _setup(tmp_path)
    try:
        data = json.loads(stats_json([vlist], progress.all(), level="A1"))
        assert data["level"] == "A1"
        summary = data["lists"][0]
        assert summary["cards"] == 3 and summary["trained"] == 2
        assert summary["secure"] == 1  # Box 5 zählt als sicher (Box 4-5)
        assert summary["boxes"]["5"] == 1 or summary["boxes"][5] == 1
        assert len(data["cards"]) == 3
    finally:
        progress.close()


def test_summarize_matches_view_semantics(tmp_path):
    vlist, progress = _setup(tmp_path)
    try:
        s = summarize_list(vlist, progress.all())
        assert s["name"] == "Testliste"
        assert s["trained"] == 2 and s["secure"] == 1
    finally:
        progress.close()


# --- Stufenfilter (content.filter_level) ------------------------------------

def test_filter_level_truth_table():
    a1 = VocabList(name="a1", book="A1")
    a2 = VocabList(name="a2", book="A2")
    none = VocabList(name="eigene", book=None)
    lists = [a1, a2, none]
    # A1-Modus: A2 ausgeblendet, stufenlose immer sichtbar
    assert filter_level(lists, "A1") == [a1, none]
    # A2-Modus sieht auch A1 (aufwärtskompatibel)
    assert filter_level(lists, "A2") == [a1, a2, none]
    # Unbekannter Wert: nichts ausblenden
    assert filter_level(lists, "alle") == lists


def test_app_settings_defaults_tolerant():
    s = AppSettings.from_dict({})
    assert s.level == "A1" and s.enabled_features == []
    # Alt-Datei mit unbekannten Schlüsseln lädt weiter
    s = AppSettings.from_dict({"theme": "dark", "unbekannt": 1})
    assert s.theme == "dark"
    # Roundtrip mit neuen Feldern
    s.enabled_features = ["textanalyse"]
    s2 = AppSettings.from_dict(s.to_dict())
    assert s2.enabled_features == ["textanalyse"]
