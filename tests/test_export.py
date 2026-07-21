"""Tests für den Spalten-Export (CSV) und den PDF-Export."""

from mathainoa1.models import VocabCard
from mathainoa1.storage import pdf_export
from mathainoa1.storage.content import export_csv_columns, export_json_columns

CARDS = [
    VocabCard(front="ο δρόμος", back="Straße", article="ο", plural="-οι",
              word_type="Nomen", forms={"gen_pl": "δρόμων"}),
    VocabCard(front="γράφω", back="schreiben", word_type="Verb",
              stem2="γράψ-"),
]


def test_export_csv_columns_subset():
    text = export_csv_columns(CARDS, ["front", "back"])
    lines = text.strip().splitlines()
    assert lines[0] == "front,back"
    assert lines[1] == "ο δρόμος,Straße"
    assert lines[2] == "γράφω,schreiben"


def test_export_csv_columns_forms_serialized():
    text = export_csv_columns(CARDS, ["front", "forms", "stem2"])
    assert "gen_pl=δρόμων" in text
    assert "γράψ-" in text


def test_export_csv_columns_keeps_field_order():
    # Reihenfolge der Auswahl ist egal — exportiert wird in CSV_FIELDS-Ordnung
    text = export_csv_columns(CARDS, ["back", "front"])
    assert text.splitlines()[0] == "front,back"


def test_export_json_columns_subset_keeps_ids():
    import json
    text = export_json_columns("Meine Liste", CARDS, ["front", "back"])
    data = json.loads(text)
    assert data["name"] == "Meine Liste"
    assert data["cards"][0] == {"id": CARDS[0].id, "front": "ο δρόμος",
                                "back": "Straße"}


def test_export_json_columns_forms_stay_dict():
    import json
    text = export_json_columns("L", CARDS, ["front", "forms"])
    data = json.loads(text)
    assert data["cards"][0]["forms"] == {"gen_pl": "δρόμων"}


def test_export_pdf_greek_roundtrip():
    data = pdf_export.export_pdf(
        "Testliste", ["Griechisch", "Deutsch"],
        [[c.front, c.back] for c in CARDS])
    assert data.startswith(b"%PDF")
    assert len(data) > 1000  # eingebettete Schrift + Inhalt


def test_export_pdf_many_columns_landscape():
    header = ["Griechisch", "Deutsch", "Plural", "Artikel", "Worttyp",
              "Formen", "2. Stamm"]
    rows = [[c.front, c.back, c.plural, c.article or "", c.word_type,
             "", c.stem2] for c in CARDS]
    data = pdf_export.export_pdf("Breit", header, rows)
    assert data.startswith(b"%PDF")
