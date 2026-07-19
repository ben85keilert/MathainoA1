import random

from mathainoa1.logic import conjugation as conj
from mathainoa1.logic.answer_check import Result
from mathainoa1.logic.conjugation import (
    ConjugationSettings,
    build_task,
    conjugate,
    generate_tasks,
    parse_verb,
)
from mathainoa1.logic.declension import DeclensionSession
from mathainoa1.models import VocabCard


def verb(front, back="x"):
    return VocabCard(front=front, back=back, word_type="Verb")


def all_forms(front):
    v = parse_verb(verb(front))
    assert v is not None, f"nicht erkannt: {front}"
    return [conjugate(v, p, n)[0] for n in ("sg", "pl") for p in (1, 2, 3)]


# --- Typ A ---

def test_type_a():
    assert all_forms("μένω") == ["μένω", "μένεις", "μένει",
                                 "μένουμε", "μένετε", "μένουν"]


def test_type_a_long_stem():
    assert all_forms("καταλαβαίνω") == [
        "καταλαβαίνω", "καταλαβαίνεις", "καταλαβαίνει",
        "καταλαβαίνουμε", "καταλαβαίνετε", "καταλαβαίνουν"]


def test_type_a_3pl_variant():
    v = parse_verb(verb("μένω"))
    assert conjugate(v, 3, "pl") == ["μένουν", "μένουνε"]


# --- Typ B1 (-άω) ---

def test_type_b1():
    assert all_forms("μιλάω") == ["μιλάω", "μιλάς", "μιλάει",
                                  "μιλάμε", "μιλάτε", "μιλάνε"]


def test_type_b1_variants():
    v = parse_verb(verb("μιλάω"))
    assert conjugate(v, 1, "sg") == ["μιλάω", "μιλώ"]
    assert conjugate(v, 3, "sg") == ["μιλάει", "μιλά"]
    assert conjugate(v, 1, "pl") == ["μιλάμε", "μιλούμε"]
    assert conjugate(v, 3, "pl") == ["μιλάνε", "μιλούν", "μιλούνε"]


# --- Typ B2 (-ώ) ---

def test_type_b2():
    assert all_forms("μπορώ") == ["μπορώ", "μπορείς", "μπορεί",
                                  "μπορούμε", "μπορείτε", "μπορούν"]


def test_type_b2_monosyllabic_zo():
    # einsilbige Formen ohne Akzent
    assert all_forms("ζω") == ["ζω", "ζεις", "ζει", "ζούμε", "ζείτε", "ζουν"]


# --- Deponentien ---

def test_deponent_omai():
    assert all_forms("έρχομαι") == ["έρχομαι", "έρχεσαι", "έρχεται",
                                    "ερχόμαστε", "έρχεστε", "έρχονται"]


def test_deponent_omai_accent_shift():
    assert all_forms("σηκώνομαι")[3] == "σηκωνόμαστε"


def test_deponent_2pl_variant():
    v = parse_verb(verb("ντύνομαι"))
    assert conjugate(v, 2, "pl") == ["ντύνεστε", "ντυνόσαστε"]


def test_deponent_amai():
    assert all_forms("κοιμάμαι") == ["κοιμάμαι", "κοιμάσαι", "κοιμάται",
                                     "κοιμόμαστε", "κοιμάστε", "κοιμούνται"]


# --- Unregelmäßige ---

def test_irregular_eimai():
    assert all_forms("είμαι") == ["είμαι", "είσαι", "είναι",
                                  "είμαστε", "είστε", "είναι"]


def test_irregular_pao_troo_leo_akouo():
    assert all_forms("πάω") == ["πάω", "πας", "πάει", "πάμε", "πάτε", "πάνε"]
    assert all_forms("τρώω") == ["τρώω", "τρως", "τρώει", "τρώμε", "τρώτε", "τρώνε"]
    assert all_forms("λέω") == ["λέω", "λες", "λέει", "λέμε", "λέτε", "λένε"]
    assert all_forms("ακούω") == ["ακούω", "ακούς", "ακούει",
                                  "ακούμε", "ακούτε", "ακούν"]


# --- Phrasen und übersprungene Karten ---

def test_phrase_first_word_conjugated():
    v = parse_verb(verb("κάνω μπάνιο"))
    assert conjugate(v, 2, "pl") == ["κάνετε μπάνιο"]


def test_fixed_forms_skipped():
    # Fixformen/Futur sind keine konjugierbaren Lemmata
    for front in ("είναι", "είσαι", "έχει", "κοστίζει", "μπορεί",
                  "βρίσκεται", "θα δούμε", "θα πιουν",
                  "κοστίζει / κοστίζουν"):
        assert parse_verb(verb(front)) is None, front


def test_non_verbs_skipped():
    assert parse_verb(VocabCard(front="ο δρόμος", back="Straße",
                                word_type="Nomen", article="ο")) is None


# --- Aufgaben und Runde ---

def test_build_task():
    v = verb("μένω", "wohnen")
    task = build_task(v, parse_verb(v), 2, "pl")
    assert task.prompt == "wohnen"
    assert task.label == "2. Person Plural"
    assert task.expected == "μένετε"


def test_task_check_variants_and_accents():
    v = verb("μιλάω", "sprechen")
    task = build_task(v, parse_verb(v), 3, "pl")
    assert task.check("μιλάνε") == Result.CORRECT
    assert task.check("μιλούν") == Result.CORRECT
    assert task.check("μιλανε") == Result.ALMOST
    assert task.check("μιλάει") == Result.WRONG


def test_generate_tasks_and_session():
    cards = [verb("μένω", "wohnen"), verb("μπορώ", "können"),
             verb("θα δούμε", "wir werden sehen"),
             VocabCard(front="καλός", back="gut", word_type="Adjektiv")]
    settings = ConjugationSettings(persons=[2], numbers=["pl"], word_count=5)
    tasks = generate_tasks(cards, settings, rng=random.Random(1))
    assert sorted(t.expected for t in tasks) == ["μένετε", "μπορείτε"]
    session = DeclensionSession(tasks, settings)
    session.check_typed(session.current.expected)
    assert session.answers[-1].result == Result.CORRECT


def test_settings_roundtrip():
    s = ConjugationSettings(persons=[1, 3], numbers=["sg"])
    assert ConjugationSettings.from_dict(s.to_dict()) == s


# --- Unregelmäßige Formen (Karten-Feld forms) ---

def test_verb_form_override():
    c = verb("πηγαίνω")
    c.forms = {"2sg": "πας"}
    v = parse_verb(c)
    assert conjugate(v, 2, "sg") == ["πας"]
    assert conjugate(v, 1, "pl")[0] == "πηγαίνουμε"  # Rest regelbasiert


def test_verb_override_variants():
    c = verb("μένω")
    c.forms = {"3pl": "μένουν/μένουνε"}
    v = parse_verb(c)
    assert conjugate(v, 3, "pl") == ["μένουν", "μένουνε"]


def test_custom_verb_via_forms():
    # unbekanntes Muster: ohne forms übersprungen, mit forms abfragbar
    assert parse_verb(verb("οφείλει")) is None
    c = verb("οφείλει")
    c.forms = {"3sg": "οφείλει", "3pl": "οφείλουν"}
    v = parse_verb(c)
    assert v.cls == "custom"
    assert conjugate(v, 3, "sg") == ["οφείλει"]
    assert conjugate(v, 3, "pl") == ["οφείλουν"]
    assert conjugate(v, 2, "sg") == []  # keine Aufgabe für fehlende Slots


# --- Futur (2. Stamm) ---

def fut_verb(front, stem2, back="x"):
    c = verb(front, back)
    c.stem2 = stem2
    return c


def test_future_accented_stem_type_a():
    # Stamm mit Akzent → Typ-A-Endungen
    v = parse_verb(fut_verb("γράφω", "γράψ-"))
    assert conj.has_future(v)
    forms = [conj.conjugate_future(v, p, n)[0]
             for n in ("sg", "pl") for p in (1, 2, 3)]
    assert forms == ["γράψω", "γράψεις", "γράψει",
                     "γράψουμε", "γράψετε", "γράψουν"]


def test_future_unaccented_stem_endbetont():
    # Stamm ohne Akzent → endbetonte Endungen (θα κοιμηθώ)
    v = parse_verb(fut_verb("κοιμάμαι", "κοιμηθ"))
    assert conj.conjugate_future(v, 1, "sg") == ["κοιμηθώ"]
    assert conj.conjugate_future(v, 2, "sg") == ["κοιμηθείς"]
    assert conj.conjugate_future(v, 2, "pl") == ["κοιμηθείτε"]


def test_future_full_form_list():
    v = parse_verb(fut_verb("πίνω", "πιω, πιεις, πιει, πιούμε, πιείτε, πιουν/πιούνε"))
    assert conj.conjugate_future(v, 2, "sg") == ["πιεις"]
    assert conj.conjugate_future(v, 3, "pl") == ["πιουν", "πιούνε"]


def test_future_phrase_keeps_rest():
    v = parse_verb(fut_verb("κάνω μπάνιο", "κάν-"))
    assert conj.conjugate_future(v, 2, "pl") == ["κάνετε μπάνιο"]


def test_future_without_stem2():
    v = parse_verb(verb("μένω"))
    assert not conj.has_future(v)
    assert conj.conjugate_future(v, 1, "sg") == []


def test_future_broken_stem2_ignored():
    # 7 Slots = ungültig → Futur wird ignoriert, Präsens bleibt nutzbar
    v = parse_verb(fut_verb("μένω", "α, β, γ, δ, ε, ζ, η"))
    assert not conj.has_future(v)
    assert conjugate(v, 1, "sg") == ["μένω"]


def test_build_task_future():
    c = fut_verb("γράφω", "γράψ-", "schreiben")
    task = build_task(c, parse_verb(c), 2, "pl", tense="future")
    assert task.expected == "θα γράψετε"
    assert task.label == "Futur: 2. Person Plural"
    # mit und ohne "θα" richtig
    assert task.check("θα γράψετε") == Result.CORRECT
    assert task.check("γράψετε") == Result.CORRECT
    assert task.check("θα γράφετε") == Result.WRONG


def test_generate_tasks_tenses():
    cards = [fut_verb("γράφω", "γράψ-", "schreiben"),
             verb("μένω", "wohnen")]  # ohne 2. Stamm
    settings = ConjugationSettings(persons=[2], numbers=["pl"],
                                   tenses=["present", "future"])
    tasks = generate_tasks(cards, settings, rng=random.Random(1))
    assert sorted(t.expected for t in tasks) == [
        "γράφετε", "θα γράψετε", "μένετε"]
    # nur Futur: Verben ohne 2. Stamm fallen raus
    settings = ConjugationSettings(persons=[2], numbers=["pl"],
                                   tenses=["future"])
    tasks = generate_tasks(cards, settings, rng=random.Random(1))
    assert [t.expected for t in tasks] == ["θα γράψετε"]


def test_settings_tenses_default_and_roundtrip():
    # alte gespeicherte Einstellungen (ohne tenses) → Präsens
    s = ConjugationSettings.from_dict({"persons": [1], "numbers": ["sg"]})
    assert s.tenses == ["present"]
    s = ConjugationSettings(tenses=["present", "future"])
    assert ConjugationSettings.from_dict(s.to_dict()) == s


# --- Verben-Vorschau: robustes Beispiel (Bug: IndexError bei custom-Verb) ---


def test_verb_sample_handles_custom_verb_without_2pl():
    from mathainoa1.ui.views.grammar import _verb_sample
    # "custom": unbekanntes Muster, nur 1sg-Override -> 2pl leer
    card = VocabCard(front="κάνει", back="macht", word_type="Verb",
                     forms={"1sg": "κάνω"})
    v = conj.parse_verb(card)
    assert v.cls == "custom"
    sample = _verb_sample(v)  # darf nicht mit IndexError abstürzen
    assert "κάνω" in sample


def test_verb_sample_regular_shows_2pl_and_future():
    from mathainoa1.ui.views.grammar import _verb_sample
    v = conj.parse_verb(VocabCard(front="γράφω", back="schreiben",
                                  word_type="Verb", stem2="γράψ-"))
    sample = _verb_sample(v)
    assert "2. Person Plural" in sample and "γράφετε" in sample
    assert "θα γράψετε" in sample
