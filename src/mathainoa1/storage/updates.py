"""Update-Check gegen die GitHub-Releases des Projekts.

Provisorium bis zur Play-Store-Verteilung: Die CI (release.yml) hängt an
jedes Versions-Tag eine signierte APK. Alle Builds tragen denselben
Signierschlüssel, darum installiert Android eine neuere APK einfach über
die bestehende App — Lernstand, Listen und Einstellungen bleiben erhalten.

Der automatische Check beim Start ist auf einen Versuch pro Tag
gedrosselt und schlägt still fehl (kein Netz, Repo privat, API-Limit):
die App startet dann einfach normal. Voraussetzung für den Check ist,
dass das Repository öffentlich ist — die ungetokente GitHub-API
antwortet bei privaten Repos mit 404.
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from mathainoa1 import __version__
from mathainoa1.storage.settings import app_data_dir

REPO = "ben85keilert/MathainoA1"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"


@dataclass
class UpdateInfo:
    version: str  # z.B. "0.9.0" (ohne "v")
    notes: str = ""  # Release-Notizen (Markdown-Rohtext)
    apk_url: str = ""  # Direktlink zur APK; "" wenn keine im Release
    page_url: str = RELEASES_PAGE


def parse_version(text: str) -> tuple[int, ...]:
    """"v0.9.1" / "0.9.1" -> (0, 9, 1); Unlesbares wird zu (0,)."""
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums) or (0,)


def _state_path() -> Path:
    return app_data_dir() / "update_check.json"


def _load_state() -> dict:
    try:
        with open(_state_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_latest(timeout: float = 6.0) -> UpdateInfo:
    """Neuestes Release von GitHub holen (blockierend — im Thread rufen).

    Wirft OSError/ValueError bei Netz- oder API-Problemen.
    """
    req = urllib.request.Request(API_LATEST, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"MathainoA1/{__version__}",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    if not isinstance(data, dict) or not data.get("tag_name"):
        raise ValueError("Unerwartete Antwort der GitHub-API")
    apk_url = next((str(a.get("browser_download_url", ""))
                    for a in (data.get("assets") or [])
                    if isinstance(a, dict)
                    and str(a.get("name", "")).endswith(".apk")), "")
    return UpdateInfo(
        version=str(data["tag_name"]).lstrip("v"),
        notes=str(data.get("body") or "").strip(),
        apk_url=apk_url,
        page_url=str(data.get("html_url") or RELEASES_PAGE),
    )


def auto_check() -> UpdateInfo | None:
    """Gedrosselter Startup-Check: ein Versuch pro Tag, still bei Fehlern.

    None = nichts zu melden (schon geprüft, kein Netz oder aktuell).
    """
    state = _load_state()
    today = date.today().isoformat()
    if state.get("last_check") == today:
        return None
    state["last_check"] = today
    _save_state(state)
    try:
        info = fetch_latest()
    except (OSError, ValueError):
        return None
    return info if is_installable_update(info) else None


def is_installable_update(info: UpdateInfo) -> bool:
    """Neuer UND installierbar — nur dann lohnt der Hinweis.

    Ein Release ohne APK ist noch nicht fertig: entweder hängt der Build
    noch, oder er ist gescheitert (bzw. das Release wurde von Hand
    angelegt, bevor die CI lief). Es zu melden würde nur zu einer
    Release-Seite ohne Download führen — also überspringen und beim
    nächsten Check erneut schauen.
    """
    return (bool(info.apk_url)
            and parse_version(info.version) > parse_version(__version__))


def downgrade_notice() -> str | None:
    """Warntext, wenn eine ältere App-Version auf neuere Daten trifft.

    Merkt sich die höchste je gestartete Version. Läuft eine ältere
    (Downgrade), kommt bei jedem Start ein Hinweis: die Parser sind zwar
    tolerant (unbekannte Felder werden ignoriert, nichts wird gelöscht),
    aber neuere Inhalte können unvollständig erscheinen — und ein
    Speichern mit der alten Version würde unbekannte Felder verwerfen.
    """
    state = _load_state()
    seen = str(state.get("max_version_run", ""))
    current = parse_version(__version__)
    if parse_version(seen) > current:
        return (f"Diese App-Version ({__version__}) ist älter als die "
                f"zuletzt benutzte ({seen}). Die Daten bleiben erhalten, "
                "neuere Inhalte werden aber eventuell unvollständig "
                "angezeigt — am besten wieder die aktuelle Version "
                "installieren.")
    if parse_version(seen) < current:
        state["max_version_run"] = __version__
        _save_state(state)
    return None
