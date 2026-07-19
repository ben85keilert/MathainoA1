"""Deklination von Nomen und Adjektiven (Neugriechisch, A1-Niveau).

Die Formen werden regelbasiert aus den vorhandenen Vokabelkarten abgeleitet:
Artikel + Nominativ Singular (front) + Pluralangabe genügen — es braucht
keine eigene Formenliste pro Wort. Karten, deren Muster nicht sicher
erkannt wird (z.B. mehrteilige Ausdrücke), werden übersprungen statt
falsche Formen zu erzeugen; decline() liefert dann None.

Unterstützte Muster:
- maskulin:  -ος, -ας, -ης, -ές (καφές), -ούς (παππούς)
- feminin:   -α, -η, -ση/-ξη/-ψη (πόλη-Typ), -ος (η οδός)
- neutrum:   -ο, -ι, -μα, -ος (το λάθος)
- unveränderliche Fremdwörter (Pluralangabe "-"): nur der Artikel wird
  dekliniert (το μετρό → του μετρό)
- reine Pluralwörter (Artikel οι/τα): nur Pluralformen
- Adjektive auf -ος (alle Adjektive der Buchlisten)
"""

from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import dataclass, field, asdict

from mathainoa1.logic import answer_check
from mathainoa1.logic.answer_check import Result
from mathainoa1.models import NOUN_FORM_KEYS, VocabCard

# Trainierbare Fälle; Nominativ wird nur im Plural abgefragt (der Singular
# steht ja schon in der Aufgabe) — damit lässt sich der Plural üben
CASES = ["nom", "acc", "gen"]
NUMBERS = ["sg", "pl"]

CASE_NAMES = {"nom": "Nominativ", "acc": "Akkusativ", "gen": "Genitiv"}
NUMBER_NAMES = {"sg": "Singular", "pl": "Plural"}

ARTICLES = {
    ("nom", "sg"): {"m": "ο", "f": "η", "n": "το"},
    ("acc", "sg"): {"m": "τον", "f": "την", "n": "το"},
    ("gen", "sg"): {"m": "του", "f": "της", "n": "του"},
    ("nom", "pl"): {"m": "οι", "f": "οι", "n": "τα"},
    ("acc", "pl"): {"m": "τους", "f": "τις", "n": "τα"},
    ("gen", "pl"): {"m": "των", "f": "των", "n": "των"},
}
# Zusätzlich akzeptierte Artikel: τη(ν) ist je nach Folgelaut beides richtig
ARTICLE_ALTS = {("acc", "sg"): {"f": ["τη"]}}

# Genitiv Plural femininer Nomen ist nicht immer aus der Form ableitbar
# (ώρα → ωρών, aber μητέρα → μητέρων). Standard: Akzent auf -ών;
# Abweichler hier eintragen (Schlüssel ohne Akzente).
FEM_GEN_PL_EXCEPTIONS = {
    "μητερα": "μητέρων",
    "δασκαλα": "δασκάλων",
}

# Unregelmäßige feminine Adjektivformen (Schlüssel = Maskulinum ohne Akzente)
ADJ_FEM_EXCEPTIONS = {
    "γλυκος": "γλυκιά",
    "φρεσκος": "φρέσκια",
}


# --- Akzent-Werkzeuge (arbeiten auf NFD, liefern NFC) ---

_ACUTE = "́"
_VOWELS = set("αεηιουω")
# Zwei Vokale, die eine Silbe bilden (sofern kein Trema/Akzent sie trennt)
_DIPHTHONGS = {"αι", "ει", "οι", "υι", "ου", "αυ", "ευ", "ηυ"}


def _nuclei(nfd: str) -> list[list[int]]:
    """Indizes der Vokalkerne (Silbenträger), von links nach rechts."""
    nuclei: list[list[int]] = []
    prev_vowel_i: int | None = None
    for i, ch in enumerate(nfd):
        if unicodedata.combining(ch):
            continue
        if ch.lower() in _VOWELS:
            if prev_vowel_i is not None and nuclei and len(nuclei[-1]) == 1:
                pair = nfd[prev_vowel_i].lower() + ch.lower()
                between = nfd[prev_vowel_i + 1:i]
                # Akzent/Trema auf einem der Vokale trennt die Silben (ρολόι, γάιδαρος)
                trema_follows = i + 1 < len(nfd) and nfd[i + 1] == "̈"
                if (pair in _DIPHTHONGS and not trema_follows
                        and not any(unicodedata.combining(c) for c in between)):
                    nuclei[-1].append(i)
                    prev_vowel_i = i
                    continue
            nuclei.append([i])
            prev_vowel_i = i
        else:
            prev_vowel_i = None
    return nuclei


def strip_acute(word: str) -> str:
    """Entfernt nur den Akut (τόνος), Trema bleibt erhalten."""
    nfd = unicodedata.normalize("NFD", word)
    return unicodedata.normalize("NFC", nfd.replace(_ACUTE, ""))


def syllable_count(word: str) -> int:
    return len(_nuclei(unicodedata.normalize("NFD", word)))


def accent_pos(word: str) -> int | None:
    """Betonte Silbe, von hinten gezählt (0 = letzte Silbe), None = unbetont."""
    nfd = unicodedata.normalize("NFD", word)
    nuclei = _nuclei(nfd)
    acc_i = nfd.find(_ACUTE)
    if acc_i < 0:
        return None
    # Basisvokal des Akzents: erstes Nicht-Kombinationszeichen davor
    base = acc_i - 1
    while base >= 0 and unicodedata.combining(nfd[base]):
        base -= 1
    for pos, nucleus in enumerate(reversed(nuclei)):
        if base in nucleus:
            return pos
    return None


def set_accent(word: str, pos_from_end: int) -> str:
    """Setzt den Akut auf die angegebene Silbe (0 = letzte)."""
    nfd = unicodedata.normalize("NFD", strip_acute(word))
    nuclei = _nuclei(nfd)
    if not nuclei:
        return unicodedata.normalize("NFC", nfd)
    pos_from_end = min(pos_from_end, len(nuclei) - 1)
    nucleus = nuclei[len(nuclei) - 1 - pos_from_end]
    i = nucleus[-1]  # beim Diphthong steht der Akzent auf dem zweiten Vokal
    # hinter eventuelle Kombinationszeichen (Trema) rücken
    j = i + 1
    while j < len(nfd) and unicodedata.combining(nfd[j]):
        j += 1
    return unicodedata.normalize("NFC", nfd[:j] + _ACUTE + nfd[j:])


def _ensure_accent(word: str) -> str:
    """Mehrsilbige Wörter brauchen einen Akzent — notfalls auf die letzte Silbe."""
    if accent_pos(word) is None and syllable_count(word) > 1:
        return set_accent(word, 0)
    return word


def _cap_accent(word: str, max_pos: int) -> str:
    """Zieht den Akzent Richtung Wortende, wenn er weiter vorne liegt
    (z.B. άνθρωπος → ανθρώπου: höchstens vorletzte Silbe)."""
    pos = accent_pos(word)
    if pos is not None and pos > max_pos:
        return set_accent(word, max_pos)
    return _ensure_accent(word)


def _stripped(word: str) -> str:
    return strip_acute(word).lower()


# --- Nomen ---

@dataclass
class Noun:
    word: str  # Grundform ohne Artikel (Nominativ Sg., bei Pluralwörtern Pl.)
    gender: str  # "m" | "f" | "n"
    cls: str  # Muster; "custom" = nur per Karten-Formen (forms) deklinierbar
    stem: str = ""
    plural: str | None = None  # Nominativ Plural (None bei Pluralwörtern)
    plural_only: bool = False
    indeclinable: bool = False
    overrides: dict[str, str] = field(default_factory=dict)  # "gen_pl" -> Form


_GREEK_SUFFIX = re.compile(r"^-[Ͱ-Ͽἀ-῿]+$")


def _clean_front(front: str) -> str:
    """Klammerzusätze entfernen: 'η Ένωση (ΕΕ)' → 'η Ένωση'."""
    return re.sub(r"\s*\([^)]*\)", "", front).strip()


def parse_noun(card: VocabCard) -> Noun | None:
    """Erkennt das Deklinationsmuster einer Nomen-Karte; None = unbekannt."""
    if card.word_type != "Nomen" or not card.article:
        return None
    front = _clean_front(card.front)
    art = card.article
    if not front.startswith(art + " "):
        return None
    word = front[len(art) + 1:].strip()
    if not word:
        return None
    plural_field = (card.plural or "").strip()
    overrides = {k: v for k, v in (card.forms or {}).items() if k in NOUN_FORM_KEYS}

    if art in ("οι", "τα"):
        noun = _parse_plural_only(word, art)
        if noun is None and overrides and art == "τα":
            # unbekanntes Muster, aber die Karte liefert die Formen selbst
            noun = Noun(word=word, gender="n", cls="custom", plural_only=True)
        if noun is not None:
            noun.overrides = overrides
        return noun
    if art not in ("ο", "η", "το"):
        return None
    gender = {"ο": "m", "η": "f", "το": "n"}[art]

    # Unveränderliche Fremdwörter: Pluralangabe "-"
    if plural_field == "-":
        return Noun(word=word, gender=gender, cls="indecl", plural=word,
                    indeclinable=True, overrides=overrides)

    cls = None
    if " " not in word:  # mehrteilige Ausdrücke nicht raten
        s = _stripped(word)
        if art == "ο":
            if s.endswith("ος"):
                cls = "m2"
            elif s.endswith("ας"):
                cls = "m1a"
            elif s.endswith("ης"):
                cls = "m1i"
            elif s.endswith("ους"):
                cls = "m_ous"
            elif s.endswith("ες"):
                cls = "m_es"
        elif art == "η":
            if s.endswith("ος"):
                cls = "f2"
            elif s.endswith(("ση", "ξη", "ψη")):
                cls = "f3"
            elif s.endswith("η") and _stripped(plural_field).endswith("εις"):
                cls = "f3"  # πόλη (-εις): 3. Deklination trotz anderer Endung
            elif s.endswith(("η", "α")):
                cls = "f1"
        else:  # το
            if s.endswith("μα"):
                cls = "n_ma"
            elif s.endswith("ος"):
                cls = "n3s"
            elif s.endswith("ο"):
                cls = "n2"
            elif s.endswith("ι"):
                cls = "n_i"
    if cls is None:
        if overrides:
            # unbekanntes Muster, aber die Karte liefert die Formen selbst
            return Noun(word=word, gender=gender, cls="custom",
                        plural=overrides.get("nom_pl"), overrides=overrides)
        return None

    ending_len = {"m2": 2, "m1a": 2, "m1i": 2, "m_ous": 3, "m_es": 2,
                  "f2": 2, "f3": 1, "f1": 1, "n_ma": 0, "n3s": 2,
                  "n2": 1, "n_i": 1}[cls]
    stem = word[:-ending_len] if ending_len else word
    noun = Noun(word=word, gender=gender, cls=cls, stem=stem, overrides=overrides)
    noun.plural = overrides.get("nom_pl") or _nominative_plural(noun, plural_field)
    return noun


def _parse_plural_only(word: str, art: str) -> Noun | None:
    if " " in word:
        return None
    s = _stripped(word)
    if art == "τα":
        if not s.endswith("α"):
            return None
        return Noun(word=word, gender="n", cls="pl_n", plural_only=True)
    # οι: Genus an der Endung ablesen
    if s.endswith("οι"):
        return Noun(word=word, gender="m", cls="pl_m", plural_only=True)
    if s.endswith("εις"):
        return Noun(word=word, gender="m", cls="pl_eis", plural_only=True)
    if s.endswith("ες"):
        return Noun(word=word, gender="f", cls="pl_f", plural_only=True)
    return None


def _nominative_plural(noun: Noun, plural_field: str) -> str | None:
    """Nominativ Plural: Pluralangabe der Karte nutzen, sonst Regelform."""
    # Einfache Angaben wie "-ες", "-οί", "-άδες" direkt anwenden.
    # Ausnahme -μα-Neutra: dort beschreibt die Angabe (z.B. "-ματα") keinen
    # Anhang an den Stamm, und die Regelform ist ohnehin eindeutig.
    if noun.cls != "n_ma" and _GREEK_SUFFIX.match(plural_field):
        suffix = plural_field[1:]
        stem = noun.stem
        if _ACUTE in unicodedata.normalize("NFD", suffix):
            stem = strip_acute(stem)
        return _ensure_accent(stem + suffix)
    st = noun.stem
    if noun.cls in ("m2", "f2"):
        return _ensure_accent(st + "οι")
    if noun.cls in ("m1a", "m1i", "f1"):
        return _ensure_accent(st + "ες")
    if noun.cls == "f3":
        return _cap_accent(st + "εις", 1)  # πόλεις, ασκήσεις
    if noun.cls == "n2":
        return _ensure_accent(st + "α")
    if noun.cls == "n_i":
        return _ensure_accent(st + "ια")  # σπίτια; παιδί → παιδιά
    if noun.cls == "n_ma":
        return _cap_accent(noun.word + "τα", 2)  # μαθήματα, θέματα
    if noun.cls == "n3s":
        return _ensure_accent(st + "η")  # λάθη, μέρη
    if noun.cls == "m_es":
        return _ensure_accent(st + "έδες")
    if noun.cls == "m_ous":
        return _ensure_accent(st + "ούδες")
    return None


def decline(noun: Noun, case: str, number: str) -> str | None:
    """Die Wortform (ohne Artikel) für Fall × Zahl; None = nicht ableitbar."""
    override = noun.overrides.get(f"{case}_{number}")
    if override:
        return override
    if noun.indeclinable:
        return noun.word
    if noun.cls == "custom":
        # ohne Override nur die Nominativ-Grundformen der Karte
        if case != "nom":
            return None
        if noun.plural_only:
            return noun.word if number == "pl" else None
        return noun.word if number == "sg" else noun.plural
    if noun.plural_only:
        return _decline_plural_only(noun, case, number)
    if number == "sg":
        return _decline_singular(noun, case)
    return _decline_plural(noun, case)


def _decline_singular(noun: Noun, case: str) -> str | None:
    w, st = noun.word, noun.stem
    if case == "nom":
        return w
    if case == "acc":
        if noun.cls in ("m2", "f2"):
            return _ensure_accent(st + "ο")
        if noun.cls in ("m1a", "m1i", "m_es", "m_ous"):
            return w[:-1]  # Schluss-ς entfällt
        return w  # Feminina auf -α/-η, Neutra: wie Nominativ
    if case == "gen":
        if noun.cls in ("m2", "f2"):
            return _cap_accent(st + "ου", 1)  # δρόμου, ανθρώπου, ουρανού
        if noun.cls in ("m1a", "m1i", "m_es", "m_ous"):
            return w[:-1]
        if noun.cls in ("f1", "f3"):
            return w + "ς"  # ώρας, τέχνης, άσκησης
        if noun.cls == "n2":
            return _cap_accent(st + "ου", 1)  # θεάτρου, βουνού
        if noun.cls == "n_i":
            return strip_acute(st) + "ιού"  # παιδιού, σπιτιού
        if noun.cls == "n_ma":
            return _cap_accent(noun.word + "τος", 2)  # μαθήματος
        if noun.cls == "n3s":
            return _ensure_accent(st + "ους")  # λάθους
    return None


def _decline_plural(noun: Noun, case: str) -> str | None:
    pl, st = noun.plural, noun.stem
    if pl is None:
        return None
    if case == "nom":
        return pl
    if case == "acc":
        if noun.cls in ("m2", "f2"):
            return _cap_accent(st + "ους", 1)  # δρόμους, ανθρώπους, ουρανούς
        return pl  # alle übrigen: wie Nominativ Plural
    if case == "gen":
        if _stripped(pl).endswith("δες"):
            return pl[:-2] + "ων"  # καφέδες → καφέδων, μπαμπάδες → μπαμπάδων
        if noun.cls in ("m2", "f2", "n2"):
            return _cap_accent(st + "ων", 1)  # δρόμων, ανθρώπων, ουρανών
        if noun.cls == "m1a":
            if accent_pos(noun.word) == 2:
                return _cap_accent(st + "ων", 1)  # πίνακας → πινάκων
            return strip_acute(st) + "ών"  # αντρών, μηνών
        if noun.cls == "m1i":
            return strip_acute(st) + "ών"  # ναυτών, πολιτών
        if noun.cls == "f1":
            exc = FEM_GEN_PL_EXCEPTIONS.get(_stripped(noun.word))
            if exc:
                return exc
            if _stripped(noun.word).endswith(("ιδα", "αδα", "ονα")):
                return _ensure_accent(st + "ων")  # σελίδων, ομάδων, εικόνων
            return strip_acute(st) + "ών"  # ωρών, γλωσσών
        if noun.cls == "f3":
            return _cap_accent(st + "εων", 2)  # πόλεων, ασκήσεων
        if noun.cls == "n_i":
            return strip_acute(st) + "ιών"  # παιδιών, σπιτιών
        if noun.cls == "n_ma":
            return strip_acute(noun.word[:-1]) + "άτων"  # μαθημάτων
        if noun.cls == "n3s":
            return strip_acute(st) + "ών"  # λαθών, μερών
    return None


def _decline_plural_only(noun: Noun, case: str, number: str) -> str | None:
    if number == "sg":
        return None
    w = noun.word
    if case in ("nom", "acc"):
        if noun.cls == "pl_m" and case == "acc":
            return _cap_accent(w[:-2] + "ους", 1)  # αριθμοί → αριθμούς
        return w
    if case == "gen":
        if noun.cls == "pl_m":
            return _cap_accent(w[:-2] + "ων", 1)  # αριθμών
        if noun.cls == "pl_f":
            return strip_acute(w[:-2]) + "ών"  # διακοπών
        if noun.cls == "pl_n":
            if _stripped(w).endswith("ματα"):
                return set_accent(w[:-1] + "ων", 1)  # χρήματα → χρημάτων
            if _stripped(w).endswith("ια"):
                return strip_acute(w[:-2]) + "ιών"  # μακαρονιών
            return _ensure_accent(w[:-1] + "ων")  # μαθηματικών
    return None  # οι γονείς u.ä.: Genitiv nicht sicher ableitbar


# --- Adjektive (Typ -ος) ---

@dataclass
class Adjective:
    word: str  # Maskulinum Nominativ Singular
    stem: str
    fem: str  # Femininum Nominativ Singular
    meaning: str = ""  # deutsche Bedeutung (für Aufgaben mit deutscher Vorgabe)


def parse_adjective(card: VocabCard) -> Adjective | None:
    if card.word_type != "Adjektiv":
        return None
    word = _clean_front(card.front).strip()
    if " " in word or not _stripped(word).endswith("ος"):
        return None
    stem = word[:-2]
    fem = ((card.forms or {}).get("fem")
           or ADJ_FEM_EXCEPTIONS.get(_stripped(word)))
    if fem is None:
        # Stamm endet auf Vokal → -α (νέα, ωραία), sonst -η (καλή)
        s = _stripped(stem)
        fem = _ensure_accent(stem + ("α" if s and s[-1] in _VOWELS else "η"))
    return Adjective(word=word, stem=stem, fem=fem, meaning=card.back)


def decline_adjective(adj: Adjective, gender: str, case: str, number: str) -> str:
    st = adj.stem
    if gender == "m":
        endings = {("nom", "sg"): "ος", ("acc", "sg"): "ο", ("gen", "sg"): "ου",
                   ("nom", "pl"): "οι", ("acc", "pl"): "ους", ("gen", "pl"): "ων"}
        return _ensure_accent(st + endings[(case, number)])
    if gender == "n":
        endings = {("nom", "sg"): "ο", ("acc", "sg"): "ο", ("gen", "sg"): "ου",
                   ("nom", "pl"): "α", ("acc", "pl"): "α", ("gen", "pl"): "ων"}
        return _ensure_accent(st + endings[(case, number)])
    # feminin: aus der Grundform (καλή / μέτρια / γλυκιά) ableiten
    fem_stem = adj.fem[:-1]
    if number == "sg":
        return adj.fem + "ς" if case == "gen" else adj.fem
    if case == "gen":
        return _ensure_accent(st + "ων")  # Gen. Pl. wie Maskulinum
    return _ensure_accent(fem_stem + "ες")  # καλές, μέτριες


# --- Aufgaben und Trainingsrunde ---

@dataclass
class DeclensionSettings:
    mode: str = "typing"  # "flashcard" | "typing"
    direction: str = "gr"  # Vorgabe: "gr" = griechische Nominativphrase,
    # "de" = deutsche Bedeutung (schwerer; zählt für die Vokabelstatistik)
    word_count: int = 20
    cases: list[str] = field(default_factory=lambda: ["acc"])
    numbers: list[str] = field(default_factory=lambda: ["sg", "pl"])
    with_adjectives: bool = False
    repeat_errors: bool = True
    accent_tolerant: bool = True
    # Groß-/Kleinschreibung tolerieren (analog zu accent_tolerant); aus:
    # falsche Schreibung zählt wie ein strenger Akzentfehler (nur Nomen,
    # relevant v.a. bei Eigennamen wie „την Αθήνα“)
    case_tolerant: bool = True
    list_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DeclensionSettings":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class DeclensionTask:
    card: VocabCard  # das Nomen (für Fehlerliste/Anzeige)
    case: str
    number: str
    prompt: str  # Nominativphrase, z.B. "ο μικρός δρόμος"
    meaning: str  # deutsche Bedeutung des Nomens
    expected: str  # kanonische Antwort, z.B. "τον μικρό δρόμο"
    variants: list[str] = field(default_factory=list)  # ebenfalls richtig

    @property
    def label(self) -> str:
        return f"{CASE_NAMES[self.case]} {NUMBER_NAMES[self.number]}"

    def check(self, given: str) -> Result:
        best = Result.WRONG
        for exp in [self.expected] + self.variants:
            r = answer_check.check_greek(exp, given)
            if r == Result.CORRECT:
                return r
            if r == Result.ALMOST:
                best = Result.ALMOST
        return best

    def case_ok(self, given: str) -> bool:
        """True, wenn die (richtige) Antwort auch in der Schreibung stimmt."""
        return any(answer_check.case_ok(exp, given, german=False)
                   for exp in [self.expected] + self.variants)


def build_task(card: VocabCard, noun: Noun, case: str, number: str,
               adj: Adjective | None = None,
               direction: str = "gr") -> DeclensionTask | None:
    """Baut eine Aufgabe Vorgabe → Zielform; None wenn nicht ableitbar.

    direction "gr": Vorgabe ist die griechische Nominativphrase, die deutsche
    Bedeutung wird dazu eingeblendet. direction "de": Vorgabe ist nur die
    deutsche Bedeutung — das griechische Wort muss mit erinnert werden.
    """
    noun_form = decline(noun, case, number)
    if noun_form is None:
        return None
    base_number = "pl" if noun.plural_only else "sg"
    prompt_words = [ARTICLES[("nom", base_number)][noun.gender]]
    answer_words = [ARTICLES[(case, number)][noun.gender]]
    if adj is not None:
        prompt_words.append(decline_adjective(adj, noun.gender, "nom", base_number))
        answer_words.append(decline_adjective(adj, noun.gender, case, number))
    prompt_words.append(noun.word)
    answer_words.append(noun_form)
    expected = " ".join(answer_words)
    variants = [" ".join([alt] + answer_words[1:])
                for alt in ARTICLE_ALTS.get((case, number), {}).get(noun.gender, [])]
    if direction == "de":
        prompt = card.back if adj is None else f"{adj.meaning} + {card.back}"
        meaning = ""
    else:
        prompt = " ".join(prompt_words)
        meaning = card.back
    return DeclensionTask(card=card, case=case, number=number,
                          prompt=prompt, meaning=meaning,
                          expected=expected, variants=variants)


def declinable_nouns(cards: list[VocabCard]) -> list[tuple[VocabCard, Noun]]:
    result = []
    for c in cards:
        noun = parse_noun(c)
        if noun is not None:
            result.append((c, noun))
    return result


def usable_adjectives(cards: list[VocabCard]) -> list[Adjective]:
    return [a for a in (parse_adjective(c) for c in cards) if a is not None]


def generate_tasks(cards: list[VocabCard], settings: DeclensionSettings,
                   rng: random.Random | None = None) -> list[DeclensionTask]:
    """Alle Aufgaben für die Auswahl: je Nomen × Fall × Zahl (mischt selbst).

    Bei "Adjektive mitdeklinieren" bekommt jede Aufgabe ein zufälliges
    Adjektiv aus derselben Auswahl (sofern vorhanden).
    """
    rng = rng or random.Random()
    adjectives = usable_adjectives(cards) if settings.with_adjectives else []
    tasks = []
    for card, noun in declinable_nouns(cards):
        # Eigennamen (Ιταλία, Κρήτη …): kein sinnvoller Plural
        proper = noun.word[:1].isupper() and not noun.plural_only
        for case in settings.cases:
            for number in settings.numbers:
                if proper and number == "pl":
                    continue
                # Nominativ Singular ist die Vorgabe selbst — nur der Plural
                # ist eine echte Aufgabe; bei reinen Pluralwörtern wäre auch
                # der trivial (Vorgabe = Lösung)
                if case == "nom" and (number == "sg" or noun.plural_only):
                    continue
                adj = rng.choice(adjectives) if adjectives else None
                task = build_task(card, noun, case, number, adj,
                                  direction=settings.direction)
                if task is not None:
                    tasks.append(task)
    rng.shuffle(tasks)
    return tasks


@dataclass
class TaskAnswer:
    task: DeclensionTask
    result: Result
    given: str = ""


class DeclensionSession:
    """Ablauf wie beim Vokabeltraining: Erstrunde, optional Fehlerrunde.

    on_result(card, correct) wird pro Aufgabe der Erstrunde aufgerufen —
    z.B. um bei deutscher Vorgabe die Vokabelstatistik zu füttern.
    """

    def __init__(self, tasks: list[DeclensionTask], settings: DeclensionSettings,
                 on_result=None, accent_resets_box: bool = False,
                 case_resets_box: bool = False):
        self.settings = settings
        self.on_result = on_result
        # App-Policy: strenger Akzent-/Groß-Klein-Fehler setzt die Box auf 1
        self.accent_resets_box = accent_resets_box
        self.case_resets_box = case_resets_box
        self.queue = tasks[: max(1, settings.word_count)]
        self.total_first_round = len(self.queue)
        self.answers: list[TaskAnswer] = []
        self._wrong_pending: list[DeclensionTask] = []
        self.in_repeat_round = False

    @property
    def current(self) -> DeclensionTask | None:
        return self.queue[0] if self.queue else None

    def check_typed(self, given: str) -> Result:
        task = self.current
        assert task is not None
        result = task.check(given)
        # Groß-/Kleinschreibung nur bei Nomen prüfen (Konjugation nutzt
        # dieselbe Session, hat aber kein case_tolerant -> immer tolerant)
        if (not getattr(self.settings, "case_tolerant", True)
                and task.card.word_type == "Nomen"
                and self.counts_correct(result)
                and not task.case_ok(given)):
            result = Result.CASE
        self._record(task, result, given)
        return result

    def mark(self, correct: bool) -> None:
        task = self.current
        assert task is not None
        self._record(task, Result.CORRECT if correct else Result.WRONG)

    def counts_correct(self, result: Result) -> bool:
        """ALMOST (nur Akzentfehler) zählt je nach Toleranz-Einstellung."""
        if result == Result.ALMOST:
            return self.settings.accent_tolerant
        return result == Result.CORRECT

    def _record(self, task: DeclensionTask, result: Result, given: str = "") -> None:
        self.answers.append(TaskAnswer(task, result, given))
        self.queue.pop(0)
        # Strenge Fehler (Akzent bei strenger Prüfung, Groß-/Kleinschreibung)
        # sind je nach App-Policy Leitner-neutral oder setzen die Box zurück;
        # beide zählen als Rundenfehler
        strict_accent = (result == Result.ALMOST
                         and not self.settings.accent_tolerant)
        strict_case = result == Result.CASE
        box_neutral = ((strict_accent and not self.accent_resets_box)
                       or (strict_case and not self.case_resets_box))
        if self.on_result and not self.in_repeat_round and not box_neutral:
            self.on_result(task.card, self.counts_correct(result))
        if (not self.counts_correct(result) and self.settings.repeat_errors
                and not self.in_repeat_round):
            self._wrong_pending.append(task)
        if not self.queue and self._wrong_pending:
            # Fehlerrunde bewusst in Fehler-Reihenfolge (linear) — gemischt
            # wird erst die Folgerunde
            self.queue = self._wrong_pending
            self._wrong_pending = []
            self.in_repeat_round = True

    @property
    def finished(self) -> bool:
        return not self.queue

    def stats(self) -> dict:
        first = self.answers[: self.total_first_round]
        correct = sum(1 for a in first if self.counts_correct(a.result))
        return {
            "total": len(first),
            "correct": correct,
            "wrong": len(first) - correct,
            "wrong_tasks": [a.task for a in first
                            if not self.counts_correct(a.result)],
        }
