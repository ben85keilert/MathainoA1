"""Speichern im Browser — das Datenverzeichnis der Web-Fassung liegt in der
IndexedDB.

In der Web-Fassung läuft Python im Browser (Pyodide), und sein Dateisystem
ist Arbeitsspeicher: Lernstand, Listen und Einstellungen wären mit dem
Neuladen weg. Hier wird das Datenverzeichnis (settings.app_data_dir()) auf
IDBFS gelegt — Emscriptens Dateisystem, das weiter im Arbeitsspeicher
arbeitet und sich auf Zuruf mit der IndexedDB des Browsers abgleicht.
SQLite und alles, was Dateien schreibt, merken davon nichts.

Ablauf:

1. VOR dem ersten Lesen des Datenverzeichnisses: einhängen und holen, was
   der Browser von früher hat (`start`) — ui/app.py:entry wartet darauf.
2. Solange die Seite offen ist: alle TICK_S Sekunden nachsehen, ob sich im
   Verzeichnis etwas geändert hat (`signature`), und nur dann schreiben
   (`tick`). Dazu sofort, wenn der Tab in den Hintergrund geht — ein „Tab
   wird geschlossen“ meldet der Browser nicht verlässlich.
3. „Alles löschen“ (`erase`): die IndexedDB dieser Seite entfernen und für
   den Rest des Besuchs nichts mehr schreiben — für fremde Geräte.

Was schiefgehen könnte, und was dagegen steht:

- Zwei Tabs: Jeder Tab hat sein eigenes Python; der zweite überschriebe,
  was der erste gespeichert hat. Der erste Tab hält deshalb eine Sperre des
  Browsers (Web Locks); wer sie nicht bekommt, zeigt den gespeicherten
  Stand und schreibt nicht (OTHER_TAB).
- Halbe Datenbank: geschrieben wird nur, wenn in SQLite gerade keine
  Transaktion offen ist (`quiet`).

Was der Browser speichert, kann er auch wieder wegnehmen (Websitedaten
löschen, privates Fenster, Safari nach sieben Tagen ohne Besuch).

Dieses Modul importiert kein flet. Den Zugang zum Browser (PyodideAccess)
gibt es nur dort; die Tests nehmen einen nachgebauten.
Vorlage: trainingsapp, ui/browserspeicher.py.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger(__name__)

# So oft sieht der Takt nach, ob etwas zu schreiben ist (Sekunden)
TICK_S = 2.0
# Name der Sperre, die der schreibende Tab hält
LOCK = "mathaino-speicher"

OFF = "off"  # noch nicht gestartet
ON = "on"  # speichert
OTHER_TAB = "other_tab"  # ein anderer Tab speichert; dieser zeigt nur
ERASED = "erased"  # „Alles löschen“ — für diesen Besuch aus
FAILED = "failed"  # der Browser lässt es nicht zu (voll, gesperrt)

TEXTS: dict[str, str] = {
    OFF: "Hier wird nichts gespeichert. Mit dem Schließen der Seite ist "
         "alles weg.",
    ON: "Lernstand, Listen und Einstellungen bleiben in diesem Browser auf "
        "diesem Gerät. Sie gehen an keinen Server. Löscht der Browser seine "
        "Websitedaten, sind sie weg — ein Backup (Einstellungen → Backup) "
        "schützt davor.",
    OTHER_TAB: "Die Seite ist in einem zweiten Tab offen, und dort wird "
               "gespeichert. Was du hier änderst, bleibt nicht. Schließe "
               "einen der beiden Tabs und lade die Seite neu.",
    ERASED: "Alles Gespeicherte ist gelöscht. Bis du die Seite schließt "
            "oder neu lädst, wird nichts mehr gespeichert.",
    FAILED: "Der Browser lässt das Speichern nicht zu (Speicher voll oder "
            "gesperrt). Was du übst, ist mit dem Schließen der Seite weg.",
}


class Access(Protocol):
    """Was der Speicher vom Browser braucht — echt: PyodideAccess."""

    def mount(self, path: str) -> None:
        """Legt path auf ein Dateisystem, das sich mit der IndexedDB
        abgleichen lässt."""

    async def sync(self, load: bool) -> None:
        """load: IndexedDB → Dateisystem (Start); sonst umgekehrt."""

    async def lock(self, name: str) -> bool:
        """Hält die Sperre, bis der Tab schließt. False: Ein anderer Tab
        hat sie."""

    async def remove(self, path: str) -> None:
        """Löscht, was zu path in der IndexedDB liegt."""


@dataclass
class BrowserStorage:
    """Hält das Datenverzeichnis mit dem Browser im Gleichgewicht."""

    folder: Path
    access: Access
    state: str = OFF
    # Lag beim Start schon etwas im Browser? (Dann gehört ein Startfehler
    # den alten Daten.)
    existing: bool = False
    # Meldung des Browsers zum letzten Fehler — fürs Protokoll
    error: str = ""
    _stamp: tuple[int, int, int] | None = field(default=None, repr=False)

    @property
    def active(self) -> bool:
        return self.state == ON

    @property
    def text(self) -> str:
        return TEXTS[self.state]

    async def start(self) -> None:
        """Einhängen, die Sperre nehmen, holen. Scheitert etwas, läuft die
        App ohne Speicher."""
        try:
            self.access.mount(str(self.folder))
            free = await self.access.lock(LOCK)
            await self.access.sync(True)
        except Exception as exc:  # noqa: BLE001 — jeder Browserfehler
            self._failed(exc)
            return
        self.existing = (any(self.folder.iterdir())
                         if self.folder.is_dir() else False)
        self._stamp = self.signature()
        self.state = ON if free else OTHER_TAB

    def signature(self) -> tuple[int, int, int]:
        """Zahl der Dateien, ihre Größe und die jüngste Änderung — ändert
        sich mit jedem Schreiben ins Verzeichnis."""
        count = size = newest = 0
        stack = [str(self.folder)]
        while stack:
            try:
                with os.scandir(stack.pop()) as entries:
                    for entry in entries:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                            continue
                        st = entry.stat(follow_symlinks=False)
                        count += 1
                        size += st.st_size
                        newest = max(newest, st.st_mtime_ns)
            except OSError:
                continue  # Ordner verschwand zwischen Auflisten und Lesen
        return count, size, newest

    def changed(self) -> bool:
        return self.signature() != self._stamp

    async def save(self) -> bool:
        """Schreibt den Stand des Verzeichnisses in den Browser. False:
        nicht geschrieben (aus, anderer Tab, gelöscht) oder gescheitert —
        dann ist der Speicher danach aus."""
        if not self.active:
            return False
        stamp = self.signature()  # vorher: was währenddessen kommt, zählt neu
        try:
            await self.access.sync(False)
        except Exception as exc:  # noqa: BLE001
            self._failed(exc)
            return False
        self._stamp = stamp
        return True

    async def tick(self, quiet: Callable[[], bool]) -> None:
        """Läuft, solange die Seite offen ist: schreibt, wenn sich etwas
        geändert hat und quiet() wahr ist (keine offene Transaktion)."""
        while True:
            await asyncio.sleep(TICK_S)
            if self.active and quiet() and self.changed():
                await self.save()

    async def erase(self) -> None:
        """Entfernt alles Gespeicherte aus dem Browser; danach schreibt
        dieser Besuch nichts mehr."""
        before = self.state
        self.state = ERASED  # zuerst: der Takt darf nicht dazwischen schreiben
        try:
            await self.access.remove(str(self.folder))
        except Exception as exc:
            self.state = before
            self.error = str(exc)
            raise

    def _failed(self, exc: Exception) -> None:
        self.state = FAILED
        self.error = str(exc)
        log.error("Speichern im Browser: %s", exc)


class PyodideAccess:
    """Der echte Zugang: Emscriptens IDBFS, IndexedDB und Web Locks — nur
    in Pyodide. Jede Methode hier läuft nur im Browser und ist dort zu
    messen, nicht in den Tests."""

    def __init__(self) -> None:
        import js
        import pyodide_js

        self._js: Any = js
        self._fs: Any = pyodide_js.FS

    def mount(self, path: str) -> None:
        self._fs.mkdirTree(path)
        self._fs.mount(self._fs.filesystems.IDBFS, self._js.Object.new(), path)

    async def sync(self, load: bool) -> None:
        from pyodide.ffi import create_once_callable

        done: asyncio.Future[Any] = asyncio.get_running_loop().create_future()

        def back(err: Any = None) -> None:
            if not done.done():
                done.set_result(err)

        self._fs.syncfs(load, create_once_callable(back))
        if err := await done:
            raise OSError(str(err))

    async def lock(self, name: str) -> bool:
        from pyodide.ffi import create_proxy

        locks = getattr(self._js.navigator, "locks", None)
        if not locks:
            return True  # Browser kennt keine Sperren — dann gilt der eine Tab
        got: asyncio.Future[bool] = asyncio.get_running_loop().create_future()

        def holder(lock: Any = None) -> Any:
            granted = bool(lock)
            if not got.done():
                got.set_result(granted)
            if not granted:
                return None
            # Ein Versprechen, das nie eingelöst wird: Die Sperre gilt, bis
            # der Tab schließt.
            return self._js.Promise.new(create_proxy(lambda yes, no: None))

        options = self._js.Object.new()
        options.ifAvailable = True
        locks.request(name, options, create_proxy(holder))
        return await got

    async def remove(self, path: str) -> None:
        from pyodide.ffi import create_once_callable

        # IDBFS hält seine Verbindung offen; solange sie steht, wartet das
        # Löschen.
        open_dbs = self._fs.filesystems.IDBFS.dbs
        if connection := self._js.Reflect.get(open_dbs, path):
            connection.close()
            self._js.Reflect.deleteProperty(open_dbs, path)
        done: asyncio.Future[str] = asyncio.get_running_loop().create_future()

        def outcome(text: str) -> Callable[..., None]:
            def report(*_: Any) -> None:
                if not done.done():
                    done.set_result(text)

            return create_once_callable(report)

        request = self._js.indexedDB.deleteDatabase(path)
        request.onsuccess = outcome("")
        request.onerror = outcome("Der Browser hat das Löschen abgelehnt.")
        request.onblocked = outcome("Ein anderer Tab hält den Speicher offen.")
        if text := await done:
            raise OSError(text)
