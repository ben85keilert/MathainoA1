"""Inhaltspaket der Web-Fassung: Listen und Lexikonpakete, mit einem Code
verschlüsselt.

Die Web-Fassung liegt als statische Seite auf einem Server — was dort
liegt, kann jeder abrufen. Die App selbst ist öffentlich; die Buchlisten
sind es nicht (Urheberrecht). Sie liegen deshalb als EINE verschlüsselte
Datei neben der Seite und werden erst im Browser mit einem Code geöffnet,
den die Person getrennt bekommt. Der Server prüft nichts; wer die Datei
ohne Code hat, sieht Zeichensalat.

Verfahren (wie die privaten Pakete der trainingsapp, core/privat.py — nur
Bordmittel von Python):

- Schlüssel: scrypt(Code, Salz; N = 2^15, r = 8, p = 1) → 64 Bytes: 32
  zum Verschlüsseln, 32 für die Prüfsumme. scrypt braucht Speicher —
  Durchprobieren lohnt nicht (8 Zeichen aus 32: rund 10^12 Möglichkeiten,
  je Versuch ein scrypt).
- Verschlüsseln: je MiB ein Schlüsselstrom aus SHAKE-256(Schlüssel ‖ Salz
  ‖ Blocknummer), mit den Daten XOR-verknüpft (wie ein Zähler-Modus).
- Echtheit: HMAC-SHA256 über Kopf und Geheimtext — falscher Code oder
  verfälschte Datei fallen auf, bevor etwas gelesen wird (WrongCode).

Aufbau der Datei: MAGIC · Version (1) · log2(N) · r · p · Salz (16) ·
Geheimtext · HMAC (32). Der Klartext ist zlib-gepacktes JSON:

    {"format": 1, "version": "…",
     "lists": [<Liste wie beim JSON-Export>, …],
     "lexikon": [<Etymologie-Paket: {"title": …, "etymology": […]}>, …]}

Gebaut wird das Paket im privaten Repo mathaino-inhalte (web/bauen.py);
dieses Modul liefert beide Richtungen, damit sie nie auseinanderlaufen.
Es importiert kein flet.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import zlib
from pathlib import Path

MAGIC = b"MATHPKT"
VERSION = 1
FORMAT = 1
# scrypt: N = 2^15, r = 8, p = 1 — gut 32 MiB Speicher je Versuch
_LOG2N, _R, _P = 15, 8, 1
_SALT = 16
_HEAD = len(MAGIC) + 4 + _SALT
_TAG = 32
_BLOCK = 1 << 20
# Mehr bekommt scrypt nicht — was ein Dateikopf darüber verlangt, ist
# verfälscht (sonst ließe sich der Browser mit einer Datei lahmlegen)
_MAXMEM = 256 * 1024 * 1024
# Die Zeichen eines Codes — ohne 0/O und 1/I, nur Großbuchstaben
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


class WrongCode(Exception):
    """Der Code passt nicht — oder die Datei ist verfälscht (beides sieht
    gleich aus)."""


class NotPossible(Exception):
    """Diesem Python fehlt scrypt — das Paket lässt sich hier nicht öffnen."""


def new_code() -> str:
    """Ein neuer Code — 8 Zeichen aus ALPHABET."""
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(text: str) -> str | None:
    """Wie getippt — groß, ohne Leer- und Bindestriche; None, wenn es kein
    Code sein kann."""
    raw = "".join(ch for ch in text.upper() if ch not in " -\t\n")
    if not 6 <= len(raw) <= 16 or any(ch not in ALPHABET for ch in raw):
        return None
    return raw


def code_text(code: str) -> str:
    """Zum Lesen in Vierergruppen: „K7QM-9XA2“."""
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


def scrypt_available() -> bool:
    """Kann dieses Python Pakete öffnen? Im Browser fehlt hashlib.scrypt;
    dort lädt die Seite cryptography nach (ui/web_content.py)."""
    import importlib.util
    return (hasattr(hashlib, "scrypt")
            or importlib.util.find_spec("cryptography") is not None)


def _scrypt(code: bytes, salt: bytes, n: int, r: int, p: int) -> bytes:
    if hasattr(hashlib, "scrypt"):
        return hashlib.scrypt(code, salt=salt, n=n, r=r, p=p, dklen=64,
                              maxmem=_MAXMEM)
    try:  # Python ohne OpenSSL-scrypt: dasselbe aus cryptography
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    except ImportError as exc:
        raise NotPossible("scrypt fehlt") from exc
    return Scrypt(salt=salt, length=64, n=n, r=r, p=p).derive(code)


def _keys(code: str, salt: bytes, log2n: int, r: int, p: int
          ) -> tuple[bytes, bytes]:
    if not (10 <= log2n <= 20 and 1 <= r <= 16 and 1 <= p <= 4
            and 128 * r * (1 << log2n) <= _MAXMEM):
        raise WrongCode("Die Datei ist verfälscht.")
    key = _scrypt(code.encode("ascii"), salt, 1 << log2n, r, p)
    return key[:32], key[32:]


def _stream(key: bytes, salt: bytes, number: int, length: int) -> bytes:
    return hashlib.shake_256(
        key + salt + number.to_bytes(8, "big")).digest(length)


def _xor(a: bytes, b: bytes) -> bytes:
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(
        len(a), "big")


def _crypt(data: bytes, key: bytes, salt: bytes) -> bytes:
    return b"".join(
        _xor(data[i:i + _BLOCK],
             _stream(key, salt, n, len(data[i:i + _BLOCK])))
        for n, i in enumerate(range(0, len(data), _BLOCK)))


def encrypt(data: bytes, code: str) -> bytes:
    """Mit frischem Salz verschlüsseln (zweimal verschlüsselt sieht anders
    aus)."""
    salt = secrets.token_bytes(_SALT)
    head = MAGIC + bytes([VERSION, _LOG2N, _R, _P]) + salt
    k_enc, k_mac = _keys(code, salt, _LOG2N, _R, _P)
    secret = _crypt(data, k_enc, salt)
    return head + secret + hmac.new(k_mac, head + secret,
                                    hashlib.sha256).digest()


def decrypt(data: bytes, code: str) -> bytes:
    """Der Klartext — wirft WrongCode."""
    if len(data) < _HEAD + _TAG or not data.startswith(MAGIC):
        raise WrongCode("Das ist kein Inhaltspaket.")
    head, secret, tag = data[:_HEAD], data[_HEAD:-_TAG], data[-_TAG:]
    version, log2n, r, p = head[len(MAGIC):len(MAGIC) + 4]
    if version != VERSION:
        raise WrongCode("Das Inhaltspaket ist neuer als diese App.")
    salt = head[len(MAGIC) + 4:]
    k_enc, k_mac = _keys(code, salt, log2n, r, p)
    if not hmac.compare_digest(
            hmac.new(k_mac, head + secret, hashlib.sha256).digest(), tag):
        raise WrongCode("Der Code passt nicht.")
    return _crypt(secret, k_enc, salt)


# --- Paket: Inhalt ↔ Bytes --------------------------------------------------

def content_version(lists: list[dict], lexikon: list[dict]) -> str:
    """Fingerabdruck des Inhalts — ändert sich genau dann, wenn sich eine
    Liste oder ein Lexikonpaket ändert (nicht mit jedem Bauen)."""
    raw = json.dumps([lists, lexikon], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def pack(lists: list[dict], lexikon: list[dict], code: str) -> bytes:
    """Listen und Lexikonpakete zu einer verschlüsselten Datei."""
    payload = {"format": FORMAT,
               "version": content_version(lists, lexikon),
               "lists": lists, "lexikon": lexikon}
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return encrypt(zlib.compress(raw, 9), code)


def unpack(data: bytes, code: str) -> dict:
    """Die Datei öffnen — wirft WrongCode (auch bei unlesbarem Inhalt)."""
    try:
        payload = json.loads(zlib.decompress(decrypt(data, code)))
    except (zlib.error, ValueError) as exc:
        raise WrongCode("Das Inhaltspaket ist nicht lesbar.") from exc
    if not isinstance(payload, dict) or payload.get("format") != FORMAT:
        raise WrongCode("Das Inhaltspaket ist neuer als diese App.")
    return payload


# --- In die App übernehmen --------------------------------------------------

def apply(payload: dict, store) -> dict:
    """Das geöffnete Paket in die App übernehmen — derselbe Weg wie
    „Importieren“ von Hand: Eine Liste mit derselben id ersetzt die alte
    (die Karten-IDs bleiben, also auch der Lernstand), Lexikoneinträge
    werden wortweise ersetzt. Was nicht mehr im Paket steht, bleibt
    stehen — hier wird nichts gelöscht.

    Rückgabe: {"lists": n, "cards": n, "lexikon": n} zum Anzeigen.
    """
    from mathainoa1.storage import content
    from mathainoa1.storage.textanalyse import lexicon_store

    stats = {"lists": 0, "cards": 0, "lexikon": 0}
    for raw in payload.get("lists") or []:
        vlist = content.import_json(json.dumps(raw, ensure_ascii=False))
        store.save_user_list(vlist)
        stats["lists"] += 1
        stats["cards"] += len(vlist.cards)
    packages = payload.get("lexikon") or []
    if packages:
        lex = lexicon_store(store)
        for raw in packages:
            done = lex.import_package(json.dumps(raw, ensure_ascii=False))
            stats["lexikon"] += done["new"] + done["updated"]
    store.load_all()
    return stats


# --- Was dieser Browser schon hat -------------------------------------------

def state_path() -> Path:
    from mathainoa1.storage.settings import app_data_dir
    return app_data_dir() / "web_content.json"


def load_state() -> dict:
    """{"code": …, "version": …} — leer, solange nichts geöffnet wurde."""
    try:
        data = json.loads(state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(code: str, version: str) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"code": code, "version": version}),
                    encoding="utf-8")


# --- Ablauf: nachsehen, laden, öffnen ---------------------------------------

STAND_URL = "inhalt/stand.json"
PACKAGE_URL = "inhalt/paket.bin"
# Obergrenze fürs Paket — alles geht im Browser durch den Arbeitsspeicher
MAX_BYTES = 32 * 1024 * 1024

NOTHING = "nothing"      # der Server hat kein Inhaltspaket (oder kein Netz)
CURRENT = "current"      # dieser Browser hat den Stand des Servers
UPDATED = "updated"      # neues Paket geöffnet und übernommen
NEED_CODE = "need_code"  # Paket da, aber kein (passender) Code


class Updater:
    """Holt das Inhaltspaket vom eigenen Server und übernimmt es.

    fetch(pfad) -> (Status, Bytes) kommt von außen: im Browser `fetch` des
    Browsers (ui/web_content.py), in den Tests ein Nachbau. Gefragt wird
    zuerst die Standdatei (wenige Bytes); das Paket nur, wenn sie eine
    andere Version nennt als die, die dieser Browser schon hat.
    """

    def __init__(self, fetch, store, prepare=None):
        self.fetch = fetch
        self.store = store
        # async, vor dem ersten Entschlüsseln: im Browser lädt das scrypt
        # nach (ui/web_content.py) — erst dann, nicht bei jedem Start
        self.prepare = prepare
        self.pending: bytes | None = None  # geladen, wartet auf den Code
        self.pending_version = ""
        self.stats: dict = {}
        # Hatte dieser Browser schon einen Code? (Dann ist „passt nicht“
        # ein gesperrter Code, kein Tippfehler.)
        self.had_code = False

    async def check(self) -> str:
        state = load_state()
        self.had_code = bool(state.get("code"))
        try:
            status, raw = await self.fetch(STAND_URL)
            if status != 200:
                return NOTHING
            version = str(json.loads(raw)["version"])
        except Exception:  # noqa: BLE001 — kein Netz, kein Paket: App läuft
            return NOTHING
        if version == state.get("version"):
            return CURRENT
        try:
            status, data = await self.fetch(PACKAGE_URL)
        except Exception:  # noqa: BLE001
            return NOTHING
        if status != 200 or len(data) > MAX_BYTES:
            return NOTHING
        self.pending, self.pending_version = data, version
        if state.get("code"):
            try:
                if self.prepare is not None:
                    await self.prepare()
                return self.open(state["code"])
            except WrongCode:
                pass  # Code gesperrt — neu fragen
        return NEED_CODE

    def open(self, code: str) -> str:
        """Das wartende Paket mit dem Code öffnen und übernehmen — wirft
        WrongCode; der Code ist dann nicht gemerkt, und nichts ist
        geändert."""
        if self.pending is None:
            raise WrongCode("Kein Paket geladen.")
        payload = unpack(self.pending, code)
        self.stats = apply(payload, self.store)
        save_state(code, str(payload.get("version") or self.pending_version))
        self.pending = None
        return UPDATED
