"""Tests für die Formen-Notation im Karten-Editor und das stem2-Feld."""

import pytest

from mathainoa1.models import (
    VocabCard,
    parse_stem2_text,
    parse_verb_forms_text,
    verb_forms_to_text,
)
from mathainoa1.storage import content


# --- parse_verb_forms_text ---

def test_parse_verb_forms_full():
    forms = parse_verb_forms_text("πάω, πας, πάει, πάμε, πάτε, πάνε")
    assert forms == {"1sg": "πάω", "2sg": "πας", "3sg": "πάει",
                     "1pl": "πάμε", "2pl": "πάτε", "3pl": "πάνε"}


def test_parse_verb_forms_partial_with_dash_and_empty():
    # "-" und leere Slots = regelmäßig, werden übersprungen
    assert parse_verb_forms_text("-, πας") == {"2sg": "πας"}
    assert parse_verb_forms_text(", πας, , , είστε/είσαστε") == {
        "2sg": "πας", "2pl": "είστε/είσαστε"}


def test_parse_verb_forms_variants_kept_verbatim():
    forms = parse_verb_forms_text("δω, δεις, δει, δούμε, δείτε, δουν/δούνε")
    assert forms["3pl"] == "δουν/δούνε"


def test_parse_verb_forms_too_many_slots():
    with pytest.raises(ValueError):
        parse_verb_forms_text("α, β, γ, δ, ε, ζ, η")


def test_parse_verb_forms_empty():
    assert parse_verb_forms_text("") == {}
    assert parse_verb_forms_text("   ") == {}


# --- verb_forms_to_text ---

def test_verb_forms_roundtrip():
    forms = {"1sg": "πάω", "2sg": "πας", "3sg": "πάει",
             "1pl": "πάμε", "2pl": "πάτε", "3pl": "πάνε"}
    assert parse_verb_forms_text(verb_forms_to_text(forms)) == forms
    partial = {"2sg": "πας"}
    assert parse_verb_forms_text(verb_forms_to_text(partial)) == partial


def test_verb_forms_to_text_ignores_noun_keys():
    assert verb_forms_to_text({"gen_pl": "γυναικών"}) == ""
    assert verb_forms_to_text({}) == ""


# --- parse_stem2_text ---

def test_parse_stem2_single_stem():
    assert parse_stem2_text("γραψ-") == "γραψ-"
    assert parse_stem2_text("  γραψ-  ") == "γραψ-"
    assert parse_stem2_text("") == ""


def test_parse_stem2_six_forms_normalized():
    assert (parse_stem2_text("πάω,πας, πάει,  πάμε, πάτε, πάνε")
            == "πάω, πας, πάει, πάμε, πάτε, πάνε")


def test_parse_stem2_too_many_slots():
    with pytest.raises(ValueError):
        parse_stem2_text("α, β, γ, δ, ε, ζ, η")


# --- stem2 Persistenz ---

def test_stem2_json_roundtrip(tmp_path):
    card = VocabCard(front="γράφω", back="schreiben",
                     word_type="Verb", stem2="γραψ-")
    vlist = content.VocabList(name="L", cards=[card])
    path = tmp_path / "l.json"
    content.save_list(vlist, path)
    loaded = content.load_list(path)
    assert loaded.cards[0].stem2 == "γραψ-"


def test_stem2_legacy_dict_defaults_empty():
    card = VocabCard.from_dict({"front": "γράφω", "back": "schreiben"})
    assert card.stem2 == ""


def test_stem2_csv_roundtrip():
    card = VocabCard(front="γράφω", back="schreiben",
                     word_type="Verb", stem2="γραψ-")
    vlist = content.VocabList(name="L", cards=[card])
    text = content.export_csv(vlist)
    assert "stem2" in text.splitlines()[0]
    imported = content.import_csv("Import", text)
    assert imported.cards[0].stem2 == "γραψ-"


def test_csv_without_stem2_column():
    text = "front,back\nγράφω,schreiben\n"
    imported = content.import_csv("Import", text)
    assert imported.cards[0].stem2 == ""


def test_with_plural_hides_indeclinable_marker():
    # "-" ist die Markierung für unveränderliche Fremdwörter -> nicht anzeigen
    card = VocabCard(front="το μετρό", article="το", back="Metro", plural="-")
    assert card.with_plural(card.front) == "το μετρό"
    # normale Pluralangabe wird weiterhin angehängt
    reg = VocabCard(front="το δώρο", article="το", back="Geschenk", plural="-α")
    assert reg.with_plural(reg.front) == "το δώρο, -α"
    # kein Plural -> reiner Text
    none = VocabCard(front="και", back="und")
    assert none.with_plural(none.front) == "και"
