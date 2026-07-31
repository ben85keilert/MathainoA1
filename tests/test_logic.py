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


def test_almost_kind_accent_vs_sigma():
    # reiner Akzentfehler
    assert ac.almost_kind("καλημέρα", "καλημερα") == "accent"
    # reiner Schluss-Sigma-Fehler
    assert ac.almost_kind("ο γύρος", "ο γύροσ") == "sigma"
    # beides falsch
    assert ac.almost_kind("ο γύρος", "ο γυροσ") == "both"
    # auch über Alternativen und Klammervarianten
    assert ac.almost_kind("τρεις / τρία", "τρια") == "accent"
    assert ac.almost_kind("αγαπ(ά)ω", "αγαπαω") == "accent"


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


# --- Kommas zählen nie als Fehler ---

def test_greek_inner_comma_ignored():
    # fehlendes oder zusätzliches Komma mitten im Satz ist kein Fehler
    assert ac.check_greek("Γεια σου, τι κάνεις;",
                          "Γεια σου τι κάνεις") == Result.CORRECT
    assert ac.check_greek("Γεια σου τι κάνεις;",
                          "Γεια σου, τι κάνεις") == Result.CORRECT
    # ohne Leerzeichen nach dem Komma ebenfalls
    assert ac.check_greek("Γεια σου, τι κάνεις;",
                          "Γεια σου,τι κάνεις") == Result.CORRECT
    # Akzentfehler bleiben trotz Komma-Toleranz ALMOST
    assert ac.check_greek("Γεια σου, τι κάνεις;",
                          "Γεια σου τι κανεις") == Result.ALMOST


def test_german_full_variant_comma_ignored():
    # die komplette Rückseite ohne Kommas getippt zählt als richtig
    assert ac.check_german("Gyros, Kreis, Runde",
                           "Gyros Kreis Runde") == Result.CORRECT
    # Kommas trennen weiterhin Alternativen
    assert ac.check_german("Gyros, Kreis, Runde", "Runde") == Result.CORRECT
    assert ac.check_german("Danke, gerne", "danke gerne") == Result.CORRECT


def test_case_check_ignores_commas():
    # Fallprüfung darf ein fehlendes Komma nicht als Fehler werten
    assert ac.case_ok("Danke, gerne", "Danke gerne", german=True)


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


def _trained_progress(cs, box=4):
    from mathainoa1.storage.progress import CardProgress
    return {c.id: CardProgress(card_id=c.id, box=box, correct=box) for c in cs}


def test_repeat_round_promotion_restores_box():
    cs = cards(2)
    restored = []
    s = TrainingSession(
        cs, TrainingSettings(word_count=2, repeat_errors=True),
        progress=_trained_progress(cs), repeat_promotion="on",
        on_repeat_correct=lambda c, box: restored.append((c.id, box)))
    wrong = s.current
    s.mark(False)
    s.mark(True)
    assert s.in_repeat_round
    s.mark(True)  # richtig in der Fehlerrunde -> alte Box zurück
    assert restored == [(wrong.id, 4)]


def test_repeat_round_promotion_off_by_default():
    cs = cards(2)
    restored = []
    s = TrainingSession(
        cs, TrainingSettings(word_count=2, repeat_errors=True),
        progress=_trained_progress(cs),
        on_repeat_correct=lambda c, box: restored.append((c.id, box)))
    s.mark(False)
    s.mark(True)
    s.mark(True)
    assert restored == []


def test_repeat_round_promotion_not_on_wrong_answer():
    cs = cards(2)
    restored = []
    s = TrainingSession(
        cs, TrainingSettings(word_count=2, repeat_errors=True),
        progress=_trained_progress(cs), repeat_promotion="on",
        on_repeat_correct=lambda c, box: restored.append((c.id, box)))
    s.mark(False)
    s.mark(True)
    s.mark(False)  # auch in der Fehlerrunde falsch -> nichts wiederherstellen
    assert restored == []


def test_repeat_round_promotion_auto_depends_on_new_words():
    # "auto": Verbesserung nur, wenn keine neuen Wörter in der Runde sind
    cs = cards(2)
    prog = _trained_progress(cs)
    s = TrainingSession(cs, TrainingSettings(word_count=2),
                        progress=prog, repeat_promotion="auto")
    assert s.repeat_promotion_active()
    del prog[cs[0].id]  # eine Karte ist neu
    s2 = TrainingSession(cs, TrainingSettings(word_count=2),
                         progress=prog, repeat_promotion="auto")
    assert not s2.repeat_promotion_active()


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
    # Box-neutral gilt nur für Karten MIT Lernstand — daher mit Progress
    from mathainoa1.storage.progress import CardProgress
    recorded = []
    card = greek_card()
    s = TrainingSession([card], TrainingSettings(
        mode="typing", direction="de_gr", word_count=1,
        accent_tolerant=False),
        progress={card.id: CardProgress(card.id, box=2, correct=1)},
        on_result=lambda c, ok: recorded.append(ok))
    assert s.check_typed("καλημερα") == Result.ALMOST
    # Leitner-neutral: kein on_result-Aufruf (Box weder hoch noch zurück)
    assert recorded == []
    # zählt in der Runde als Fehler: Fehlerrunde + Rundenergebnis
    assert s.in_repeat_round and not s.finished
    stats = s.stats()
    assert stats["wrong"] == 1 and stats["wrong_cards"] == [s.current]


def test_strict_error_on_new_card_goes_to_box_1():
    """Neue (graue) Karten haben keine Box zu schützen: der strenge
    Akzent-/Schreibfehler wird normal als falsch verbucht -> Box 1."""
    from mathainoa1.storage.progress import CardProgress
    recorded = []
    s = TrainingSession([greek_card()], TrainingSettings(
        mode="typing", direction="de_gr", word_count=1,
        accent_tolerant=False), on_result=lambda c, ok: recorded.append(ok))
    assert s.check_typed("καλημερα") == Result.ALMOST
    assert recorded == [False]  # nicht mehr "neu", startet in Box 1
    # Karte mit Eintrag, aber seen == 0 zählt ebenfalls als neu
    recorded2 = []
    card = noun_card()
    s2 = TrainingSession([card], TrainingSettings(
        mode="typing", direction="de_gr", word_count=1,
        case_tolerant=False),
        progress={card.id: CardProgress(card.id)},
        on_result=lambda c, ok: recorded2.append(ok))
    assert s2.check_typed("η αθήνα") == Result.CASE
    assert recorded2 == [False]


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
    from mathainoa1.storage.progress import CardProgress
    recorded = []
    card = noun_card()
    s = TrainingSession([card], TrainingSettings(
        mode="typing", direction="de_gr", word_count=1,
        case_tolerant=False),
        progress={card.id: CardProgress(card.id, box=2, correct=1)},
        on_result=lambda c, ok: recorded.append(ok))
    # richtig, aber klein geschrieben -> CASE: Rundenfehler, Box neutral
    # (Box-neutral nur bei Karten mit Lernstand, daher mit Progress)
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
    from mathainoa1.storage.progress import CardProgress
    recorded = []
    card = greek_card()
    s = TrainingSession(
        [card],
        TrainingSettings(mode="typing", direction="de_gr", word_count=1,
                         accent_tolerant=False),
        progress={card.id: CardProgress(card.id, box=3, correct=2)},
        on_result=lambda c, ok: recorded.append(ok))
    assert s.check_typed("καλημερα") == Result.ALMOST
    assert recorded == []  # Default: Box unverändert (kein on_result)


# --- [a/b]-Gruppen und optionale deutsche Klammern ---


def test_bracket_variants():
    from mathainoa1.logic.answer_check import bracket_variants
    assert bracket_variants("Ich spreche [nicht/kein] Chinesisch.") == [
        "Ich spreche nicht Chinesisch.", "Ich spreche kein Chinesisch."]
    assert bracket_variants("ohne Gruppe") == ["ohne Gruppe"]
    # mehrere Gruppen: kartesisch
    assert len(bracket_variants("[a/b] und [c/d]")) == 4


def test_bracket_groups_german():
    from mathainoa1.logic.answer_check import check_german
    back = "Ich spreche [nicht/kein] Chinesisch."
    assert check_german(back, "Ich spreche kein Chinesisch") == Result.CORRECT
    assert check_german(back, "Ich spreche nicht Chinesisch") == Result.CORRECT
    assert check_german("Wie geht es [dir/euch/Ihnen]?",
                        "Wie geht es Ihnen") == Result.CORRECT


def test_bracket_groups_greek():
    from mathainoa1.logic.answer_check import check_greek
    front = "Πώς [είσαι/είστε];"
    assert check_greek(front, "Πώς είσαι;") == Result.CORRECT
    assert check_greek(front, "Πώς είστε;") == Result.CORRECT
    assert check_greek(front, "Πώς είναι;") == Result.WRONG
    # Akzentfehler in der Variante bleibt ALMOST
    assert check_greek(front, "Πως είστε;") == Result.ALMOST
    # nackter Top-Level-Slash bleibt Alternativen-Trenner
    assert check_greek("και / κι", "κι") == Result.CORRECT


def test_german_parens_optional():
    from mathainoa1.logic.answer_check import check_german, german_alternatives
    assert check_german("(Visiten-)Karte", "Karte") == Result.CORRECT
    assert check_german("(Visiten-)Karte", "Visitenkarte") == Result.CORRECT
    # Zusatzinfo funktioniert weiter wie bisher
    assert check_german("Sie (Akk.)", "Sie") == Result.CORRECT
    # Kommas INNERHALB von Klammern erzeugen keine Schein-Alternativen
    assert "b" not in german_alternatives("Wort (a, b)")


def test_bracket_case_ok():
    from mathainoa1.logic.answer_check import case_ok
    assert case_ok("Πώς [είσαι/είστε];", "Πώς είστε;", german=False)
    assert not case_ok("Πώς [είσαι/είστε];", "πώς είστε;", german=False)
    assert case_ok("Ich spreche [nicht/kein] Chinesisch.",
                   "Ich spreche kein Chinesisch", german=True)


# --- Kartenauswahl: heute Beantwortetes rückt ans Ende ---


def test_select_cards_demotes_answered_today():
    from datetime import datetime, timedelta
    from mathainoa1.logic.session import select_cards
    from mathainoa1.storage.progress import CardProgress

    now = datetime(2026, 7, 26, 12, 0)
    cards = [VocabCard(front=f"w{i}", back=str(i)) for i in range(4)]
    fresh, stale, due_card, new_card = cards
    progress = {
        # heute richtig beantwortet: Fälligkeit morgen (kleinste Zukunft)
        fresh.id: CardProgress(fresh.id, box=2, correct=1,
                               last_seen=now - timedelta(hours=1),
                               due=now + timedelta(days=1)),
        # gestern gesehen, Fälligkeit übermorgen
        stale.id: CardProgress(stale.id, box=3, correct=2,
                               last_seen=now - timedelta(days=1),
                               due=now + timedelta(days=2)),
        # überfällig
        due_card.id: CardProgress(due_card.id, box=1, wrong=1,
                                  last_seen=now - timedelta(days=1),
                                  due=now - timedelta(hours=1)),
    }
    # 3 Plätze: fällig + neu + ältere Rest-Karte — die heute beantwortete
    # (trotz kleinster Fälligkeit) bleibt draußen
    picked = select_cards(cards, 3, progress, now=now)
    assert set(p.id for p in picked) == {due_card.id, new_card.id, stale.id}
    # 4 Plätze: jetzt kommt sie als letzte Priorität doch mit
    picked = select_cards(cards, 4, progress, now=now)
    assert set(p.id for p in picked) == {c.id for c in cards}
