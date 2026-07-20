import json

from mathainoa1.models import VocabCard, VocabList
from mathainoa1.storage import content


def make_list(**kw) -> VocabList:
    cards = [
        VocabCard(front="το βιβλίο", article="το",
                  back="das Buch", word_type="Nomen"),
        VocabCard(front="καλημέρα", back="guten Morgen", word_type="Phrase"),
    ]
    return VocabList(name="Testliste", cards=cards, **kw)


def test_json_roundtrip(tmp_path):
    vlist = make_list(chapter=1, book="A1")
    path = tmp_path / "l.json"
    content.save_list(vlist, path)
    loaded = content.load_list(path)
    assert loaded.to_dict() == vlist.to_dict()
    assert loaded.cards[0].front == "το βιβλίο"


def test_card_greek_with_without_article():
    card = VocabCard(front="το βιβλίο", article="το", back="das Buch")
    assert card.greek(with_article=True) == "το βιβλίο"
    # Form ohne Artikel wird aus front abgeleitet, kein eigenes Feld
    assert card.greek(with_article=False) == "βιβλίο"
    phrase = VocabCard(front="καλημέρα", back="guten Morgen")
    assert phrase.greek(with_article=False) == "καλημέρα"


def test_store_book_lists_not_editable(tmp_path):
    book_dir, user_dir = tmp_path / "book", tmp_path / "user"
    content.save_list(make_list(chapter=1), book_dir / "kap01.json")
    store = content.ContentStore(book_dir, user_dir)
    store.load_all()
    (vlist,) = store.lists.values()
    assert vlist.editable is False
    try:
        store.save_user_list(vlist)
        assert False, "Buchliste darf nicht speicherbar sein"
    except ValueError:
        pass


def test_store_user_list_crud(tmp_path):
    store = content.ContentStore(tmp_path / "book", tmp_path / "user")
    store.load_all()
    vlist = make_list(chapter=None)
    store.save_user_list(vlist)
    assert (tmp_path / "user" / f"{vlist.id}.json").exists()
    assert store.general_lists() == [vlist]
    store.delete_user_list(vlist.id)
    assert store.lists == {}


def test_csv_roundtrip():
    vlist = make_list()
    text = content.export_csv(vlist)
    imported = content.import_csv("Import", text)
    assert len(imported.cards) == 2
    assert imported.cards[0].article == "το"
    assert imported.cards[1].word_type == "Phrase"


HEADER = ",".join(content.CSV_FIELDS)


def test_csv_import_tolerates_bom_and_whitespace():
    text = ("﻿" + HEADER + "\n"
            + 'ο δρόμος, Straße ,-οι, ο ,Nomen,,,,,,\n')
    imported = content.import_csv("Import", text)
    assert len(imported.cards) == 1
    c = imported.cards[0]
    assert (c.front, c.back, c.article) == ("ο δρόμος", "Straße", "ο")


def test_csv_import_normalizes_latin_lookalike_article():
    # lateinisches "o" statt griechischem "ο" (OCR-/Chatbot-Fehler)
    text = HEADER + '\n"o δρόμος","Straße","-οι","o","Nomen",,,,,,\n'
    c = content.import_csv("Import", text).cards[0]
    assert c.article == "ο" and c.front == "ο δρόμος"
    from mathainoa1.logic.declension import parse_noun
    assert parse_noun(c) is not None


def test_csv_import_derives_or_prepends_article():
    # Artikel nur in der Spalte -> wird front vorangestellt
    text = HEADER + '\n"δρόμος","Straße","-οι","ο","Nomen",,,,,,\n'
    c = content.import_csv("Import", text).cards[0]
    assert c.front == "ο δρόμος" and c.article == "ο"
    # Artikel nur in front (Nomen) -> Spalte wird abgeleitet
    text = HEADER + '\n"η ταβέρνα","Taverne","-ες",,"Nomen",,,,,,\n'
    c = content.import_csv("Import", text).cards[0]
    assert c.article == "η"
    # Widerspruch: front gewinnt
    text = HEADER + '\n"ο δρόμος","Straße","-οι","η","Nomen",,,,,,\n'
    c = content.import_csv("Import", text).cards[0]
    assert c.article == "ο" and c.front == "ο δρόμος"


def test_csv_import_no_article_for_phrases():
    # "τα λέμε" beginnt mit Artikel-Wort, ist aber keins
    text = HEADER + '\n"τα λέμε","bis dann",,,"Phrase",,,,,,\n'
    c = content.import_csv("Import", text).cards[0]
    assert c.article is None and c.front == "τα λέμε"


def test_csv_import_unknown_word_type_falls_back():
    text = (HEADER + '\n"και","und",,,"Konjunktion",,,,,,\n'
            + '"εδώ","hier",,,"adverb",,,,,,\n')
    cards = content.import_csv("Import", text).cards
    assert cards[0].word_type == "Sonstiges"
    assert cards[1].word_type == "Adverb"  # Groß-/Kleinschreibung tolerant


def test_json_import_forces_editable():
    vlist = make_list()
    vlist.editable = False
    imported = content.import_json(content.export_json(vlist))
    assert imported.editable is True
    assert json.loads(content.export_json(imported))["name"] == "Testliste"


# --- Listen-Reihenfolge (list_order.json) ---


def make_store(tmp_path, names):
    """Store mit einer Buchliste ("Buch") und User-Listen (names)."""
    book_dir, user_dir = tmp_path / "book", tmp_path / "user"
    content.save_list(VocabList(name="Buch", cards=[]), book_dir / "b.json")
    store = content.ContentStore(book_dir, user_dir)
    store.load_all()
    for n in names:
        store.save_user_list(VocabList(name=n, cards=[]))
    return store


def test_ordered_lists_default(tmp_path):
    store = make_store(tmp_path, ["Zeta", "Alpha"])
    # ohne Order-Datei: Buchlisten zuerst, dann alphabetisch
    assert [l.name for l in store.ordered_lists()] == ["Buch", "Alpha", "Zeta"]


def test_move_list_persists(tmp_path):
    store = make_store(tmp_path, ["Zeta", "Alpha"])
    alpha = next(l for l in store.lists.values() if l.name == "Alpha")
    store.move_list(alpha.id, -1)
    assert [l.name for l in store.ordered_lists()] == ["Alpha", "Buch", "Zeta"]
    # Reihenfolge überlebt ein Neuladen
    fresh = content.ContentStore(store.book_dir, store.user_dir)
    fresh.load_all()
    assert [l.name for l in fresh.ordered_lists()] == ["Alpha", "Buch", "Zeta"]
    # Order-Datei wird nicht als Vokabelliste geladen
    assert all(l.name != "" for l in fresh.lists.values())
    assert len(fresh.lists) == 3


def test_move_list_clamps_at_edges(tmp_path):
    store = make_store(tmp_path, ["Alpha"])
    first = store.ordered_lists()[0]
    store.move_list(first.id, -1)  # no-op
    last = store.ordered_lists()[-1]
    store.move_list(last.id, 1)  # no-op
    assert [l.name for l in store.ordered_lists()] == ["Buch", "Alpha"]


def test_ordered_lists_ignores_stale_and_appends_new(tmp_path):
    store = make_store(tmp_path, ["Alpha"])
    store.move_list(store.ordered_lists()[0].id, 1)  # Order-Datei anlegen
    # verwaiste ID einschmuggeln
    with open(store.order_path, encoding="utf-8") as f:
        order = json.load(f)["order"]
    with open(store.order_path, "w", encoding="utf-8") as f:
        json.dump({"order": ["geloescht123"] + order}, f)
    fresh = content.ContentStore(store.book_dir, store.user_dir)
    fresh.load_all()
    assert [l.name for l in fresh.ordered_lists()] == ["Alpha", "Buch"]
    # neue Liste landet hinten
    fresh.save_user_list(VocabList(name="Neu", cards=[]))
    assert [l.name for l in fresh.ordered_lists()] == ["Alpha", "Buch", "Neu"]


def test_broken_order_file_falls_back(tmp_path):
    store = make_store(tmp_path, ["Alpha"])
    store.user_dir.mkdir(parents=True, exist_ok=True)
    store.order_path.write_text("kein json", encoding="utf-8")
    fresh = content.ContentStore(store.book_dir, store.user_dir)
    fresh.load_all()
    assert [l.name for l in fresh.ordered_lists()] == ["Buch", "Alpha"]


def test_card_reorder_roundtrip(tmp_path):
    store = content.ContentStore(tmp_path / "book", tmp_path / "user")
    store.load_all()
    vlist = make_list()
    store.save_user_list(vlist)
    vlist.cards[0], vlist.cards[1] = vlist.cards[1], vlist.cards[0]
    store.save_user_list(vlist)
    fresh = content.ContentStore(store.book_dir, store.user_dir)
    fresh.load_all()
    assert [c.front for c in fresh.lists[vlist.id].cards] == [
        "καλημέρα", "το βιβλίο"]


# --- Beispielliste ---


def test_example_list_covers_all_word_types():
    from mathainoa1.models import WORD_TYPES
    vlist = content.example_vocab_list()
    assert vlist.editable
    present = {c.word_type for c in vlist.cards}
    assert present == set(WORD_TYPES)  # alle Worttypen vertreten


def test_example_list_has_regular_and_irregular():
    vlist = content.example_vocab_list()
    by_front = {c.front: c for c in vlist.cards}
    # unregelmäßig: forms/stem2 gesetzt
    assert by_front["η γυναίκα"].forms.get("gen_pl") == "γυναικών"
    assert by_front["πάω"].forms.get("2sg") == "πας"
    assert by_front["γλυκός"].forms.get("fem") == "γλυκιά"
    assert by_front["γράφω"].stem2 == "γράψ-"
    # regelmäßig: keine Sonderformen
    assert not by_front["ο δρόμος"].forms and not by_front["ο δρόμος"].stem2


def test_example_list_export_roundtrip():
    vlist = content.example_vocab_list()
    again = content.import_csv("x", content.export_csv(vlist))
    assert len(again.cards) == len(vlist.cards)


def test_example_future_is_type_a():
    # regressionssicher: 2. Stamm mit Akzent -> γράψω, nicht γραψώ
    from mathainoa1.logic import conjugation as conj
    vlist = content.example_vocab_list()
    verb = next(v for c, v in conj.conjugatable_verbs(vlist.cards)
                if c.front == "γράφω")
    assert conj.conjugate_future(verb, 1, "sg") == ["γράψω"]


# --- Wortsuche (search_cards) ---


def _search_store(tmp_path):
    store = content.ContentStore(tmp_path / "book", tmp_path / "user")
    store.load_all()
    l1 = VocabList(name="Kapitel 1", cards=[
        VocabCard(front="ο δρόμος", back="Straße", article="ο", word_type="Nomen"),
        VocabCard(front="το σπίτι", back="Haus", article="το", word_type="Nomen"),
    ])
    l2 = VocabList(name="Kapitel 2", cards=[
        VocabCard(front="ο δρόμος", back="Straße, Weg", article="ο", word_type="Nomen"),
    ])
    store.save_user_list(l1)
    store.save_user_list(l2)
    return store, l1, l2


def test_search_by_german_and_greek(tmp_path):
    store, *_ = _search_store(tmp_path)
    assert [c.back for _, c, _ in store.search_cards("Haus")] == ["Haus"]
    assert all(c.front == "το σπίτι" for _, c, _ in store.search_cards("σπίτι"))


def test_search_is_accent_and_case_insensitive(tmp_path):
    store, *_ = _search_store(tmp_path)
    # ohne Akzent, groß geschrieben -> findet trotzdem
    assert store.search_cards("ΔΡΟΜΟΣ")
    assert store.search_cards("straße")


def test_search_same_word_in_two_lists_appears_twice(tmp_path):
    store, l1, l2 = _search_store(tmp_path)
    hits = store.search_cards("δρόμος")
    assert len(hits) == 2
    assert {vl.name for vl, _, _ in hits} == {"Kapitel 1", "Kapitel 2"}


def test_search_marks_cards_in_selection(tmp_path):
    from mathainoa1.models import SelectionList
    store, l1, l2 = _search_store(tmp_path)
    target = l1.cards[0]
    store.save_selection(SelectionList(name="Meine Auswahl", card_ids=[target.id]))
    hits = {c.id: sels for _, c, sels in store.search_cards("δρόμος")}
    assert hits[target.id] == ["Meine Auswahl"]
    assert hits[l2.cards[0].id] == []  # gleiche Bedeutung, andere Karte -> kein Stern


def test_search_empty_query(tmp_path):
    store, *_ = _search_store(tmp_path)
    assert store.search_cards("") == []
    assert store.search_cards("   ") == []


def test_app_settings_roundtrip():
    from mathainoa1.storage.settings import AppSettings
    s = AppSettings(theme="dark", seed="green", accent_resets_box=True,
                    case_resets_box=True, high_boxes_need_production=False,
                    top_box_needs_typing=False, autoplay_audio=True)
    assert AppSettings.from_dict(s.to_dict()) == s
    # unbekannte Keys werden ignoriert, Defaults greifen (Beschränkungen an)
    d = AppSettings.from_dict({"foo": 1})
    assert d.theme == "system"
    assert d.high_boxes_need_production and d.top_box_needs_typing


def test_card_ids_survive_json_roundtrip():
    # Lernstand (progress.db) hängt an den Karten-IDs — sie müssen den
    # Export/Import-Rundweg unverändert überstehen
    vlist = make_list()
    loaded = content.import_json(content.export_json(vlist))
    assert [c.id for c in loaded.cards] == [c.id for c in vlist.cards]
