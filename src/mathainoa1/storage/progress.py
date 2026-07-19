"""Lernfortschritt: vereinfachtes Leitner-System (5 Boxen) in SQLite.

Richtig beantwortet -> eine Box höher, Karte wird seltener fällig.
Falsch beantwortet -> zurück in Box 1, Karte ist sofort wieder fällig.
Wie hoch eine Karte steigen kann, hängt von der Abfrageart ab (Parameter
`max_box` in `record`): reines Wiedererkennen (Griechisch -> Deutsch) bis
Box 3, Deutsch -> Griechisch als Karteikarte bis Box 4, getippt (schreiben
können) bis Box 5. Eine bereits höhere Box wird nie zurückgestuft.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

MAX_BOX = 5
# Höchste Box, die über reines Wiedererkennen (GR -> DE) erreichbar ist
RECOGNITION_MAX_BOX = 3
# Höchste Box für DE -> GR im Karteikarten-Modus (Selbstbewertung);
# nur getipptes DE -> GR (schreiben können) führt bis Box 5
FLASHCARD_MAX_BOX = 4
# Tage bis zur nächsten Fälligkeit je Box
BOX_INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 30}


def max_box_for_mode(production: bool, typed: bool, *,
                     high_needs_production: bool = True,
                     top_needs_typing: bool = True) -> int:
    """Höchste per Beförderung erreichbare Box je Abfrageart.

    production: DE -> GR (aktiv erzeugen) statt GR -> DE (wiedererkennen).
    typed: getippte Produktion (schreiben) statt Karteikarte (Selbstbewertung).

    Zwei Beschränkungen (aus den App-Einstellungen, Standard an):
    - high_needs_production: Box 4+5 nur über Produktion (Wiedererkennen
      höchstens Box 3).
    - top_needs_typing: Box 5 nur über getippte Produktion (sonst höchstens
      Box 4).

    Sind beide aus, erreicht jede Abfrageart Box 5.
    """
    if production and typed:
        return MAX_BOX  # getippte Produktion erreicht immer die Spitze
    ceiling = FLASHCARD_MAX_BOX if top_needs_typing else MAX_BOX
    if not production:  # Wiedererkennen
        return RECOGNITION_MAX_BOX if high_needs_production else ceiling
    return ceiling  # Produktion per Karteikarte


@dataclass
class CardProgress:
    card_id: str
    box: int = 1
    correct: int = 0
    wrong: int = 0
    streak: int = 0
    last_seen: datetime | None = None
    due: datetime | None = None

    @property
    def seen(self) -> int:
        return self.correct + self.wrong

    def is_due(self, now: datetime) -> bool:
        return self.due is None or self.due <= now


class ProgressStore:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS card_progress (
                card_id TEXT PRIMARY KEY,
                box INTEGER NOT NULL DEFAULT 1,
                correct INTEGER NOT NULL DEFAULT 0,
                wrong INTEGER NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0,
                last_seen TEXT,
                due TEXT
            )"""
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def record(self, card_id: str, correct: bool, now: datetime | None = None,
               max_box: int = MAX_BOX) -> CardProgress:
        """max_box: höchste per Beförderung erreichbare Box dieser Abfrageart
        (GR->DE: 3, DE->GR Karteikarte: 4, DE->GR getippt: 5)."""
        now = now or datetime.now()
        p = self.get(card_id) or CardProgress(card_id)
        if correct:
            # Eine bereits höhere Box bleibt stehen, wird aber nicht
            # zurückgestuft — nur die Beförderung ist gedeckelt
            cap = max(p.box, max_box)
            p.box = min(cap, p.box + 1)
            p.correct += 1
            p.streak += 1
        else:
            p.box = 1
            p.wrong += 1
            p.streak = 0
        p.last_seen = now
        p.due = now + timedelta(days=BOX_INTERVALS[p.box])
        self.conn.execute(
            """INSERT INTO card_progress
               (card_id, box, correct, wrong, streak, last_seen, due)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(card_id) DO UPDATE SET
               box=excluded.box, correct=excluded.correct, wrong=excluded.wrong,
               streak=excluded.streak, last_seen=excluded.last_seen, due=excluded.due""",
            (p.card_id, p.box, p.correct, p.wrong, p.streak,
             p.last_seen.isoformat(), p.due.isoformat()),
        )
        self.conn.commit()
        return p

    def _row_to_progress(self, row) -> CardProgress:
        return CardProgress(
            card_id=row[0], box=row[1], correct=row[2], wrong=row[3], streak=row[4],
            last_seen=datetime.fromisoformat(row[5]) if row[5] else None,
            due=datetime.fromisoformat(row[6]) if row[6] else None,
        )

    def reset(self, card_ids: list[str]) -> None:
        """Lernstand der Karten löschen (z.B. Statistik einer Liste auf null)."""
        if not card_ids:
            return
        placeholders = ",".join("?" for _ in card_ids)
        self.conn.execute(
            f"DELETE FROM card_progress WHERE card_id IN ({placeholders})",
            list(card_ids),
        )
        self.conn.commit()

    def get(self, card_id: str) -> CardProgress | None:
        row = self.conn.execute(
            "SELECT card_id, box, correct, wrong, streak, last_seen, due"
            " FROM card_progress WHERE card_id = ?", (card_id,)
        ).fetchone()
        return self._row_to_progress(row) if row else None

    def all(self) -> dict[str, CardProgress]:
        rows = self.conn.execute(
            "SELECT card_id, box, correct, wrong, streak, last_seen, due FROM card_progress"
        ).fetchall()
        return {r[0]: self._row_to_progress(r) for r in rows}
