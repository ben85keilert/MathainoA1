from datetime import datetime, timedelta

from mathainoa1.logic.session import TrainingSession, TrainingSettings, select_cards
from mathainoa1.models import VocabCard
from mathainoa1.storage.progress import BOX_INTERVALS, CardProgress, ProgressStore

NOW = datetime(2026, 7, 12, 12, 0)


def store(tmp_path) -> ProgressStore:
    return ProgressStore(tmp_path / "progress.db")


def test_leitner_box_up_and_reset(tmp_path):
    s = store(tmp_path)
    p = s.record("c1", True, NOW)
    assert (p.box, p.correct, p.streak) == (2, 1, 1)
    p = s.record("c1", True, NOW)
    assert p.box == 3
    p = s.record("c1", False, NOW)
    assert (p.box, p.wrong, p.streak) == (1, 1, 0)


def test_leitner_box_max(tmp_path):
    s = store(tmp_path)
    for _ in range(10):
        p = s.record("c1", True, NOW)
    assert p.box == 5
    assert p.due == NOW + timedelta(days=BOX_INTERVALS[5])


def test_max_box_caps(tmp_path):
    s = store(tmp_path)
    # Wiedererkennen (GR->DE) befördert höchstens bis Box 3
    for _ in range(5):
        p = s.record("c1", True, NOW, max_box=3)
    assert p.box == 3
    # DE->GR als Karteikarte: bis Box 4
    for _ in range(3):
        p = s.record("c1", True, NOW, max_box=4)
    assert p.box == 4
    # eine höhere Box bleibt bei niedrigerem Deckel stehen (keine Rückstufung)
    p = s.record("c1", True, NOW, max_box=3)
    assert p.box == 4
    # DE->GR getippt: bis Box 5
    p = s.record("c1", True, NOW, max_box=5)
    assert p.box == 5
    # Fehler setzen wie immer auf Box 1 zurück
    p = s.record("c1", False, NOW, max_box=3)
    assert p.box == 1


def test_reset(tmp_path):
    s = store(tmp_path)
    s.record("c1", True, NOW)
    s.record("c2", True, NOW)
    s.record("c3", True, NOW)
    s.reset(["c1", "c2"])
    assert s.get("c1") is None and s.get("c2") is None
    assert s.get("c3") is not None
    s.reset([])  # leer = nichts zu tun, kein Fehler


def test_progress_persisted(tmp_path):
    s = store(tmp_path)
    s.record("c1", True, NOW)
    s.close()
    s2 = store(tmp_path)
    p = s2.get("c1")
    assert p is not None and p.box == 2 and p.last_seen == NOW
    assert "c1" in s2.all()


def test_due_logic():
    p = CardProgress("c1", due=NOW + timedelta(days=1))
    assert not p.is_due(NOW)
    assert p.is_due(NOW + timedelta(days=1))
    assert CardProgress("c2").is_due(NOW)  # nie gesehen -> fällig


def test_select_cards_due_first():
    cards = [VocabCard(front=f"λ{i}", back=f"W{i}", id=f"c{i}") for i in range(4)]
    progress = {
        "c0": CardProgress("c0", due=NOW + timedelta(days=5)),   # nicht fällig
        "c1": CardProgress("c1", due=NOW - timedelta(days=2)),   # überfällig
        "c2": CardProgress("c2", due=NOW - timedelta(days=1)),   # überfällig
        # c3: neu
    }
    # Priorität bestimmt die Auswahl, die Reihenfolge wird danach gemischt
    assert {c.id for c in select_cards(cards, 10, progress, NOW)} \
        == {"c0", "c1", "c2", "c3"}
    # bei knappem Kontingent gewinnen die überfälligen Karten
    assert {c.id for c in select_cards(cards, 2, progress, NOW)} == {"c1", "c2"}


def test_session_records_via_callback(tmp_path):
    s = store(tmp_path)
    cards = [VocabCard(front="α", back="a", id="c1"),
             VocabCard(front="β", back="b", id="c2")]
    sess = TrainingSession(
        cards, TrainingSettings(word_count=2, repeat_errors=True),
        on_result=lambda card, ok: s.record(card.id, ok, NOW),
    )
    first = sess.current
    sess.mark(False)
    sess.mark(True)
    # Fehlerrunde läuft, wird aber nicht doppelt aufgezeichnet
    assert sess.in_repeat_round
    sess.mark(True)
    assert sess.finished
    assert s.get(first.id).wrong == 1 and s.get(first.id).correct == 0
    other = [c for c in cards if c is not first][0]
    assert s.get(other.id).correct == 1


# --- max_box_for_mode: Beschränkungen durch die Abfragemodi ---


def test_max_box_for_mode_defaults():
    from mathainoa1.storage.progress import max_box_for_mode
    # beide Beschränkungen an (Standard)
    assert max_box_for_mode(production=False, typed=False) == 3   # GR->DE
    assert max_box_for_mode(production=True, typed=False) == 4    # D->G Karteikarte
    assert max_box_for_mode(production=True, typed=True) == 5     # D->G getippt


def test_max_box_for_mode_both_off():
    from mathainoa1.storage.progress import max_box_for_mode
    kw = dict(high_needs_production=False, top_needs_typing=False)
    # jede Abfrageart erreicht Box 5
    assert max_box_for_mode(False, False, **kw) == 5
    assert max_box_for_mode(True, False, **kw) == 5
    assert max_box_for_mode(True, True, **kw) == 5


def test_max_box_for_mode_only_top_restriction():
    from mathainoa1.storage.progress import max_box_for_mode
    # Box 5 nur getippt (an), Box-4/5-Produktionsregel aus
    kw = dict(high_needs_production=False, top_needs_typing=True)
    assert max_box_for_mode(False, False, **kw) == 4   # Wiedererkennen bis 4
    assert max_box_for_mode(True, False, **kw) == 4    # Karteikarte bis 4
    assert max_box_for_mode(True, True, **kw) == 5     # nur getippt bis 5


def test_max_box_for_mode_only_high_restriction():
    from mathainoa1.storage.progress import max_box_for_mode
    # Box 4+5 nur Produktion (an), Box-5-Tipp-Regel aus
    kw = dict(high_needs_production=True, top_needs_typing=False)
    assert max_box_for_mode(False, False, **kw) == 3   # Wiedererkennen bis 3
    assert max_box_for_mode(True, False, **kw) == 5    # Karteikarte bis 5
    assert max_box_for_mode(True, True, **kw) == 5
