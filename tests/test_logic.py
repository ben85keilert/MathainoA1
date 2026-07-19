from mathainoa1.logic import answer_check as ac
from mathainoa1.logic.answer_check import Result
from mathainoa1.logic.session import TrainingSession, TrainingSettings, filter_cards
from mathainoa1.models import VocabCard


# --- Griechisch-Prüfung ---

def test_greek_exact():
    assert ac.check_greek("το βιβλίο", "το βιβλίο") == Result.CORRECT


def test_greek_whitespace_and_case():
    assert ac.check_greek("Καλημέρα!", "  καλημέρα! ") == Result.CORRECT


def test_greek_missing_accent_is_almost():
    # Akzentfehler sind immer ALMOST — die Session entscheidet über
    # accent_tolerant, ob das als richtig oder als Rundenfehler zählt
    assert ac.check_greek("καλημέρα", "καλημερα") == Result.ALMOST


def test_greek_final_sigma():
    assert ac.check_greek("ο γύρος", "ο γύροσ") == Result.ALMOST


def test_greek_punctuation_optional():
    assert ac.check_greek("Συγνώμη!", "Συγνώμη") == Result.CORRECT
    assert ac.check_greek("Πώς σε λένε;", "Πώς σε λένε") == Result.CORRECT


def test_greek_wrong():
    assert ac.check_greek("το βιβλίο", "η βιβλίο") == Result.WRONG


def test_greek_parentheses_optional():
    # Klammerinhalt darf, muss aber nicht getippt werden
    assert ac.check_greek("αγαπ(ά)ω", "αγαπάω") == Result.CORRECT
    assert ac.check_greek("αγαπ(ά)ω", "αγαπ(ά)ω") == Result.CORRECT
    # ohne Klammerinhalt wandert der Akzent -> akzent-unabhängig richtig
    assert ac.check_greek("αγαπ(ά)ω", "αγαπώ") == Result.CORRECT
    assert ac.check_greek("αγαπ(ά)ω", "αγαπω") == Result.CORRECT
    # volle Form bleibt akzent-streng ("Fast!")
    assert ac.check_greek("αγαπ(ά)ω", "αγαπαω") == Result.ALMOST
    assert ac.check_greek("αγαπ(ά)ω", "αγαπάει") == Result.WRONG


def test_greek_slash_alternatives():
    # "A / B" auf der griechischen Seite: jede Alternative zählt
    assert ac.check_greek("και / κι", "και") == Result.CORRECT
    assert ac.check_greek("και / κι", "κι") == Result.CORRECT
    assert ac.check_greek("και / κι", "και / κι") == Result.CORRECT
    assert ac.check_greek("τρεις / τρία", "τρια") == Result.ALMOST
    assert ac.check_greek("και / κι", "να") == Result.WRONG


def test_greek_variants():
    assert ac.greek_variants("αγαπώ") == ["αγαπώ"]
    assert set(ac.greek_variants("αγαπ(ά)ω")) == {"αγαπ(ά)ω", "αγαπάω", "αγαπω"}
    # mehrere Gruppen: alle Kombinationen
    assert "αβ" in ac.greek_variants("α(1)β(2)")
    assert "α1β2" in ac.greek_variants("α(1)β(2)")
    assert "α1β" in ac.greek_variants("α(1)β(2)")


# --- Deutsch-Prüfung ---

def test_german_alternatives():
    assert ac.check_german("Gyros, Kreis, Runde", "Kreis") == Result.CORRECT
    assert ac.check_german("und, auch", "auch") == Result.CORRECT
    assert ac.check_german("Hallo! Guten Tag!", "guten tag") == Result.CORRECT


def test_german_parentheses_ignored():
    assert ac.check_german("(Visiten-)Karte", "Karte") == Result.CORRECT
    assert ac.check_german("Danke. (wörtl.: Ich danke.)", "danke") == Result.CORRECT


def test_german_wrong_and_empty():
    assert ac.check_german("das Buch", "der Tisch") == Result.WRONG
    assert ac.check_german("das Buch", "   ") == Result.WRONG


# --- Session ---

def cards(n=5):
    return [VocabCard(front=f"λέξη{i}", back=f"Wort{i}") for i in range(n)]


def test_session_word_count_limits_queue():
    s = TrainingSession(cards(30), TrainingSettings(word_count=10))
    assert len(s.queue) == 10


def test_session_repeat_errors():
    s = TrainingSession(cards(3), TrainingSettings(word_count=3, repeat_errors=True))
    first_wrong = s.current
    s.mark(False)
    s.mark(True)
    s.mark(True)
    # Fehlerrunde: die falsche Karte kommt erneut
    assert not s.finished
    assert s.current is first_wrong
    s.mark(True)
    assert s.finished
    stats = s.stats()
    assert stats == {"total": 3, "correct": 2, "wrong": 1,
                     "wrong_cards": [first_wrong]}


def test_session_repeat_round_keeps_error_order():
    # Fehlerrunde wiederholt die falschen Karten linear in Fehler-Reihenfolge
    s = TrainingSession(cards(6), TrainingSettings(word_count=6, repeat_errors=True))
    wrong = []
    for i in range(6):
        if i % 2 == 0:
            wrong.append(s.current)
            s.mark(False)
        else:
            s.mark(True)
    assert s.in_repeat_round
    assert [id(c) for c in s.queue] == [id(c) for c in wrong]


def test_session_no_repeat_when_disabled():
    s = TrainingSession(cards(2), TrainingSettings(word_count=2, repeat_errors=False))
    s.mark(False)
    s.mark(False)
    assert s.finished


def test_session_typing_article_setting():
    card = VocabCard(front="το βιβλίο", article="το", back="das Buch")
    with_art = TrainingSession([card], TrainingSettings(
        mode="typing", direction="de_gr", with_article=True, word_count=1))
    assert with_art.check_typed("βιβλίο") == Result.WRONG

    without = TrainingSession([card], TrainingSettings(
        mode="typing", direction="de_gr", with_article=False, word_count=1,
        repeat_errors=False))
    assert without.check_typed("βιβλίο") == Result.CORRECT


def greek_card():
    return VocabCard(front="καλημέρα", back="guten Morgen")


def test_accent_error_tolerant_counts_correct():
    recorded = []
    s = TrainingSession([greek_card()], TrainingSettings(
        mode="typing", direction="de_gr", word_count=1,
        accent_tolerant=True), on_result=lambda c, ok: recorded.append(ok))
    assert s.check_typed("καλημερα") == Result.ALMOST
    assert recorded == [True]  # zählt als richtig, Box steigt
    assert s.finished  # keine Fehlerrunde
    assert s.stats()["wrong"] == 0


def test_accent_error_strict_is_round_error_but_leitner_neutral():
    recorded = []
    s = TrainingSession([greek_card()], TrainingSettings(
        mode="typing", direction="de_gr", word_count=1,
        accent_tolerant=False), on_result=lambda c, ok: recorded.append(ok))
    assert s.check_typed("καλημερα") == Result.ALMOST
    # Leitner-neutral: kein on_result-Aufruf (Box weder hoch noch zurück)
    assert recorded == []
    # zählt in der Runde als Fehler: Fehlerrunde + Rundenergebnis
    assert s.in_repeat_round and not s.finished
    stats = s.stats()
    assert stats["wrong"] == 1 and stats["wrong_cards"] == [s.current]


def test_filter_cards():
    all_cards = [
        VocabCard(front="α", back="a", task="1", word_type="Nomen"),
        VocabCard(front="β", back="b", task="2", word_type="Verb"),
    ]
    s = TrainingSettings(task="1")
    assert [c.front for c in filter_cards(all_cards, s)] == ["α"]
    s = TrainingSettings(word_type="Verb")
    assert [c.front for c in filter_cards(all_cards, s)] == ["β"]


# --- Groß-/Kleinschreibung (nur Nomen) ---


def noun_card():
    return VocabCard(front="η Αθήνα", article="η", back="Athen",
                     word_type="Nomen")


def test_case_check_greek_noun():
    recorded = []
    s = TrainingSession([noun_card()], TrainingSettings(
        mode="typing", direction="de_gr", word_count=1,
        case_tolerant=False), on_result=lambda c, ok: recorded.append(ok))
    # richtig, aber klein geschrieben -> CASE: Rundenfehler, Box neutral
    assert s.check_typed("η αθήνα") == Result.CASE
    assert recorded == []
    assert s.in_repeat_round and not s.finished
    assert s.stats()["wrong"] == 1


def test_case_check_german_noun():
    card = VocabCard(front="ο δρόμος", article="ο", back="Straße, Weg",
                     word_type="Nomen")
    s = TrainingSession([card], TrainingSettings(
        mode="typing", direction="gr_de", word_count=1, case_tolerant=False))
    assert s.check_typed("weg") == Result.CASE
    s2 = TrainingSession([card], TrainingSettings(
        mode="typing", direction="gr_de", word_count=1, case_tolerant=False))
    assert s2.check_typed("Weg") == Result.CORRECT


def test_case_check_off_by_default_and_not_for_phrases():
    # Schalter aus: Schreibung bleibt egal
    s = TrainingSession([noun_card()], TrainingSettings(
        mode="typing", direction="de_gr", word_count=1))
    assert s.check_typed("η αθήνα") == Result.CORRECT
    # Phrase: auch mit Schalter nie CASE
    phrase = VocabCard(front="Τι κάνεις;", back="Wie geht's?",
                       word_type="Phrase")
    s2 = TrainingSession([phrase], TrainingSettings(
        mode="typing", direction="de_gr", word_count=1, case_tolerant=False))
    assert s2.check_typed("τι κάνεις") == Result.CORRECT


def test_case_check_does_not_double_punish_accents():
    # Akzentfehler + richtige Schreibung: bleibt ALMOST (tolerant -> richtig)
    s = TrainingSession([noun_card()], TrainingSettings(
        mode="typing", direction="de_gr", word_count=1,
        accent_tolerant=True, case_tolerant=False))
    assert s.check_typed("η Αθηνα") == Result.ALMOST


# --- Box-Reset-Policy (App-Einstellung) ---


def test_accent_strict_resets_box_when_enabled():
    recorded = []
    s = TrainingSession(
        [greek_card()],
        TrainingSettings(mode="typing", direction="de_gr", word_count=1,
                         accent_tolerant=False),
        accent_resets_box=True,
        on_result=lambda c, ok: recorded.append(ok))
    assert s.check_typed("καλημερα") == Result.ALMOST
    # Policy an: strenger Akzentfehler setzt die Box zurück -> on_result(False)
    assert recorded == [False]
    # zählt weiterhin als Rundenfehler
    assert s.in_repeat_round and s.stats()["wrong"] == 1


def test_case_strict_resets_box_when_enabled():
    recorded = []
    s = TrainingSession(
        [noun_card()],
        TrainingSettings(mode="typing", direction="de_gr", word_count=1,
                         case_tolerant=False),
        case_resets_box=True,
        on_result=lambda c, ok: recorded.append(ok))
    assert s.check_typed("η αθήνα") == Result.CASE
    assert recorded == [False]  # Box zurück


def test_strict_errors_box_neutral_by_default():
    recorded = []
    s = TrainingSession(
        [greek_card()],
        TrainingSettings(mode="typing", direction="de_gr", word_count=1,
                         accent_tolerant=False),
        on_result=lambda c, ok: recorded.append(ok))
    assert s.check_typed("καλημερα") == Result.ALMOST
    assert recorded == []  # Default: Box unverändert (kein on_result)
