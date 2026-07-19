from mathainoa1.models import SelectionList, VocabCard, VocabList
from mathainoa1.storage import content
from mathainoa1.storage.content import ContentStore


def make_store(tmp_path) -> ContentStore:
    book = VocabList(
        id="book1", name="Kapitel 1", chapter=1,
        cards=[VocabCard(front=f"λ{i}", back=f"W{i}", id=f"b{i}") for i in range(5)],
    )
    content.save_list(book, tmp_path / "book" / "kap01.json")
    store = ContentStore(tmp_path / "book", tmp_path / "user")
    store.load_all()
    return store


def test_selection_roundtrip_and_resolve(tmp_path):
    store = make_store(tmp_path)
    sel = SelectionList(name="Schwere Wörter", card_ids=["b1", "b3", "fehlt"])
    store.save_selection(sel)

    store2 = make_store(tmp_path)
    loaded = store2.selections[sel.id]
    assert loaded.name == "Schwere Wörter"
    # fehlende IDs werden beim Auflösen still übersprungen
    assert [c.id for c in store2.cards_for(sel.id)] == ["b1", "b3"]
    assert store2.name_for(sel.id) == "Schwere Wörter"

    store2.delete_selection(sel.id)
    assert store2.cards_for(sel.id) == []


def test_cards_for_vocab_list(tmp_path):
    store = make_store(tmp_path)
    assert len(store.cards_for("book1")) == 5
    assert store.name_for("book1") == "Kapitel 1"


def test_book_card_annotations_persist(tmp_path):
    store = make_store(tmp_path)
    card = store.cards_for("book1")[0]
    store.update_notes(card, "H-gr", "H-de", "N-gr", "auch: Tschüs")
    assert card.hints_gr == "H-gr"

    # Neu laden: Overlay wird auf die (unveränderte) Buchliste angewendet
    store2 = make_store(tmp_path)
    card2 = store2.cards_for("book1")[0]
    assert (card2.hints_gr, card2.hints_de) == ("H-gr", "H-de")
    assert (card2.notes_gr, card2.notes_de) == ("N-gr", "auch: Tschüs")
    # Buchdatei selbst bleibt unangetastet
    reloaded = content.load_list(tmp_path / "book" / "kap01.json")
    assert reloaded.cards[0].hints_gr == ""


def test_custom_card_notes_saved_directly(tmp_path):
    store = make_store(tmp_path)
    own = VocabList(name="Eigene", cards=[VocabCard(front="α", back="a", id="c1")])
    store.save_user_list(own)
    store.update_notes(own.cards[0], "Hinweis", "", "Notiz", "")

    store2 = make_store(tmp_path)
    card = store2.cards_for(own.id)[0]
    assert (card.hints_gr, card.notes_gr) == ("Hinweis", "Notiz")
    # kein Overlay-Eintrag für eigene Karten
    assert not store2._annotations


def test_annotations_file_not_loaded_as_list(tmp_path):
    store = make_store(tmp_path)
    store.update_notes(store.cards_for("book1")[0], "x", "", "y", "")
    store2 = make_store(tmp_path)  # darf nicht an annotations.json scheitern
    assert "book1" in store2.lists


def test_legacy_card_fields_migrated():
    card = VocabCard.from_dict({"front": "α", "back": "a",
                                "hints": "alt-Hinweis", "notes": "alt-Notiz"})
    assert card.hints_gr == "alt-Hinweis"
    assert card.notes_gr == "alt-Notiz"


def test_plural_display():
    card = VocabCard(front="ο σκύλος", article="ο",
                     plural="-οι", back="der Hund")
    assert card.with_plural(card.front) == "ο σκύλος, -οι"
    assert card.with_plural(card.greek(False)) == "σκύλος, -οι"
    no_pl = VocabCard(front="καλημέρα", back="guten Morgen")
    assert no_pl.with_plural(no_pl.front) == "καλημέρα"
