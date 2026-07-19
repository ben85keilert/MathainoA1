"""Konjugation von Verben im Präsens und Futur (Neugriechisch, A1-Niveau).

Wie bei der Deklination entstehen die Formen regelbasiert aus den
Vokabelkarten: die griechische Vorderseite ist das Lemma (1. Person
Singular), mehr braucht es nicht. Karten, die kein konjugierbares
Lemma sind (Fixformen wie "κοστίζει", Futur-Phrasen wie "θα δούμε"),
werden übersprungen.

Unterstützte Muster (Präsens):
- Typ A:  -ω unbetont (μένω, διαβάζω)
- Typ B1: -άω (μιλάω; Nebenformen μιλώ, μιλά, μιλούμε, μιλούν)
- Typ B2: -ώ endbetont (μπορώ, ζω)
- Deponentien: -ομαι (έρχομαι), -άμαι (κοιμάμαι)
- unregelmäßig per Tabelle: είμαι, πάω, τρώω, λέω, ακούω
- Phrasen wie "κάνω μπάνιο": das erste Wort wird konjugiert

Futur (θα + 2. Stamm) aus dem Karten-Feld stem2:
- einzelner Stamm: mit Akzent (γράψ-) → Typ-A-Endungen (θα γράψω),
  ohne Akzent (κοιμηθ-) → endbetonte Endungen (θα κοιμηθώ)
- oder 6 Personenformen kommagetrennt (Varianten mit "/")
Verben ohne stem2 werden im Futur-Training übersprungen.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict

from mathainoa1.logic import answer_check
from mathainoa1.logic.answer_check import Result
from mathainoa1.logic.declension import (
    NUMBER_NAMES,
    _clean_front,
    _ensure_accent,
    _stripped,
    accent_pos,
    strip_acute,
    syllable_count,
)
from mathainoa1.models import VERB_FORM_KEYS, VocabCard, parse_verb_forms_text

PERSONS = [1, 2, 3]
TENSES = ["present", "future"]
TENSE_NAMES = {"present": "Präsens", "future": "Futur"}

# Reihenfolge der Formen-Slots; entspricht den Karten-Schlüsseln (forms)
_SLOT_KEYS = ["1sg", "2sg", "3sg", "1pl", "2pl", "3pl"]

# Unregelmäßige Präsensformen: Lemma (ohne Akzente) -> 6 Formenlisten
# (1sg, 2sg, 3sg, 1pl, 2pl, 3pl); erste Form ist jeweils die kanonische.
IRREGULAR = {
    "ειμαι": [["είμαι"], ["είσαι"], ["είναι"],
              ["είμαστε"], ["είστε", "είσαστε"], ["είναι"]],
    "παω": [["πάω"], ["πας"], ["πάει"], ["πάμε"], ["πάτε"], ["πάνε"]],
    "τρωω": [["τρώω"], ["τρως"], ["τρώει"], ["τρώμε"], ["τρώτε"], ["τρώνε"]],
    "λεω": [["λέω"], ["λες"], ["λέει"], ["λέμε"], ["λέτε"], ["λένε"]],
    "ακουω": [["ακούω"], ["ακούς"], ["ακούει"],
              ["ακούμε"], ["ακούτε"], ["ακούν", "ακούνε"]],
}


@dataclass
class Verb:
    word: str  # Lemma: 1. Person Singular
    cls: str  # "a" | "b1" | "b2" | "dep_o" | "dep_a" | "irr" | "custom"
    stem: str = ""
    rest: str = ""  # Rest der Phrase ("μπάνιο" bei "κάνω μπάνιο")
    overrides: dict[str, str] = field(default_factory=dict)  # "2sg" -> "πας"
    fut_stem: str = ""  # 2. Stamm (ohne "-"), leer = kein Futur
    fut_forms: dict[str, str] = field(default_factory=dict)  # "2sg" -> "πιεις"


def _parse_stem2(text: str) -> tuple[str, dict[str, str]]:
    """Zerlegt das stem2-Feld: einzelner Stamm ODER 6-Formen-Kommaliste."""
    text = (text or "").strip()
    if not text:
        return "", {}
    if "," in text:
        try:
            return "", parse_verb_forms_text(text)
        except ValueError:
            return "", {}  # kaputte Angabe lieber ignorieren als abbrechen
    return text.rstrip("-"), {}


def parse_verb(card: VocabCard) -> Verb | None:
    """Erkennt das Konjugationsmuster einer Verb-Karte; None = unbekannt."""
    verb = _parse_present(card)
    if verb is not None:
        verb.fut_stem, verb.fut_forms = _parse_stem2(card.stem2)
    return verb


def _parse_present(card: VocabCard) -> Verb | None:
    if card.word_type != "Verb":
        return None
    front = _clean_front(card.front)
    word, _, rest = front.partition(" ")
    rest = rest.strip()
    if not word or "/" in front:
        return None
    overrides = {k: v for k, v in (card.forms or {}).items() if k in VERB_FORM_KEYS}
    s = _stripped(word)
    if s in IRREGULAR:
        return Verb(word=word, cls="irr", rest=rest, overrides=overrides)
    if s.endswith("αω"):
        return Verb(word=word, cls="b1", stem=strip_acute(word[:-2]), rest=rest,
                    overrides=overrides)
    if s.endswith("ομαι") and len(word) > 4:
        return Verb(word=word, cls="dep_o", stem=word[:-4], rest=rest,
                    overrides=overrides)
    if s.endswith("αμαι") and len(word) > 4:
        return Verb(word=word, cls="dep_a", stem=word[:-4], rest=rest,
                    overrides=overrides)
    if s.endswith("ω"):
        # endbetont (μπορώ) oder einsilbig (ζω) -> Typ B2, sonst Typ A
        if accent_pos(word) == 0 or syllable_count(word) == 1:
            return Verb(word=word, cls="b2", stem=strip_acute(word[:-1]), rest=rest,
                        overrides=overrides)
        return Verb(word=word, cls="a", stem=word[:-1], rest=rest,
                    overrides=overrides)
    if overrides:
        # unbekanntes Muster, aber die Karte liefert die Formen selbst
        return Verb(word=word, cls="custom", rest=rest, overrides=overrides)
    return None


def _mono(form: str) -> str:
    """Einsilbige Formen tragen keinen Akzent (ζω, ζεις, ζουν)."""
    return strip_acute(form) if syllable_count(form) == 1 else form


# Endungstabellen: je Person/Zahl Liste der Endungen (erste = kanonisch)
_ENDINGS = {
    "a": [["ω"], ["εις"], ["ει"], ["ουμε"], ["ετε"], ["ουν", "ουνε"]],
    "b1": [["άω", "ώ"], ["άς"], ["άει", "ά"],
           ["άμε", "ούμε"], ["άτε"], ["άνε", "ούν", "ούνε"]],
    "b2": [["ώ"], ["είς"], ["εί"], ["ούμε"], ["είτε"], ["ούν", "ούνε"]],
}


def conjugate(verb: Verb, person: int, number: str) -> list[str]:
    """Alle richtigen Formen (erste = kanonisch), inkl. Phrasenrest.

    Unregelmäßige Formen der Karte (forms) haben Vorrang vor den Regeln;
    mehrere richtige Formen sind dort mit "/" getrennt.
    """
    idx = (person - 1) + (3 if number == "pl" else 0)
    override = verb.overrides.get(_SLOT_KEYS[idx])
    if override:
        forms = [f.strip() for f in override.split("/") if f.strip()]
    elif verb.cls == "custom":
        # ohne Override nur das Lemma (1. Person Singular) selbst
        if idx != 0:
            return []
        forms = [verb.word]
    elif verb.cls == "irr":
        forms = list(IRREGULAR[_stripped(verb.word)][idx])
    elif verb.cls in _ENDINGS:
        st = verb.stem
        forms = [_mono(_ensure_accent(st + e)) for e in _ENDINGS[verb.cls][idx]]
    elif verb.cls == "dep_o":
        st = verb.stem
        forms = [[st + "ομαι"], [st + "εσαι"], [st + "εται"],
                 [strip_acute(st) + "όμαστε"],
                 [st + "εστε", strip_acute(st) + "όσαστε"],
                 [st + "ονται"]][idx]
    elif verb.cls == "dep_a":
        st, bare = verb.stem, strip_acute(verb.stem)
        forms = [[st + "άμαι"], [st + "άσαι"], [st + "άται"],
                 [bare + "όμαστε"], [st + "άστε", bare + "όσαστε"],
                 [bare + "ούνται"]][idx]
    else:
        return []
    if verb.rest:
        forms = [f"{f} {verb.rest}" for f in forms]
    return forms


def has_future(verb: Verb) -> bool:
    """True, wenn die Karte einen 2. Stamm (Futur) mitbringt."""
    return bool(verb.fut_stem or verb.fut_forms)


def conjugate_future(verb: Verb, person: int, number: str) -> list[str]:
    """Futurformen ohne "θα" (erste = kanonisch), inkl. Phrasenrest.

    Einzelner Stamm: mit Akzent → Typ-A-Endungen (γράψ → γράψεις),
    ohne Akzent → endbetont (κοιμηθ → κοιμηθείς). Kommaliste in
    fut_forms hat Vorrang; leer = kein Futur für diesen Slot.
    """
    idx = (person - 1) + (3 if number == "pl" else 0)
    if verb.fut_forms:
        raw = verb.fut_forms.get(_SLOT_KEYS[idx])
        if not raw:
            return []
        forms = [f.strip() for f in raw.split("/") if f.strip()]
    elif verb.fut_stem:
        st = verb.fut_stem
        cls = "a" if accent_pos(st) is not None else "b2"
        forms = [_mono(_ensure_accent(st + e)) for e in _ENDINGS[cls][idx]]
    else:
        return []
    if verb.rest:
        forms = [f"{f} {verb.rest}" for f in forms]
    return forms


# --- Aufgaben ---

@dataclass
class ConjugationSettings:
    mode: str = "typing"  # "flashcard" | "typing"
    word_count: int = 20
    persons: list[int] = field(default_factory=lambda: [1, 2, 3])
    numbers: list[str] = field(default_factory=lambda: ["sg", "pl"])
    tenses: list[str] = field(default_factory=lambda: ["present"])
    repeat_errors: bool = True
    accent_tolerant: bool = True
    list_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ConjugationSettings":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class ConjugationTask:
    card: VocabCard
    person: int
    number: str
    prompt: str  # deutscher Infinitiv (Rückseite der Karte)
    meaning: str  # leer — die Bedeutung ist ja die Frage
    expected: str  # kanonische Form, z.B. "μένετε" / "θα γράψετε"
    variants: list[str] = field(default_factory=list)
    tense: str = "present"

    @property
    def label(self) -> str:
        base = f"{self.person}. Person {NUMBER_NAMES[self.number]}"
        return f"Futur: {base}" if self.tense == "future" else base

    def check(self, given: str) -> Result:
        best = Result.WRONG
        for exp in [self.expected] + self.variants:
            r = answer_check.check_greek(exp, given)
            if r == Result.CORRECT:
                return r
            if r == Result.ALMOST:
                best = Result.ALMOST
        return best


def conjugatable_verbs(cards: list[VocabCard]) -> list[tuple[VocabCard, Verb]]:
    result = []
    for c in cards:
        verb = parse_verb(c)
        if verb is not None:
            result.append((c, verb))
    return result


def build_task(card: VocabCard, verb: Verb, person: int, number: str,
               tense: str = "present") -> ConjugationTask | None:
    if tense == "future":
        forms = conjugate_future(verb, person, number)
        if not forms:
            return None
        # kanonisch mit "θα"; die bloße Form (ohne θα) zählt auch als richtig
        expected = f"θα {forms[0]}"
        variants = [f"θα {f}" for f in forms[1:]] + forms
    else:
        forms = conjugate(verb, person, number)
        if not forms:
            return None
        expected, variants = forms[0], forms[1:]
    return ConjugationTask(card=card, person=person, number=number,
                           prompt=card.back, meaning="",
                           expected=expected, variants=variants, tense=tense)


def generate_tasks(cards: list[VocabCard], settings: ConjugationSettings,
                   rng: random.Random | None = None) -> list[ConjugationTask]:
    """Alle Aufgaben für die Auswahl: je Verb × Zeit × Person × Zahl
    (mischt selbst). Verben ohne 2. Stamm liefern keine Futur-Aufgaben."""
    rng = rng or random.Random()
    tenses = [t for t in settings.tenses if t in TENSES] or ["present"]
    tasks = []
    for card, verb in conjugatable_verbs(cards):
        for tense in tenses:
            if tense == "future" and not has_future(verb):
                continue
            for person in settings.persons:
                for number in settings.numbers:
                    task = build_task(card, verb, person, number, tense)
                    if task is not None:
                        tasks.append(task)
    rng.shuffle(tasks)
    return tasks
