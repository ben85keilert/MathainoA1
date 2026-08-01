"""Einstellungsmenü (Zahnrad): Ansicht (Theme, Akzentfarbe) und Abfrage.

`apply_app_theme` wird beim App-Start und bei jeder Änderung aufgerufen und
setzt Theme-Modus und Akzentfarbe der ganzen App.
"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from mathainoa1.storage import backup
from mathainoa1.storage.content import LEVELS
from mathainoa1.storage.settings import (
    TTS_GOOGLE,
    TTS_SYSTEM,
    AppSettings,
    load_app_settings,
    save_app_settings,
)
from mathainoa1.ui.audio import set_slow_tap_seconds, set_tts_engine
from mathainoa1.ui.features import FEATURES

# Auswählbare Akzentfarben (Schlüssel wird in AppSettings.seed gespeichert)
SEED_COLORS: dict[str, tuple[str, str]] = {
    "blue": ("Blau", ft.Colors.BLUE),
    "green": ("Grün", ft.Colors.GREEN),
    "purple": ("Violett", ft.Colors.DEEP_PURPLE),
    "amber": ("Amber", ft.Colors.AMBER),
    "teal": ("Türkis", ft.Colors.TEAL),
}

_THEME_MODES = {
    "light": ft.ThemeMode.LIGHT,
    "dark": ft.ThemeMode.DARK,
    "system": ft.ThemeMode.SYSTEM,
}


def apply_app_theme(page: ft.Page, s: AppSettings) -> None:
    """Setzt Theme-Modus und Akzentfarbe der App gemäß den Einstellungen."""
    page.theme_mode = _THEME_MODES.get(s.theme, ft.ThemeMode.SYSTEM)
    seed = SEED_COLORS.get(s.seed, SEED_COLORS["blue"])[1]
    page.theme = ft.Theme(color_scheme_seed=seed)
    page.dark_theme = ft.Theme(color_scheme_seed=seed)


def settings_view(nav, store=None, progress=None) -> ft.Control:
    page = nav.page
    s = load_app_settings()

    def apply_and_save():
        apply_app_theme(page, s)
        save_app_settings(s)
        page.update()

    # --- Ansicht: Theme ---
    seg_theme = ft.SegmentedButton(
        selected=[s.theme],
        segments=[
            ft.Segment(value="light", label=ft.Text("Hell"),
                       icon=ft.Icons.LIGHT_MODE),
            ft.Segment(value="dark", label=ft.Text("Dunkel"),
                       icon=ft.Icons.DARK_MODE),
            ft.Segment(value="system", label=ft.Text("System"),
                       icon=ft.Icons.BRIGHTNESS_AUTO),
        ],
    )

    def on_theme(e):
        sel = seg_theme.selected
        s.theme = next(iter(sel)) if isinstance(sel, (list, set, tuple)) else sel
        apply_and_save()

    seg_theme.on_change = on_theme

    # --- Ansicht: Akzentfarbe ---
    dd_color = ft.Dropdown(
        label="Akzentfarbe", value=s.seed,
        options=[ft.DropdownOption(key=k, text=label)
                 for k, (label, _c) in SEED_COLORS.items()],
    )

    def on_color(e):
        s.seed = dd_color.value or "blue"
        apply_and_save()

    dd_color.on_select = on_color  # Flet 0.85: Dropdowns feuern on_select

    # --- Ansicht: Reihenfolge der Hauptmenü-Kacheln (Drag & Drop) ---
    # Lazy-Import: app importiert dieses Modul (Importzirkel)
    from mathainoa1.ui.app import menu_tiles_meta, ordered_menu_keys
    from mathainoa1.ui.views.wordlist import drag_row
    tile_meta = {k: (title, icon) for k, title, icon in menu_tiles_meta(s)}
    menu_keys = ordered_menu_keys(list(tile_meta), s.menu_order)
    menu_list = ft.ReorderableListView(show_default_drag_handles=False)

    def rebuild_menu_rows():
        menu_list.controls = [
            drag_row(ft.Row([ft.Icon(tile_meta[k][1], size=20),
                             ft.Text(tile_meta[k][0])], spacing=8))
            for k in menu_keys]

    def on_menu_reorder(e):
        menu_keys.insert(e.new_index, menu_keys.pop(e.old_index))
        s.menu_order = list(menu_keys)
        save_app_settings(s)
        rebuild_menu_rows()
        page.update()

    menu_list.on_reorder = on_menu_reorder
    rebuild_menu_rows()

    # --- Abfrage: Box-Reset bei strengen Fehlern ---
    sw_accent = ft.Switch(
        label="Akzentfehler setzt die Box zurück (auf Box 1)",
        value=s.accent_resets_box)
    sw_case = ft.Switch(
        label="Groß-/Kleinfehler setzt die Box zurück (auf Box 1)",
        value=s.case_resets_box)

    def on_accent(e):
        s.accent_resets_box = sw_accent.value
        save_app_settings(s)

    def on_case(e):
        s.case_resets_box = sw_case.value
        save_app_settings(s)

    sw_accent.on_change = on_accent
    sw_case.on_change = on_case

    # --- Abfrage: Beschränkungen durch die Abfragemodi ---
    sw_high = ft.Switch(
        label="Box 4 und 5 nur über Deutsch → Griechisch",
        value=s.high_boxes_need_production)
    sw_top = ft.Switch(
        label="Box 5 nur über Deutsch → Griechisch mit Schreiben",
        value=s.top_box_needs_typing)

    def on_high(e):
        s.high_boxes_need_production = sw_high.value
        save_app_settings(s)

    def on_top(e):
        s.top_box_needs_typing = sw_top.value
        save_app_settings(s)

    sw_high.on_change = on_high
    sw_top.on_change = on_top

    # --- Abfrage: Prüfbutton-Stil beim Schreiben ---
    sw_check = ft.Switch(
        label="Prüf-Häkchen rechts neben dem Antwortfeld (kompakt)",
        value=s.check_beside_field)

    def on_check(e):
        s.check_beside_field = sw_check.value
        save_app_settings(s)

    sw_check.on_change = on_check

    # --- Abfrage: Fehlerrunde und Leitner-Box ---
    rg_repeat = ft.RadioGroup(
        value=(s.repeat_round_box_policy
               if s.repeat_round_box_policy in ("none", "box2", "original",
                                                "step_down") else "step_down"),
        content=ft.Column([
            ft.Radio(value="none",
                     label="Keine Verbesserung — Wort bleibt in Box 1"),
            ft.Radio(value="box2", label="Richtig in der Fehlerrunde → Box 2"),
            ft.Radio(value="original",
                     label="Richtig in der Fehlerrunde → zurück in die "
                           "ursprüngliche Box"),
            ft.Radio(value="step_down",
                     label="Richtig in der Fehlerrunde → eine Box zurück "
                           "(mindestens Box 2) (Standard)"),
        ], spacing=4),
    )

    def on_repeat(e):
        s.repeat_round_box_policy = rg_repeat.value or "step_down"
        save_app_settings(s)

    rg_repeat.on_change = on_repeat

    # --- Sprachausgabe: Doppeltipp-Zeit für langsames Abspielen ---
    dd_tap = ft.Dropdown(
        label="Doppeltipp-Zeitfenster (langsam abspielen)",
        value=f"{s.slow_double_tap_seconds:g}",
        options=[ft.DropdownOption(key=v, text=f"{v} Sekunden")
                 for v in ("0.3", "0.5", "0.8", "1")],
    )

    def on_tap_time(e):
        try:
            set_slow_tap_seconds(float(dd_tap.value))
        except (TypeError, ValueError):
            pass

    dd_tap.on_select = on_tap_time  # Flet 0.85: Dropdowns feuern on_select

    # --- Sprachausgabe: Weg wählen ---
    rg_tts = ft.RadioGroup(
        value=(s.tts_engine if s.tts_engine in (TTS_SYSTEM, TTS_GOOGLE)
               else TTS_SYSTEM),
        content=ft.Column([
            ft.Radio(value=TTS_SYSTEM, label="Systemstimme (Standard)"),
            ft.Text("Spricht offline über die Sprachausgabe des Geräts — "
                    "es werden keine Daten übertragen. Braucht eine "
                    "installierte griechische Stimme (Android: meist schon "
                    "dabei; Windows: Sprachpaket „Ελληνικά“ hinzufügen). "
                    "Nicht verfügbar in der Entwicklungs-Vorschau und "
                    "unter Linux.", size=13, italic=True),
            ft.Radio(value=TTS_GOOGLE, label="Google (online)"),
            ft.Text("Holt das Audio von Google-Servern — dabei werden der "
                    "gesprochene Text und die IP-Adresse an Google (USA) "
                    "übertragen. Danach liegt das Audio im lokalen Cache "
                    "und spielt offline. Für Geräte ohne griechische "
                    "Systemstimme; „Audio vorbereiten“ im Listenmenü lädt "
                    "ganze Listen vor.", size=13, italic=True),
        ], spacing=4),
    )

    def on_tts(e):
        set_tts_engine(rg_tts.value or TTS_SYSTEM)
        s.tts_engine = rg_tts.value or TTS_SYSTEM

    rg_tts.on_change = on_tts

    # --- Stufe: sichtbare Vokabellisten (A1/A2) ---
    seg_level = ft.SegmentedButton(
        selected=[s.level if s.level in LEVELS else LEVELS[0]],
        segments=[ft.Segment(value=lv, label=ft.Text(lv)) for lv in LEVELS],
    )

    def on_level(e):
        sel = seg_level.selected
        s.level = next(iter(sel)) if isinstance(sel, (list, set, tuple)) else sel
        save_app_settings(s)

    seg_level.on_change = on_level

    # --- Erweiterte Funktionen: einzeln zuschaltbare Features ---
    def feature_switch(f) -> ft.Switch:
        sw = ft.Switch(label=f.title, value=f.key in s.enabled_features)

        def on_toggle(e, f=f, sw=sw):
            enabled = set(s.enabled_features)
            (enabled.add if sw.value else enabled.discard)(f.key)
            # Registry-Reihenfolge statt Einschalt-Reihenfolge speichern
            s.enabled_features = [x.key for x in FEATURES if x.key in enabled]
            save_app_settings(s)
            # Gecachte Feature-Zustände (z.B. Etymologie-Index) auffrischen
            from mathainoa1.storage.textanalyse import invalidate_cache
            invalidate_cache()

        sw.on_change = on_toggle
        return sw

    feature_rows: list[ft.Control] = []
    for f in FEATURES:
        feature_rows.append(feature_switch(f))
        feature_rows.append(ft.Text(f.subtitle, size=13, italic=True))
    if not feature_rows:
        feature_rows.append(ft.Text(
            "Noch keine Zusatzfunktionen verfügbar — weitere folgen in "
            "künftigen Versionen.", size=13, italic=True))

    def _h(text: str) -> ft.Text:
        return ft.Text(text, size=16, weight=ft.FontWeight.BOLD)

    # --- Backup: Export/Import der Nutzerdaten (kategorieweise) ---
    backup_rows: list[ft.Control] = []
    if store is not None and progress is not None:
        picker = ft.FilePicker()
        if picker not in page.services:
            page.services.append(picker)

        def create_dialog(e):
            boxes = {key: ft.Checkbox(label=label, value=True)
                     for key, label in backup.PARTS}

            def sync(e=None):
                # Fortschritt hängt an den Karten-IDs der Vokabeln
                if not boxes["vocab"].value:
                    boxes["progress"].value = False
                boxes["progress"].disabled = not boxes["vocab"].value
                page.update()

            boxes["vocab"].on_change = sync

            async def do_export(e):
                parts = [k for k, cb in boxes.items() if cb.value]
                try:
                    data = backup.create_backup(progress, parts)
                except ValueError as exc:
                    page.pop_dialog()
                    page.show_dialog(ft.SnackBar(ft.Text(str(exc))))
                    return
                page.pop_dialog()
                await picker.save_file(
                    dialog_title="Backup speichern",
                    file_name=backup.suggested_filename(),
                    allowed_extensions=["zip"], src_bytes=data)
                page.show_dialog(ft.SnackBar(ft.Text(
                    f"Backup erstellt ({max(1, len(data) // 1024)} kB).")))

            page.show_dialog(ft.AlertDialog(
                title=ft.Text("Backup erstellen"),
                content=ft.Column(
                    [ft.Text("Was soll in die Backup-Datei?", size=13),
                     *boxes.values(),
                     ft.Text("Heruntergeladenes Audio ist nie enthalten — "
                             "es wird bei Bedarf neu geladen.",
                             size=13, italic=True)],
                    tight=True, spacing=6, width=420,
                    scroll=ft.ScrollMode.AUTO),
                actions=[ft.TextButton("Abbrechen",
                                       on_click=lambda e: page.pop_dialog()),
                         ft.FilledButton("Speichern", on_click=do_export)],
            ))

        async def pick_restore(e):
            files = await picker.pick_files(
                dialog_title="Backup wiederherstellen",
                allowed_extensions=["zip"], with_data=True)
            if not files:
                return
            f = files[0]
            data = f.bytes_data if hasattr(f, "bytes_data") else None
            if data is None and f.path:
                data = Path(f.path).read_bytes()
            if data is None:
                return
            try:
                manifest = backup.read_manifest(data)
            except ValueError as exc:
                page.show_dialog(ft.SnackBar(ft.Text(str(exc))))
                return
            labels = ", ".join(backup.part_label(p)
                               for p in manifest["parts"])

            def do_restore(e):
                try:
                    backup.restore_backup(data, store, progress)
                except ValueError as exc:
                    page.pop_dialog()
                    page.show_dialog(ft.SnackBar(ft.Text(str(exc))))
                    return
                # Wiederhergestellte Einstellungen sofort wirksam machen
                fresh = load_app_settings()
                apply_app_theme(page, fresh)
                set_tts_engine(fresh.tts_engine)
                page.pop_dialog()
                title = nav.stack[-1][0]
                nav.stack[-1] = (title,
                                 settings_view(nav, store, progress))
                nav._show()
                page.show_dialog(ft.SnackBar(ft.Text(
                    f"Backup wiederhergestellt: {labels}.")))

            page.show_dialog(ft.AlertDialog(
                title=ft.Text("Backup wiederherstellen?"),
                content=ft.Text(
                    f"Ersetzt auf diesem Gerät: {labels}. Das lässt sich "
                    "nicht rückgängig machen — nicht enthaltene Bereiche "
                    "bleiben unverändert."),
                actions=[ft.TextButton("Abbrechen",
                                       on_click=lambda e: page.pop_dialog()),
                         ft.FilledButton("Wiederherstellen",
                                         on_click=do_restore)],
            ))

        backup_rows = [
            ft.Divider(),
            _h("Backup"),
            ft.Text("Sichert die gewählten Bereiche als eine ZIP-Datei — "
                    "für Sicherungskopien und den Umzug auf ein neues "
                    "Gerät. Beim Wiederherstellen werden genau die im "
                    "Backup enthaltenen Bereiche ersetzt.",
                    size=13, italic=True),
            ft.Row([
                ft.FilledButton("Backup erstellen", icon=ft.Icons.ARCHIVE,
                                on_click=create_dialog),
                ft.OutlinedButton("Backup wiederherstellen",
                                  icon=ft.Icons.UNARCHIVE,
                                  on_click=pick_restore),
            ], spacing=8, wrap=True),
        ]

    return ft.Column(
        [
            _h("Stufe"),
            ft.Text("Filtert, welche Vokabellisten in Training, Verwaltung "
                    "und Statistik erscheinen. A2 zeigt auch A1-Listen. "
                    "Eigene Listen ohne Stufe sind immer sichtbar.",
                    size=13, italic=True),
            seg_level,
            ft.Divider(),
            _h("Ansicht"),
            ft.Text("Design", size=13),
            seg_theme,
            dd_color,
            ft.Text("Hauptmenü-Reihenfolge", size=13),
            ft.Text("Kacheln am ≡ ziehen — die Startseite übernimmt die "
                    "neue Reihenfolge sofort.", size=13, italic=True),
            ft.Container(menu_list,
                         height=min(480, 60 * max(1, len(menu_keys)))),
            ft.Divider(),
            _h("Abfrage"),
            ft.Text("Greift nur, wenn beim Training „Akzentfehler tolerieren“ "
                    "bzw. „Groß-/Kleinschreibung tolerieren“ ausgeschaltet ist. "
                    "Aus = die Box bleibt bei so einem Fehler unverändert.",
                    size=13, italic=True),
            sw_accent,
            sw_case,
            ft.Divider(),
            ft.Text("Beschränkung durch die Abfragemodi", size=13),
            ft.Text("Steuert, wie hoch eine Karte je nach Abfrageart steigen "
                    "kann. Beide aus = jede Abfrageart erreicht Box 5.",
                    size=13, italic=True),
            sw_high,
            sw_top,
            ft.Divider(),
            ft.Text("Prüfen beim Schreiben", size=13),
            ft.Text("Aus = „Prüfen“-Button mittig unter dem Antwortfeld, "
                    "an = rundes Häkchen rechts daneben (spart Platz bei "
                    "eingeblendeter Tastatur).", size=13, italic=True),
            sw_check,
            ft.Divider(),
            ft.Text("Fehlerrunde", size=13),
            ft.Text("Ein Fehler setzt die Box sofort auf 1. Hier lässt sich "
                    "einstellen, wohin ein Wort wandert, das in der "
                    "Fehlerrunde richtig beantwortet wird — Leichtsinns"
                    "fehler werden so weniger hart bestraft. „Ursprüngliche "
                    "Box“ ist die Box vor dem Fehler; „eine Box zurück“ "
                    "bedeutet eine Box unter der ursprünglichen.",
                    size=13, italic=True),
            rg_repeat,
            ft.Divider(),
            _h("Sprachausgabe"),
            rg_tts,
            ft.Text("Doppeltipp auf einen Lautsprecher (oder langes "
                    "Drücken) schaltet die langsame Wiedergabe an/aus — "
                    "das Symbol wird dann zur Schildkröte 🐢.",
                    size=13, italic=True),
            dd_tap,
            *backup_rows,
            ft.Divider(),
            _h("Erweiterte Funktionen"),
            ft.Text("Zusatzfunktionen für Fortgeschrittene. Eingeschaltete "
                    "Funktionen erscheinen als eigene Karte im Hauptmenü "
                    "und gelten für alle Stufen.", size=13, italic=True),
            *feature_rows,
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )
