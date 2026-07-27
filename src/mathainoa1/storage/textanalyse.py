"""Textanalyse-Feature: Analyse-Dateien, Vokabellisten-Sync, Etymologie.

Eine Analyse ist ein JSON im app-definierten Schema (erzeugt vom Chatbot
nach der mitgelieferten Arbeitsanweisung III, siehe
ui/views/textanalyse.ARBEITSANWEISUNG_III). Ablage: eine Datei pro Analyse
unter app_data_dir()/features/textanalyse/<id>.json.

Reimport = Korrekturmechanismus: dieselbe id (oder derselbe Titel) ersetzt
die Analyse komplett; die daraus erzeugten Vokabellisten werden dabei so
gemergt, dass Karten-IDs — und damit der Leitner-Fortschritt — erhalten
bleiben. Die Analyse ist die Quelle der Wahrheit: Wörter, die in der
korrigierten Fassung fehlen, werden aus den Listen entfernt.

Daneben das zentrale Lexikon (Feature "lexikon"): eigenständige
Etymologie-Pakete (Arbeitsanweisung IV) werden wortweise in eine einzige
Datei gemergt — gleiches Lemma ersetzt den Eintrag (Nachbessern), Neues
kommt dazu, nichts geht verloren. Der Etymologie-Index speist sich aus
Lexikon UND Alt-Analysen mit eingebetteter Etymologie; das Lexikon hat
Vorrang.
"""

from __future__ import annotations

import datetime
import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from mathainoa1.logic.answer_check import normalize, strip_accents
from mathainoa1.models import (
    WORD_TYPES,
    SelectionList,
    VocabCard,
    VocabList,
    parse_forms_text,
    parse_stem2_text,
)
from mathainoa1.storage.content import (
    ContentStore,
    _clean_article,
    _split_leading_article,
)
from mathainoa1.storage.settings import app_data_dir, load_app_settings

FEATURE_KEY = "textanalyse"
LEXIKON_KEY = "lexikon"

# Feste Reihenfolge und Anzeigenamen der Kognaten-Gruppen
COGNATE_GROUPS = [
    ("identical", "Neugr. identisch"),
    ("related", "Neugr. verwandt"),
    ("german_latin", "Deutsch / Latein"),
]


def analyses_dir() -> Path:
    return app_data_dir() / "features" / FEATURE_KEY


def lexicon_path() -> Path:
    # Eigener Ordner, damit der Analyse-Glob in _build_index sauber bleibt
    return app_data_dir() / "features" / LEXIKON_KEY / "lexikon.json"


def word_key(text: str) -> str:
    """Normalisierter Lemma-Schlüssel: ohne Klammern, Alternativen,
    Artikel, Akzente und Groß-/Kleinschreibung."""
    text = re.sub(r"\([^)]*\)", " ", text or "")
    text = text.split("/")[0]
    text = re.sub(r"\s+", " ", text).strip()
    _art, word = _split_leading_article(text)
    return strip_accents(normalize(word))


@dataclass
class Segment:
    gr: str
    de: str
    note: str = ""

    def to_dict(self) -> dict:
        return {"gr": self.gr, "de": self.de, "note": self.note}

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        return cls(gr=str(d.get("gr", "")), de=str(d.get("de", "")),
                   note=str(d.get("note", "")))


# Phrasen haben dieselbe Struktur (gr, de, note) wie Segmente
Phrase = Segment


@dataclass
class Synonym:
    word: str
    nuance: str = ""

    def to_dict(self) -> dict:
        return {"word": self.word, "nuance": self.nuance}

    @classmethod
    def from_dict(cls, d: dict) -> "Synonym":
        return cls(word=str(d.get("word", "")), nuance=str(d.get("nuance", "")))


@dataclass
class EtymologyEntry:
    """Linguistischer Worthintergrund eines Analyseworts.

    breakdown: Wortzerlegung als [{"element": …, "meaning": …}, …]
    cognates: {"identical"|"related"|"german_latin": [{"word","meaning"},…]}
    extra_vocab: zusätzliche neugriechische Lernwörter aus Kognaten und
    Synonymen (Quelle B), als Karten-Dicts im vocab-Format.
    """

    word: str
    breakdown: list[dict] = field(default_factory=list)
    total: str = ""
    semantics: str = ""
    cognates: dict[str, list[dict]] = field(default_factory=dict)
    synonyms: list[Synonym] = field(default_factory=list)
    extra_vocab: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "breakdown": self.breakdown,
            "total": self.total,
            "semantics": self.semantics,
            "cognates": self.cognates,
            "synonyms": [s.to_dict() for s in self.synonyms],
            "extra_vocab": self.extra_vocab,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EtymologyEntry":
        cognates = {}
        raw = d.get("cognates") or {}
        if isinstance(raw, dict):
            for key, _label in COGNATE_GROUPS:
                rows = raw.get(key) or []
                if isinstance(rows, list):
                    cognates[key] = [r for r in rows if isinstance(r, dict)]
        return cls(
            word=str(d.get("word", "")),
            breakdown=[b for b in (d.get("breakdown") or [])
                       if isinstance(b, dict)],
            total=str(d.get("total", "")),
            semantics=str(d.get("semantics", "")),
            cognates=cognates,
            synonyms=[Synonym.from_dict(s) for s in (d.get("synonyms") or [])
                      if isinstance(s, dict)],
            extra_vocab=[v for v in (d.get("extra_vocab") or [])
                         if isinstance(v, dict)],
        )


@dataclass
class TextAnalysis:
    title: str
    id: str = ""
    source: str = ""
    date: str = ""
    original_text: str = ""
    translation: str = ""
    segments: list[Segment] = field(default_factory=list)
    vocab: list[dict] = field(default_factory=list)
    phrases: list[Phrase] = field(default_factory=list)
    etymology: list[EtymologyEntry] = field(default_factory=list)
    # App-verwaltet: IDs der erzeugten Listen — überleben Titeländerung
    # beim Reimport und Umbenennen der Listen durch den Nutzer
    vocab_list_id: str = ""
    etym_list_id: str = ""

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "date": self.date,
            "original_text": self.original_text,
            "translation": self.translation,
            "segments": [s.to_dict() for s in self.segments],
            "vocab": self.vocab,
            "phrases": [p.to_dict() for p in self.phrases],
            "etymology": [e.to_dict() for e in self.etymology],
            "vocab_list_id": self.vocab_list_id,
            "etym_list_id": self.etym_list_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TextAnalysis":
        return cls(
            title=str(d.get("title", "")).strip(),
            id=str(d.get("id", "")).strip(),
            source=str(d.get("source", "") or ""),
            date=str(d.get("date", "") or ""),
            original_text=str(d.get("original_text", "")),
            translation=str(d.get("translation", "")),
            segments=[Segment.from_dict(s) for s in (d.get("segments") or [])
                      if isinstance(s, dict)],
            vocab=[v for v in (d.get("vocab") or []) if isinstance(v, dict)],
            phrases=[Phrase.from_dict(p) for p in (d.get("phrases") or [])
                     if isinstance(p, dict)],
            etymology=[EtymologyEntry.from_dict(e)
                       for e in (d.get("etymology") or [])
                       if isinstance(e, dict)],
            vocab_list_id=str(d.get("vocab_list_id", "")),
            etym_list_id=str(d.get("etym_list_id", "")),
        )


def _slugify(title: str) -> str:
    slug = strip_accents(normalize(title))
    slug = re.sub(r"[^a-z0-9α-ω]+", "-", slug).strip("-")[:40]
    return f"{slug or 'analyse'}-{uuid.uuid4().hex[:6]}"


def parse_analysis(text: str) -> TextAnalysis:
    """JSON-Text in eine TextAnalysis übersetzen.

    Tolerant bei fehlenden optionalen Feldern; ValueError mit
    verständlicher deutscher Meldung bei grundlegenden Problemen.
    """
    try:
        data = json.loads(text.lstrip("﻿"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Kein gültiges JSON — ist die komplette Datei/Antwort "
            f"eingefügt? ({exc.msg}, Zeile {exc.lineno})") from exc
    if not isinstance(data, dict):
        raise ValueError("Erwartet wird ein JSON-Objekt {…} mit den "
                         "Analyse-Feldern.")
    analysis = TextAnalysis.from_dict(data)
    if not analysis.title:
        raise ValueError("Der Analyse fehlt das Pflichtfeld \"title\".")
    if not analysis.original_text and not analysis.vocab:
        raise ValueError("Die Analyse enthält weder \"original_text\" "
                         "noch \"vocab\" — falsche Datei?")
    return analysis


def card_from_entry(entry: dict) -> VocabCard | None:
    """Vokabeleintrag der Analyse in eine VocabCard übersetzen.

    Gleiche Artikel-Konvention wie der CSV-Import; unlesbare Formangaben
    werden verworfen statt den Import abzubrechen. None bei Einträgen
    ohne Vorder- oder Rückseite.
    """
    front = str(entry.get("front", "")).strip()
    back = str(entry.get("back", "")).strip()
    if not front or not back:
        return None
    wt = str(entry.get("word_type", "")).strip()
    word_type = next((t for t in WORD_TYPES if t.lower() == wt.lower()),
                     "Sonstiges")
    card = VocabCard(front=front, back=back, word_type=word_type)
    card.plural = str(entry.get("plural", "") or "").strip()
    card.hints_gr = str(entry.get("hints_gr", "") or "").strip()
    card.hints_de = str(entry.get("hints_de", "") or "").strip()
    card.notes_gr = str(entry.get("notes_gr", "") or "").strip()
    card.notes_de = str(entry.get("notes_de", "") or "").strip()
    card.participle = str(entry.get("participle", "") or "").strip()
    for stem_field in ("stem2", "aorist_passive"):
        try:
            setattr(card, stem_field,
                    parse_stem2_text(str(entry.get(stem_field, "") or "")))
        except ValueError:
            pass
    forms = entry.get("forms") or {}
    if isinstance(forms, str):
        try:
            forms = parse_forms_text(forms)
        except ValueError:
            forms = {}
    if isinstance(forms, dict):
        card.forms = {str(k): str(v) for k, v in forms.items()}
    # Artikel-Konvention wie import_csv: front trägt den Artikel sichtbar,
    # article wiederholt ihn; bei Widerspruch gewinnt der Artikel in front
    col_art = _clean_article(str(entry.get("article", "") or ""))
    front_art, word = _split_leading_article(card.front)
    if front_art and (col_art or card.word_type == "Nomen"):
        card.article = front_art
        card.front = f"{front_art} {word}"
    elif col_art:
        card.article = col_art
        card.front = f"{col_art} {card.front}"
    return card


def _copy_card_fields(src: VocabCard, dst: VocabCard) -> bool:
    """Inhaltsfelder von src auf dst übertragen (id/book/chapter/source
    bleiben). True, wenn sich dabei etwas geändert hat."""
    fields = ("front", "back", "article", "plural", "word_type", "forms",
              "stem2", "aorist_passive", "participle",
              "hints_gr", "hints_de", "notes_gr", "notes_de")
    changed = False
    for name in fields:
        if getattr(dst, name) != getattr(src, name):
            setattr(dst, name, getattr(src, name))
            changed = True
    return changed


def merge_cards(vlist: VocabList,
                entries: list[VocabCard]) -> dict[str, int]:
    """Merged die Karten einer erzeugten Liste mit dem neuen Analysestand.

    Matching primär über das normalisierte Lemma (word_key), sekundär —
    für Tippfehler-Korrekturen im Griechischen — über eindeutiges
    back+word_type-Paar. Gematchte Karten behalten ihre id (Lernstand!),
    neue kommen dazu, nicht mehr vorhandene fliegen raus. Die Reihenfolge
    ist danach die Analyse-Reihenfolge.
    """
    old_unmatched: dict[str, VocabCard] = {}
    for c in vlist.cards:
        old_unmatched.setdefault(word_key(c.front), c)
    stats = {"changed": 0, "new": 0, "removed": 0}
    result: list[VocabCard] = []
    pending: list[VocabCard] = []  # neue Einträge ohne Lemma-Match
    for new in entries:
        old = old_unmatched.pop(word_key(new.front), None)
        if old is not None:
            if _copy_card_fields(new, old):
                stats["changed"] += 1
            result.append(old)
        else:
            result.append(new)
            pending.append(new)
    # Heuristik: korrigiertes Lemma (gleiche Bedeutung + Worttyp) nicht
    # als neue Karte werten, sondern die alte Karte weiterverwenden
    for new in pending:
        candidates = [c for c in old_unmatched.values()
                      if normalize(c.back) == normalize(new.back)
                      and c.word_type == new.word_type]
        if len(candidates) == 1:
            old = candidates[0]
            del old_unmatched[word_key(old.front)]
            _copy_card_fields(new, old)
            stats["changed"] += 1
            result[result.index(new)] = old
        else:
            stats["new"] += 1
    stats["removed"] = len(old_unmatched)
    vlist.cards = result
    return stats


class AnalysisStore:
    """Verwaltet die Analyse-Dateien und hält sie mit den erzeugten
    Vokabellisten im ContentStore synchron."""

    def __init__(self, directory: Path, content: ContentStore):
        self.dir = directory
        self.content = content
        self.analyses: dict[str, TextAnalysis] = {}

    def load_all(self) -> None:
        self.analyses.clear()
        if not self.dir.exists():
            return
        for p in sorted(self.dir.glob("*.json")):
            try:
                with open(p, encoding="utf-8") as f:
                    analysis = TextAnalysis.from_dict(json.load(f))
            except (json.JSONDecodeError, OSError):
                continue  # kaputte Datei überspringen statt Absturz
            if analysis.id:
                self.analyses[analysis.id] = analysis

    def ordered(self) -> list[TextAnalysis]:
        """Neueste zuerst (nach Datum, dann Titel)."""
        return sorted(self.analyses.values(),
                      key=lambda a: (a.date == "", a.date, a.title),
                      reverse=True)

    def _path(self, analysis: TextAnalysis) -> Path:
        return self.dir / f"{analysis.id}.json"

    def _save(self, analysis: TextAnalysis) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self._path(analysis), "w", encoding="utf-8") as f:
            json.dump(analysis.to_dict(), f, ensure_ascii=False, indent=2)
        self.analyses[analysis.id] = analysis

    def _match_existing(self, analysis: TextAnalysis) -> TextAnalysis | None:
        if analysis.id and analysis.id in self.analyses:
            return self.analyses[analysis.id]
        title_key = strip_accents(normalize(analysis.title))
        return next((a for a in self.analyses.values()
                     if strip_accents(normalize(a.title)) == title_key), None)

    def import_analysis(self, text: str) -> tuple[TextAnalysis, dict]:
        """Importiert (oder korrigiert) eine Analyse aus JSON-Text.

        Rückgabe: (Analyse, Statistik) mit Statistik-Schlüsseln
        created(bool), changed, new, removed (Kartensummen beider Listen).
        """
        analysis = parse_analysis(text)
        existing = self._match_existing(analysis)
        if existing is not None:
            # Korrektur: Identität und Listen-Verknüpfung übernehmen
            analysis.id = existing.id
            analysis.vocab_list_id = existing.vocab_list_id
            analysis.etym_list_id = existing.etym_list_id
        elif not analysis.id:
            analysis.id = _slugify(analysis.title)
        stats = {"created": existing is None,
                 "changed": 0, "new": 0, "removed": 0}
        for part in self.sync_vocab_lists(analysis):
            for key in ("changed", "new", "removed"):
                stats[key] += part[key]
        self._save(analysis)
        invalidate_cache()
        return analysis, stats

    def sync_vocab_lists(self, analysis: TextAnalysis) -> list[dict]:
        """Erzeugt/aktualisiert die beiden Listen einer Analyse.

        Hauptliste aus vocab; Etymologieliste aus allen extra_vocab-
        Einträgen, gebündelt in Analyse-Reihenfolge und dedupliziert
        gegen die Hauptliste.
        """
        main_cards = [c for c in (card_from_entry(v) for v in analysis.vocab)
                      if c is not None]
        main_keys = {word_key(c.front) for c in main_cards}
        etym_cards: list[VocabCard] = []
        seen: set[str] = set(main_keys)
        for entry in analysis.etymology:
            for v in entry.extra_vocab:
                card = card_from_entry(v)
                if card is None:
                    continue
                key = word_key(card.front)
                if key in seen:
                    continue  # Dublette gegen Hauptliste/frühere Bündel
                seen.add(key)
                etym_cards.append(card)
        results = []
        for cards, id_attr, suffix in (
                (main_cards, "vocab_list_id", "Vokabeln"),
                (etym_cards, "etym_list_id", "Etymologie")):
            list_id = getattr(analysis, id_attr)
            vlist = self.content.lists.get(list_id)
            if vlist is not None and not vlist.editable:
                vlist = None  # Buchliste kann nie unsere Zielliste sein
            if vlist is None:
                if not cards:
                    continue  # keine leere Liste anlegen
                vlist = VocabList(name=f"{analysis.title} – {suffix}")
                setattr(analysis, id_attr, vlist.id)
            else:
                vlist.name = f"{analysis.title} – {suffix}"
            results.append(merge_cards(vlist, cards))
            self.content.save_user_list(vlist)
        return results

    def delete_analysis(self, analysis_id: str,
                        delete_lists: bool) -> None:
        analysis = self.analyses.pop(analysis_id, None)
        if analysis is None:
            return
        self._path(analysis).unlink(missing_ok=True)
        if delete_lists:
            for list_id in (analysis.vocab_list_id, analysis.etym_list_id):
                if list_id in self.content.lists:
                    self.content.delete_user_list(list_id)
        invalidate_cache()


def parse_lexicon_package(text: str) -> tuple[str, list[EtymologyEntry]]:
    """JSON-Text eines Etymologie-Pakets (Arbeitsanweisung IV) lesen.

    Akzeptiert auch komplette Analyse-Dateien — übernommen wird nur das
    Feld "etymology". Rückgabe: (Titel, Einträge); ValueError mit
    deutscher Meldung bei grundlegenden Problemen.
    """
    try:
        data = json.loads(text.lstrip("﻿"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Kein gültiges JSON — ist die komplette Datei/Antwort "
            f"eingefügt? ({exc.msg}, Zeile {exc.lineno})") from exc
    if not isinstance(data, dict):
        raise ValueError("Erwartet wird ein JSON-Objekt {…} mit dem "
                         "Feld \"etymology\".")
    entries = [e for e in (EtymologyEntry.from_dict(raw)
                           for raw in (data.get("etymology") or [])
                           if isinstance(raw, dict))
               if e.word.strip()]
    if not entries:
        raise ValueError("Das Paket enthält keine \"etymology\"-Einträge "
                         "— falsche Datei?")
    return str(data.get("title", "")).strip(), entries


class LexiconStore:
    """Zentrales Lexikon: eine Datei, wortweiser Merge, plus Sync der
    globalen Zusatzwörter-Liste und einer Auswahlliste pro Paket."""

    EXTRA_LIST_NAME = "Lexikon – Zusatzwörter"

    def __init__(self, path: Path, content: ContentStore):
        self.path = path
        self.content = content
        self.entries: list[EtymologyEntry] = []
        self.extra_list_id: str = ""

    def load(self) -> None:
        self.entries = []
        self.extra_list_id = ""
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, dict):
            return
        self.entries = [EtymologyEntry.from_dict(e)
                        for e in (data.get("entries") or [])
                        if isinstance(e, dict)]
        self.extra_list_id = str(data.get("extra_list_id", ""))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"schema_version": 1,
                "extra_list_id": self.extra_list_id,
                "entries": [e.to_dict() for e in self.entries]}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_package(self, text: str) -> dict:
        """Paket einlesen und wortweise mergen.

        Statistik-Schlüssel: new/updated (Lexikon-Einträge),
        extra_new/extra_updated (Karten der Zusatzwörter-Liste),
        selection (Name der erzeugten Auswahlliste oder "").
        """
        title, new_entries = parse_lexicon_package(text)
        stats = {"new": 0, "updated": 0,
                 "extra_new": 0, "extra_updated": 0, "selection": ""}
        by_key = {word_key(e.word): i for i, e in enumerate(self.entries)}
        for entry in new_entries:
            key = word_key(entry.word)
            if not key:
                continue
            pos = by_key.get(key)
            if pos is None:
                by_key[key] = len(self.entries)
                self.entries.append(entry)
                stats["new"] += 1
            else:
                self.entries[pos] = entry  # Nachbessern: Eintrag ersetzen
                stats["updated"] += 1
        card_ids = self._sync_extra_list(new_entries, stats)
        if card_ids:
            name = (f"Lexikon: {title}" if title else
                    f"Lexikon-Paket {datetime.date.today().isoformat()}")
            self.content.save_selection(
                SelectionList(name=name, card_ids=card_ids))
            stats["selection"] = name
        self.save()
        invalidate_cache()
        return stats

    def _sync_extra_list(self, new_entries: list[EtymologyEntry],
                         stats: dict) -> list[str]:
        """Zusatzwörter des Pakets in die globale Liste einpflegen.

        Additiv (nie löschen), gebündelt in Paket-Reihenfolge, dedupliziert
        gegen Ursprungswörter und Bestand; gematchte Karten behalten ihre
        id (Lernstand). Anders als sync_vocab_lists wird der Listenname
        nicht überschrieben — Umbenennungen des Nutzers bleiben.
        Rückgabe: Karten-IDs dieses Pakets (für die Auswahlliste).
        """
        seen = {word_key(e.word) for e in new_entries}
        cards: list[VocabCard] = []
        for entry in new_entries:
            for v in entry.extra_vocab:
                card = card_from_entry(v)
                if card is None:
                    continue
                key = word_key(card.front)
                if key in seen:
                    continue
                seen.add(key)
                cards.append(card)
        if not cards:
            return []
        vlist = self.content.lists.get(self.extra_list_id)
        if vlist is not None and not vlist.editable:
            vlist = None
        if vlist is None:  # noch nie erzeugt oder vom Nutzer gelöscht
            vlist = VocabList(name=self.EXTRA_LIST_NAME)
            self.extra_list_id = vlist.id
        existing: dict[str, VocabCard] = {}
        for c in vlist.cards:
            existing.setdefault(word_key(c.front), c)
        card_ids: list[str] = []
        for card in cards:
            old = existing.get(word_key(card.front))
            if old is not None:
                if _copy_card_fields(card, old):
                    stats["extra_updated"] += 1
                card_ids.append(old.id)
            else:
                vlist.cards.append(card)
                stats["extra_new"] += 1
                card_ids.append(card.id)
        self.content.save_user_list(vlist)
        return card_ids

    def delete_entry(self, word: str) -> bool:
        """Eintrag entfernen; die Zusatzwörter-Liste bleibt unberührt
        (eigenständiger Lernstoff)."""
        key = word_key(word)
        kept = [e for e in self.entries if word_key(e.word) != key]
        if len(kept) == len(self.entries):
            return False
        self.entries = kept
        self.save()
        invalidate_cache()
        return True


def lexicon_store(content: ContentStore) -> LexiconStore:
    store = LexiconStore(lexicon_path(), content)
    store.load()
    return store


# --- Feature-Zustand und Etymologie-Index (modulweit gecacht) ---
#
# Trainer und Wortlisten fragen pro Karte nach Etymologie-Infos; dafür
# jedes Mal Settings und Analyse-Dateien zu lesen wäre zu teuer. Der
# Cache wird beim Umschalten des Features und nach jedem Import über
# invalidate_cache() geleert (Muster: Settings-Cache in ui/audio.py).

_cache: dict = {"enabled": None, "index": None}


def invalidate_cache() -> None:
    _cache["enabled"] = None
    _cache["index"] = None


def feature_enabled() -> bool:
    # Der ⓘ-Infobutton lebt mit jedem der beiden Schalter
    if _cache["enabled"] is None:
        enabled = load_app_settings().enabled_features
        _cache["enabled"] = (FEATURE_KEY in enabled
                             or LEXIKON_KEY in enabled)
    return _cache["enabled"]


def _build_index() -> dict[str, EtymologyEntry]:
    index: dict[str, EtymologyEntry] = {}
    directory = analyses_dir()
    for p in sorted(directory.glob("*.json")) if directory.exists() else []:
        try:
            with open(p, encoding="utf-8") as f:
                analysis = TextAnalysis.from_dict(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
        for entry in analysis.etymology:
            key = word_key(entry.word)
            if key:
                index[key] = entry
            # Zusatzwörter (Kognaten/Synonyme) zeigen auf den Eintrag
            # ihres Analyseworts — so hat auch die Etymologie-Liste Infos
            for v in entry.extra_vocab:
                extra_key = word_key(str(v.get("front", "")))
                if extra_key:
                    index.setdefault(extra_key, entry)
    # Lexikon zuletzt: die gepflegte Quelle überschreibt Alt-Analysen
    try:
        with open(lexicon_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = None
    if isinstance(data, dict):
        for raw in data.get("entries") or []:
            if not isinstance(raw, dict):
                continue
            entry = EtymologyEntry.from_dict(raw)
            key = word_key(entry.word)
            if key:
                index[key] = entry
            for v in entry.extra_vocab:
                extra_key = word_key(str(v.get("front", "")))
                if extra_key:
                    index.setdefault(extra_key, entry)
    return index


def etymology_for(card: VocabCard) -> EtymologyEntry | None:
    """Etymologie-Eintrag zu einer Karte — None, wenn das Feature aus ist
    oder es keinen Eintrag gibt."""
    if not feature_enabled():
        return None
    if _cache["index"] is None:
        _cache["index"] = _build_index()
    return _cache["index"].get(word_key(card.front))


def missing_cards(cards: list[VocabCard]) -> list[VocabCard]:
    """Karten ohne Eintrag in Lexikon/Analysen — Input für den
    Gap-Export an Arbeitsanweisung IV. Unabhängig vom Feature-Schalter,
    damit der Export nie fälschlich "alles gedeckt" meldet."""
    if _cache["index"] is None:
        _cache["index"] = _build_index()
    index = _cache["index"]
    return [c for c in cards if word_key(c.front) not in index]
