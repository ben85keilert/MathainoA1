"""Export der Lernstatistik als CSV oder JSON (reine Logik, ohne UI).

CSV: eine Zeile pro Karte aller übergebenen Listen — auch untrainierte
Karten (leere Fortschrittsspalten), damit die Datei ein vollständiges
Inventar ist. JSON: zusätzlich eine Zusammenfassung pro Liste.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from mathainoa1.models import VocabList
from mathainoa1.storage.progress import MAX_BOX, CardProgress

STATS_FIELDS = ["liste", "front", "back", "word_type", "box",
                "correct", "wrong", "streak", "last_seen", "due"]


def _iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def stats_rows(lists: list[VocabList],
               all_progress: dict[str, CardProgress]) -> list[dict]:
    rows = []
    for vlist in lists:
        for c in vlist.cards:
            p = all_progress.get(c.id)
            trained = bool(p and p.seen)
            rows.append({
                "liste": vlist.name,
                "front": c.front,
                "back": c.back,
                "word_type": c.word_type,
                "box": p.box if trained else "",
                "correct": p.correct if trained else 0,
                "wrong": p.wrong if trained else 0,
                "streak": p.streak if trained else 0,
                "last_seen": _iso(p.last_seen) if trained else "",
                "due": _iso(p.due) if trained else "",
            })
    return rows


def summarize_list(vlist: VocabList,
                   all_progress: dict[str, CardProgress]) -> dict:
    """Kennzahlen einer Liste — dieselbe Semantik wie die Statistik-View:
    trainiert = mindestens einmal beantwortet, sicher = Box 4–5."""
    boxes = {i: 0 for i in range(1, MAX_BOX + 1)}
    seen = 0
    for c in vlist.cards:
        p = all_progress.get(c.id)
        if p and p.seen:
            seen += 1
            boxes[p.box] += 1
    return {
        "id": vlist.id,
        "name": vlist.name,
        "cards": len(vlist.cards),
        "trained": seen,
        "secure": boxes[MAX_BOX - 1] + boxes[MAX_BOX],
        "boxes": boxes,
    }


def stats_csv(lists: list[VocabList],
              all_progress: dict[str, CardProgress]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=STATS_FIELDS)
    writer.writeheader()
    for row in stats_rows(lists, all_progress):
        writer.writerow(row)
    return buf.getvalue()


def stats_json(lists: list[VocabList],
               all_progress: dict[str, CardProgress], level: str) -> str:
    out = {
        "exported": datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "lists": [summarize_list(l, all_progress) for l in lists],
        "cards": stats_rows(lists, all_progress),
    }
    return json.dumps(out, ensure_ascii=False, indent=2)
