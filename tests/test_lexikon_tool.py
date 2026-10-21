"""Tests für tools/lexikon.py (Lexikon-Pakete erzeugen und prüfen) mit
einem erfundenen Mini-Projekt — echte Buchlisten bleiben in private/."""

import importlib.util
import json
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "lexikon_tool", Path(__file__).resolve().parents[1] / "tools" / "lexikon.py")
lx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lx)


def card(front, back, word_type, article=None, **kw):
    return {"front": front, "back": back, "word_type": word_type,
            "article": article, **kw}


def entry(word, extras=(), related=(), synonyms=()):
    return {"word": word,
            "breakdown": [{"element": "γραφ-", "meaning": "ritzen, schreiben"}],
            "total": "das Geschriebene → Brief",
            "semantics": "Zu altgr. γράφω „ritzen, schreiben“.",
            "cognates": {"identical": [],
                         "related": [{"word": w, "meaning": "verwandt"} for w in related],
                         "german_latin": [{"word": "Grammatik",
                                           "meaning": "über lat. aus griech."}]},
            "synonyms": [{"word": w, "nuance": "andere Wurzel"} for w in synonyms],
            "extra_vocab": list(extras)}


GRAMMA = {"front": "το γράμμα", "back": "Buchstabe / Brief", "article": "το",
          "plural": "-ματα", "word_type": "Nomen"}


@pytest.fixture
def projekt(tmp_path):
    def liste(name, cards):
        return {"name": name, "cards": cards}
    (tmp_path / "k1.json").write_text(json.dumps(liste("Buch – Kapitel 1", [
        card("γράφω", "schreiben", "Verb", stem2="γράψ-"),
        card("ο φίλος", "Freund", "Nomen", "ο", plural="-οι"),
    ]), ensure_ascii=False), encoding="utf-8")
    (tmp_path / "k2.json").write_text(json.dumps(liste("Buch – Kapitel 2", [
        card("γράφω", "schreiben", "Verb"),
        card("η γραφή", "Schrift", "Nomen", "η", plural="-ές"),
    ]), ensure_ascii=False), encoding="utf-8")
    d = tmp_path / "lexikon"
    d.mkdir()
    (d / "projekt.json").write_text(json.dumps({
        "stufe": "A2", "listen": {"kap01": "../k1.json", "kap02": "../k2.json"},
        "paket": "../lexikon-{id}.json"}), encoding="utf-8")
    return d


def schreibe(projekt, lid, eintraege, teil=1):
    (projekt / lid).mkdir(exist_ok=True)
    (projekt / lid / f"teil{teil:02d}.json").write_text(
        json.dumps(eintraege, ensure_ascii=False), encoding="utf-8")


def gute_kap01():
    return [entry("γράφω", extras=[GRAMMA], related=["το γράμμα"]),
            entry("ο φίλος")]


def test_erwartet_ueberspringt_woerter_frueherer_listen(projekt):
    pj = lx.Projekt(projekt)
    assert [c["front"] for _, c in pj.erwartet("kap02")] == ["η γραφή"]


def test_korrektes_paket_ohne_befund_und_bauen(projekt):
    schreibe(projekt, "kap01", gute_kap01())
    pj = lx.Projekt(projekt)
    befund, _ = lx.pruefe(pj, "kap01")
    assert befund.fehler == [] and befund.warnungen == []
    assert lx.cmd_pruefen(pj, ["kap01"], schreiben=True) == 0
    paket = json.loads((projekt.parent / "lexikon-kap01.json").read_text("utf-8"))
    assert paket["title"] == "Buch – Kapitel 1"
    assert [e["word"] for e in paket["etymology"]] == ["γράφω", "ο φίλος"]


def fehler_zu(projekt, eintraege):
    schreibe(projekt, "kap01", eintraege)
    befund, _ = lx.pruefe(lx.Projekt(projekt), "kap01")
    return "\n".join(befund.fehler)


@pytest.mark.parametrize("extra, erwartet", [
    (dict(GRAMMA, plural="-τα"), "-μα-Plural"),
    (dict(GRAMMA, forms="gen_sg=γράμματος, nom_pl=γράμματα"), "forms"),
    (dict(GRAMMA, forms="gen_sg=του γράμματος"), "ohne Artikel"),
    (dict(GRAMMA, article="η"), "≠ Artikel"),
    (dict(GRAMMA, front="το γραμμα"), "Zusatzwort steht weder"),
    (dict(GRAMMA, aorist_passive="γράφτηκα"), "nicht erlaubt"),
    ({"front": "γράφω", "back": "schreiben", "word_type": "Verb"}, "Verb ohne stem2"),
    ({"front": "σκούρος", "back": "dunkel", "word_type": "Adjektiv",
      "hints_gr": "Endungen: -ος, -α, -ο"}, "Femininum"),
    ({"front": "η ποιότητα", "back": "Qualität", "article": "η", "plural": "-ες",
      "word_type": "Nomen"}, "Gen.Pl."),
    ({"front": "τα μεσάνυχτα", "back": "Mitternacht", "article": "τα",
      "word_type": "Nomen", "hints_gr": "nur Plural"}, "Pluralwort"),
])
def test_typische_fehler_werden_erkannt(projekt, extra, erwartet):
    word = extra["front"].split()[-1]
    eintraege = gute_kap01()
    eintraege[1] = entry("ο φίλος", extras=[extra], related=[extra["front"]])
    if extra["front"] == "το γραμμα":  # Tippfehler: nicht mehr verknüpft
        eintraege[1] = entry("ο φίλος", extras=[extra])
    assert erwartet in fehler_zu(projekt, eintraege), word


def test_unpersoenliches_verb_mit_begruendung_erlaubt(projekt):
    extra = {"front": "βραδιάζει", "back": "es wird Abend", "word_type": "Verb",
             "hints_gr": "unpersönlich, nur 3. Person"}
    eintraege = gute_kap01()
    eintraege[1] = entry("ο φίλος", extras=[extra], related=["βραδιάζει"])
    assert fehler_zu(projekt, eintraege) == ""


def test_vollstaendigkeit_und_reihenfolge(projekt):
    assert "FEHLT: 'ο φίλος'" in fehler_zu(projekt, gute_kap01()[:1])
    assert "REIHENFOLGE" in fehler_zu(projekt, gute_kap01()[::-1])
    assert "NICHT ERWARTET" in fehler_zu(projekt, gute_kap01() + [entry("η γραφή")])


def test_homoglyph_wird_erkannt(projekt):
    eintraege = gute_kap01()
    eintraege[0]["semantics"] = "Zu altgr. γpάφω „ritzen“."  # lateinisches p
    assert "gemischte Schrift" in fehler_zu(projekt, eintraege)


def test_patch_ersetzt_zusatzwort_in_allen_kapiteln(projekt):
    schreibe(projekt, "kap01", gute_kap01())
    schreibe(projekt, "kap02", [entry("η γραφή", extras=[GRAMMA], related=["το γράμμα"])])
    offen = projekt / "patches" / "offen"
    offen.mkdir(parents=True)
    neu = dict(GRAMMA, back="Buchstabe / Brief / Schreiben")
    (offen / "p.json").write_text(json.dumps([
        {"chapter": 1, "word": "γράφω", "field": "extra_vocab",
         "item": "το γράμμα", "value": neu, "reason": "Test"},
        {"chapter": "kap01", "word": "ο φίλος", "field": "semantics",
         "value": "Neu.", "reason": "Test"},
    ], ensure_ascii=False), encoding="utf-8")
    pj = lx.Projekt(projekt)
    assert lx.cmd_patch(pj, ["--anwenden"]) == 0
    assert pj.eintraege("kap02")[0]["extra_vocab"][0] == neu
    assert pj.eintraege("kap01")[1]["semantics"] == "Neu."
    assert not list(offen.glob("*.json"))


def test_patch_konflikt_schreibt_nichts(projekt):
    schreibe(projekt, "kap01", gute_kap01())
    offen = projekt / "patches" / "offen"
    offen.mkdir(parents=True)
    for i, wert in enumerate(["A.", "B."]):
        (offen / f"p{i}.json").write_text(json.dumps([
            {"chapter": 1, "word": "ο φίλος", "field": "total", "value": wert}]),
            encoding="utf-8")
    pj = lx.Projekt(projekt)
    assert lx.cmd_patch(pj, ["--anwenden"]) == 1
    assert pj.eintraege("kap01")[1]["total"] == "das Geschriebene → Brief"


def test_angleichen_uebernimmt_frueheste_fassung(projekt):
    schreibe(projekt, "kap01", gute_kap01())
    schreibe(projekt, "kap02", [entry("η γραφή", related=["το γράμμα"],
                                      extras=[dict(GRAMMA, back="Brief")])])
    pj = lx.Projekt(projekt)
    lx.cmd_angleichen(pj, ["--anwenden"])
    assert pj.eintraege("kap02")[0]["extra_vocab"][0] == GRAMMA


def test_ma_plural_konvention():
    assert lx.ma_plural("γράμμα") == "-ματα"
    assert lx.ma_plural("μάθημα") == "-(θή)ματα"


def test_teilweise_prueft_nur_vorhandene(projekt):
    schreibe(projekt, "kap01", gute_kap01()[:1])
    befund, _ = lx.pruefe(lx.Projekt(projekt), "kap01", teilweise=True)
    assert befund.fehler == []
