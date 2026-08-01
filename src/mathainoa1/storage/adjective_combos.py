"""Kuratierte Adjektiv↔Nomen-Verbindungen für das Adjektivtraining.

Zwei Wörterbücher in einer Datei: "pairs" sind die AKTIVIERTEN Paare
(Whitelisting — nur sie werden abgefragt), "blocked" die AUSNAHMEN
(Blacklisting — alle Kombinationen außer ihnen). Welcher Modus gilt,
steuert AppSettings.adjective_combos_mode. Schlüssel sind wortbasiert
(artikel-los, akzentfrei, klein), damit eine Verbindung listen-
übergreifend gilt und Kartenkopien übersteht. Tote Verbindungen (Wort
existiert in keiner Liste mehr) räumt prune_combos() auf.
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


def _read_dict(data: dict, name: str) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    raw = data.get(name)
    if isinstance(raw, dict):
        for adj, nouns in raw.items():
            if isinstance(nouns, list):
                keys = {str(n) for n in nouns if n}
                if adj and keys:
                    result[str(adj)] = keys
    return result


def load_combos() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """(pairs, blocked): adj_key -> noun_keys; leer bei fehlender Datei.

    Alte Dateien enthalten nur "pairs" — "blocked" ist dann leer.
    """
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}, {}
    if not isinstance(data, dict):
        return {}, {}
    return _read_dict(data, "pairs"), _read_dict(data, "blocked")


def save_combos(pairs: dict[str, set[str]],
                blocked: dict[str, set[str]]) -> None:
    """Beide Wörterbücher schreiben — immer zusammen, damit der jeweils
    andere Modus seine Daten nicht verliert."""
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {name: {adj: sorted(nouns)
                   for adj, nouns in sorted(d.items()) if nouns}
            for name, d in (("pairs", pairs), ("blocked", blocked))}
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


def prune_combos(pairs: dict[str, set[str]], blocked: dict[str, set[str]],
                 valid_adj_keys: set[str],
                 valid_noun_keys: set[str]) -> bool:
    """prune_pairs für beide Wörterbücher; True = speichern nötig."""
    a = prune_pairs(pairs, valid_adj_keys, valid_noun_keys)
    b = prune_pairs(blocked, valid_adj_keys, valid_noun_keys)
    return a or b
