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

_NOUN_EXAMPLES = [
    ("m, -ος", "ο δρόμος", "ο", "-οι", None),
    ("m, -ης", "ο χάρτης", "ο", "-ες", None),
    ("m, -ας", "ο άντρας", "ο", "-ες", None),
    ("f, -α", "η θάλασσα", "η", "-ες", None),
    ("f, -η", "η τέχνη", "η", "-ες", None),
    ("f, -η/-εις", "η πόλη", "η", "-εις", None),
    ("n, -ο", "το δώρο", "το", "-α", None),
    ("n, -ι", "το σπίτι", "το", "-ια", None),
    ("n, -μα", "το πρόβλημα", "το", "-ματα", None),
]


def declensions_view() -> ft.Control:
    nouns = []
    for label, front, art, pl, forms in _NOUN_EXAMPLES:
        card = _card(front, article=art, plural=pl, word_type="Nomen",
                     forms=forms or {})
        nouns.append((label, decl.parse_noun(card)))
    rows = []
    for case, num, _ in _CASE_LABELS:
        row = []
        for _, noun in nouns:
            form = decl.decline(noun, case, num)
            art = decl.ARTICLES[(case, num)][noun.gender]
            row.append(_form_cell(form, noun.stem, art) if form else "—")
        rows.append(row)
    return _view(
        _h("Nomen: A1-Muster mit allen Formen"),
        _frozen_table("", [l for _, _, l in _CASE_LABELS],
                      [label for label, _ in nouns], rows),
        _p("Unveränderliche Fremdwörter (το σουβενίρ, το φαξ): alle Formen "
           "gleich, im Programm mit Plural „-“ gekennzeichnet."),
        _p("Eigennamen (η Αθήνα) haben keinen Plural."),
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
    erx = conj.parse_verb(_card("έρχομαι", word_type="Verb"))
    ime = conj.parse_verb(_card("είμαι", word_type="Verb"))
    cols = [_conj_column(v) for v in (graf, agap, erx, ime)]
    fut = _conj_column(graf, future=True)
    return _view(
        _h("Präsens"),
        _frozen_table("Person", _PERSON_LABELS,
                      ["γράφω (A-Typ)", "αγαπάω (B-Typ)",
                       "έρχομαι (-ομαι)", "είμαι (sein)"],
                      [[cols[0][i], cols[1][i], cols[2][i], cols[3][i]]
                       for i in range(6)]),
        _p("A-Typ: Endungen -ω, -εις, -ει, -ουμε, -ετε, -ουν(ε). "
           "B-Typ (-άω): -άω/-ώ, -άς, -άει/-ά, -άμε/-ούμε, -άτε, "
           "-άνε/-ούν(ε). "
           "Endbetont auf -ώ (μπορώ): -ώ, -είς, -εί, -ούμε, -είτε, -ούν(ε). "
           "-ομαι: -ομαι, -εσαι, -εται, -όμαστε, -εστε/-όσαστε, -ονται."),
        _h("Futur und να-Form: θα / να + 2. Stamm"),
        _table(["Person", "γράφω → θα γράψω"],
               [[_PERSON_LABELS[i], fut[i]] for i in range(6)]),
        _p("Nach να stehen dieselben Formen wie nach θα: θέλω να γράψω, "
           "θέλεις να γράψεις … Der 2. Stamm steht im Programm im Feld "
           "„2. Stamm“ (z.B. γράψ-); die Endungen entsprechen dem A-Typ."),
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
