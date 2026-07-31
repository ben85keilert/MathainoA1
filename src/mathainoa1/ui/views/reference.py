"""Grammatik-Nachschlag: A1-Übersichtstabellen (Buchsymbol oben rechts).

Wo möglich werden die Formen aus den Regel-Engines der Trainer erzeugt
(logic/declension.py, logic/conjugation.py) — die Tabellen zeigen damit
exakt die Formen, die auch abgefragt werden.
"""

from __future__ import annotations

import flet as ft

from mathainoa1.logic import conjugation as conj
from mathainoa1.logic import declension as decl
from mathainoa1.models import VocabCard


def _p(text: str) -> ft.Text:
    return ft.Text(text, size=13)


def _h(text: str) -> ft.Text:
    return ft.Text(text, size=15, weight=ft.FontWeight.BOLD)


def _cell_content(v: str | ft.Control) -> ft.Control:
    return v if isinstance(v, ft.Control) else ft.Text(v, size=13)


def _form_cell(form: str, stem: str, article: str = "") -> ft.Control:
    """Zelle wie „του δρόμ-ου“: Endung mit „-“ abgetrennt und fett.

    Der Stamm wird akzent-unabhängig verglichen (δρόμος → δρόμ-ου trotz
    Akzentwanderung); passt er nicht oder gibt es keine Endung (πρόβλημα),
    bleibt die Form ungeteilt."""
    plain = f"{article} {form}".strip()
    s_form = decl.strip_acute(form).lower()
    s_stem = decl.strip_acute(stem).lower() if stem else ""
    if not s_stem or not s_form.startswith(s_stem) or len(form) <= len(stem):
        return ft.Text(plain, size=13)
    head = (f"{article} " if article else "") + form[:len(stem)] + "-"
    return ft.Text(size=13, spans=[
        ft.TextSpan(head),
        ft.TextSpan(form[len(stem):],
                    ft.TextStyle(weight=ft.FontWeight.BOLD)),
    ])


def _table(headers: list[str], rows: list[list[str | ft.Control]]) -> ft.Control:
    table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text(h, weight=ft.FontWeight.BOLD, size=13))
                 for h in headers],
        rows=[ft.DataRow(cells=[ft.DataCell(_cell_content(v)) for v in r])
              for r in rows],
        column_spacing=18,
        heading_row_height=36,
        data_row_min_height=32,
    )
    # breiter als das Fenster -> horizontal scrollen
    return ft.Row([table], scroll=ft.ScrollMode.AUTO)


def _frozen_table(corner: str, row_labels: list[str], headers: list[str],
                  rows: list[list[str]]) -> ft.Control:
    """Tabelle, deren erste Spalte beim horizontalen Scrollen stehen
    bleibt: zwei DataTables mit identischen Zeilenhöhen nebeneinander."""
    dims = dict(column_spacing=18, heading_row_height=36,
                data_row_min_height=34, data_row_max_height=34)

    def head(t: str) -> ft.DataColumn:
        return ft.DataColumn(ft.Text(t, weight=ft.FontWeight.BOLD, size=13))

    def cell(t: str | ft.Control) -> ft.DataCell:
        return ft.DataCell(_cell_content(t))

    left = ft.DataTable(
        columns=[head(corner)],
        rows=[ft.DataRow(cells=[cell(l)]) for l in row_labels], **dims)
    right = ft.DataTable(
        columns=[head(h) for h in headers],
        rows=[ft.DataRow(cells=[cell(v) for v in r]) for r in rows], **dims)
    return ft.Row(
        [left, ft.Row([right], scroll=ft.ScrollMode.AUTO, expand=True)],
        spacing=0, vertical_alignment=ft.CrossAxisAlignment.START)


def _view(*controls: ft.Control) -> ft.Control:
    return ft.Column(list(controls), spacing=12, scroll=ft.ScrollMode.AUTO)


def _card(front: str, **kw) -> VocabCard:
    return VocabCard(front=front, back="", **kw)


# --- 0) Alphabet ---

_LETTERS = [
    ("Α α", "Άλφα", "Alfa", "a"), ("Β β", "Βήτα", "Vita", "w"),
    ("Γ γ", "Γάμα", "Gamma", "gh / j"),
    ("Δ δ", "Δέλτα", "Delta", "th, weich (engl. this)"),
    ("Ε ε", "Έψιλον", "Epsilon", "e"),
    ("Ζ ζ", "Ζήτα", "Sita", "s, stimmhaft"), ("Η η", "Ήτα", "Ita", "i"),
    ("Θ θ", "Θήτα", "Thita", "th, hart (engl. think)"),
    ("Ι ι", "Γιώτα", "Jota", "i"), ("Κ κ", "Κάπα", "Kappa", "k"),
    ("Λ λ", "Λάμδα", "Lamda", "l"), ("Μ μ", "Μι", "Mi", "m"),
    ("Ν ν", "Νι", "Ni", "n"), ("Ξ ξ", "Ξι", "Xi", "x"),
    ("Ο ο", "Όμικρον", "Omikron", "o"), ("Π π", "Πι", "Pi", "p"),
    ("Ρ ρ", "Ρο", "Ro", "r (gerollt)"),
    ("Σ σ / ς", "Σίγμα", "Sigma", "s (ς nur am Wortende)"),
    ("Τ τ", "Ταυ", "Taf", "t"), ("Υ υ", "Ύψιλον", "Ypsilon", "i"),
    ("Φ φ", "Φι", "Fi", "f"),
    ("Χ χ", "Χι", "Chi", "ch (wie in „ach“ / „ich“)"),
    ("Ψ ψ", "Ψι", "Psi", "ps"), ("Ω ω", "Ωμέγα", "Omega", "o"),
]

_COMBOS = [
    ("ου", "u", "μου"),
    ("αι", "e", "και"),
    ("ει, οι, υι", "i", "είμαι, οικογένεια"),
    ("αυ", "av / af", "αύριο, αυτός"),
    ("ευ", "ev / ef", "Ευρώπη, ευχαριστώ"),
    ("μπ", "b am Wortanfang, mb im Wort", "μπαμπάς"),
    ("ντ", "d am Wortanfang, nd im Wort", "ντομάτα"),
    ("γκ, γγ", "g / ng", "γκαρσόν, Αγγλία"),
    ("τσ", "ts", "έτσι"),
    ("τζ", "ds", "τζατζίκι"),
]


def alphabet_view() -> ft.Control:
    return _view(
        _h("Das Alphabet (24 Buchstaben)"),
        _table(["Buchstabe", "Name (gr.)", "Name", "Aussprache"],
               [list(row) for row in _LETTERS]),
        _h("Buchstabenkombinationen"),
        _table(["Kombination", "Aussprache", "Beispiel"],
               [[a, b, c] for a, b, c in _COMBOS]),
        _p("Der Akzent (τόνος) zeigt die betonte Silbe: καλημέρα. "
           "Einsilbige Wörter haben keinen Akzent."),
    )


# --- 1) Artikel ---

_CASE_LABELS = [("nom", "sg", "Nominativ Sg."), ("gen", "sg", "Genitiv Sg."),
                ("acc", "sg", "Akkusativ Sg."), ("nom", "pl", "Nominativ Pl."),
                ("gen", "pl", "Genitiv Pl."), ("acc", "pl", "Akkusativ Pl.")]


def articles_view() -> ft.Control:
    rows = []
    for case, num, label in _CASE_LABELS:
        cells = [label]
        for g in ("m", "f", "n"):
            art = decl.ARTICLES[(case, num)][g]
            # τη(ν): optionales Schluss-ν in Klammern statt zweier Formen
            if decl.ARTICLE_ALTS.get((case, num), {}).get(g):
                art = art[:-1] + f"({art[-1]})"
            cells.append(art)
        rows.append(cells)
    return _view(
        _h("Bestimmter Artikel (der, die, das)"),
        _table(["", "maskulin", "feminin", "neutrum"], rows),
        _p("τη(ν): das Schluss-ν steht vor Vokal und vor κ, π, τ, ξ, ψ, "
           "μπ, ντ, γκ, τσ, τζ — sonst τη. Das Programm akzeptiert beide "
           "Schreibweisen."),
        _h("Unbestimmter Artikel (ein, eine)"),
        _table(["", "maskulin", "feminin", "neutrum"], [
            ["Nominativ", "ένας", "μία / μια", "ένα"],
            ["Genitiv", "ενός", "μιας", "ενός"],
            ["Akkusativ", "έναν", "μία / μια", "ένα"],
        ]),
        _p("Keinen Plural — „einige“ heißt μερικοί/-ές/-ά."),
    )


# --- 2) Deklinationen ---

# Muster je Geschlecht — alle Endungen, die in den A1-Buchlisten
# (Kapitel 1–8) tatsächlich vorkommen, mit Beispielwörtern von dort
_NOUN_EXAMPLES_BY_GENDER = [
    ("Maskulin", [
        ("-ος", "ο γύρος", "ο", "-οι"),
        ("-ης", "ο χάρτης", "ο", "-ες"),
        ("-ας", "ο άντρας", "ο", "-ες"),
        ("-ές", "ο καφές", "ο", "-έδες"),
        ("-ούς", "ο παππούς", "ο", "-ούδες"),
    ]),
    ("Feminin", [
        ("-α", "η ταβέρνα", "η", "-ες"),
        ("-η", "η φίλη", "η", "-ες"),
        ("-ση/-ξη/-ψη", "η ερώτηση", "η", "-εις"),
        ("-ος", "η οδός", "η", "-οί"),
    ]),
    ("Neutrum", [
        ("-ο", "το θέατρο", "το", "-α"),
        ("-ι", "το σπίτι", "το", "-ια"),
        ("-μα", "το όνομα", "το", "-ματα"),
        ("-ος", "το λάθος", "το", "-η"),
    ]),
]


def declensions_view() -> ft.Control:
    sections: list[ft.Control] = [
        _h("Nomen: A1-Muster mit allen Formen"),
        _p("Alle Muster, die in den Buchlisten der Kapitel 1–8 vorkommen, "
           "getrennt nach Geschlecht."),
    ]
    for gender_title, examples in _NOUN_EXAMPLES_BY_GENDER:
        nouns = []
        for label, front, art, pl in examples:
            card = _card(front, article=art, plural=pl, word_type="Nomen")
            nouns.append((label, decl.parse_noun(card)))
        rows = []
        for case, num, _ in _CASE_LABELS:
            row = []
            for _, noun in nouns:
                form = decl.decline(noun, case, num)
                art = decl.ARTICLES[(case, num)][noun.gender]
                row.append(_form_cell(form, noun.stem, art) if form else "—")
            rows.append(row)
        sections += [
            _h(gender_title),
            _frozen_table("", [l for _, _, l in _CASE_LABELS],
                          [label for label, _ in nouns], rows),
        ]
    return _view(
        *sections,
        _p("Unveränderliche Fremdwörter (το μετρό, το σινεμά, η πανσιόν): "
           "alle Formen gleich, im Programm mit Plural „-“ gekennzeichnet."),
        _p("Nur-Plural-Wörter: τα ελληνικά, οι διακοπές, οι γονείς — es "
           "gibt keinen Singular; der Genitiv von οι γονείς (των γονιών/"
           "γονέων) folgt keinem A1-Muster."),
        _p("Eigennamen (η Αθήνα) haben keinen Plural."),
        _p("Sonderfälle aus den Listen ohne A1-Muster: το γάλα → τα "
           "γάλατα, το κρέας → τα κρέατα, το βράδυ → τα βράδια."),
    )


# --- 3) Verben ---

_PERSON_LABELS = ["1. Sg. (εγώ)", "2. Sg. (εσύ)", "3. Sg. (αυτός/-ή/-ό)",
                  "1. Pl. (εμείς)", "2. Pl. (εσείς)", "3. Pl. (αυτοί/-ές/-ά)"]


def _conj_column(verb: conj.Verb, future: bool = False) -> list[str]:
    out = []
    for num in ("sg", "pl"):
        for person in (1, 2, 3):
            forms = (conj.conjugate_future(verb, person, num) if future
                     else conj.conjugate(verb, person, num))
            out.append(("θα " if future else "") + " / ".join(forms or ["—"]))
    return out


def verbs_view() -> ft.Control:
    graf = conj.parse_verb(_card("γράφω", word_type="Verb", stem2="γράψ-"))
    agap = conj.parse_verb(_card("αγαπάω", word_type="Verb"))
    boro = conj.parse_verb(_card("μπορώ", word_type="Verb"))
    erx = conj.parse_verb(_card("έρχομαι", word_type="Verb"))
    sik = conj.parse_verb(_card("σηκώνομαι", word_type="Verb",
                                stem2="σηκωθ-"))
    ime = conj.parse_verb(_card("είμαι", word_type="Verb"))
    present = (graf, agap, boro, erx, ime)
    cols = [_conj_column(v) for v in present]
    # Unregelmäßige Präsens-Verben, die in den Kapiteln 1–8 vorkommen
    irregular = [conj.parse_verb(_card(w, word_type="Verb"))
                 for w in ("πάω", "τρώω", "λέω", "ακούω")]
    irr_cols = [_conj_column(v) for v in irregular]
    fut = _conj_column(graf, future=True)
    fut_sik = _conj_column(sik, future=True)
    return _view(
        _h("Präsens"),
        _frozen_table("Person", _PERSON_LABELS,
                      ["γράφω (A-Typ)", "αγαπάω (B1, -άω)",
                       "μπορώ (B2, -ώ)", "έρχομαι (-ομαι)", "είμαι (sein)"],
                      [[c[i] for c in cols] for i in range(6)]),
        _p("A-Typ: Endungen -ω, -εις, -ει, -ουμε, -ετε, -ουν(ε). "
           "B1 (-άω): -άω/-ώ, -άς, -άει/-ά, -άμε/-ούμε, -άτε, "
           "-άνε/-ούν(ε). "
           "B2, endbetont auf -ώ (μπορώ, ζω): -ώ, -είς, -εί, -ούμε, "
           "-είτε, -ούν(ε). "
           "-ομαι: -ομαι, -εσαι, -εται, -όμαστε, -εστε/-όσαστε, -ονται."),
        _h("Unregelmäßiges Präsens"),
        _frozen_table("Person", _PERSON_LABELS,
                      ["πάω", "τρώω", "λέω", "ακούω"],
                      [[c[i] for c in irr_cols] for i in range(6)]),
        _h("Futur und να-Form: θα / να + 2. Stamm"),
        _frozen_table("Person", _PERSON_LABELS,
                      ["γράφω → θα γράψω (Stamm betont)",
                       "σηκώνομαι → θα σηκωθώ (Stamm unbetont)"],
                      [[fut[i], fut_sik[i]] for i in range(6)]),
        _p("Nach να stehen dieselben Formen wie nach θα: θέλω να γράψω, "
           "θέλεις να γράψεις … Der 2. Stamm steht im Programm im Feld "
           "„2. Stamm“ (z.B. γράψ-). Stamm mit Akzent → A-Typ-Endungen "
           "(θα γράψω); Stamm ohne Akzent → endbetont wie B2 "
           "(σηκωθ- → θα σηκωθώ, θα σηκωθείς …)."),
        _p("Unregelmäßiges Futur aus den Kapiteln 1–8: βλέπω → θα δω, "
           "πίνω → θα πιω, λέω → θα πω, τρώω → θα φάω, πάω → θα πάω. "
           "Im Programm stehen solche Futur-Formen als 6er-Liste im "
           "Feld „2. Stamm“."),
    )


# --- 4) Adjektive ---

_ADJ_EXAMPLES = [("μικρός", "-ος, -η, -ο"), ("ωραίος", "-ος, -α, -ο"),
                 ("γλυκός", "-ός, -ιά, -ό")]


def adjectives_view() -> ft.Control:
    muster_rows = []
    for word, label in _ADJ_EXAMPLES:
        adj = decl.parse_adjective(_card(word, word_type="Adjektiv"))
        muster_rows.append([
            label, adj.word, adj.fem,
            decl.decline_adjective(adj, "n", "nom", "sg"),
        ])
    mikros = decl.parse_adjective(_card("μικρός", word_type="Adjektiv"))
    full_rows = []
    for case, num, label in _CASE_LABELS:
        full_rows.append([label] + [
            _form_cell(decl.decline_adjective(mikros, g, case, num),
                       mikros.stem)
            for g in ("m", "f", "n")
        ])
    return _view(
        _h("Die drei A1-Muster (Nominativ)"),
        _table(["Muster", "maskulin", "feminin", "neutrum"], muster_rows),
        _p("Nach Vokal-Stamm ist das Femininum -α (ωραία), sonst -η "
           "(μικρή); wenige enden auf -ιά (γλυκιά)."),
        _h("Alle Formen am Beispiel μικρός"),
        _table(["", "maskulin", "feminin", "neutrum"], full_rows),
        _p("Die Endungen entsprechen den Nomen-Mustern -ος / -η (-α) / -ο."),
    )


# --- 5) Zahlen ---

_NUMBERS = [
    ("0", "μηδέν"), ("1", "ένα"), ("2", "δύο"), ("3", "τρία"),
    ("4", "τέσσερα"), ("5", "πέντε"), ("6", "έξι"), ("7", "επτά / εφτά"),
    ("8", "οκτώ / οχτώ"), ("9", "εννέα / εννιά"), ("10", "δέκα"),
    ("11", "έντεκα"), ("12", "δώδεκα"), ("13", "δεκατρία"),
    ("14", "δεκατέσσερα"), ("15", "δεκαπέντε"), ("16", "δεκαέξι"),
    ("17", "δεκαεπτά"), ("18", "δεκαοκτώ"), ("19", "δεκαεννέα"),
    ("20", "είκοσι"), ("21", "είκοσι ένα"), ("30", "τριάντα"),
    ("40", "σαράντα"), ("50", "πενήντα"), ("60", "εξήντα"),
    ("70", "εβδομήντα"), ("80", "ογδόντα"), ("90", "ενενήντα"),
    ("100", "εκατό"), ("101", "εκατόν ένα"), ("102", "εκατόν δύο"),
    ("200", "διακόσια"), ("1000", "χίλια"),
]


def numbers_view() -> ft.Control:
    return _view(
        _h("Zahlen"),
        _table(["Zahl", "Griechisch"], [[a, b] for a, b in _NUMBERS]),
        _h("Deklinierbare Zahlen"),
        _table(["Zahl", "maskulin", "feminin", "neutrum"], [
            ["1", "ένας (Akk. έναν)", "μία / μια", "ένα"],
            ["3", "τρεις", "τρεις", "τρία"],
            ["4", "τέσσερις", "τέσσερις", "τέσσερα"],
        ]),
        _p("13 und 14 richten sich nach 3 und 4: δεκατρείς φοιτητές, "
           "δεκατέσσερις μέρες. Alle anderen Zahlen sind unveränderlich."),
    )


# --- 6) Pronomen ---

def pronouns_view() -> ft.Control:
    return _view(
        _h("Personalpronomen"),
        _frozen_table(
            "Person",
            ["ich", "du", "er", "sie (Sg.)", "es", "wir", "ihr",
             "sie (m)", "sie (f)", "sie (n)"],
            ["Nominativ betont", "Genitiv betont", "Akkusativ betont",
             "Genitiv unbetont", "Akkusativ unbetont"],
            [
                ["εγώ", "εμένα", "εμένα", "μου", "με"],
                ["εσύ", "εσένα", "εσένα", "σου", "σε"],
                ["αυτός", "αυτού", "αυτόν", "του", "τον"],
                ["αυτή", "αυτής", "αυτή(ν)", "της", "τη(ν)"],
                ["αυτό", "αυτού", "αυτό", "του", "το"],
                ["εμείς", "εμάς", "εμάς", "μας", "μας"],
                ["εσείς", "εσάς", "εσάς", "σας", "σας"],
                ["αυτοί", "αυτών", "αυτούς", "τους", "τους"],
                ["αυτές", "αυτών", "αυτές", "τους", "τις"],
                ["αυτά", "αυτών", "αυτά", "τους", "τα"],
            ],
        ),
        _p("Die betonten Formen stehen zur Hervorhebung oder nach "
           "Präpositionen: Εγώ είμαι ο Νίκος. Για μένα, σε εμένα. — "
           "Sonst genügt die Verbform: είμαι = ich bin."),
        _p("Der unbetonte Genitiv ist auch das indirekte Objekt (mir, "
           "dir …): μου αρέσει = mir gefällt; σου δίνω = ich gebe dir."),
        _h("Possessiv (mein, dein, …) — nach dem Nomen"),
        _table(["Person", "Form", "Beispiel"], [
            ["mein", "μου", "ο φίλος μου"],
            ["dein", "σου", "το όνομά σου"],
            ["sein", "του", "η φίλη του"],
            ["ihr (Sg.)", "της", "ο γιος της"],
            ["sein (n)", "του", "το χρώμα του"],
            ["unser", "μας", "το σπίτι μας"],
            ["euer / Ihr", "σας", "η σειρά σας"],
            ["ihr (Pl.)", "τους", "τα παιδιά τους"],
        ]),
    )


# --- 7) Fragewörter + Präpositionen ---

def questions_view() -> ft.Control:
    return _view(
        _h("Fragewörter"),
        _table(["Griechisch", "Deutsch"], [
            ["τι;", "was?"],
            ["ποιος; / ποια; / ποιο;", "wer? / welcher, -e, -es?"],
            ["πού;", "wo? wohin?"],
            ["από πού;", "woher?"],
            ["πότε;", "wann?"],
            ["πώς;", "wie?"],
            ["πόσο;", "wie viel?"],
            ["πόσοι; / πόσες; / πόσα;", "wie viele? (m / f / n)"],
            ["γιατί;", "warum?"],
        ]),
        _p("Das griechische Fragezeichen ist das Semikolon (;)."),
        _h("Präpositionen — alle mit Akkusativ"),
        _table(["Griechisch", "Deutsch", "Beispiel"], [
            ["σε", "in, an, zu, nach", "στην Αθήνα"],
            ["από", "von, aus", "από τη Γερμανία"],
            ["με", "mit", "με το λεωφορείο"],
            ["για", "für, nach (Richtung)", "για την Κρήτη"],
            ["χωρίς", "ohne", "χωρίς ζάχαρη"],
            ["μετά", "nach (zeitlich)", "μετά το μάθημα"],
            ["πριν (από)", "vor (zeitlich)", "πριν από το πρωινό"],
            ["μέχρι", "bis", "μέχρι τις δέκα"],
            ["κοντά σε", "nahe bei", "κοντά στο κέντρο"],
            ["μακριά από", "weit weg von", "μακριά από τη θάλασσα"],
        ]),
        _p("σε verschmilzt mit dem bestimmten Artikel: στο(ν), στη(ν), "
           "στο, στους, στις, στα."),
    )


# --- Beugungstabellen für ein einzelnes Wort (Dialog in den Trainern) ---

def _noun_forms_table(card: VocabCard) -> ft.Control | None:
    noun = decl.parse_noun(card)
    if noun is None:
        return None
    rows, any_form = [], False
    for case, num, label in _CASE_LABELS:
        form = decl.decline(noun, case, num)
        if form:
            any_form = True
            art = decl.ARTICLES[(case, num)][noun.gender]
            rows.append([label, _form_cell(form, noun.stem, art)])
        else:
            rows.append([label, "—"])
    if not any_form:
        return None
    return _table(["Fall", "Form"], rows)


def _adjective_forms_table(card: VocabCard) -> ft.Control | None:
    adj = decl.parse_adjective(card)
    if adj is None:
        return None
    rows = [[label] + [_form_cell(decl.decline_adjective(adj, g, case, num),
                                  adj.stem)
                       for g in ("m", "f", "n")]
            for case, num, label in _CASE_LABELS]
    return _table(["", "maskulin", "feminin", "neutrum"], rows)


def _verb_forms_tables(card: VocabCard) -> ft.Control | None:
    verb = conj.parse_verb(card)
    if verb is None:
        return None
    col = _conj_column(verb)
    controls: list[ft.Control] = [
        _h("Präsens"),
        _table(["Person", "Form"],
               [[_PERSON_LABELS[i], col[i]] for i in range(6)]),
    ]
    if conj.has_future(verb):
        fut = _conj_column(verb, future=True)
        controls += [
            _h("Futur (θα + 2. Stamm)"),
            _table(["Person", "Form"],
                   [[_PERSON_LABELS[i], fut[i]] for i in range(6)]),
        ]
    return ft.Column(controls, tight=True, spacing=12)


def word_forms_content(card: VocabCard) -> ft.Control | None:
    """Deklinations-/Konjugationstabelle für genau diese Karte —
    None, wenn kein Muster erkannt wird (dann keinen Button anbieten)."""
    if card.word_type == "Nomen":
        return _noun_forms_table(card)
    if card.word_type == "Adjektiv":
        return _adjective_forms_table(card)
    if card.word_type == "Verb":
        return _verb_forms_tables(card)
    return None


def has_word_forms(card: VocabCard) -> bool:
    return word_forms_content(card) is not None


def show_word_forms(page: ft.Page, card: VocabCard) -> None:
    """Beugungsformen der Karte als Dialog (aus den Trainern aufrufbar)."""
    content = word_forms_content(card)
    if content is None:
        page.show_dialog(ft.SnackBar(ft.Text(
            "Für dieses Wort sind keine Beugungsformen ableitbar.")))
        return
    page.show_dialog(ft.AlertDialog(
        title=ft.Text(card.with_plural(card.front)),
        content=ft.Container(
            ft.Column([content], tight=True, scroll=ft.ScrollMode.AUTO),
            width=420),
        actions=[ft.IconButton(ft.Icons.CLOSE, tooltip="Schließen",
                               on_click=lambda e: page.pop_dialog())],
    ))


CHAPTERS = [
    ("Alphabet", ft.Icons.ABC, alphabet_view),
    ("Artikel", ft.Icons.LABEL_OUTLINE, articles_view),
    ("Deklinationen", ft.Icons.TABLE_CHART_OUTLINED, declensions_view),
    ("Verben", ft.Icons.SYNC_ALT, verbs_view),
    ("Adjektive", ft.Icons.PALETTE_OUTLINED, adjectives_view),
    ("Zahlen", ft.Icons.NUMBERS, numbers_view),
    ("Pronomen", ft.Icons.PERSON_OUTLINE, pronouns_view),
    ("Fragewörter + Präpositionen", ft.Icons.QUESTION_MARK, questions_view),
]


def reference_menu_button(nav) -> ft.PopupMenuButton:
    """Buchsymbol in der App-Leiste: Menü mit den Grammatik-Kapiteln."""
    def open_chapter(title: str, builder):
        def handler(e):
            nav.go(title, builder())
        return handler

    return ft.PopupMenuButton(
        icon=ft.Icons.MENU_BOOK_OUTLINED,
        tooltip="Grammatik-Tabellen",
        items=[
            ft.PopupMenuItem(content=ft.Text(title), icon=icon,
                             on_click=open_chapter(title, builder))
            for title, icon, builder in CHAPTERS
        ],
    )
