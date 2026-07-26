"""Antwortprüfung mit Unicode-Normalisierung und Akzent-Toleranz.

Notation (beide Sprachseiten):
- [a/b]-Gruppen im Satz: genau EINE Variante muss genannt werden —
  "Ich spreche [nicht/kein] Chinesisch." akzeptiert beide vollständigen
  Sätze, "Πώς [είσαι/είστε];" ebenso.
- Text in runden Klammern ist optional: "αγαπ(ά)ω" akzeptiert αγαπάω und
  αγαπώ, "(Visiten-)Karte" akzeptiert Visitenkarte und Karte (ein
  Bindestrich am Klammerrand verbindet die Teile).
- Nacktes "/" auf oberster Ebene trennt komplette Alternativantworten
  ("και / κι"): jede einzelne zählt als richtig.

Griechisch: Eine Antwort mit falschen/fehlenden Akzenten (τόνος) oder
falschem Schluss-Sigma ist immer ALMOST — ob das als richtig zählt
(Toleranz an) oder als Rundenfehler bei neutraler Leitner-Box (Toleranz
aus), entscheidet die Session.
Deutsch: Die Rückseite kann Alternativen enthalten ("Gyros, Kreis, Runde",
"und, auch", "Hallo! Guten Tag!"); jede Alternative wird akzeptiert.
"""

from __future__ import annotations

import itertools
import re
import unicodedata
from enum import Enum


class Result(Enum):
    CORRECT = "correct"
    ALMOST = "almost"  # richtig bis auf Akzente / Schluss-Sigma
    CASE = "case"  # richtig bis auf Groß-/Kleinschreibung (nur Nomen)
    WRONG = "wrong"


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", " ", s).strip()
    # lower() statt casefold(): casefold würde ς zu σ falten und damit
    # Schluss-Sigma-Fehler unbemerkt durchlassen
    return s.lower()


def strip_accents(s: str) -> str:
    decomposed = unicodedata.normalize("NFD", s)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", stripped).replace("ς", "σ")


_PUNCT = ";·!?.,…"


def _strip_punct(s: str) -> str:
    return s.strip(_PUNCT + " ")


def bracket_variants(text: str) -> list[str]:
    """Expandiert [a/b]-Gruppen: pro Gruppe muss genau eine Variante
    genannt werden.

    "Ich spreche [nicht/kein] Chinesisch." -> beide vollständigen Sätze.
    Mehrere Gruppen werden kartesisch kombiniert; ohne Gruppe kommt der
    Text unverändert zurück.
    """
    groups = re.findall(r"\[([^\]]*)\]", text)
    if not groups:
        return [text]
    template = re.sub(r"\[[^\]]*\]", "\x00", text)
    choices = [[p.strip() for p in g.split("/") if p.strip()] or [""]
               for g in groups]
    variants: list[str] = []
    for combo in itertools.product(*choices):
        s = template
        for part in combo:
            s = s.replace("\x00", part, 1)
        s = re.sub(r"\s+", " ", s).strip()
        if s and s not in variants:
            variants.append(s)
    return variants or [text]


def _optional_paren_variants(text: str) -> list[str]:
    """Deutsche Klammern als optionale Wortteile (wie griechisch).

    "(Visiten-)Karte" -> "Visitenkarte" und "Karte" — ein Bindestrich am
    Klammerrand verbindet die Teile. Klammern MIT Satzzeichen sind reine
    Zusatzinfo ("Sie (Akk.)", "(wörtl.: …)") und werden wie bisher nur
    entfernt — ihre Innen-Kommas dürfen keine Schein-Alternativen liefern.
    """
    # Zusatzinfo-Klammern (mit Satzzeichen) zuerst komplett entfernen
    text = re.sub(r"\(([^)]*[,;:.!?…][^)]*)\)", " ", text)
    groups = re.findall(r"\(([^)]*)\)", text)
    if not groups:
        return [re.sub(r"\s+", " ", text).strip()]
    template = re.sub(r"\([^)]*\)", "\x00", text)
    variants: list[str] = []
    for combo in itertools.product(*([g, ""] for g in groups)):
        s = template
        for part in combo:
            # \x01 markiert die Einfügeränder, um verbindende
            # Bindestriche zu erkennen ("Visiten-" + "Karte")
            s = s.replace("\x00", f"\x01{part}\x01", 1)
        # Verbindender Bindestrich am Klammerrand: Teile zusammenziehen,
        # der Folgebuchstabe wird dabei klein ("Visiten-"+"Karte" ->
        # "Visitenkarte", nicht "VisitenKarte")
        s = re.sub(r"-\x01(\w)", lambda m: "\x01" + m.group(1).lower(), s)
        s = re.sub(r"(?<=\w)\x01-(\w)",
                   lambda m: "\x01" + m.group(1).lower(), s)
        s = s.replace("\x01", "")
        s = re.sub(r"\s+", " ", s).strip()
        if s and s not in variants:
            variants.append(s)
    return variants


def greek_variants(expected: str) -> list[str]:
    """Varianten der Vorgabe: jeder Klammerinhalt ist optional.

    "αγαπ(ά)ω" -> ["αγαπ(ά)ω", "αγαπάω", "αγαπω"]; die Rohform bleibt
    dabei, damit auch die wörtliche Eingabe mit Klammern zählt.
    Reihenfolge: Rohform, dann voller Klammerinhalt, dann reduzierte
    Varianten — check_greek wertet reduzierte Varianten akzent-unabhängig.
    """
    groups = re.findall(r"\(([^)]*)\)", expected)
    if not groups:
        return [expected]
    template = re.sub(r"\(([^)]*)\)", "\x00", expected)
    variants = [expected]
    for combo in itertools.product(*([g, ""] for g in groups)):
        s = template
        for part in combo:
            s = s.replace("\x00", part, 1)
        s = re.sub(r"\s+", " ", s).strip()
        if s and s not in variants:
            variants.append(s)
    return variants


def check_greek(expected: str, given: str) -> Result:
    # [a/b]-Gruppen zuerst zu vollständigen Sätzen expandieren; jede
    # Expansion wird einzeln geprüft, die beste Wertung gewinnt
    best = Result.WRONG
    for variant in bracket_variants(expected):
        r = _check_greek_alternatives(variant, given)
        if r == Result.CORRECT:
            return r
        if r == Result.ALMOST:
            best = Result.ALMOST
    return best


def _check_greek_alternatives(expected: str, given: str) -> Result:
    # Alternativen "και / κι": jede einzeln prüfen, die Gesamtform bleibt
    # zusätzlich gültig (falls jemand sie wörtlich abtippt)
    if "/" in expected:
        alts = [a for a in (p.strip() for p in expected.split("/")) if a]
        best = Result.WRONG
        for alt in alts + ([expected] if len(alts) > 1 else []):
            r = _check_greek_single(alt, given)
            if r == Result.CORRECT:
                return r
            if r == Result.ALMOST:
                best = Result.ALMOST
        return best
    return _check_greek_single(expected, given)


def _check_greek_single(expected: str, given: str) -> Result:
    best = Result.WRONG
    for i, exp_variant in enumerate(greek_variants(expected)):
        exp, giv = normalize(exp_variant), normalize(given)
        if exp == giv or _strip_punct(exp) == _strip_punct(giv):
            return Result.CORRECT
        exp_s = strip_accents(_strip_punct(exp))
        giv_s = strip_accents(_strip_punct(giv))
        if exp_s == giv_s:
            if i >= 2:
                # Reduzierte Variante: der Akzent kann durch den weggefallenen
                # Klammerinhalt gewandert sein (αγαπ(ά)ω -> αγαπώ), also
                # akzent-unabhängig als richtig werten
                return Result.CORRECT
            best = Result.ALMOST
    return best


def german_alternatives(back: str) -> list[str]:
    """Zerlegt die deutsche Rückseite in akzeptierte Einzelantworten.

    [a/b]-Gruppen werden zuerst zu vollständigen Texten expandiert,
    Klammerinhalte sind optional (mit und ohne zählt); erst danach wird
    auf Komma, Satzenden und verbleibende Top-Level-"/" gesplittet.
    """
    alts: list[str] = []
    for bracketed in bracket_variants(back):
        for text in _optional_paren_variants(bracketed):
            parts = re.split(r"[,/]|(?<=[!?.])\s+", text)
            for p in parts:
                a = _strip_punct(re.sub(r"\s+", " ", p))
                if a and a not in alts:
                    alts.append(a)
            # zusätzlich die komplette Variante als Antwort erlauben
            full = _strip_punct(re.sub(r"\s+", " ", text))
            if full and full not in alts:
                alts.append(full)
    return alts


def check_german(back: str, given: str) -> Result:
    giv = _strip_punct(normalize(given))
    if not giv:
        return Result.WRONG
    for alt in german_alternatives(back):
        if normalize(alt) == giv:
            return Result.CORRECT
    return Result.WRONG


def _norm_keep_case(s: str) -> str:
    """Wie normalize(), aber ohne Kleinschreibung — für die Fallprüfung."""
    s = unicodedata.normalize("NFC", s)
    return re.sub(r"\s+", " ", s).strip()


def case_ok(expected: str, given: str, german: bool) -> bool:
    """True, wenn die (bereits als richtig gewertete) Antwort auch in der
    Groß-/Kleinschreibung stimmt.

    Vergleicht akzent- und satzzeichenunabhängig, aber mit erhaltener
    Schreibung — Akzentfehler werden hier also nicht doppelt bestraft.
    """
    giv = strip_accents(_strip_punct(_norm_keep_case(given)))
    if german:
        alts = german_alternatives(expected)
    else:
        alts = [v
                for bracketed in bracket_variants(expected)
                for part in ([p.strip() for p in bracketed.split("/")]
                             if "/" in bracketed else [bracketed])
                if part for v in greek_variants(part)]
    return any(strip_accents(_strip_punct(_norm_keep_case(a))) == giv
               for a in alts)
