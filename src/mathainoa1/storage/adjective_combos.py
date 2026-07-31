"""Kuratierte Adjektiv↔Nomen-Verbindungen für das Adjektivtraining.

Gespeichert werden die AKTIVIERTEN Paare (Whitelist) — nur sie werden
abgefragt. Schlüssel sind wortbasiert (artikel-los, akzentfrei, klein),
damit eine Verbindung listenübergreifend gilt und Kartenkopien übersteht.
Tote Verbindungen (Wort existiert in keiner Liste mehr) räumt
prune_pairs() auf.
"""

from __future__ import annotations

import json

from mathainoa1.logic.answer_check import normalize, strip_accents
from mathainoa1.storage.settings import app_data_dir


def _path():
    return app_data_dir() / "adjective_combos.json"


def combo_key(word: str) -> str:
    """Normalisierter Schlüssel eines (artikel-losen) Wortes."""
    return strip_accents(normalize(word or ""))


def load_pairs() -> dict[str, set[str]]:
    """adj_key -> Menge aktivierter noun_keys; leer bei fehlender Datei."""
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    pairs: dict[str, set[str]] = {}
    raw = data.get("pairs")
    if isinstance(raw, dict):
        for adj, nouns in raw.items():
            if isinstance(nouns, list):
                keys = {str(n) for n in nouns if n}
                if adj and keys:
                    pairs[str(adj)] = keys
    return pairs


def save_pairs(pairs: dict[str, set[str]]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"pairs": {adj: sorted(nouns)
                      for adj, nouns in sorted(pairs.items()) if nouns}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def prune_pairs(pairs: dict[str, set[str]], valid_adj_keys: set[str],
                valid_noun_keys: set[str]) -> bool:
    """Tote Verbindungen entfernen (Wort in keiner Liste mehr vorhanden).

    Verändert pairs in place; True = etwas wurde gelöscht (dann speichern).
    """
    changed = False
    for adj in list(pairs):
        if adj not in valid_adj_keys:
            del pairs[adj]
            changed = True
            continue
        kept = pairs[adj] & valid_noun_keys
        if kept != pairs[adj]:
            changed = True
            if kept:
                pairs[adj] = kept
            else:
                del pairs[adj]
    return changed
