"""Trainingsrunde: Einstellungen, Kartenauswahl, Ablauf, Ergebnis."""

from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Callable

from mathainoa1.models import VocabCard
from mathainoa1.logic import answer_check
from mathainoa1.logic.answer_check import Result


@dataclass
class TrainingSettings:
    """Vom User änderbare Defaults für eine Trainingsrunde."""

    mode: str = "flashcard"  # "flashcard" | "typing"
    direction: str = "de_gr"  # "de_gr" | "gr_de" | "mixed"
    word_count: int = 7  # Standard bei Neuinstallation; Änderungen werden gespeichert
    with_article: bool = True
    repeat_errors: bool = True
    accent_tolerant: bool = True
    # Groß-/Kleinschreibung tolerieren (analog zu accent_tolerant): ist der
    # Schalter aus, zählt bei Nomen (nicht bei Phrasen) eine falsche
    # Schreibung wie ein strenger Akzentfehler — Runde ja, Leitner-Box nein
    case_tolerant: bool = True
    # Fehler der Hauptrunde bei „Nochmal“/nächstem Start derselben Liste
    # garantiert wieder aufnehmen (mit neuen Wörtern aufgefüllt)
    carry_errors_next_round: bool = True
    notes_on: bool = True  # Notizen standardmäßig bei der Frage einblenden
    hints_on: bool = False  # Hinweise nur auf Klick (bzw. hier dauerhaft)
    # Filter
    list_id: str | None = None
    task: str | None = None  # None = alle
    word_type: str | None = None  # None = alle

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TrainingSettings":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def filter_cards(cards: list[VocabCard], settings: TrainingSettings) -> list[VocabCard]:
    result = cards
    if settings.task:
        result = [c for c in result if c.task == settings.task]
    if settings.word_type:
        result = [c for c in result if c.word_type == settings.word_type]
    return result


def select_cards(cards: list[VocabCard], count: int, progress: dict | None = None,
                 now: datetime | None = None,
                 must_include: list[VocabCard] | None = None) -> list[VocabCard]:
    """Kartenauswahl nach Leitner: überfällige zuerst, dann neue, dann der Rest.

    Die Priorität bestimmt nur, WELCHE Karten in die Runde kommen (Fehler
    der Vorrunde sind sofort fällig und damit sicher dabei); die Abfrage-
    Reihenfolge der Auswahl wird gemischt, damit alte Fehler zwischen den
    übrigen/neuen Wörtern auftauchen.

    Im Rest-Topf (nicht fällig) rücken Karten, die HEUTE schon beantwortet
    wurden, ans Ende: Wer mehrere Runden am selben Tag spielt, bekommt
    gerade richtig beantwortete Wörter (kleinste Zukunfts-Fälligkeit)
    sonst immer wieder zuerst — sie kommen jetzt erst dran, wenn Fällige,
    Neue und ältere Karten aufgebraucht sind.

    progress: card_id -> CardProgress (siehe storage/progress.py); None = mischen.
    must_include: diese Karten (z.B. Fehler der Vorrunde) kommen garantiert
    in die Auswahl — vor allen anderen Töpfen, dedupliziert per id und nur
    soweit sie im Karten-Pool liegen; aufgefüllt wird wie üblich.
    """
    fixed: list[VocabCard] = []
    if must_include:
        pool_ids = {c.id for c in cards}
        seen: set[str] = set()
        for c in must_include:
            if c.id in pool_ids and c.id not in seen:
                seen.add(c.id)
                fixed.append(c)
        fixed = fixed[:count]
        cards = [c for c in cards if c.id not in seen]
        count -= len(fixed)
    if not progress:
        pool = list(cards)
        random.shuffle(pool)
        selected = fixed + pool[:count]
        random.shuffle(selected)
        return selected
    now = now or datetime.now()
    due, new, rest, rest_today = [], [], [], []
    for c in cards:
        p = progress.get(c.id)
        if p is None:
            new.append(c)
        elif p.is_due(now):
            due.append((p.due or now, c))
        elif p.last_seen is not None and p.last_seen.date() == now.date():
            rest_today.append((p.due, c))
        else:
            rest.append((p.due, c))
    due.sort(key=lambda t: t[0])
    random.shuffle(new)
    rest.sort(key=lambda t: t[0])
    rest_today.sort(key=lambda t: t[0])
    ordered = ([c for _, c in due] + new + [c for _, c in rest]
               + [c for _, c in rest_today])
    selected = fixed + ordered[:count]
    random.shuffle(selected)
    return selected


@dataclass
class Answer:
    card: VocabCard
    result: Result
    given: str = ""


@dataclass
class TrainingSession:
    cards: list[VocabCard]
    settings: TrainingSettings
    progress: dict | None = None  # card_id -> CardProgress, für "Fällige zuerst"
    on_result: Callable[[VocabCard, bool], None] | None = None  # Fortschritt aufzeichnen
    # App-Policy: strenger Akzent-/Groß-Klein-Fehler setzt die Box auf 1
    accent_resets_box: bool = False
    case_resets_box: bool = False
    # App-Policy: wohin wandert ein Wort, das in der ersten Runde falsch
    # (→ Box 1) und in der Fehlerrunde richtig beantwortet wurde?
    # "none" = bleibt Box 1, "box2" = immer Box 2, "original" = zurück in
    # die ursprüngliche Box, "step_down" = eine Box unter der
    # ursprünglichen, mindestens Box 2 (Standard)
    repeat_box_policy: str = "step_down"
    # Callback dafür: (card, Zielbox) — z.B. ProgressStore.restore_box
    on_repeat_correct: Callable[[VocabCard, int], None] | None = None
    # Karten, die garantiert in die Runde kommen (Fehler der Vorrunde bei
    # „Fehler in nächster Runde wiederholen“)
    must_include: list[VocabCard] = field(default_factory=list)
    queue: list[VocabCard] = field(init=False)
    answers: list[Answer] = field(default_factory=list)
    _wrong_pending: list[VocabCard] = field(default_factory=list)
    # Box vor dem Fehler-Reset, je falsch beantworteter Karte der Erstrunde
    _prev_box: dict[str, int] = field(default_factory=dict)
    in_repeat_round: bool = field(default=False)

    def __post_init__(self):
        self.queue = select_cards(self.cards, self.settings.word_count,
                                  self.progress,
                                  must_include=self.must_include)
        self.total_first_round = len(self.queue)
        # Bei "Gemischt": Richtung pro Karte einmal festlegen (bleibt auch in
        # der Fehlerrunde gleich)
        self._directions: dict[str, str] = {}
        if self.settings.direction == "mixed":
            for c in self.queue:
                self._directions[c.id] = random.choice(["de_gr", "gr_de"])

    # --- Ablauf ---

    @property
    def current(self) -> VocabCard | None:
        return self.queue[0] if self.queue else None

    def direction_for(self, card: VocabCard) -> str:
        if self.settings.direction == "mixed":
            return self._directions.get(card.id, "de_gr")
        return self.settings.direction

    def prompt_side(self, card: VocabCard) -> str:
        return "de" if self.direction_for(card) == "de_gr" else "gr"

    def answer_side(self, card: VocabCard) -> str:
        return "gr" if self.direction_for(card) == "de_gr" else "de"

    def prompt_for(self, card: VocabCard) -> str:
        if self.direction_for(card) == "de_gr":
            return card.back
        # GR->DE: Plural nur zur Info einblenden, er ist nicht Teil der Frage
        return card.with_plural(card.front)

    def expected_for(self, card: VocabCard) -> str:
        """Erwartete Antwort (für die Prüfung, ohne Plural-Zusatz)."""
        if self.direction_for(card) == "de_gr":
            return card.greek(self.settings.with_article)
        return card.back

    def answer_display_for(self, card: VocabCard) -> str:
        """Anzeigeform der Antwort (mit Plural-Zusatz bei Griechisch)."""
        if self.direction_for(card) == "de_gr":
            return card.with_plural(self.expected_for(card))
        return card.back

    def check_typed(self, given: str) -> Result:
        card = self.current
        assert card is not None
        if self.direction_for(card) == "de_gr":
            expected, german = self.expected_for(card), False
            result = answer_check.check_greek(expected, given)
        else:
            expected, german = card.back, True
            result = answer_check.check_german(expected, given)
        # Groß-/Kleinschreibung nur bei Nomen prüfen (nicht bei Phrasen):
        # eine sonst richtige Antwort mit falscher Schreibung wird CASE
        if (not self.settings.case_tolerant and card.word_type == "Nomen"
                and self.counts_correct(result)
                and not answer_check.case_ok(expected, given, german=german)):
            result = Result.CASE
        self._record(card, result, given)
        return result

    def mark(self, correct: bool) -> None:
        """Karteikarten-Modus: Selbstbewertung."""
        card = self.current
        assert card is not None
        self._record(card, Result.CORRECT if correct else Result.WRONG)

    def counts_correct(self, result: Result) -> bool:
        """ALMOST (nur Akzentfehler) zählt je nach Toleranz-Einstellung."""
        if result == Result.ALMOST:
            return self.settings.accent_tolerant
        return result == Result.CORRECT

    def repeat_target_box(self, card: VocabCard) -> int | None:
        """Zielbox für eine richtige Fehlerrunden-Antwort — None = keine
        Verbesserung. Neue Wörter (ohne gemerkte Box) gelten als Box 1."""
        old = self._prev_box.get(card.id, 1)
        if self.repeat_box_policy == "box2":
            return 2
        if self.repeat_box_policy == "original":
            return old if old > 1 else None
        if self.repeat_box_policy == "step_down":
            return max(2, old - 1)
        return None

    def _record(self, card: VocabCard, result: Result, given: str = "") -> None:
        self.answers.append(Answer(card, result, given))
        self.queue.pop(0)
        # Strenge Fehler (Akzent bei strenger Prüfung, Groß-/Kleinschreibung)
        # sind je nach App-Policy Leitner-neutral (Box unverändert, kein
        # on_result) oder sie setzen die Box zurück (on_result mit False).
        # In beiden Fällen zählen sie als Fehler der Runde (inkl. Fehlerrunde).
        strict_accent = (result == Result.ALMOST
                         and not self.settings.accent_tolerant)
        strict_case = result == Result.CASE
        box_neutral = ((strict_accent and not self.accent_resets_box)
                       or (strict_case and not self.case_resets_box))
        # "Box-neutral" gibt es nur bei Karten MIT Lernstand — eine neue
        # Karte hat keine Box zu schützen und würde sonst für immer als
        # "neu" (grau) gelten. Sie wird normal als falsch verbucht und
        # startet in Box 1.
        prev = (self.progress or {}).get(card.id)
        if box_neutral and (prev is None or not prev.seen):
            box_neutral = False
        if (not self.in_repeat_round and not box_neutral
                and not self.counts_correct(result)
                and prev is not None and prev.seen):
            # Box vor dem Reset merken — für die mögliche
            # Wiederherstellung in der Fehlerrunde
            self._prev_box[card.id] = prev.box
        if self.on_result and not self.in_repeat_round and not box_neutral:
            self.on_result(card, self.counts_correct(result))
        if (self.in_repeat_round and self.on_repeat_correct
                and self.counts_correct(result)):
            target = self.repeat_target_box(card)
            if target is not None:
                self.on_repeat_correct(card, target)
        if (not self.counts_correct(result) and self.settings.repeat_errors
                and not self.in_repeat_round):
            self._wrong_pending.append(card)
        if not self.queue and self._wrong_pending:
            # Fehlerrunde bewusst in Fehler-Reihenfolge (linear) — gemischt
            # wird erst die Folgerunde (siehe select_cards)
            self.queue = self._wrong_pending
            self._wrong_pending = []
            self.in_repeat_round = True

    @property
    def finished(self) -> bool:
        return not self.queue

    # --- Ergebnis ---

    def stats(self) -> dict:
        first = self.answers[: self.total_first_round]
        correct = sum(1 for a in first if self.counts_correct(a.result))
        return {
            "total": len(first),
            "correct": correct,
            "wrong": len(first) - correct,
            "wrong_cards": [a.card for a in first
                            if not self.counts_correct(a.result)],
        }
