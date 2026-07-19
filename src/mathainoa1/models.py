"""Datenmodell: Vokabellisten und -karten.

Inhalte werden als JSON gespeichert (siehe storage/content.py).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict

WORD_TYPES = [
    "Nomen",
    "Verb",
    "Adjektiv",
    "Adverb",
    "Präposition",
    "Phrase",
    "Zahl",
    "Sonstiges",
]

# Gültige Schlüssel für unregelmäßige Formen (Feld VocabCard.forms).
# Nomen: einzelne Fälle überschreiben die regelbasierte Deklination.
# Adjektive: abweichendes Femininum. Verben: einzelne Präsensformen
# (mehrere richtige Formen mit "/" trennen, z.B. "2pl=είστε/είσαστε").
NOUN_FORM_KEYS = ["acc_sg", "gen_sg", "nom_pl", "acc_pl", "gen_pl"]
ADJ_FORM_KEYS = ["fem"]
VERB_FORM_KEYS = ["1sg", "2sg", "3sg", "1pl", "2pl", "3pl"]
FORM_KEYS = set(NOUN_FORM_KEYS) | set(ADJ_FORM_KEYS) | set(VERB_FORM_KEYS)

# Reihenfolge der Deklinationsfelder im Karten-Editor
NOUN_EDITOR_KEYS = ["gen_sg", "gen_pl", "acc_sg", "acc_pl"]


def forms_to_text(forms: dict[str, str]) -> str:
    """Formen-Dict als editierbaren Text: 'gen_pl=γυναικών; fem=γλυκιά'."""
    return "; ".join(f"{k}={v}" for k, v in forms.items())


def parse_forms_text(text: str) -> dict[str, str]:
    """Text aus dem Editor zurück ins Dict; ValueError bei ungültigem Schlüssel."""
    forms: dict[str, str] = {}
    for part in text.replace("\n", ";").split(";"):
        part = part.strip()
        if not part:
            continue
        key, sep, value = part.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not value:
            raise ValueError(f"Ungültiger Eintrag: „{part}“ (Format: schlüssel=form)")
        if key not in FORM_KEYS:
            raise ValueError(f"Unbekannter Schlüssel: „{key}“")
        forms[key] = value
    return forms


def verb_forms_to_text(forms: dict[str, str]) -> str:
    """Verbformen als Kommaliste in Personenreihenfolge 1sg..3pl.

    Regelmäßige (fehlende) Slots werden als "-" ausgegeben; enthält das
    Dict gar keine Verbform, kommt "" zurück.
    """
    if not any(k in forms for k in VERB_FORM_KEYS):
        return ""
    return ", ".join(forms.get(k, "-") for k in VERB_FORM_KEYS)


def parse_verb_forms_text(text: str) -> dict[str, str]:
    """Kommaliste (1sg, 2sg, 3sg, 1pl, 2pl, 3pl) zurück ins Formen-Dict.

    Leere Slots oder "-" bedeuten "regelmäßig" und werden übersprungen.
    Varianten innerhalb eines Slots bleiben unverändert ("δουν/δούνε").
    ValueError bei mehr als 6 Slots.
    """
    text = text.strip()
    if not text:
        return {}
    slots = [s.strip() for s in text.split(",")]
    if len(slots) > len(VERB_FORM_KEYS):
        raise ValueError(
            "Höchstens 6 Formen (1sg, 2sg, 3sg, 1pl, 2pl, 3pl)")
    return {k: v for k, v in zip(VERB_FORM_KEYS, slots) if v not in ("", "-")}


def parse_stem2_text(text: str) -> str:
    """Normalisiert die '2. Stamm'-Eingabe.

    Ein Wort = regelmäßiger Stamm; sonst bis zu 6 Personenformen
    kommagetrennt (1sg..3pl). ValueError bei mehr als 6 Slots.
    """
    text = text.strip()
    if not text:
        return ""
    slots = [s.strip() for s in text.split(",")]
    if len(slots) > len(VERB_FORM_KEYS):
        raise ValueError(
            "Höchstens 6 Formen (1sg, 2sg, 3sg, 1pl, 2pl, 3pl)")
    return ", ".join(slots)


@dataclass
class VocabCard:
    front: str  # Griechisch, inkl. Artikel bei Nomen
    back: str  # Deutsch
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    article: str | None = None  # ο / η / το / οι / τα ... , None bei Nicht-Nomen
    plural: str = ""  # Pluralendung/-form, z.B. "-α"; "-" = unverändert
    word_type: str = "Sonstiges"
    book: str | None = None  # "A1" / "A2", None bei eigenen Karten
    chapter: int | None = None
    task: str | None = None  # Aufgabe im Buch, z.B. "3a"
    hints_gr: str = ""  # Hinweis zur griechischen Seite
    hints_de: str = ""  # Hinweis zur deutschen Seite
    notes_gr: str = ""  # Notiz zur griechischen Seite
    notes_de: str = ""  # Notiz zur deutschen Seite (z.B. "per du")
    source: str = "custom"  # "book" | "custom"
    # Unregelmäßige Formen für Deklination/Konjugation, z.B.
    # {"gen_pl": "γυναικών"} oder {"2sg": "πας"}; siehe FORM_KEYS.
    forms: dict[str, str] = field(default_factory=dict)
    # 2. Stamm (Futur/να-Form) bei Verben: einzelner Stamm (z.B. "γράψ-")
    # ODER 6 Personenformen kommagetrennt (1sg..3pl), Varianten mit "/".
    # Vorerst nur Speicherung — Trainingslogik folgt später.
    stem2: str = ""

    def greek(self, with_article: bool) -> str:
        """Die erwartete griechische Form, je nach Artikel-Einstellung.

        Die Form ohne Artikel wird aus front abgeleitet (kein eigenes Feld).
        """
        if (not with_article and self.article
                and self.front.startswith(self.article + " ")):
            return self.front[len(self.article) + 1:]
        return self.front

    def with_plural(self, text: str) -> str:
        """Griechische Anzeigeform inkl. Pluralangabe (nicht Teil der Abfrage).

        „-" ist die interne Markierung für unveränderliche Fremdwörter und
        wird nicht angezeigt (kein „το μετρό, -")."""
        return f"{text}, {self.plural}" if self.plural and self.plural != "-" else text

    def notes_for(self, side: str) -> str:
        return self.notes_gr if side == "gr" else self.notes_de

    def hints_for(self, side: str) -> str:
        return self.hints_gr if side == "gr" else self.hints_de

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "VocabCard":
        d = dict(d)
        # Altformat: hints/notes ohne Sprachseite -> griechische Seite
        if "hints" in d and not d.get("hints_gr"):
            d["hints_gr"] = d.pop("hints")
        if "notes" in d and not d.get("notes_gr"):
            d["notes_gr"] = d.pop("notes")
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class SelectionList:
    """Auswahlliste: reine Referenz auf Karten bestehender Listen (per ID).

    Fortschritt/Statistik laufen über die referenzierten Karten weiter.
    """

    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    card_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "card_ids": self.card_ids}

    @classmethod
    def from_dict(cls, d: dict) -> "SelectionList":
        return cls(name=d["name"], id=d.get("id", uuid.uuid4().hex[:12]),
                   card_ids=list(d.get("card_ids", [])))


@dataclass
class VocabList:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    book: str | None = None
    chapter: int | None = None  # None = Ordner "Allgemein"
    editable: bool = True  # Buchlisten: False (in der App ausgegraut)
    cards: list[VocabCard] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "book": self.book,
            "chapter": self.chapter,
            "editable": self.editable,
            "cards": [c.to_dict() for c in self.cards],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VocabList":
        cards = [VocabCard.from_dict(c) for c in d.get("cards", [])]
        return cls(
            name=d["name"],
            id=d.get("id", uuid.uuid4().hex[:12]),
            book=d.get("book"),
            chapter=d.get("chapter"),
            editable=d.get("editable", True),
            cards=cards,
        )
