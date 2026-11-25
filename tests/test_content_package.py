"""Tests für das verschlüsselte Inhaltspaket der Web-Fassung
(storage/content_package.py)."""

import asyncio
import json

import pytest

from mathainoa1.storage import content_package as cp
from mathainoa1.storage.content import ContentStore
from mathainoa1.storage.textanalyse import lexicon_store

CODE = "K7QM9XA2"

LISTE = {"id": "t-kap01", "name": "Test – Kapitel 1", "book": "A2",
         "chapter": 1, "editable": True,
         "cards": [{"id": "t-k01-001", "front": "το μάθημα",
                    "back": "die Lektion", "article": "το",
                    "word_type": "Nomen"},
                   {"id": "t-k01-002", "front": "γράφω", "back": "schreiben",
                    "word_type": "Verb"}]}
LEXIKON = {"title": "Test – Kapitel 1",
           "etymology": [{"word": "το μάθημα", "breakdown": [],
                          "total": "das Gelernte", "semantics": "Lektion"}]}


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path / "data"))
    s = ContentStore(tmp_path / "book", tmp_path / "data" / "vocab")
    s.load_all()
    return s


def fetcher(files: dict):
    """Nachbau des Servers: Pfad -> Bytes; was fehlt, ist 404."""
    calls = []

    async def fetch(path):
        calls.append(path)
        if path not in files:
            return 404, b""
        return 200, files[path]

    fetch.calls = calls
    return fetch


def server(lists=(LISTE,), lexikon=(LEXIKON,), code=CODE):
    lists, lexikon = list(lists), list(lexikon)
    stand = {"version": cp.content_version(lists, lexikon)}
    return {cp.STAND_URL: json.dumps(stand).encode(),
            cp.PACKAGE_URL: cp.pack(lists, lexikon, code)}


# --- Verschlüsselung ---

def test_hin_und_zurueck():
    secret = cp.encrypt(b"Geheim " * 1000, CODE)
    assert secret.startswith(cp.MAGIC) and b"Geheim" not in secret
    assert cp.decrypt(secret, CODE) == b"Geheim " * 1000
    # frisches Salz: zweimal verschlüsselt sieht anders aus
    assert cp.encrypt(b"x", CODE) != cp.encrypt(b"x", CODE)


def test_falscher_code_und_verfaelschte_datei():
    secret = cp.encrypt(b"Inhalt", CODE)
    with pytest.raises(cp.WrongCode):
        cp.decrypt(secret, "K7QM9XA3")
    kaputt = bytearray(secret)
    kaputt[len(secret) // 2] ^= 1
    with pytest.raises(cp.WrongCode):
        cp.decrypt(bytes(kaputt), CODE)
    with pytest.raises(cp.WrongCode):
        cp.decrypt(b"kein Paket", CODE)


def test_kopf_kann_scrypt_nicht_aufblasen():
    """Ein verfälschter Kopf darf dem Browser nicht Gigabytes abverlangen."""
    secret = bytearray(cp.encrypt(b"x", CODE))
    secret[len(cp.MAGIC) + 1] = 30  # log2(N) = 30
    with pytest.raises(cp.WrongCode):
        cp.decrypt(bytes(secret), CODE)


def test_paket_enthaelt_keinen_klartext():
    data = cp.pack([LISTE], [LEXIKON], CODE)
    assert "μάθημα".encode() not in data and b"Lektion" not in data
    payload = cp.unpack(data, CODE)
    assert payload["lists"] == [LISTE] and payload["lexikon"] == [LEXIKON]
    assert payload["version"] == cp.content_version([LISTE], [LEXIKON])


def test_version_folgt_dem_inhalt():
    v = cp.content_version([LISTE], [LEXIKON])
    assert v == cp.content_version([LISTE], [LEXIKON])
    geaendert = json.loads(json.dumps(LISTE))
    geaendert["cards"][0]["back"] = "der Unterricht"
    assert v != cp.content_version([geaendert], [LEXIKON])


def test_codes():
    code = cp.new_code()
    assert len(code) == 8 and set(code) <= set(cp.ALPHABET)
    assert cp.normalize_code("k7qm-9xa2") == "K7QM9XA2"
    assert cp.normalize_code(" K7QM 9XA2 ") == "K7QM9XA2"
    assert cp.normalize_code("K7QM-9XA0") is None  # 0 gibt es nicht
    assert cp.normalize_code("abc") is None
    assert cp.code_text("K7QM9XA2") == "K7QM-9XA2"


# --- Übernehmen ---

def test_uebernehmen_legt_listen_und_lexikon_an(store):
    stats = cp.apply(cp.unpack(cp.pack([LISTE], [LEXIKON], CODE), CODE), store)
    assert stats == {"lists": 1, "cards": 2, "lexikon": 1}
    assert [c.id for c in store.lists["t-kap01"].cards] == ["t-k01-001",
                                                           "t-k01-002"]
    assert [e.word for e in lexicon_store(store).entries] == ["το μάθημα"]


def test_korrektur_ersetzt_die_liste_ids_bleiben(store):
    cp.apply({"lists": [LISTE], "lexikon": []}, store)
    neu = json.loads(json.dumps(LISTE))
    neu["cards"][0]["back"] = "der Unterricht"
    cp.apply({"lists": [neu], "lexikon": []}, store)
    cards = store.lists["t-kap01"].cards
    assert cards[0].id == "t-k01-001" and cards[0].back == "der Unterricht"
    assert len(store.lists) == 1


# --- Ablauf ---

def test_kein_paket_auf_dem_server(store):
    up = cp.Updater(fetcher({}), store)
    assert asyncio.run(up.check()) == cp.NOTHING
    assert not store.lists


def test_erster_besuch_fragt_nach_dem_code(store):
    up = cp.Updater(fetcher(server()), store)
    assert asyncio.run(up.check()) == cp.NEED_CODE
    assert not up.had_code and not store.lists
    with pytest.raises(cp.WrongCode):
        up.open("AAAAAAAA")
    assert not store.lists and cp.load_state() == {}
    assert up.open(CODE) == cp.UPDATED
    assert "t-kap01" in store.lists
    assert cp.load_state()["code"] == CODE


def test_gleicher_stand_laedt_das_paket_nicht(store):
    files = server()
    up = cp.Updater(fetcher(files), store)
    asyncio.run(up.check())
    up.open(CODE)
    fetch = fetcher(files)
    assert asyncio.run(cp.Updater(fetch, store).check()) == cp.CURRENT
    assert fetch.calls == [cp.STAND_URL]


def test_neuer_stand_kommt_mit_gemerktem_code_von_selbst(store):
    up = cp.Updater(fetcher(server()), store)
    asyncio.run(up.check())
    up.open(CODE)
    neu = json.loads(json.dumps(LISTE))
    neu["cards"][1]["back"] = "schreiben, verfassen"
    up2 = cp.Updater(fetcher(server(lists=[neu])), store)
    assert asyncio.run(up2.check()) == cp.UPDATED
    assert store.lists["t-kap01"].cards[1].back == "schreiben, verfassen"
    assert cp.load_state()["version"] == cp.content_version([neu], [LEXIKON])


def test_gesperrter_code_fragt_neu_und_laesst_alles_stehen(store):
    up = cp.Updater(fetcher(server()), store)
    asyncio.run(up.check())
    up.open(CODE)
    neu = json.loads(json.dumps(LISTE))
    neu["cards"][0]["back"] = "nur mit neuem Code"
    up2 = cp.Updater(fetcher(server(lists=[neu], code="NEUERC2D")), store)
    assert asyncio.run(up2.check()) == cp.NEED_CODE
    assert up2.had_code
    assert store.lists["t-kap01"].cards[0].back == "die Lektion"
    assert up2.open("NEUERC2D") == cp.UPDATED
    assert store.lists["t-kap01"].cards[0].back == "nur mit neuem Code"


def test_netzfehler_laesst_die_app_laufen(store):
    async def kaputt(path):
        raise OSError("kein Netz")

    assert asyncio.run(cp.Updater(kaputt, store).check()) == cp.NOTHING
