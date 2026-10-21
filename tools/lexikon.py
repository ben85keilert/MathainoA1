"""Lexikon-Werkzeug: Etymologie-Pakete (Arbeitsanweisung IV) zu Buchlisten
erzeugen, prüfen und korrigieren.

Alles, was sich maschinell prüfen lässt, prüft dieses Skript (Schema,
Vollständigkeit, Reihenfolge, Schreibweise, App-Formen, bekannte
Stolperfallen) — die KI schreibt nur Inhalte und liest gezielte Auszüge.
Ablauf und Inhaltsregeln: .claude/skills/lexikon/.

Arbeitsordner (lokal, Inhalte urheberrechtlich nah am Buch → private/):

    projekt.json        {"stufe": "A2",
                         "listen": {"kap01": "../a2-kap01.json", …},
                         "paket": "../a2-lexikon-{id}.json",
                         "bekannt": []}
                        listen in Buchreihenfolge: ein Wort bekommt seinen
                        Eintrag nur in der ersten Liste, in der es vorkommt.
                        bekannt: weitere Pakete oder App-Lexika (lexikon.json),
                        deren Wörter schon abgedeckt sind.
    <id>/teilNN.json    Quelle der Wahrheit: JSON-Arrays von Einträgen
    patches/offen/      Korrekturlisten → nach dem Anwenden patches/angewendet/
    arbeit/             erzeugte Hilfsdateien (Wortlisten, Formen, Audit, Auszüge)

Aufruf: python tools/lexikon.py <befehl> <arbeitsordner> [...]
    status                         Überblick über alle Listen
    vorbereiten <id>               Wortliste + Teilplan für die Schreiber
    pruefen <id>... | --alle       Validator (Fehler/Warnungen); --teilweise
                                   während des Schreibens (fehlende Wörter ok)
    bauen <id>... | --alle         prüfen und Paket schreiben
    formen <id>...                 von der App erzeugte Formen je Zusatzwort
    audit [<id>...]                Verdachtsfälle für die Prüfer
    auszug <art> <id>... [--nur P] kompakter Prüfauszug (art: inhalt | form)
    patch [--anwenden]             patches/offen/*.json anwenden
    angleichen [--anwenden]        Zusatzwörter kapitelübergreifend vereinheitlichen
    importtest                     alle Pakete in eine frische App importieren
    zerlegen <id> <paket.json>     fertiges Paket in Teildateien zerlegen
"""

from __future__ import annotations

import collections
import datetime
import glob
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mathainoa1.logic import conjugation as C  # noqa: E402
from mathainoa1.logic import declension as D  # noqa: E402
from mathainoa1.logic.answer_check import strip_accents  # noqa: E402
from mathainoa1.models import (  # noqa: E402
    WORD_TYPES, parse_forms_text, parse_stem2_text)
from mathainoa1.storage.content import (  # noqa: E402
    _split_leading_article, verb_fields_for)
from mathainoa1.storage.textanalyse import (  # noqa: E402
    card_from_entry, parse_lexicon_package, word_key)

TEIL_GROESSE = 20
ENTRY_KEYS = {"word", "breakdown", "total", "semantics", "cognates",
              "synonyms", "extra_vocab"}
COG_GROUPS = ("identical", "related", "german_latin")
EXTRA_BASE_KEYS = {"front", "back", "article", "plural", "word_type", "forms",
                   "hints_gr", "hints_de", "notes_gr", "notes_de"}
# Begründung in hints_gr, wenn ein Verb bewusst ohne Stammfelder bleibt
VERB_OHNE_STAMM = ("unpersönlich", "kein Aorist", "nur Präsens")
# Kennzeichnung von Nicht-Kognaten in cognates.related
NICHT_KOGNAT = ("Wortfeld", "Gegenwort", "andere Wurzel")
GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
LATIN = re.compile(r"[A-Za-z]")
ARTIKEL = ("ο", "η", "το", "οι", "τα", "του", "της", "των", "τον", "την")
ACUTE = "́"


# --- Projekt ---------------------------------------------------------------

class Projekt:
    def __init__(self, ordner: str):
        self.dir = Path(ordner).resolve()
        cfg_path = self.dir / "projekt.json"
        if not cfg_path.exists():
            sys.exit(f"{cfg_path} fehlt — siehe Kopf von tools/lexikon.py")
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.stufe = cfg.get("stufe", "A2")
        self.listen = {k: (self.dir / v).resolve()
                       for k, v in cfg["listen"].items()}
        self.paket_muster = cfg["paket"]
        self.bekannt = [(self.dir / p).resolve() for p in cfg.get("bekannt", [])]
        self.extra_keys = EXTRA_BASE_KEYS | set(verb_fields_for(self.stufe))
        self._cache: dict[str, dict] = {}

    def ids(self) -> list[str]:
        return list(self.listen)

    def id_von(self, x) -> str:
        """Listen-id aus Patch-Angaben: "kap03" oder Kapitelnummer 3."""
        if isinstance(x, int) or str(x).isdigit():
            x = f"kap{int(x):02d}"
        if x not in self.listen:
            sys.exit(f"unbekannte Liste {x!r} (projekt.json: {self.ids()})")
        return x

    def liste(self, lid: str) -> dict:
        if lid not in self._cache:
            p = self.listen[lid]
            self._cache[lid] = (json.loads(p.read_text(encoding="utf-8"))
                                if p.exists() else {"name": lid, "cards": []})
        return self._cache[lid]

    def paket_pfad(self, lid: str) -> Path:
        return (self.dir / self.paket_muster.format(id=lid)).resolve()

    def teile(self, lid: str) -> list[Path]:
        return sorted(Path(p) for p in glob.glob(str(self.dir / lid / "teil*.json")))

    def eintraege(self, lid: str) -> list[dict]:
        out = []
        for p in self.teile(lid):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as ex:
                sys.exit(f"{p}: kein gültiges JSON: {ex}")
            if not isinstance(data, list):
                sys.exit(f"{p}: erwartet wird ein JSON-Array von Einträgen")
            out += data
        return out

    def bekannte_keys(self) -> set[str]:
        keys = set()
        for p in self.bekannt:
            data = json.loads(p.read_text(encoding="utf-8"))
            for e in data.get("etymology") or data.get("entries") or []:
                keys.add(word_key(e.get("word", "")))
        return keys

    def erwartet(self, lid: str) -> list[tuple[str, dict]]:
        """(word_key, Karte) aller Wörter, die in dieser Liste einen
        Eintrag brauchen — ohne frühere Listen, bekannte Pakete, Dubletten."""
        vorher = self.bekannte_keys()
        for k in self.ids():
            if k == lid:
                break
            vorher |= {word_key(c["front"]) for c in self.liste(k)["cards"]}
        out, seen = [], set()
        for c in self.liste(lid)["cards"]:
            key = word_key(c["front"])
            if key and key not in vorher and key not in seen:
                seen.add(key)
                out.append((key, c))
        return out

    def buchwoerter(self, bis: str | None = None) -> dict[str, str]:
        """word_key → Listen-id der ersten Liste (bis einschließlich `bis`)."""
        out: dict[str, str] = {}
        for k in self.ids():
            for c in self.liste(k)["cards"]:
                out.setdefault(word_key(c["front"]), k)
            if k == bis:
                break
        return out

    def arbeit(self, name: str) -> Path:
        (self.dir / "arbeit").mkdir(exist_ok=True)
        return self.dir / "arbeit" / name


def ids_aus(pj: Projekt, args: list[str], nur_vorhandene=True) -> list[str]:
    if not args or "--alle" in args:
        return [k for k in pj.ids() if not nur_vorhandene or pj.teile(k)]
    return [pj.id_von(a) for a in args if not a.startswith("--")]


# --- Griechisch-Helfer -----------------------------------------------------

def ma_plural(word: str) -> str:
    """Buchkonvention für -μα-Plurale: "-ματα" oder "-(θή)ματα"."""
    pl = D._cap_accent(word + "τα", 2)

    def pos_front(w):
        nfd = unicodedata.normalize("NFD", w)
        return len(unicodedata.normalize("NFC", nfd[:nfd.find(ACUTE)]))

    if pos_front(word) == pos_front(pl):
        return "-ματα"
    stem = pl[:-4]
    nfd = unicodedata.normalize("NFD", stem)
    i = nfd.find(ACUTE)
    pre = unicodedata.normalize("NFC", nfd[:i])
    vowel = unicodedata.normalize("NFC", pre[-1] + ACUTE)
    rest = unicodedata.normalize("NFC", nfd[i + 1:])
    before = pre[:-1]
    if before and (before[-1] + pre[-1]) in ("ει", "αι", "οι", "ου", "ευ", "αυ", "υι"):
        vowel, before = before[-1] + vowel, before[:-1]
    if rest:
        seg = vowel + rest
    else:
        m = re.search(r"[^αεηιουωάέήίόύώ]+$", before)
        seg = (m.group(0) if m else "") + vowel
    return f"-({seg})ματα"


def _plain(s: str) -> str:
    return strip_accents(s).lower()


def _endbetont(w: str) -> bool:
    return D.accent_pos(w) == 0


def adjektiv_endungen(hints: str) -> list[str] | None:
    """Femininum-Angaben aus hints_gr ("Endungen: -ος, -η, -ο" oder
    "δεξιός, δεξιά, δεξί"); Varianten mit "/" — None, wenn keine Angabe."""
    m = re.search(r"([-\w/]+),\s*([-\w/]+),\s*([-\w/]+)", hints)
    if not m:
        return None
    return [x.strip() for x in m.group(2).split("/") if x.strip()]


def app_formfehler(v: dict) -> list[str]:
    """Bekannte Schwächen der App-Deklination, die explizite forms brauchen
    (siehe Skill-Regeln „App-Formen“). Leere Liste = unauffällig."""
    card = card_from_entry(v)
    if card is None:
        return []
    out = []
    if card.word_type == "Nomen":
        noun = D.parse_noun(card)
        if noun is None:
            return out
        art, bare = _split_leading_article(card.front)
        gen_pl = D.decline(noun, "gen", "pl")
        if gen_pl and "gen_pl" not in card.forms:
            if _plain(bare).endswith("οτητα") and _endbetont(gen_pl):
                out.append(f"App bildet Gen.Pl. {gen_pl} → forms gen_pl=…ήτων setzen")
            elif "nur Plural" in card.hints_gr:
                # Akzent im Gen.Pl. der Pluralwörter rät die App oft falsch
                # (μεσάνυχτων, γενεθλιών) — deshalb immer ausdrücklich
                out.append(f"Pluralwort: Gen.Pl. ausdrücklich angeben, forms "
                           f"gen_pl=… (App bildet {gen_pl} — stimmt das?)")
    elif card.word_type == "Adjektiv":
        adj = D.parse_adjective(card)
        want = adjektiv_endungen(card.hints_gr)
        if adj is None or not want:
            return out
        fem = D.decline_adjective(adj, "f", "nom", "sg")
        ok = any(_plain(fem) == _plain(w) if not w.startswith("-")
                 else _plain(fem).endswith(_plain(w[1:])) for w in want)
        if not ok:
            out.append(f"App bildet Femininum {fem}, hints_gr sagt {'/'.join(want)} "
                       "→ forms fem=… setzen")
    return out


# --- Validator -------------------------------------------------------------

class Befund:
    def __init__(self):
        self.fehler: list[str] = []
        self.warnungen: list[str] = []

    def f(self, m):
        self.fehler.append(m)

    def w(self, m):
        self.warnungen.append(m)


def _text(b: Befund, s, wo: str, griechisch=False):
    if not isinstance(s, str):
        b.f(f"{wo}: kein String: {s!r}")
        return
    if unicodedata.normalize("NFC", s) != s:
        b.f(f"{wo}: nicht NFC: {s!r}")
    if s != s.strip() or "  " in s:
        b.f(f"{wo}: Leerzeichen am Rand oder doppelt: {s!r}")
    for tok in re.split(r"[\s,;:/()\[\]„“\"'«»→\-–.!?]+", s):
        if GREEK.search(tok) and LATIN.search(tok):
            b.f(f"{wo}: gemischte Schrift in {tok!r} — lateinischer Doppelgänger?")
    if griechisch and not GREEK.search(s):
        b.f(f"{wo}: kein Griechisch in {s!r}")


def _erwaehnt(front: str, e: dict) -> bool:
    """Kommt das Zusatzwort (Stamm, auch gebeugt) irgendwo im Eintrag vor —
    in semantics, total, Kognaten oder Synonymen (z.B. „στη σχάρα“)?"""
    _art, bare = _split_leading_article(
        re.sub(r"\([^)]*\)", "", front).split("/")[0].strip())
    bare = _plain(bare)
    stamm = bare[:-4] if bare.endswith("ομαι") else bare[:-2]
    stamm = stamm if len(stamm) >= 3 else bare
    text = " ".join([e.get("semantics", ""), e.get("total", "")]
                    + [r["word"] for g in COG_GROUPS for r in e["cognates"].get(g, [])]
                    + [s["word"] for s in e.get("synonyms", [])])
    return stamm in _plain(text)


def _pruefe_zusatz(pj: Projekt, b: Befund, v, tag: str, cogsyn: set[str],
                   buch: dict[str, str], e: dict):
    if not isinstance(v, dict):
        b.f(f"{tag}: extra_vocab-Element kein Objekt")
        return
    vt = f"{tag} extra {v.get('front')!r}"
    bad = set(v) - pj.extra_keys
    if bad:
        b.f(f"{vt}: Felder auf Stufe {pj.stufe} nicht erlaubt: {sorted(bad)}")
    wt = v.get("word_type")
    if wt not in WORD_TYPES:
        b.f(f"{vt}: word_type ungültig {wt!r}")
    if card_from_entry(v) is None:
        b.f(f"{vt}: unlesbar (front/back leer)")
        return
    _text(b, v["front"], vt + " front", griechisch=True)
    _text(b, v["back"], vt + " back")
    for f in ("hints_gr", "hints_de", "notes_gr", "notes_de", "plural"):
        if v.get(f):
            _text(b, v[f], f"{vt} {f}")
    art, bare = _split_leading_article(v["front"])
    hints = str(v.get("hints_gr", ""))
    if wt == "Nomen":
        if v["front"].startswith("[ο/η] "):
            if v.get("article"):
                b.f(f"{vt}: Doppelgenus [ο/η] braucht leeres article")
        else:
            if not art:
                b.f(f"{vt}: Nomen ohne Artikel in front")
            elif v.get("article") != art:
                b.f(f"{vt}: article {v.get('article')!r} ≠ Artikel in front {art!r}")
        if (not v.get("plural") and "nur Singular" not in hints
                and art not in ("οι", "τα") and not bare[:1].isupper()):
            b.f(f"{vt}: Nomen ohne plural (oder „nur Singular“ in hints_gr)")
        if (art == "το" and " " not in bare and D._stripped(bare).endswith("μα")
                and "nur Singular" not in hints):
            want = ma_plural(bare)
            if v.get("plural") != want:
                b.f(f"{vt}: -μα-Plural nach Buchkonvention {want!r}, nicht {v.get('plural')!r}")
    elif art and wt not in ("Phrase", "Sonstiges"):
        b.w(f"{vt}: Artikel in front, aber word_type {wt}")
    if wt == "Verb":
        begruendet = any(x in hints for x in VERB_OHNE_STAMM)
        felder = [f for f in ("stem2", "aorist") if f in pj.extra_keys]
        for f in felder:
            if not v.get(f) and not begruendet:
                b.f(f"{vt}: Verb ohne {f} — ergänzen oder Grund in hints_gr "
                    f"({' / '.join(VERB_OHNE_STAMM)})")
            try:
                parse_stem2_text(str(v.get(f, "") or ""))
            except ValueError as ex:
                b.f(f"{vt}: {f}: {ex}")
        if v.get("stem2") and not str(v["stem2"]).endswith("-") and "," not in v["stem2"]:
            b.f(f"{vt}: stem2 als Stamm mit Bindestrich angeben (z.B. „γράψ-“)")
        im = v.get("imperative") or ""
        if im and not all(x.strip()[:1].isupper() and x.strip().endswith("!")
                          for x in im.split("/")):
            b.f(f"{vt}: imperative groß und mit „!“ (z.B. „Γράψε!“): {im!r}")
    if wt == "Adjektiv" and "unveränderlich" not in hints:
        if not re.search(r"(ος|ός|ης|ής|ύς|ων)$", bare.split("/")[0].strip()):
            b.f(f"{vt}: Adjektiv-front im Maskulinum Sg. (oder „unveränderlich“ in hints_gr)")
        if adjektiv_endungen(hints) is None:
            b.f(f"{vt}: Adjektiv braucht Endungen in hints_gr (z.B. „Endungen: -ος, -η, -ο“)")
    fo = v.get("forms")
    if fo:
        if not isinstance(fo, str):
            b.f(f"{vt}: forms als String „schlüssel=form; …“ angeben")
        else:
            try:
                if any("=" in x for x in parse_forms_text(fo).values()):
                    raise ValueError("Trenner zwischen Formen ist „;“, nicht „,“")
            except ValueError as ex:
                b.f(f"{vt}: forms: {ex}")
            if re.search(r"=\s*(" + "|".join(ARTIKEL) + r")\s", fo + " "):
                b.f(f"{vt}: forms ohne Artikel angeben: {fo!r}")
    for m in app_formfehler(v):
        b.f(f"{vt}: {m}")
    fk = word_key(v["front"])
    if fk in buch:
        b.w(f"{vt}: ist Buchwort ({buch[fk]}) — als Zusatzwort doppelt")
    if fk not in cogsyn and not _erwaehnt(v["front"], e):
        b.f(f"{vt}: Zusatzwort steht weder in cognates/synonyms noch in semantics "
            "(Wortfeld-/Gegenwörter in semantics nennen)")


def pruefe(pj: Projekt, lid: str, teilweise=False) -> tuple[Befund, list[dict]]:
    """teilweise: Liste noch in Arbeit — noch nicht geschriebene Wörter
    zählen nicht als FEHLT, die Reihenfolge gilt für die vorhandenen."""
    b = Befund()
    eintraege = pj.eintraege(lid)
    if not eintraege:
        b.f(f"keine Teildateien {lid}/teil*.json")
        return b, []
    buch = pj.buchwoerter(bis=lid)
    erwartet = pj.erwartet(lid)
    zusatz_bei: dict[str, str] = {}
    keys = []
    for i, e in enumerate(eintraege):
        if not isinstance(e, dict):
            b.f(f"Eintrag {i}: kein Objekt")
            keys.append("")
            continue
        w = e.get("word", "")
        tag = f"[{w}]"
        keys.append(word_key(w))
        _text(b, w, tag + " word", griechisch=True)
        if set(e) != ENTRY_KEYS:
            b.f(f"{tag}: Felder müssen genau {sorted(ENTRY_KEYS)} sein, "
                f"fehlend {sorted(ENTRY_KEYS - set(e))}, zu viel {sorted(set(e) - ENTRY_KEYS)}")
        total, sem = str(e.get("total", "")), str(e.get("semantics", ""))
        if not total.strip():
            b.f(f"{tag}: total leer")
        if total.count("→") > 1:
            b.f(f"{tag}: total mit höchstens einem „→“")
        if not sem.strip():
            b.f(f"{tag}: semantics leer")
        if "\n" in sem:
            b.f(f"{tag}: semantics mehrzeilig")
        if sem and sem[-1] not in ".!?)“\"":
            b.f(f"{tag}: semantics ohne Schlusspunkt")
        _text(b, total, tag + " total")
        _text(b, sem, tag + " semantics")
        for x in e.get("breakdown") or []:
            if not isinstance(x, dict) or set(x) != {"element", "meaning"}:
                b.f(f"{tag}: breakdown-Element braucht genau element+meaning: {x!r}")
                continue
            _text(b, x["element"], tag + " breakdown.element")
            _text(b, x["meaning"], tag + " breakdown.meaning")
        cog = e.get("cognates") or {}
        if not isinstance(cog, dict) or set(cog) != set(COG_GROUPS):
            b.f(f"{tag}: cognates braucht genau die Gruppen {list(COG_GROUPS)}")
            cog = {}
        cogsyn = set()
        for g, rows in cog.items():
            for r in rows if isinstance(rows, list) else [None]:
                if not isinstance(r, dict) or set(r) != {"word", "meaning"}:
                    b.f(f"{tag}: cognates.{g}: Zeile braucht genau word+meaning: {r!r}")
                    continue
                _text(b, r["word"], f"{tag} cognates.{g}.word",
                      griechisch=(g != "german_latin"))
                _text(b, r["meaning"], f"{tag} cognates.{g}.meaning")
                if not r["meaning"].strip():
                    b.f(f"{tag}: cognates.{g} {r['word']!r} ohne meaning")
                if g != "german_latin":
                    cogsyn.add(word_key(r["word"]))
                elif GREEK.search(r["word"]) and not LATIN.search(r["word"]):
                    b.f(f"{tag}: german_latin.word rein griechisch: {r['word']!r}")
        syn_keys = set()
        for s in e.get("synonyms") or []:
            if not isinstance(s, dict) or set(s) != {"word", "nuance"}:
                b.f(f"{tag}: synonyms-Zeile braucht genau word+nuance: {s!r}")
                continue
            _text(b, s["word"], tag + " synonyms.word", griechisch=True)
            _text(b, s["nuance"], tag + " synonyms.nuance")
            if not s["nuance"].strip():
                b.f(f"{tag}: Synonym {s['word']!r} ohne nuance")
            syn_keys.add(word_key(s["word"]))
        cogsyn |= syn_keys
        for v in e.get("extra_vocab") or []:
            _pruefe_zusatz(pj, b, v, tag, cogsyn, buch, e)
            if isinstance(v, dict) and v.get("front"):
                fk = word_key(v["front"])
                if fk in zusatz_bei and zusatz_bei[fk] != w:
                    b.w(f"{tag} extra {v['front']!r}: schon bei [{zusatz_bei[fk]}] "
                        "— Dublette im Paket, die App übernimmt nur die erste")
                zusatz_bei.setdefault(fk, w)
    # Abgleich mit der Liste
    exp_keys = [k for k, _ in erwartet]
    exp_front = {k: c["front"] for k, c in erwartet}
    for k in exp_keys:
        if k not in keys and not teilweise:
            b.f(f"FEHLT: {exp_front[k]!r}")
    for i, k in enumerate(keys):
        if k and k not in exp_front:
            b.f(f"NICHT ERWARTET (nicht in {lid} oder schon früher abgedeckt): "
                f"{eintraege[i].get('word')!r}")
        elif k and eintraege[i].get("word") != exp_front[k]:
            b.f(f"word muss exakt der Karten-front entsprechen: "
                f"{eintraege[i].get('word')!r} ≠ {exp_front[k]!r}")
    for d in sorted({k for k in keys if k and keys.count(k) > 1}):
        b.f(f"DOPPELT im Paket: {d!r}")
    soll = [k for k in exp_keys if k in keys] if teilweise else exp_keys
    if not b.fehler and keys != soll:
        b.f("REIHENFOLGE weicht von der Listenreihenfolge ab")
    pkg = {"title": pj.liste(lid)["name"], "etymology": eintraege}
    try:
        title, parsed = parse_lexicon_package(json.dumps(pkg, ensure_ascii=False))
        assert len(parsed) == len(eintraege)
    except Exception as ex:  # noqa: BLE001 — jede Ablehnung der App melden
        b.f(f"App lehnt das Paket ab: {ex}")
    return b, eintraege


def cmd_pruefen(pj: Projekt, args: list[str], schreiben=False) -> int:
    rc = 0
    for lid in ids_aus(pj, args):
        b, eintraege = pruefe(pj, lid, teilweise="--teilweise" in args)
        n_extra = sum(len(e.get("extra_vocab") or []) for e in eintraege
                      if isinstance(e, dict))
        print(f"== {lid}: {len(eintraege)} Einträge (erwartet "
              f"{len(pj.erwartet(lid))}), {n_extra} Zusatzwörter")
        for m in b.warnungen:
            print("WARNUNG:", m)
        for m in b.fehler:
            print("FEHLER:", m)
        print(f"{len(b.fehler)} Fehler, {len(b.warnungen)} Warnungen")
        if b.fehler:
            rc = 1
            continue
        if schreiben and "--teilweise" not in args:
            out = pj.paket_pfad(lid)
            pkg = {"title": pj.liste(lid)["name"], "etymology": eintraege}
            with open(out, "w", encoding="utf-8") as f:
                json.dump(pkg, f, ensure_ascii=False, indent=1)
                f.write("\n")
            print("geschrieben:", out)
    return rc


# --- Formen, Audit, Auszüge -----------------------------------------------

def formen_zeile(v: dict) -> str:
    card = card_from_entry(v)
    if card is None:
        return f"{v.get('front')!r}: unlesbar"
    head = f"{card.front} | {card.back}"
    if card.word_type == "Nomen":
        noun = D.parse_noun(card)
        if noun is None:
            return f"{head} | Pl {card.plural!r} → kein Deklinationsmuster"
        f = [D.decline(noun, c, n) for c, n in
             (("gen", "sg"), ("nom", "pl"), ("gen", "pl"))]
        extra = f" forms={card.forms}" if card.forms else ""
        hints = f" ({card.hints_gr})" if card.hints_gr else ""
        return (f"{head} | Pl {card.plural!r}{hints} → Gen.Sg {f[0]}, Nom.Pl {f[1]}, "
                f"Gen.Pl {f[2]}{extra}")
    if card.word_type == "Verb":
        verb = C.parse_verb(card)
        if verb is None:
            return f"{head} → nicht konjugierbar ({card.hints_gr})"

        def g(fn, *a):
            try:
                return "/".join(fn(verb, *a))
            except Exception as ex:  # noqa: BLE001
                return f"FEHLER {ex}"
        fut = g(C.conjugate_future, 1, "pl") if C.has_future(verb) else "-"
        aor = (f"{g(C.conjugate_aorist, 3, 'sg')}, {g(C.conjugate_aorist, 1, 'pl')}"
               if C.has_aorist(verb) else "-")
        hints = f" ({card.hints_gr})" if card.hints_gr else ""
        return (f"{head} | st2 {card.stem2!r} ao {card.aorist!r} imp {card.imperative!r}{hints}"
                f" → Präs.2sg {g(C.conjugate, 2, 'sg')}, Fut.1pl {fut}, Aor.3sg/1pl {aor}")
    if card.word_type == "Adjektiv":
        adj = D.parse_adjective(card)
        if adj is None:
            return f"{head} → kein Adjektivmuster ({card.hints_gr})"
        return (f"{head} | {card.hints_gr} → f {D.decline_adjective(adj, 'f', 'nom', 'sg')},"
                f" n {D.decline_adjective(adj, 'n', 'nom', 'sg')}")
    return f"{head} ({card.word_type})"


def cmd_formen(pj: Projekt, args: list[str]) -> int:
    for lid in ids_aus(pj, args):
        lines = [f"[{e['word']}] {formen_zeile(v)}"
                 for e in pj.eintraege(lid) for v in e.get("extra_vocab") or []]
        out = pj.arbeit(f"{lid}_formen.txt")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{lid}: {len(lines)} Zusatzwörter → {out}")
    return 0


def verdacht(e: dict) -> list[tuple[str, str]]:
    """Heuristische Verdachtsfälle eines Eintrags (Kategorie, Text) — keine
    Fehler, sondern Lesehilfe: die Prüfer sehen sie im Auszug am Eintrag."""
    out = []
    wk = word_key(e["word"])
    cog_keys = {word_key(r["word"]) for g in ("identical", "related")
                for r in e["cognates"].get(g, [])}
    syn_keys = {word_key(s["word"]) for s in e["synonyms"]}
    if wk in cog_keys:
        out.append(("kognat_ist_eintragswort", "Eintragswort selbst unter den "
                    "Kognaten — nur ok bei anderer Wortart"))
    if cog_keys & syn_keys:
        out.append(("in_kognaten_und_synonymen", f"{sorted(cog_keys & syn_keys)} — "
                    "echtes Synonym gleicher Wurzel oder Dublette?"))
    for x in e.get("breakdown") or []:
        el = _plain(re.split(r"[\s(/]", x["element"].strip())[0].replace("-", ""))
        if (len(el) > 2 and GREEK.search(el)
                and el not in _plain(word_key(e["word"]).replace(" ", ""))):
            out.append(("zerlegung_nicht_im_wort", f"Element {x['element']!r}"))
    if len(e["semantics"]) > 320:
        out.append(("semantics_lang", f"{len(e['semantics'])} Zeichen"))
    for v in e["extra_vocab"]:
        if v.get("word_type") == "Verb" and v.get("stem2") and v.get("aorist"):
            s2 = _plain(v["stem2"].rstrip("-"))
            ao = _plain(v["aorist"])
            if "," not in ao and s2 not in ao and s2[1:] not in ao:
                out.append(("aorist_stamm", f"{v['front']}: {v['stem2']} / {v['aorist']} "
                            "(Innenaugment/Suppletiv ok)"))
    for where, w in ([("extra", v["front"]) for v in e["extra_vocab"]]
                     + [(g, r["word"]) for g in ("identical", "related")
                        for r in e["cognates"].get(g, [])]
                     + [("syn", s["word"]) for s in e["synonyms"]]):
        for tok in re.split(r"[\s/()\[\],;!?·.]+", w):
            if not re.fullmatch(r"[Ͱ-Ͽἀ-῿]+", tok) or tok.isupper():
                continue
            n_acc = sum(c in "άέήίόύώΐΰ" for c in tok.lower())
            silben = len(re.findall(r"[αεηιουωάέήίόύώϊϋΐΰ]+", tok.lower()))
            if n_acc > 1 or (n_acc == 0 and silben > 1 and tok not in UNBETONT):
                out.append(("akzent", f"{where} {w!r}: {tok}"))
    return out


# einsilbig gesprochene bzw. klitische Wörter ohne Akzent
UNBETONT = {"και", "σε", "με", "να", "θα", "του", "της", "των", "τον", "την",
            "μου", "σου", "μας", "σας", "τους", "τις", "τα", "ένα", "δεν", "μην"}


def cmd_audit(pj: Projekt, args: list[str]) -> int:
    """Alle Verdachtsfälle gesammelt (dieselben stehen im Auszug am Eintrag)
    plus kapitelübergreifend uneinheitliche Zusatzwörter."""
    out = collections.defaultdict(list)
    zusatz = collections.defaultdict(list)
    for lid in ids_aus(pj, args):
        for e in pj.eintraege(lid):
            for kat, text in verdacht(e):
                out[kat].append(f"{lid} [{e['word']}] {text}")
            for v in e["extra_vocab"]:
                zusatz[word_key(v["front"])].append((lid, e["word"], v))
    for lst in zusatz.values():
        if len({json.dumps(v, ensure_ascii=False, sort_keys=True) for *_, v in lst}) > 1:
            out["zusatzwort_uneinheitlich (→ angleichen)"].append(
                f"{lst[0][2]['front']}: " + ", ".join(f"{l}[{w}]" for l, w, _ in lst))
    lines = []
    for k, lst in out.items():
        lines.append(f"### {k}: {len(lst)}")
        lines += ["  " + x for x in lst]
    path = pj.arbeit("audit.txt")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for k, lst in out.items():
        print(f"{k}: {len(lst)}")
    print("→", path)
    return 0


def _woerter_aus_patches(pj: Projekt, muster: str) -> set[tuple[str, str]]:
    out = set()
    for p in glob.glob(str(pj.dir / muster)) or glob.glob(muster):
        for x in json.loads(Path(p).read_text(encoding="utf-8")):
            out.add((pj.id_von(x["chapter"]), word_key(x["word"])))
    return out


def _zeilen(rows, a, b, sep=" = "):
    return "; ".join(f"{r[a]}{sep}{r[b]}" for r in rows) or "–"


# Felder, die formen_zeile ohnehin zeigt (Artikel steckt in front)
SCHON_IN_FORMEN = {"front", "back", "word_type", "article", "plural", "stem2",
                   "aorist", "imperative", "hints_gr"}


def cmd_auszug(pj: Projekt, args: list[str]) -> int:
    """Kompakter Prüfauszug: nur die Felder, die die jeweilige Prüfung
    braucht, eine Zeile je Feld — spart Lese-Tokens gegenüber dem JSON."""
    if not args or args[0] not in ("inhalt", "form"):
        sys.exit("auszug inhalt|form <id>... [--nur patches/angewendet/…/*.json]")
    art, rest = args[0], args[1:]
    nur = None
    if "--nur" in rest:
        i = rest.index("--nur")
        nur = _woerter_aus_patches(pj, rest[i + 1])
        rest = rest[:i] + rest[i + 2:]
    lids = ids_aus(pj, rest)
    lines = []
    for lid in lids:
        karten = {word_key(c["front"]): c for c in pj.liste(lid)["cards"]}
        for nr, e in enumerate(pj.eintraege(lid), 1):
            if nur is not None and (lid, word_key(e["word"])) not in nur:
                continue
            c = karten.get(word_key(e["word"]), {})
            lines.append(f"## {lid} #{nr} {e['word']} — {c.get('back', '')} "
                         f"({c.get('word_type', '')})")
            if art == "inhalt":
                lines.append("  zerlegung: " + _zeilen(e["breakdown"], "element", "meaning"))
                lines.append("  total: " + e["total"])
                lines.append("  semantics: " + e["semantics"])
                for g in COG_GROUPS:
                    lines.append(f"  {g}: " + _zeilen(e["cognates"].get(g, []), "word", "meaning"))
                lines.append("  synonyme: " + _zeilen(e["synonyms"], "word", "nuance", " — "))
                lines.append("  zusatzwörter: " + (", ".join(
                    v["front"] for v in e["extra_vocab"]) or "–"))
                lines += [f"  ⚑ {t}" for k, t in verdacht(e) if k != "akzent"]
            else:
                lines.append("  total: " + e["total"])
                lines.append("  griech.: " + ", ".join(
                    [r["word"] for g in ("identical", "related") for r in e["cognates"][g]]
                    + [s["word"] for s in e["synonyms"]]) )
                for v in e["extra_vocab"]:
                    felder = ", ".join(f"{k}={v[k]!r}" for k in sorted(v)
                                       if k not in SCHON_IN_FORMEN and v[k])
                    lines.append(f"  + {formen_zeile(v)}" + (f" [{felder}]" if felder else ""))
                lines += [f"  ⚑ {t}" for k, t in verdacht(e) if k == "akzent"]
    tag = "-".join(lids) if len(lids) < 4 else f"{lids[0]}-bis-{lids[-1]}"
    path = pj.arbeit(f"auszug_{art}_{tag}{'_nur' if nur is not None else ''}.txt")
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    print(f"{sum(1 for x in lines if x.startswith('## '))} Einträge, "
          f"{len(text)} Zeichen → {path}")
    return 0


# --- Patches, Angleichen ---------------------------------------------------

PATCH_FELDER = ("total", "semantics", "breakdown", "cognates.identical",
                "cognates.related", "cognates.german_latin", "synonyms", "extra_vocab")


def _alle_teile(pj: Projekt) -> dict[Path, tuple[str, list]]:
    return {p: (lid, json.loads(p.read_text(encoding="utf-8")))
            for lid in pj.ids() for p in pj.teile(lid)}


def _schreibe_teile(teile: dict):
    for p, (_lid, data) in teile.items():
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)


def cmd_patch(pj: Projekt, args: list[str]) -> int:
    """Korrekturlisten anwenden. Format je Patch:
    {"chapter": "kap03", "word": "<word exakt>", "field": "<feld>",
     "item": "<word/front des Listenelements>", "value": …, "reason": "…"}
    Listenfelder (cognates.*, synonyms, extra_vocab) brauchen "item";
    value null löscht, unbekanntes item hängt an. Ein ersetztes
    Zusatzwort wird in ALLEN Kapiteln mitgeändert (gleiche Fassung)."""
    dateien = sorted(glob.glob(str(pj.dir / "patches" / "offen" / "*.json")))
    if not dateien:
        print("keine Patches in patches/offen/")
        return 0
    patches = []
    for p in dateien:
        try:
            data = json.loads(Path(p).read_text(encoding="utf-8"))
        except json.JSONDecodeError as ex:
            sys.exit(f"{p}: kein gültiges JSON: {ex}")
        for x in data:
            x["_src"] = Path(p).name
            if x.get("field") not in PATCH_FELDER:
                sys.exit(f"{p}: unbekanntes field {x.get('field')!r} bei {x.get('word')!r}")
            if x["field"] in PATCH_FELDER[3:] and not x.get("item"):
                sys.exit(f"{p}: {x['field']} braucht item ({x.get('word')!r})")
        patches += data
        print(f"{Path(p).name}: {len(data)} Patches")

    def key(x):
        return (pj.id_von(x["chapter"]), word_key(x["word"]), x["field"],
                word_key(x.get("item") or ""))

    gruppen = collections.defaultdict(list)
    for x in patches:
        gruppen[key(x)].append(x)
    konflikte = {k: v for k, v in gruppen.items()
                 if len({json.dumps(y.get("value"), ensure_ascii=False, sort_keys=True)
                         for y in v}) > 1}
    for k, v in konflikte.items():
        print("KONFLIKT", k, [(y["_src"], y.get("value")) for y in v])
    teile = _alle_teile(pj)
    angewendet = fehlt = propagiert = 0
    for k, v in gruppen.items():
        if k in konflikte:
            continue
        lid, wk, feld, ik = k
        x = v[0]
        treffer = [e for p, (l, data) in teile.items() if l == lid
                   for e in data if word_key(e["word"]) == wk]
        if not treffer:
            fehlt += 1
            print("NICHT GEFUNDEN:", lid, x["word"], feld, x["_src"])
            continue
        for e in treffer:
            if feld in ("total", "semantics", "breakdown"):
                e[feld] = x["value"]
                continue
            if feld.startswith("cognates."):
                lst, name = e["cognates"].setdefault(feld.split(".")[1], []), "word"
            elif feld == "synonyms":
                lst, name = e["synonyms"], "word"
            else:
                lst, name = e["extra_vocab"], "front"
            idx = [i for i, it in enumerate(lst) if word_key(it.get(name, "")) == ik]
            if x.get("value") is None:
                for i in reversed(idx):
                    lst.pop(i)
            elif idx:
                lst[idx[0]] = x["value"]
            else:
                lst.append(x["value"])
        angewendet += 1
        if feld == "extra_vocab" and x.get("value") is not None:
            for _p, (_l, data) in teile.items():
                for e in data:
                    for i, it in enumerate(e["extra_vocab"]):
                        if word_key(it.get("front", "")) == ik and it != x["value"]:
                            e["extra_vocab"][i] = x["value"]
                            propagiert += 1
    print(f"{angewendet} angewendet, {propagiert} Zusatzwort-Kopien in anderen "
          f"Einträgen mitgeändert, {fehlt} nicht gefunden, {len(konflikte)} Konflikte")
    if "--anwenden" not in args:
        print("(Probelauf — mit --anwenden schreiben)")
        return 1 if konflikte or fehlt else 0
    if konflikte or fehlt:
        print("Konflikte/fehlende Wörter offen — nichts geschrieben")
        return 1
    _schreibe_teile(teile)
    ziel = (pj.dir / "patches" / "angewendet"
            / datetime.datetime.now().strftime("%Y-%m-%d-%H%M"))
    ziel.mkdir(parents=True, exist_ok=True)
    for p in dateien:
        shutil.move(p, ziel / Path(p).name)
    print(f"Teildateien geschrieben, Patches nach {ziel.relative_to(pj.dir)}")
    return 0


def cmd_angleichen(pj: Projekt, args: list[str]) -> int:
    """Zusatzwörter, die mehrfach vorkommen, auf die Fassung des frühesten
    Vorkommens bringen (frühere Kapitel sind die geprüften)."""
    teile = _alle_teile(pj)
    kanon: dict[str, dict] = {}
    n = 0
    for p, (lid, data) in teile.items():
        for e in data:
            for i, v in enumerate(e["extra_vocab"]):
                k = word_key(v.get("front", ""))
                if k not in kanon:
                    kanon[k] = v
                elif v != kanon[k]:
                    diff = {f: (v.get(f), kanon[k].get(f)) for f in set(v) | set(kanon[k])
                            if v.get(f) != kanon[k].get(f)}
                    print(f"{lid} [{e['word']}] {v.get('front')}: " + ", ".join(
                        f"{f}: {a!r} → {b!r}" for f, (a, b) in diff.items()))
                    e["extra_vocab"][i] = dict(kanon[k])
                    n += 1
    print(f"{n} Zusatzwort-Fassungen angeglichen")
    if "--anwenden" in args and n:
        _schreibe_teile(teile)
        print("Teildateien geschrieben")
    elif n:
        print("(Probelauf — mit --anwenden schreiben)")
    return 0


# --- Vorbereiten, Status, Importtest, Zerlegen ------------------------------

def _info(c: dict) -> str:
    parts = []
    if c.get("plural"):
        parts.append(f"Pl. {c['plural']}")
    for f in ("hints_gr", "hints_de", "notes_de"):
        if c.get(f):
            parts.append(c[f])
    for f in ("stem2", "aorist", "imperative"):
        if c.get(f):
            parts.append(f"{f} {c[f]}")
    return "; ".join(parts)


def cmd_vorbereiten(pj: Projekt, args: list[str]) -> int:
    lid = pj.id_von(args[0])
    erwartet = pj.erwartet(lid)
    vorhanden = {word_key(e.get("word", "")) for e in pj.eintraege(lid)}
    rows = [f"Liste: {pj.liste(lid)['name']}"]
    for nr, (_k, c) in enumerate(erwartet, 1):
        rows.append("\t".join([str(nr), c["front"], c["back"], c.get("article") or "",
                               c.get("word_type", ""), _info(c)]))
    path = pj.arbeit(f"{lid}_woerter.tsv")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"{lid}: {len(erwartet)} Wörter brauchen einen Eintrag → {path}")
    teile = (len(erwartet) + TEIL_GROESSE - 1) // TEIL_GROESSE
    for t in range(teile):
        a, b = t * TEIL_GROESSE, min(len(erwartet), (t + 1) * TEIL_GROESSE)
        offen = sum(1 for k, _ in erwartet[a:b] if k not in vorhanden)
        stand = "fertig" if not offen else f"{offen} offen"
        print(f"  {lid}/teil{t + 1:02d}.json: Nr. {a + 1}–{b} ({stand})")
    return 0


def cmd_status(pj: Projekt, args: list[str]) -> int:
    print(f"{'Liste':10} {'Karten':>6} {'nötig':>6} {'Teile':>6} {'Einträge':>8}  Paket")
    for lid in pj.ids():
        n_karten = len(pj.liste(lid)["cards"])
        if not pj.listen[lid].exists():
            print(f"{lid:10} Listendatei fehlt: {pj.listen[lid]}")
            continue
        teile = pj.teile(lid)
        eintraege = pj.eintraege(lid) if teile else []
        paket = pj.paket_pfad(lid)
        if not paket.exists():
            pstand = "–"
        else:
            data = json.loads(paket.read_text(encoding="utf-8"))
            pstand = ("aktuell" if data.get("etymology") == eintraege
                      else "VERALTET (bauen!)" if teile else "ohne Teile (zerlegen?)")
        if teile:
            b, _ = pruefe(pj, lid)
            pstand += f", {len(b.fehler)} Fehler, {len(b.warnungen)} Warnungen"
        print(f"{lid:10} {n_karten:6} {len(pj.erwartet(lid)):6} {len(teile):6} "
              f"{len(eintraege):8}  {pstand}")
    offen = glob.glob(str(pj.dir / "patches" / "offen" / "*.json"))
    if offen:
        print(f"offene Patchdateien: {len(offen)}")
    return 0


def cmd_importtest(pj: Projekt, args: list[str]) -> int:
    """Alle vorhandenen Pakete in eine frische App-Umgebung importieren
    (echter LexiconStore) und je Liste die ungedeckten Karten melden."""
    tmp = tempfile.mkdtemp()
    alt_env = os.environ.get("FLET_APP_STORAGE_DATA")
    os.environ["FLET_APP_STORAGE_DATA"] = tmp
    try:
        return _importtest(pj, tmp)
    finally:
        if alt_env is None:
            os.environ.pop("FLET_APP_STORAGE_DATA", None)
        else:
            os.environ["FLET_APP_STORAGE_DATA"] = alt_env
        shutil.rmtree(tmp, ignore_errors=True)


def _importtest(pj: Projekt, tmp: str) -> int:
    from mathainoa1.storage import textanalyse as ta
    from mathainoa1.storage.content import ContentStore, load_list
    from mathainoa1.storage.settings import AppSettings, save_app_settings
    store = ContentStore(Path(tmp) / "book", Path(tmp) / "user")
    store.load_all()
    s = AppSettings()
    s.enabled_features = [ta.LEXIKON_KEY]
    s.level = pj.stufe
    save_app_settings(s)
    ta.invalidate_cache()
    lex = ta.lexicon_store(store)
    for p in pj.bekannt:
        if "etymology" in json.loads(p.read_text(encoding="utf-8")):
            lex.import_package(p.read_text(encoding="utf-8"))
    mit_paket = [lid for lid in pj.ids() if pj.paket_pfad(lid).exists()]
    for lid in mit_paket:
        st = lex.import_package(pj.paket_pfad(lid).read_text(encoding="utf-8"))
        print(f"{lid}: {st['new']} neu, {st['updated']} ersetzt, "
              f"{st['extra_new']} Zusatzkarten → „{st['extra_list']}“")
    ok = True
    for lid in mit_paket:
        missing = ta.missing_cards(load_list(pj.listen[lid]).cards)
        print(f"{lid}: ohne Eintrag: {[c.front for c in missing] or 'keine'}")
        ok &= not missing
    for vl in store.lists.values():
        if not vl.editable:
            continue
        # [ο/η]-Nomen dekliniert die App grundsätzlich nicht (auch Buchkarten),
        # begründet stammlose Verben sind gewollt
        kaputt = [c.front for c in vl.cards
                  if (c.word_type == "Nomen" and len(c.front.split()) == 2
                      and not c.front.startswith("[") and D.parse_noun(c) is None)
                  or (c.word_type == "Verb" and C.parse_verb(c) is None
                      and not any(x in c.hints_gr for x in VERB_OHNE_STAMM))]
        if kaputt:
            print(f"„{vl.name}“: App bildet keine Formen (im Training ausgelassen; "
                  f"Plural/Stämme prüfen oder App-Grenze): {kaputt}")
    ta.invalidate_cache()
    print("OK" if ok else "FEHLER: ungedeckte Karten")
    return 0 if ok else 1


def cmd_zerlegen(pj: Projekt, args: list[str]) -> int:
    lid, quelle = pj.id_von(args[0]), Path(args[1])
    if pj.teile(lid) and "--ueberschreiben" not in args:
        sys.exit(f"{lid}/ hat schon Teildateien (--ueberschreiben)")
    data = json.loads(quelle.read_text(encoding="utf-8-sig"))
    eintraege = data.get("etymology") or data.get("entries") or []
    (pj.dir / lid).mkdir(exist_ok=True)
    for p in pj.teile(lid):
        p.unlink()
    for t in range(0, len(eintraege), TEIL_GROESSE):
        p = pj.dir / lid / f"teil{t // TEIL_GROESSE + 1:02d}.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(eintraege[t:t + TEIL_GROESSE], f, ensure_ascii=False, indent=1)
    print(f"{len(eintraege)} Einträge → {len(pj.teile(lid))} Teildateien in {lid}/")
    return 0


BEFEHLE = {
    "status": cmd_status,
    "vorbereiten": cmd_vorbereiten,
    "pruefen": cmd_pruefen,
    "bauen": lambda pj, a: cmd_pruefen(pj, a, schreiben=True),
    "formen": cmd_formen,
    "audit": cmd_audit,
    "auszug": cmd_auszug,
    "patch": cmd_patch,
    "angleichen": cmd_angleichen,
    "importtest": cmd_importtest,
    "zerlegen": cmd_zerlegen,
}


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in BEFEHLE:
        print(__doc__)
        return 2
    return BEFEHLE[argv[0]](Projekt(argv[1]), argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
