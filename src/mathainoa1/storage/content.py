"""Laden/Speichern der Vokabellisten.

- Buchlisten: read-only JSON-Dateien im mitgelieferten data/vocab/
- Eigene Listen: JSON-Dateien im App-Datenverzeichnis (user_dir)
"""

from __future__ import annotations

import csv
import json
import io
from pathlib import Path

from mathainoa1.logic.answer_check import normalize, strip_accents
from mathainoa1.models import (
    WORD_TYPES,
    SelectionList,
    VocabCard,
    VocabList,
    forms_to_text,
    parse_forms_text,
    parse_stem2_text,
)


# Stufen in aufsteigender Reihenfolge; die Stufen-Einstellung zeigt eine
# Liste, wenn ihre Stufe <= der eingestellten ist (A2 sieht also auch A1).
LEVELS = ["A1", "A2"]


def filter_level(lists, level: str) -> list[VocabList]:
    """Filtert Listen nach der eingestellten Stufe.

    Listen ohne Stufe (book=None, alle eigenen) sind immer sichtbar;
    unbekannte Stufenwerte verhalten sich wie die höchste Stufe.
    """
    if level not in LEVELS:
        return list(lists)
    rank = LEVELS.index(level)
    return [l for l in lists
            if l.book not in LEVELS or LEVELS.index(l.book) <= rank]


def load_list(path: Path) -> VocabList:
    with open(path, encoding="utf-8") as f:
        return VocabList.from_dict(json.load(f))


def save_list(vlist: VocabList, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(vlist.to_dict(), f, ensure_ascii=False, indent=2)


class ContentStore:
    """Verwaltet alle Vokabellisten: feste Buchlisten + eigene Listen."""

    def __init__(self, book_dir: Path, user_dir: Path):
        self.book_dir = book_dir
        self.user_dir = user_dir
        self.selections_dir = user_dir / "selections"
        self.annotations_path = user_dir / "annotations.json"
        self.order_path = user_dir / "list_order.json"
        self.lists: dict[str, VocabList] = {}
        self.selections: dict[str, SelectionList] = {}
        self._annotations: dict[str, dict] = {}
        self._list_order: list[str] = []
        self._selection_order: list[str] = []

    def load_all(self) -> None:
        self.lists.clear()
        for d, editable in ((self.book_dir, False), (self.user_dir, True)):
            if not d.exists():
                continue
            for p in sorted(d.glob("*.json")):
                if p.name in (self.annotations_path.name, self.order_path.name):
                    continue
                vlist = load_list(p)
                vlist.editable = editable
                self.lists[vlist.id] = vlist
        self._load_annotations()
        self._load_list_order()
        self.selections.clear()
        if self.selections_dir.exists():
            for p in sorted(self.selections_dir.glob("*.json")):
                with open(p, encoding="utf-8") as f:
                    sel = SelectionList.from_dict(json.load(f))
                self.selections[sel.id] = sel

    # --- Reihenfolge der Listen (auch Buchlisten; extern gespeichert) ---

    def _load_list_order(self) -> None:
        self._list_order = []
        self._selection_order = []
        if self.order_path.exists():
            try:
                with open(self.order_path, encoding="utf-8") as f:
                    data = json.load(f)
                order = data.get("order", [])
                if isinstance(order, list):
                    self._list_order = [i for i in order if isinstance(i, str)]
                sel_order = data.get("selections", [])
                if isinstance(sel_order, list):
                    self._selection_order = [i for i in sel_order
                                             if isinstance(i, str)]
            except (json.JSONDecodeError, OSError):
                pass  # kaputte Datei: Default-Reihenfolge statt Absturz

    def ordered_lists(self) -> list[VocabList]:
        """Alle Listen in gespeicherter Reihenfolge; unbekannte (neue) Listen
        hinten, in der bisherigen Default-Sortierung (Buchlisten zuerst)."""
        known = [self.lists[i] for i in self._list_order if i in self.lists]
        seen = set(self._list_order)
        rest = sorted((l for l in self.lists.values() if l.id not in seen),
                      key=lambda l: (l.editable, l.name))
        return known + rest

    def _write_order(self) -> None:
        self.order_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.order_path, "w", encoding="utf-8") as f:
            json.dump({"order": self._list_order,
                       "selections": self._selection_order},
                      f, ensure_ascii=False, indent=2)

    def set_list_order(self, ids: list[str]) -> None:
        """Speichert die komplette Listen-Reihenfolge (verwaiste IDs
        verschwinden dabei, weil nur die übergebenen IDs geschrieben werden)."""
        self._list_order = list(ids)
        self._write_order()

    def ordered_selections(self, kind: str = "words") -> list[SelectionList]:
        """Auswahllisten einer Art in gespeicherter Reihenfolge; neue
        hinten (alphabetisch). Adjektiv-Auswahllisten (kind="adjektive")
        erscheinen nur im Adjektivtraining."""
        known = [self.selections[i] for i in self._selection_order
                 if i in self.selections]
        seen = set(self._selection_order)
        rest = sorted((s for s in self.selections.values()
                       if s.id not in seen), key=lambda s: s.name)
        return [s for s in known + rest if s.kind == kind]

    def selections_of(self, kind: str = "words") -> list[SelectionList]:
        """Auswahllisten einer Art, alphabetisch sortiert."""
        return sorted((s for s in self.selections.values()
                       if s.kind == kind), key=lambda s: s.name)

    def set_selection_order(self, ids: list[str], kind: str = "words") -> None:
        """Reihenfolge einer Auswahllisten-Art speichern; die gespeicherte
        Reihenfolge der anderen Art bleibt dabei erhalten (eine Datei
        führt beide Arten)."""
        others = [i for i in self._selection_order
                  if i in self.selections and self.selections[i].kind != kind]
        self._selection_order = others + list(ids)
        self._write_order()

    def move_list(self, list_id: str, delta: int) -> None:
        """Verschiebt eine Liste um eine Position (klemmt an den Rändern)."""
        ids = [l.id for l in self.ordered_lists()]
        i = ids.index(list_id)
        j = i + delta
        if not 0 <= j < len(ids):
            return  # am Rand: nichts zu tun
        ids[i], ids[j] = ids[j], ids[i]
        self.set_list_order(ids)

    # --- eigene Listen ---

    def _user_path(self, vlist: VocabList) -> Path:
        return self.user_dir / f"{vlist.id}.json"

    def save_user_list(self, vlist: VocabList) -> None:
        if not vlist.editable:
            raise ValueError("Buchlisten sind nicht editierbar")
        save_list(vlist, self._user_path(vlist))
        self.lists[vlist.id] = vlist

    def delete_user_list(self, list_id: str) -> None:
        vlist = self.lists[list_id]
        if not vlist.editable:
            raise ValueError("Buchlisten können nicht gelöscht werden")
        self._user_path(vlist).unlink(missing_ok=True)
        del self.lists[list_id]

    # --- Auswahllisten (Referenzen auf bestehende Karten) ---

    def save_selection(self, sel: SelectionList) -> None:
        self.selections_dir.mkdir(parents=True, exist_ok=True)
        with open(self.selections_dir / f"{sel.id}.json", "w", encoding="utf-8") as f:
            json.dump(sel.to_dict(), f, ensure_ascii=False, indent=2)
        self.selections[sel.id] = sel

    def delete_selection(self, sel_id: str) -> None:
        (self.selections_dir / f"{sel_id}.json").unlink(missing_ok=True)
        self.selections.pop(sel_id, None)

    def cards_by_id(self) -> dict[str, VocabCard]:
        return {c.id: c for l in self.lists.values() for c in l.cards}

    def cards_for(self, source_id: str) -> list[VocabCard]:
        """Karten einer Vokabelliste ODER Auswahlliste."""
        if source_id in self.lists:
            return self.lists[source_id].cards
        if source_id in self.selections:
            by_id = self.cards_by_id()
            return [by_id[cid] for cid in self.selections[source_id].card_ids
                    if cid in by_id]
        return []

    def name_for(self, source_id: str) -> str:
        if source_id in self.lists:
            return self.lists[source_id].name
        if source_id in self.selections:
            return self.selections[source_id].name
        return "?"

    def search_cards(
        self, query: str
    ) -> list[tuple[VocabList, VocabCard, list[str]]]:
        """Sucht ein Wort (Deutsch oder Griechisch) über alle Vokabellisten.

        Case- und akzentunabhängig; Teilstring auf Vorder- oder Rückseite.
        Eine Zeile pro Karte — dasselbe Wort in zwei Listen ergibt zwei
        Treffer. Der dritte Wert nennt die Auswahllisten, in denen die Karte
        referenziert ist (leer = kein Stern).
        """
        key = strip_accents(normalize(query))
        if not key:
            return []
        results: list[tuple[VocabList, VocabCard, list[str]]] = []
        for vlist in self.ordered_lists():
            for card in vlist.cards:
                if (key in strip_accents(normalize(card.front))
                        or key in strip_accents(normalize(card.back))):
                    in_selections = [s.name for s in self.selections.values()
                                     if card.id in s.card_ids]
                    results.append((vlist, card, in_selections))
        return results

    # --- Hinweise/Notizen (auch für Buchlisten, als Overlay-Datei) ---

    def _load_annotations(self) -> None:
        self._annotations = {}
        if self.annotations_path.exists():
            with open(self.annotations_path, encoding="utf-8") as f:
                self._annotations = json.load(f)
        for card in self.cards_by_id().values():
            ann = self._annotations.get(card.id)
            if ann:
                # Altformat: hints/notes -> griechische Seite
                card.hints_gr = ann.get("hints_gr", ann.get("hints", card.hints_gr))
                card.notes_gr = ann.get("notes_gr", ann.get("notes", card.notes_gr))
                card.hints_de = ann.get("hints_de", card.hints_de)
                card.notes_de = ann.get("notes_de", card.notes_de)

    def _write_annotations(self) -> None:
        self.annotations_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.annotations_path, "w", encoding="utf-8") as f:
            json.dump(self._annotations, f, ensure_ascii=False, indent=2)

    def _remember_annotation(self, card: VocabCard) -> None:
        self._annotations[card.id] = {
            "hints_gr": card.hints_gr, "hints_de": card.hints_de,
            "notes_gr": card.notes_gr, "notes_de": card.notes_de}

    def update_notes(self, card: VocabCard, hints_gr: str, hints_de: str,
                     notes_gr: str, notes_de: str) -> None:
        """Speichert Hinweise/Notizen: Buchkarten als Overlay, eigene direkt."""
        card.hints_gr = hints_gr
        card.hints_de = hints_de
        card.notes_gr = notes_gr
        card.notes_de = notes_de
        owner = next((l for l in self.lists.values()
                      if any(c.id == card.id for c in l.cards)), None)
        if owner is not None and owner.editable:
            self.save_user_list(owner)
            return
        self._remember_annotation(card)
        self._write_annotations()

    # --- Bestehende Liste per Datei/Text aktualisieren (Abgleich über ID) ---

    def update_list_from_text(self, vlist: VocabList, text: str) -> dict:
        """Karten einer Liste aus CSV-/JSON-Text aktualisieren.

        Angefasst werden nur die Spalten, die die Datei mitbringt; eine
        leere Zelle löscht den Wert (Ausnahme front/back). Zeilen ohne
        bekannte ID werden als neue Karten angehängt, gelöscht wird nie.
        Buchlisten sind nicht editierbar — dort lassen sich nur
        Hinweise/Notizen ändern (sie liegen als Overlay daneben).
        """
        rows, fields = parse_import_rows(text)
        if not rows:
            raise ValueError("Keine Zeilen gefunden.")
        if not fields:
            raise ValueError(
                "Keine bekannten Spalten gefunden — fehlt die Kopfzeile "
                "mit den Spaltennamen (id,front,back,…)?")
        if not any(r.get("id") for r in rows):
            raise ValueError(
                "Keine ID-Spalte — ohne sie lassen sich die Zeilen keiner "
                "Karte zuordnen. Bitte die Liste mit der Spalte „ID“ "
                "exportieren, dort ändern und wieder einlesen.")
        if vlist.editable:
            result = update_cards(vlist, rows, fields)
            if result["updated"] or result["added"]:
                self.save_user_list(vlist)
            return result
        # Buchliste: nur die Overlay-Felder sind änderbar
        forbidden = [f for f in fields if f not in ANNOTATION_FIELDS]
        if forbidden:
            raise ValueError(
                "Buchlisten lassen sich nur bei Hinweisen und Notizen "
                "aktualisieren — bitte nur diese Spalten exportieren "
                "(gefunden: " + ", ".join(forbidden) + ").")
        by_id = {c.id: c for c in vlist.cards}
        result = {"updated": 0, "unchanged": 0, "added": 0, "skipped": 0}
        for row in rows:
            card = by_id.get(str(row.get("id") or ""))
            if card is None:
                result["skipped"] += 1
                continue
            if _apply_row(card, row, fields):
                self._remember_annotation(card)
                result["updated"] += 1
            else:
                result["unchanged"] += 1
        if result["updated"]:
            self._write_annotations()
        return result

    # --- Abfragen ---

    def lists_for_chapter(self, book: str, chapter: int) -> list[VocabList]:
        return [
            l for l in self.lists.values()
            if l.chapter == chapter and (l.book in (book, None))
        ]

    def general_lists(self) -> list[VocabList]:
        return [l for l in self.lists.values() if l.chapter is None]

    def all_cards(self) -> list[VocabCard]:
        return [c for l in self.lists.values() for c in l.cards]


# --- Import / Export ---

CSV_FIELDS = ["front", "back", "plural", "article", "word_type",
              "hints_gr", "hints_de", "notes_gr", "notes_de", "forms", "stem2",
              "aorist_passive", "participle"]
# Die Karten-ID ist keine inhaltliche Spalte, aber exportierbar: nur mit
# ihr findet der Update-Import (update_list_from_text) die Karte wieder
EXPORT_FIELDS = ["id"] + CSV_FIELDS


def export_csv(vlist: VocabList) -> str:
    return export_csv_columns(vlist.cards, CSV_FIELDS)


def export_csv_columns(cards: list[VocabCard], fields: list[str]) -> str:
    """CSV nur mit den gewünschten Spalten (Reihenfolge wie EXPORT_FIELDS)."""
    fields = [f for f in EXPORT_FIELDS if f in fields]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for c in cards:
        row = {k: (v if v is not None else "") for k, v in c.to_dict().items()
               if k in fields}
        if "forms" in fields:
            # forms als Text serialisieren: "gen_pl=γυναικών; 2sg=πας"
            row["forms"] = forms_to_text(c.forms)
        writer.writerow(row)
    return buf.getvalue()


VALID_ARTICLES = {"ο", "η", "το", "οι", "τα"}
# Lateinische Doppelgänger-Buchstaben, wie sie OCR/Chatbots in Artikel
# einschmuggeln (unsichtbar fürs Auge): a→α, o→ο, i→ι, n→η, t→τ
_ARTICLE_LOOKALIKES = str.maketrans("aoint", "αοιητ")


def _clean_article(raw: str) -> str | None:
    """Artikel normalisieren; None wenn kein gültiger Artikel."""
    art = (raw or "").strip().lower().translate(_ARTICLE_LOOKALIKES)
    return art if art in VALID_ARTICLES else None


def _split_leading_article(front: str) -> tuple[str | None, str]:
    """Zerlegt 'ο δρόμος' in (Artikel, Rest); toleriert Doppelgänger."""
    first, _, rest = front.partition(" ")
    art = _clean_article(first)
    if art and rest.strip():
        return art, rest.strip()
    return None, front


def _normalize_row(row: dict, word_type_fallback: str | None = None) -> dict:
    """Rohzeile (CSV/JSON) auf die Karten-Konvention bringen.

    Bearbeitet nur die tatsächlich vorhandenen Spalten — beim Update
    einer bestehenden Liste kommen oft nur einzelne Felder mit.
    word_type_fallback: Worttyp der bestehenden Karte, wenn die Zeile
    keine Worttyp-Spalte hat (entscheidet über die Artikel-Ableitung).
    """
    row = dict(row)
    if "word_type" in row:
        wt = row.get("word_type") or ""
        row["word_type"] = next(
            (t for t in WORD_TYPES if t.lower() == wt.lower()), "Sonstiges")
    word_type = row.get("word_type", word_type_fallback)
    # Artikel-Konvention herstellen: front beginnt mit dem Artikel UND
    # die article-Spalte wiederholt ihn (darauf bauen Deklination und
    # der "Artikel mittippen"-Schalter). Bei Widerspruch gewinnt der
    # sichtbare Artikel in front; abgeleitet wird er nur bei Nomen,
    # damit Phrasen wie "τα λέμε" keinen Artikel untergeschoben bekommen.
    if row.get("front"):
        col_art = _clean_article(row.get("article", ""))
        front_art, word = _split_leading_article(row["front"])
        if front_art and (col_art or word_type == "Nomen"):
            row["article"] = front_art
            row["front"] = f"{front_art} {word}"
        elif col_art:
            row["article"] = col_art
            row["front"] = f"{col_art} {row['front']}"
        elif "article" in row:
            row["article"] = None
    elif "article" in row:
        row["article"] = _clean_article(row.get("article", ""))
    if "forms" in row and not isinstance(row["forms"], dict):
        try:
            row["forms"] = parse_forms_text(row["forms"] or "")
        except ValueError:
            del row["forms"]  # kaputte Angabe lieber ignorieren als abbrechen
    for stem_field in ("stem2", "aorist_passive"):
        if stem_field in row:
            try:
                row[stem_field] = parse_stem2_text(row[stem_field] or "")
            except ValueError:
                del row[stem_field]
    return row


def import_csv(name: str, text: str, chapter: int | None = None) -> VocabList:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    cards = []
    for row in reader:
        row = {k: v.strip() for k, v in row.items()
               if k in CSV_FIELDS and v is not None and v.strip()}
        if not row.get("front") or not row.get("back"):
            continue
        row.setdefault("word_type", "")
        row = _normalize_row(row)
        if row.get("article") is None:
            row.pop("article", None)
        cards.append(VocabCard(**row))
    return VocabList(name=name, chapter=chapter, cards=cards)


# --- Update bestehender Listen (Abgleich über die Karten-ID) ---

# Felder, die auch an Buchkarten geändert werden dürfen — sie liegen als
# Overlay neben der (unveränderlichen) Buchliste (siehe update_notes)
ANNOTATION_FIELDS = ["hints_gr", "hints_de", "notes_gr", "notes_de"]
# Ohne diese Felder ergibt eine Karte keinen Sinn: eine leere Zelle löscht
# hier NICHT, sie wird übersprungen
REQUIRED_FIELDS = ["front", "back"]


def parse_import_rows(text: str) -> tuple[list[dict], list[str]]:
    """Import-Text (CSV oder JSON) als Rohzeilen + benutzte Spalten.

    Anders als import_csv/import_json wird hier NICHT auf Karten
    abgebildet: fürs Update muss unterscheidbar bleiben, welche Spalten
    die Datei überhaupt mitbringt (nur die werden angefasst) und welche
    davon leer sind (= Wert löschen). Rückgabe: (Zeilen, Spalten);
    "id" ist in den Spalten nicht enthalten, steht aber in den Zeilen.
    """
    text = text.lstrip("﻿").strip()
    if not text:
        raise ValueError("Der Text ist leer.")
    known = set(CSV_FIELDS)
    if text.startswith("{") or text.startswith("["):
        data = json.loads(text)
        raw = data if isinstance(data, list) else data.get("cards", [])
        if not isinstance(raw, list):
            raise ValueError("JSON ohne Kartenliste („cards“).")
        rows, fields = [], []
        for item in raw:
            if not isinstance(item, dict):
                continue
            row = {k: v for k, v in item.items() if k in known or k == "id"}
            rows.append(row)
            for k in row:
                if k in known and k not in fields:
                    fields.append(k)
        return rows, [f for f in CSV_FIELDS if f in fields]
    reader = csv.DictReader(io.StringIO(text))
    names = [n.strip() for n in (reader.fieldnames or [])]
    fields = [f for f in CSV_FIELDS if f in names]
    rows = []
    for raw_row in reader:
        row = {}
        for key, value in raw_row.items():
            key = (key or "").strip()
            if key in known or key == "id":
                row[key] = (value or "").strip()
        rows.append(row)
    return rows, fields


def _apply_row(card: VocabCard, row: dict, fields: list[str]) -> bool:
    """Übernimmt die Felder der Zeile in die Karte; True = etwas geändert.

    Leere Werte löschen den Inhalt — außer bei front/back (dort wäre die
    Karte danach kaputt) und bei Feldern, die die Zeile gar nicht hat."""
    changed = False
    for key in fields:
        if key not in row:
            continue
        value = row[key]
        if key in REQUIRED_FIELDS and not value:
            continue
        if key == "forms":
            value = value if isinstance(value, dict) else {}
        elif key == "article":
            value = value or None
        elif value is None:
            value = ""
        if getattr(card, key) != value:
            setattr(card, key, value)
            changed = True
    return changed


def update_cards(vlist: VocabList, rows: list[dict], fields: list[str],
                 add_new: bool = True) -> dict:
    """Karten einer Liste per ID aktualisieren, unbekannte anhängen.

    Zeilen ohne bekannte ID werden zu neuen Karten (nur mit front UND
    back). Karten der Liste, die in der Datei fehlen, bleiben unberührt —
    gelöscht wird nie. Rückgabe: Zähler für die Rückmeldung.
    """
    by_id = {c.id: c for c in vlist.cards}
    result = {"updated": 0, "unchanged": 0, "added": 0, "skipped": 0}
    for row in rows:
        card = by_id.get(str(row.get("id") or ""))
        if card is not None:
            clean = _normalize_row(row, word_type_fallback=card.word_type)
            if _apply_row(card, clean, fields):
                result["updated"] += 1
            else:
                result["unchanged"] += 1
            continue
        clean = _normalize_row(row)
        if not add_new or not clean.get("front") or not clean.get("back"):
            result["skipped"] += 1
            continue
        new_card = VocabCard(front="", back="")
        _apply_row(new_card, clean, fields)
        new_card.source = "custom"
        vlist.cards.append(new_card)
        result["added"] += 1
    return result


# --- Beispielliste (über die Hilfe hinzufügbar) ---

EXAMPLE_LIST_NAME = "Beispiel (alle Worttypen)"

# Minimalistisch, aber vollständig: je Worttyp ein Beispiel, dazu regelmäßige
# und unregelmäßige Nomen/Verben/Adjektive. Bewusst als CSV-Text, damit die
# Liste exakt das Import-/Export-Format zeigt und sich exportieren lässt.
_EXAMPLE_CSV = (
    ",".join(CSV_FIELDS) + "\n"
    '"ο δρόμος","Straße","-οι","ο","Nomen",,,,,,,,\n'
    '"η γυναίκα","Frau","-ες","η","Nomen",,,,,"gen_pl=γυναικών",,,\n'
    '"το πρόβλημα","Problem","-ματα","το","Nomen",,,,,,,,\n'
    '"το παιδί","Kind","-ιά","το","Nomen",,,,,,,,\n'
    '"γράφω","schreiben",,,"Verb",,,,,,"γράψ-","γραφτ-","γραμμένος"\n'
    '"βλέπω","sehen",,,"Verb",,,,,,'
    '"δω, δεις, δει, δούμε, δείτε, δουν/δούνε",,\n'
    '"πάω","gehen",,,"Verb",,,,,'
    '"1sg=πάω; 2sg=πας; 3sg=πάει; 1pl=πάμε; 2pl=πάτε; 3pl=πάνε",'
    '"πάω, πας, πάει, πάμε, πάτε, πάνε",,\n'
    '"μικρός","klein",,,"Adjektiv",,,,,,,,\n'
    '"γλυκός","süß",,,"Adjektiv",,,,,"fem=γλυκιά",,,\n'
    '"εδώ","hier",,,"Adverb",,,,,,,,\n'
    '"από","von, aus",,,"Präposition",,"mit Akkusativ",,,,,,\n'
    '"Τι κάνεις;","Wie geht\'s?",,,"Phrase",,,,"per du",,,,\n'
    '"πέντε","fünf",,,"Zahl",,,,,,,,\n'
    '"και","und, auch",,,"Sonstiges",,,,,,,,\n'
)


def example_vocab_list() -> VocabList:
    """Fertige Beispielliste mit allen Worttypen (regelmäßig + unregelmäßig)."""
    vlist = import_csv(EXAMPLE_LIST_NAME, _EXAMPLE_CSV)
    vlist.editable = True
    return vlist


def export_json(vlist: VocabList) -> str:
    return json.dumps(vlist.to_dict(), ensure_ascii=False, indent=2)


def export_json_columns(name: str, cards: list[VocabCard],
                        fields: list[str]) -> str:
    """JSON nur mit den gewünschten Spalten.

    Die Karten-ID wird immer mitgeschrieben: beim Reimport bleibt der
    Lernstand (progress.db) so an den Karten hängen. forms bleibt ein
    Dict (kein Text wie im CSV)."""
    fields = [f for f in CSV_FIELDS if f in fields]  # id steht schon fest
    out = {"name": name, "cards": []}
    for c in cards:
        d = c.to_dict()
        row = {"id": c.id}
        row.update({k: d[k] for k in fields})
        out["cards"].append(row)
    return json.dumps(out, ensure_ascii=False, indent=2)


def import_json(text: str) -> VocabList:
    vlist = VocabList.from_dict(json.loads(text))
    vlist.editable = True
    return vlist
