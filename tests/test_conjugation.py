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
    assert task.label == "2. Pers. - Plural 👥 (ihr / höfliches Sie)"
    assert task.expected == "μένετε"


def test_task_display_joins_variants():
    # Aufdeck-Anzeige nennt alle Alternativformen mit "/"
    v = verb("σηκώνομαι", "aufstehen")
    task = build_task(v, parse_verb(v), 2, "pl")
    assert task.display == "σηκώνεστε/σηκωνόσαστε"
    assert task.tense_base == ""


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


def test_build_task_greek_prompt():
    v = verb("μένω", "wohnen")
    task = build_task(v, parse_verb(v), 2, "pl", direction="gr")
    assert task.prompt == "μένω"
    assert task.meaning == "wohnen"
    assert task.expected == "μένετε"


def test_generate_tasks_greek_skips_1sg_present():
    cards = [verb("μένω", "wohnen")]
    settings = ConjugationSettings(persons=[1, 2], numbers=["sg"],
                                   direction="gr")
    tasks = generate_tasks(cards, settings, rng=random.Random(1))
    # 1. Person Singular Präsens entfällt — sie ist das angezeigte Lemma
    assert sorted(t.expected for t in tasks) == ["μένεις"]
    assert all(t.prompt == "μένω" for t in tasks)


def test_generate_tasks_greek_keeps_1sg_future():
    card = verb("γράφω", "schreiben")
    card.stem2 = "γράψ-"
    settings = ConjugationSettings(persons=[1], numbers=["sg"],
                                   tenses=["future"], direction="gr")
    tasks = generate_tasks([card], settings, rng=random.Random(1))
    # im Futur ist die 1. Person Singular nicht offensichtlich
    assert [t.expected for t in tasks] == ["θα γράψω"]


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
    assert task.label == "Futur - 2. Pers. - Plural 👥 (ihr / höfliches Sie)"
    assert task.display == "θα γράψετε"
    assert task.tense_base == "θα γράψω"
    # mit und ohne "θα" richtig
    assert task.check("θα γράψετε") == Result.CORRECT
    assert task.check("γράψετε") == Result.CORRECT
    assert task.check("θα γράφετε") == Result.WRONG


def test_future_display_and_base_with_variants():
    # "θα" steht in der Anzeige nur einmal vorweg; die Futur-Grundform
    # ist die 1. Person Singular mit "θα"
    c = fut_verb("πίνω", "πιω, πιεις, πιει, πιούμε, πιείτε, πιουν/πιούνε",
                 "trinken")
    task = build_task(c, parse_verb(c), 3, "pl", tense="future")
    assert task.display == "θα πιουν/πιούνε"
    assert task.tense_base == "θα πιω"


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


def test_conjugation_settings_carry_default_true():
    s = ConjugationSettings.from_dict({"mode": "typing"})
    assert s.carry_errors_next_round is True
    assert ConjugationSettings.from_dict(
        {"carry_errors_next_round": False}).carry_errors_next_round is False


# --- Aorist (A2): aus der 1. Person Singular -------------------------------

def aor_verb(front, aorist, back="x", **kw):
    return VocabCard(front=front, back=back, word_type="Verb",
                     aorist=aorist, **kw)


def aorist_forms(front, aorist):
    v = parse_verb(aor_verb(front, aorist))
    assert v is not None and conj.has_aorist(v), f"kein Aorist: {front}"
    return ["/".join(conj.conjugate_aorist(v, p, n))
            for n in ("sg", "pl") for p in (1, 2, 3)]


def test_aorist_augment_drops_in_plural():
    assert aorist_forms("γράφω", "έγραψα") == [
        "έγραψα", "έγραψες", "έγραψε", "γράψαμε", "γράψατε",
        "έγραψαν/γράψανε"]
    assert aorist_forms("τρώω", "έφαγα")[3:5] == ["φάγαμε", "φάγατε"]
    assert aorist_forms("γίνομαι", "έγινα")[3] == "γίναμε"


def test_aorist_stress_moves_to_antepenult():
    assert aorist_forms("αγοράζω", "αγόρασα") == [
        "αγόρασα", "αγόρασες", "αγόρασε", "αγοράσαμε", "αγοράσατε",
        "αγόρασαν/αγοράσανε"]
    assert aorist_forms("καταλαβαίνω", "κατάλαβα")[3] == "καταλάβαμε"
    assert aorist_forms("περιμένω", "περίμενα")[4] == "περιμένατε"


def test_aorist_stem_epsilon_is_no_augment():
    # ελπίζω beginnt selbst mit ε — das ε von έλπισα bleibt im Plural
    assert aorist_forms("ελπίζω", "έλπισα")[3] == "ελπίσαμε"


def test_aorist_eta_and_ei_forms_keep_their_vowel():
    assert aorist_forms("έρχομαι", "ήρθα")[3:] == [
        "ήρθαμε", "ήρθατε", "ήρθαν/ήρθανε"]
    assert aorist_forms("λέω", "είπα")[3] == "είπαμε"
    assert aorist_forms("έχω", "είχα")[4] == "είχατε"
    assert aorist_forms("βγαίνω", "βγήκα")[3] == "βγήκαμε"


def test_aorist_passive_type_omai_verbs():
    assert aorist_forms("κοιμάμαι", "κοιμήθηκα") == [
        "κοιμήθηκα", "κοιμήθηκες", "κοιμήθηκε", "κοιμηθήκαμε",
        "κοιμηθήκατε", "κοιμήθηκαν/κοιμηθήκανε"]
    assert aorist_forms("ανεβαίνω", "ανέβηκα")[3] == "ανεβήκαμε"
    assert aorist_forms("χαίρομαι", "χάρηκα")[4] == "χαρήκατε"


def test_aorist_irregular_table():
    assert aorist_forms("είμαι", "ήμουν") == [
        "ήμουν/ήμουνα", "ήσουν/ήσουνα", "ήταν/ήτανε",
        "ήμασταν/ήμαστε", "ήσασταν/ήσαστε", "ήταν/ήτανε"]
    assert aorist_forms("θέλω", "ήθελα")[3:] == [
        "θέλαμε", "θέλατε", "ήθελαν/θέλανε"]
    assert aorist_forms("ξέρω", "ήξερα")[3] == "ξέραμε"
    # Synizese: ήπια bleibt auf dem ή betont
    assert aorist_forms("πίνω", "ήπια")[3] == "ήπιαμε"


def test_aorist_sample_from_verb_list():
    """Stichprobe der Pame-A2-Verbliste: 1. Pers. Pl. aus der 1. Pers. Sg."""
    cases = {
        ("ακούω", "άκουσα"): "ακούσαμε", ("βάζω", "έβαλα"): "βάλαμε",
        ("βλέπω", "είδα"): "είδαμε", ("δίνω", "έδωσα"): "δώσαμε",
        ("κάθομαι", "έκατσα"): "κάτσαμε", ("μένω", "έμεινα"): "μείναμε",
        ("νιώθω", "ένιωσα"): "νιώσαμε", ("παίρνω", "πήρα"): "πήραμε",
        ("πάω", "πήγα"): "πήγαμε", ("στέλνω", "έστειλα"): "στείλαμε",
        ("τελειώνω", "τελείωσα"): "τελειώσαμε",
        ("κρυώνω", "κρύωσα"): "κρυώσαμε",
        ("σκέφτομαι", "σκέφτηκα"): "σκεφτήκαμε",
        ("ευχαριστώ", "ευχαρίστησα"): "ευχαριστήσαμε",
    }
    for (front, aorist), first_pl in cases.items():
        assert aorist_forms(front, aorist)[3] == first_pl, front


def test_aorist_variants_phrase_and_unaccented_input():
    # zwei Aoriste nacheinander, kanonisch der erste
    v = parse_verb(aor_verb("κάθομαι", "έκατσα/κάθισα"))
    assert conj.conjugate_aorist(v, 1, "pl") == ["κάτσαμε", "καθίσαμε"]
    # Phrase: der Rest kommt aus der Vorderseite
    v = parse_verb(aor_verb("κάνω μπάνιο", "έκανα"))
    assert conj.conjugate_aorist(v, 1, "pl") == ["κάναμε μπάνιο"]
    # unbetont eingegeben → Ton auf der drittletzten Silbe
    v = parse_verb(aor_verb("γράφω", "εγραψα"))
    assert conj.conjugate_aorist(v, 1, "sg") == ["έγραψα"]


def test_aorist_six_forms_and_unusable_input():
    v = parse_verb(aor_verb(
        "επιστρέφω", "επέστρεψα, επέστρεψες, επέστρεψε, επιστρέψαμε, "
                     "επιστρέψατε, επέστρεψαν/επιστρέψανε"))
    assert conj.conjugate_aorist(v, 1, "pl") == ["επιστρέψαμε"]
    assert conj.conjugate_aorist(v, 3, "pl") == ["επέστρεψαν", "επιστρέψανε"]
    # ein Stamm statt der 1. Person ist kein verwertbarer Aorist
    assert not conj.has_aorist(parse_verb(aor_verb("γράφω", "γράψ-")))
    assert not conj.has_aorist(parse_verb(verb("γράφω")))


def test_build_task_aorist():
    c = aor_verb("γράφω", "έγραψα", "schreiben")
    task = build_task(c, parse_verb(c), 3, "pl", tense="aorist")
    assert task.label == "Vergangenheit - 3. Pers. - Plural 👥"
    assert task.expected == "έγραψαν"
    assert task.display == "έγραψαν/γράψανε"
    assert task.tense_base == "έγραψα"
    assert task.check("γράψανε") == Result.CORRECT
    assert task.check("εγραψαν") == Result.ALMOST
    assert task.check("γράφουν") == Result.WRONG
    # ohne Aorist keine Aufgabe
    c2 = verb("μένω")
    assert build_task(c2, parse_verb(c2), 1, "sg", tense="aorist") is None


def test_build_task_imperative():
    c = VocabCard(front="κάθομαι", back="sitzen", word_type="Verb",
                  imperative="Κάτσε!/Κάθισε!")
    v = parse_verb(c)
    task = build_task(c, v, 2, "sg", tense="imperative")
    assert task.label == "Imperativ - 2. Pers. - Singular 👤"
    assert task.display == "Κάτσε!/Κάθισε!" and task.tense_base == ""
    assert task.check("κάθισε") == Result.CORRECT
    assert task.check("Κάτσε!") == Result.CORRECT
    assert task.check("κάτσετε") == Result.WRONG
    # nur 2. Person Singular
    assert build_task(c, v, 2, "pl", tense="imperative") is None
    # optionaler Teil in Klammern
    c2 = VocabCard(front="ακούω", back="hören", word_type="Verb",
                   imperative="Άκου(σε)!")
    t2 = build_task(c2, parse_verb(c2), 2, "sg", tense="imperative")
    assert t2.check("άκου") == Result.CORRECT
    assert t2.check("άκουσε") == Result.CORRECT


def test_generate_tasks_aorist_and_imperative():
    cards = [VocabCard(front="γράφω", back="schreiben", word_type="Verb",
                       aorist="έγραψα", imperative="Γράψε!"),
             verb("μένω", "wohnen")]  # ohne Aorist/Imperativ
    settings = ConjugationSettings(persons=[1], numbers=["pl"],
                                   tenses=["aorist", "imperative"])
    tasks = generate_tasks(cards, settings, rng=random.Random(1))
    # Imperativ unabhängig von der Personen-/Zahl-Auswahl (immer 2. Sg.)
    assert sorted((t.tense, t.expected) for t in tasks) == [
        ("aorist", "γράψαμε"), ("imperative", "Γράψε!")]
    # griechische Vorgabe: die 1. Sg. Aorist bleibt (sie ist nicht das Lemma)
    settings = ConjugationSettings(persons=[1], numbers=["sg"],
                                   tenses=["aorist"], direction="gr")
    assert [t.expected for t in generate_tasks(cards, settings)] == ["έγραψα"]


def test_tenses_for_level():
    assert conj.tenses_for_level("A1") == ["present", "future"]
    assert conj.tenses_for_level("A2") == [
        "present", "future", "aorist", "imperative"]
    assert conj.tenses_for_level("A2+") == conj.TENSES  # unbekannt: alle


def test_base_form_text_aorist_and_imperative():
    from mathainoa1.ui.views.grammar import _base_form_text
    c = VocabCard(front="γράφω", back="schreiben", word_type="Verb",
                  aorist="έγραψα", imperative="Γράψε!")
    v = parse_verb(c)
    aor = build_task(c, v, 2, "pl", tense="aorist")
    assert _base_form_text(aor, "both") == "έγραψα (γράφω)"
    assert _base_form_text(aor, "stem2") == "έγραψα"
    assert _base_form_text(aor, "present") == "γράφω"
    imp = build_task(c, v, 2, "sg", tense="imperative")
    assert _base_form_text(imp, "both") == "γράφω"


def test_verb_sample_shows_aorist_only_on_level():
    from mathainoa1.ui.views.grammar import _verb_sample
    v = parse_verb(VocabCard(front="γράφω", back="schreiben", word_type="Verb",
                             aorist="έγραψα", imperative="Γράψε!"))
    a1 = _verb_sample(v, conj.tenses_for_level("A1"))
    a2 = _verb_sample(v, conj.tenses_for_level("A2"))
    assert "Aorist" not in a1 and "Imperativ" not in a1
    assert "Vergangenheit: γράψατε" in a2 and "Imperativ: Γράψε!" in a2
