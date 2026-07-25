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
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from mathainoa1.logic.answer_check import normalize, strip_accents
from mathainoa1.models import WORD_TYPES, VocabCard, VocabList, parse_forms_text, parse_stem2_text
from mathainoa1.storage.content import (
    ContentStore,
    _clean_article,
    _split_leading_article,
)
from mathainoa1.storage.settings import app_data_dir, load_app_settings

FEATURE_KEY = "textanalyse"

# Feste Reihenfolge und Anzeigenamen der Kognaten-Gruppen
COGNATE_GROUPS = [
    ("identical", "Neugr. identisch"),
    ("related", "Neugr. verwandt"),
    ("german_latin", "Deutsch / Latein"),
]


def analyses_dir() -> Path:
    return app_data_dir() / "features" / FEATURE_KEY


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
    if _cache["enabled"] is None:
        _cache["enabled"] = (
            FEATURE_KEY in load_app_settings().enabled_features)
    return _cache["enabled"]


def _build_index() -> dict[str, EtymologyEntry]:
    index: dict[str, EtymologyEntry] = {}
    directory = analyses_dir()
    if not directory.exists():
        return index
    for p in sorted(directory.glob("*.json")):
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
    return index


def etymology_for(card: VocabCard) -> EtymologyEntry | None:
    """Etymologie-Eintrag zu einer Karte — None, wenn das Feature aus ist
    oder es keinen Eintrag gibt."""
    if not feature_enabled():
        return None
    if _cache["index"] is None:
        _cache["index"] = _build_index()
    return _cache["index"].get(word_key(card.front))
