import random

from mathainoa1.logic import declension as decl
from mathainoa1.logic.answer_check import Result
from mathainoa1.logic.declension import (
    DeclensionSession,
    DeclensionSettings,
    build_task,
    decline,
    decline_adjective,
    generate_tasks,
    parse_adjective,
    parse_noun,
)
from mathainoa1.models import VocabCard


def noun(front, article, plural="", back="x"):
    return VocabCard(front=front, back=back, article=article,
                     plural=plural, word_type="Nomen")


def adj(front):
    return VocabCard(front=front, back="x", word_type="Adjektiv")


def forms(card):
    n = parse_noun(card)
    assert n is not None, f"nicht erkannt: {card.front}"
    return {(c, num): decl.decline(n, c, num)
            for c in ("nom", "acc", "gen") for num in ("sg", "pl")}


# --- Akzent-Werkzeuge ---

def test_accent_pos():
    assert decl.accent_pos("άνθρωπος") == 2
    assert decl.accent_pos("δρόμος") == 1
    assert decl.accent_pos("ουρανός") == 0
    assert decl.accent_pos("ναύτης") == 1  # αυ ist ein Diphthong
    assert decl.accent_pos("τραγούδι") == 1  # ου ebenso
    assert decl.accent_pos("και") is None


def test_set_accent_diphthong():
    # Akzent gehört auf den zweiten Vokal des Diphthongs
    assert decl.set_accent("τραγουδι", 1) == "τραγούδι"
    assert decl.set_accent("ανθρωπου", 1) == "ανθρώπου"


# --- Maskulina ---

def test_masc_os():
    f = forms(noun("ο δρόμος", "ο", "-οι"))
    assert f[("acc", "sg")] == "δρόμο"
    assert f[("gen", "sg")] == "δρόμου"
    assert f[("nom", "pl")] == "δρόμοι"
    assert f[("acc", "pl")] == "δρόμους"
    assert f[("gen", "pl")] == "δρόμων"


def test_masc_os_accent_shift():
    f = forms(noun("ο άνθρωπος", "ο", "-οι"))
    assert f[("acc", "sg")] == "άνθρωπο"  # kein Akzentwechsel
    assert f[("gen", "sg")] == "ανθρώπου"
    assert f[("acc", "pl")] == "ανθρώπους"
    assert f[("gen", "pl")] == "ανθρώπων"


def test_masc_os_oxytone():
    f = forms(noun("ο ουρανός", "ο", "-οί"))
    assert f[("acc", "sg")] == "ουρανό"
    assert f[("gen", "sg")] == "ουρανού"
    assert f[("nom", "pl")] == "ουρανοί"
    assert f[("acc", "pl")] == "ουρανούς"
    assert f[("gen", "pl")] == "ουρανών"


def test_masc_as():
    f = forms(noun("ο άντρας", "ο", "-ες"))
    assert f[("acc", "sg")] == "άντρα"
    assert f[("gen", "sg")] == "άντρα"
    assert f[("nom", "pl")] == "άντρες"
    assert f[("acc", "pl")] == "άντρες"
    assert f[("gen", "pl")] == "αντρών"


def test_masc_as_proparoxytone():
    f = forms(noun("ο πίνακας", "ο", "-ες"))
    assert f[("gen", "pl")] == "πινάκων"


def test_masc_is():
    f = forms(noun("ο ναύτης", "ο", "-ες"))
    assert f[("acc", "sg")] == "ναύτη"
    assert f[("gen", "sg")] == "ναύτη"
    assert f[("gen", "pl")] == "ναυτών"


def test_masc_es_kafes():
    f = forms(noun("ο καφές", "ο", "-έδες"))
    assert f[("acc", "sg")] == "καφέ"
    assert f[("gen", "sg")] == "καφέ"
    assert f[("nom", "pl")] == "καφέδες"
    assert f[("gen", "pl")] == "καφέδων"


def test_masc_ous_pappous():
    f = forms(noun("ο παππούς", "ο", "-ούδες"))
    assert f[("acc", "sg")] == "παππού"
    assert f[("nom", "pl")] == "παππούδες"
    assert f[("gen", "pl")] == "παππούδων"


# --- Feminina ---

def test_fem_a():
    f = forms(noun("η ταβέρνα", "η", "-ες"))
    assert f[("acc", "sg")] == "ταβέρνα"
    assert f[("gen", "sg")] == "ταβέρνας"
    assert f[("nom", "pl")] == "ταβέρνες"
    assert f[("gen", "pl")] == "ταβερνών"


def test_fem_a_gen_pl_third_declension():
    # -ίδα/-άδα/-όνα behalten die Betonung
    assert forms(noun("η σελίδα", "η", "-ες"))[("gen", "pl")] == "σελίδων"
    assert forms(noun("η ομάδα", "η", "-ες"))[("gen", "pl")] == "ομάδων"
    assert forms(noun("η εικόνα", "η", "-ες"))[("gen", "pl")] == "εικόνων"


def test_fem_a_gen_pl_exception():
    assert forms(noun("η μητέρα", "η", "-ες"))[("gen", "pl")] == "μητέρων"


def test_fem_i():
    f = forms(noun("η τέχνη", "η", "-ες"))
    assert f[("gen", "sg")] == "τέχνης"
    assert f[("nom", "pl")] == "τέχνες"
    assert f[("gen", "pl")] == "τεχνών"


def test_fem_si_third_declension():
    f = forms(noun("η άσκηση", "η", "-(ήσ)εις"))
    assert f[("acc", "sg")] == "άσκηση"
    assert f[("gen", "sg")] == "άσκησης"
    assert f[("nom", "pl")] == "ασκήσεις"
    assert f[("acc", "pl")] == "ασκήσεις"
    assert f[("gen", "pl")] == "ασκήσεων"


def test_fem_poli():
    # Pluralangabe "-εις" klassifiziert als 3. Deklination (f3),
    # auch ohne -ση/-ξη/-ψη-Endung — wichtig für den Genitiv Plural
    f = forms(noun("η πόλη", "η", "-εις"))
    assert f[("gen", "sg")] == "πόλης"
    assert f[("nom", "pl")] == "πόλεις"
    assert f[("acc", "pl")] == "πόλεις"
    assert f[("gen", "pl")] == "πόλεων"


def test_fem_os():
    f = forms(noun("η είσοδος", "η"))
    assert f[("acc", "sg")] == "είσοδο"
    assert f[("gen", "sg")] == "εισόδου"
    assert f[("nom", "pl")] == "είσοδοι"
    assert f[("acc", "pl")] == "εισόδους"


# --- Neutra ---

def test_neut_o():
    f = forms(noun("το θέατρο", "το", "-α"))
    assert f[("acc", "sg")] == "θέατρο"
    assert f[("gen", "sg")] == "θεάτρου"
    assert f[("nom", "pl")] == "θέατρα"
    assert f[("gen", "pl")] == "θεάτρων"


def test_neut_o_oxytone():
    f = forms(noun("το βουνό", "το", "-ά"))
    assert f[("gen", "sg")] == "βουνού"
    assert f[("nom", "pl")] == "βουνά"
    assert f[("gen", "pl")] == "βουνών"


def test_neut_i():
    f = forms(noun("το σπίτι", "το", "-ια"))
    assert f[("gen", "sg")] == "σπιτιού"
    assert f[("nom", "pl")] == "σπίτια"
    assert f[("gen", "pl")] == "σπιτιών"


def test_neut_i_oxytone():
    f = forms(noun("το παιδί", "το", "-ιά"))
    assert f[("gen", "sg")] == "παιδιού"
    assert f[("nom", "pl")] == "παιδιά"
    assert f[("gen", "pl")] == "παιδιών"


def test_neut_i_default_plural():
    # ohne Pluralangabe: Regelform
    assert forms(noun("το τραγούδι", "το"))[("nom", "pl")] == "τραγούδια"
    assert forms(noun("το παιδί", "το"))[("nom", "pl")] == "παιδιά"


def test_neut_ma():
    f = forms(noun("το μάθημα", "το", "-ματα"))
    assert f[("gen", "sg")] == "μαθήματος"
    assert f[("nom", "pl")] == "μαθήματα"
    assert f[("gen", "pl")] == "μαθημάτων"


def test_neut_os():
    f = forms(noun("το λάθος", "το", "-η"))
    assert f[("gen", "sg")] == "λάθους"
    assert f[("nom", "pl")] == "λάθη"
    assert f[("gen", "pl")] == "λαθών"


# --- Sonderfälle ---

def test_indeclinable():
    f = forms(noun("το μετρό", "το", "-"))
    assert f[("acc", "sg")] == "μετρό"
    assert f[("gen", "sg")] == "μετρό"
    assert f[("gen", "pl")] == "μετρό"


def test_indeclinable_multiword():
    f = forms(noun("το μίνι μάρκετ", "το", "-"))
    assert f[("gen", "sg")] == "μίνι μάρκετ"


def test_plural_only_neuter():
    n = parse_noun(noun("τα ελληνικά", "τα"))
    assert n is not None and n.plural_only
    assert decline(n, "acc", "pl") == "ελληνικά"
    assert decline(n, "gen", "pl") == "ελληνικών"
    assert decline(n, "acc", "sg") is None  # kein Singular


def test_plural_only_masc():
    n = parse_noun(noun("οι αριθμοί", "οι"))
    assert decline(n, "acc", "pl") == "αριθμούς"
    assert decline(n, "gen", "pl") == "αριθμών"


def test_plural_only_fem():
    n = parse_noun(noun("οι διακοπές", "οι"))
    assert n.gender == "f"
    assert decline(n, "acc", "pl") == "διακοπές"
    assert decline(n, "gen", "pl") == "διακοπών"


def test_unparseable_skipped():
    assert parse_noun(noun("το λαϊκό πανεπιστήμιο", "το")) is None
    assert parse_noun(VocabCard(front="τρέχω", back="laufen",
                                word_type="Verb")) is None


def test_parenthetical_stripped():
    n = parse_noun(noun("η βιβλιοθήκη (ΕΕ)", "η"))
    assert n is not None and n.word == "βιβλιοθήκη"


# --- Adjektive ---

def test_adjective_forms():
    a = parse_adjective(adj("μικρός"))
    assert decline_adjective(a, "m", "acc", "sg") == "μικρό"
    assert decline_adjective(a, "m", "acc", "pl") == "μικρούς"
    assert decline_adjective(a, "f", "nom", "sg") == "μικρή"
    assert decline_adjective(a, "f", "gen", "sg") == "μικρής"
    assert decline_adjective(a, "f", "acc", "pl") == "μικρές"
    assert decline_adjective(a, "n", "gen", "sg") == "μικρού"
    assert decline_adjective(a, "n", "nom", "pl") == "μικρά"
    assert decline_adjective(a, "n", "gen", "pl") == "μικρών"


def test_adjective_fem_after_vowel():
    assert parse_adjective(adj("νέος")).fem == "νέα"
    assert parse_adjective(adj("μέτριος")).fem == "μέτρια"
    assert parse_adjective(adj("ωραίος")).fem == "ωραία"


def test_adjective_fem_exception():
    assert parse_adjective(adj("γλυκός")).fem == "γλυκιά"


def test_adjective_no_accent_shift():
    a = parse_adjective(adj("όμορφος"))
    assert decline_adjective(a, "m", "gen", "sg") == "όμορφου"


# --- Aufgaben ---

def test_build_task_with_article():
    n = noun("ο δρόμος", "ο", "-οι")
    task = build_task(n, parse_noun(n), "acc", "sg")
    assert task.prompt == "ο δρόμος"
    assert task.expected == "τον δρόμο"
    assert task.label == "Akkusativ Singular"


def test_build_task_feminine_article_variants():
    n = noun("η ταβέρνα", "η", "-ες")
    task = build_task(n, parse_noun(n), "acc", "sg")
    assert task.expected == "την ταβέρνα"
    assert task.check("τη ταβέρνα") == Result.CORRECT
    assert task.check("την ταβέρνα") == Result.CORRECT
    assert task.check("το ταβέρνα") == Result.WRONG


def test_build_task_accent_tolerance():
    # Akzentfehler sind immer ALMOST — wie streng das zählt,
    # entscheidet die Session über accent_tolerant
    n = noun("ο δρόμος", "ο", "-οι")
    task = build_task(n, parse_noun(n), "gen", "sg")
    assert task.check("του δρομου") == Result.ALMOST


def test_build_task_with_adjective():
    n = noun("ο δρόμος", "ο", "-οι")
    a = parse_adjective(adj("μικρός"))
    task = build_task(n, parse_noun(n), "acc", "pl", a)
    assert task.prompt == "ο μικρός δρόμος"
    assert task.expected == "τους μικρούς δρόμους"


def test_build_task_adjective_feminine_agreement():
    n = noun("η ταβέρνα", "η", "-ες")
    a = parse_adjective(adj("μεγάλος"))
    task = build_task(n, parse_noun(n), "gen", "sg", a)
    assert task.prompt == "η μεγάλη ταβέρνα"
    assert task.expected == "της μεγάλης ταβέρνας"


def test_generate_tasks_and_session():
    cards = [
        noun("ο δρόμος", "ο", "-οι"),
        noun("η ταβέρνα", "η", "-ες"),
        noun("το σπίτι", "το", "-ια"),
        adj("μικρός"),
        VocabCard(front="τρέχω", back="laufen", word_type="Verb"),
    ]
    settings = DeclensionSettings(cases=["acc", "gen"], numbers=["sg", "pl"],
                                  with_adjectives=True, word_count=5)
    tasks = generate_tasks(cards, settings, rng=random.Random(1))
    assert len(tasks) == 3 * 4  # 3 Nomen × 2 Fälle × 2 Zahlen
    session = DeclensionSession(tasks, settings)
    assert len(session.queue) == 5
    first = session.current
    session.check_typed(first.expected)
    assert session.answers[-1].result == Result.CORRECT


def test_session_repeat_round():
    cards = [noun("ο δρόμος", "ο", "-οι")]
    settings = DeclensionSettings(cases=["acc"], numbers=["sg"],
                                  repeat_errors=True, word_count=5)
    session = DeclensionSession(generate_tasks(cards, settings), settings)
    session.check_typed("falsch")
    assert session.in_repeat_round
    assert session.current is not None
    session.check_typed("τον δρόμο")
    assert session.finished
    stats = session.stats()
    assert stats["total"] == 1 and stats["wrong"] == 1


def test_settings_roundtrip():
    s = DeclensionSettings(cases=["acc", "gen"], with_adjectives=True)
    assert DeclensionSettings.from_dict(s.to_dict()) == s


# --- Unregelmäßige Formen (Karten-Feld forms) ---

def test_noun_form_override():
    c = noun("η γάτα", "η", "-ες")
    c.forms = {"gen_pl": "γατών"}
    f = forms(c)
    assert f[("gen", "pl")] == "γατών"
    assert f[("acc", "sg")] == "γάτα"  # übrige Formen weiter regelbasiert


def test_noun_nom_pl_override():
    c = noun("το φαγητό", "το")
    c.forms = {"nom_pl": "φαγητά"}
    f = forms(c)
    assert f[("nom", "pl")] == "φαγητά"


def test_custom_noun_via_forms():
    # unbekanntes Muster: ohne forms übersprungen, mit forms abfragbar
    c = noun("το φως", "το")
    assert parse_noun(c) is None
    c.forms = {"acc_sg": "φως", "gen_sg": "φωτός",
               "nom_pl": "φώτα", "acc_pl": "φώτα", "gen_pl": "φώτων"}
    f = forms(c)
    assert f[("gen", "sg")] == "φωτός"
    assert f[("nom", "pl")] == "φώτα"
    assert f[("nom", "sg")] == "φως"


def test_custom_noun_missing_form_skips_task():
    c = noun("το φως", "το")
    c.forms = {"gen_sg": "φωτός"}
    n = parse_noun(c)
    assert decl.decline(n, "gen", "sg") == "φωτός"
    assert decl.decline(n, "acc", "pl") is None  # keine Aufgabe erzeugen


def test_adjective_fem_override_via_forms():
    c = adj("ελαφρύς")  # kein -ος-Typ: bleibt unerkannt
    assert parse_adjective(c) is None
    c2 = adj("κακός")
    c2.forms = {"fem": "κακιά"}
    a = parse_adjective(c2)
    assert a.fem == "κακιά"
    assert decline_adjective(a, "f", "nom", "sg") == "κακιά"


# --- Vorgabe Deutsch (direction="de") ---

def test_build_task_direction_de():
    c = noun("ο δρόμος", "ο", "-οι", back="der Weg")
    n = parse_noun(c)
    task = build_task(c, n, "acc", "sg", direction="de")
    assert task.prompt == "der Weg"
    assert task.meaning == ""
    assert task.expected == "τον δρόμο"


def test_build_task_direction_de_with_adjective():
    c = noun("ο δρόμος", "ο", "-οι", back="der Weg")
    a = parse_adjective(VocabCard(front="μικρός", back="klein",
                                  word_type="Adjektiv"))
    task = build_task(c, parse_noun(c), "acc", "sg", adj=a, direction="de")
    assert task.prompt == "klein + der Weg"
    assert task.expected == "τον μικρό δρόμο"


def test_session_on_result_positive_only():
    cards = [noun("ο δρόμος", "ο", "-οι", back="der Weg"),
             noun("η ώρα", "η", "-ες", back="die Stunde")]
    settings = DeclensionSettings(cases=["acc"], numbers=["sg"],
                                  direction="de", repeat_errors=False,
                                  word_count=5)
    recorded = []
    session = DeclensionSession(
        generate_tasks(cards, settings, rng=random.Random(1)), settings,
        on_result=lambda card, ok: recorded.append((card.front, ok)))
    session.check_typed(session.current.expected)
    session.check_typed("falsch")
    assert len(recorded) == 2
    assert recorded[0][1] is True and recorded[1][1] is False


# --- Groß-/Kleinschreibung (nur Nomen, Eigennamen) ---


def test_declension_case_check_proper_noun():
    cards = [noun("η Αθήνα", "η", "-", back="Athen")]
    settings = DeclensionSettings(cases=["acc"], numbers=["sg"],
                                  case_tolerant=False, word_count=5)
    session = DeclensionSession(generate_tasks(cards, settings), settings)
    exp = session.current.expected  # "την Αθήνα"
    # klein geschrieben: sonst richtig -> CASE, Rundenfehler, Box neutral
    result = session.check_typed(exp.lower())
    assert result == Result.CASE
    assert session.in_repeat_round and not session.finished
    assert session.stats()["wrong"] == 1


def test_declension_case_tolerant_default():
    cards = [noun("η Αθήνα", "η", "-", back="Athen")]
    settings = DeclensionSettings(cases=["acc"], numbers=["sg"], word_count=5)
    session = DeclensionSession(generate_tasks(cards, settings), settings)
    # Standard tolerant: Schreibung egal
    assert session.check_typed(session.current.expected.lower()) == Result.CORRECT


def test_declension_case_leitner_neutral():
    cards = [noun("η Αθήνα", "η", "-", back="Athen")]
    settings = DeclensionSettings(cases=["acc"], numbers=["sg"], direction="de",
                                  case_tolerant=False, repeat_errors=False,
                                  word_count=5)
    recorded = []
    session = DeclensionSession(
        generate_tasks(cards, settings), settings,
        on_result=lambda card, ok: recorded.append(ok))
    session.check_typed(session.current.expected.lower())  # CASE
    assert recorded == []  # kein on_result -> Vokabel-Box unverändert


def test_declension_accent_resets_box_policy():
    cards = [noun("η Αθήνα", "η", "-", back="Athen")]
    settings = DeclensionSettings(cases=["acc"], numbers=["sg"], direction="de",
                                  case_tolerant=False, word_count=5)
    recorded = []
    session = DeclensionSession(
        generate_tasks(cards, settings), settings, case_resets_box=True,
        on_result=lambda card, ok: recorded.append(ok))
    session.check_typed(session.current.expected.lower())  # CASE
    assert recorded == [False]  # Policy an -> Box zurück


# --- Nominativ-Training (nur Plural = Pluraltraining) ---


def test_nominative_tasks_only_plural():
    cards = [noun("ο δρόμος", "ο", "-οι")]
    settings = DeclensionSettings(cases=["nom"], numbers=["sg", "pl"],
                                  word_count=10)
    tasks = generate_tasks(cards, settings)
    # Nominativ Singular ist die Vorgabe selbst -> nur die Plural-Aufgabe
    assert [(t.case, t.number) for t in tasks] == [("nom", "pl")]
    t = tasks[0]
    assert t.prompt == "ο δρόμος" and t.expected == "οι δρόμοι"
    assert t.check("οι δρόμοι") == Result.CORRECT


def test_nominative_skips_plural_only_nouns():
    # reine Pluralwörter: Vorgabe = Lösung, also keine Aufgabe
    cards = [noun("οι διακοπές", "οι")]
    settings = DeclensionSettings(cases=["nom"], numbers=["sg", "pl"],
                                  word_count=10)
    assert generate_tasks(cards, settings) == []


def test_nominative_plural_with_adjective():
    cards = [noun("ο δρόμος", "ο", "-οι"), adj("μικρός")]
    settings = DeclensionSettings(cases=["nom"], numbers=["pl"],
                                  with_adjectives=True, word_count=10)
    tasks = generate_tasks(cards, settings, rng=random.Random(1))
    assert tasks and tasks[0].expected == "οι μικροί δρόμοι"
