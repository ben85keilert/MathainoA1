"""Einstellungen (Zahnrad): Übersicht mit Kategorien, je Kategorie eine
eigene Unterseite.

Kategorien: Darstellung (Design, Zoom, Hauptmenü), Stufe, Abfrage &
Wertung, Beugungstraining, Sprachausgabe, Backup, Erweiterte Funktionen.
Die Übersicht zeigt je Kachel eine Kurzfassung des aktuellen Stands und
frischt sich beim Zurückkehren auf (on_reappear).

`apply_app_theme` wird beim App-Start und bei jeder Änderung aufgerufen und
setzt Design (Farben, Theme-Modus, Hintergrundverlauf) und Zoomfaktor der
ganzen App.
"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from mathainoa1.logic.conjugation import tenses_for_level
from mathainoa1.storage import backup
from mathainoa1.storage.content import LEVELS
from mathainoa1.storage.settings import (
    STRICT_BOX_POLICIES,
    TTS_GOOGLE,
    TTS_SYSTEM,
    VERB_BASE_FORM_MODES,
    AppSettings,
    load_app_settings,
    save_app_settings,
)
from mathainoa1.ui.audio import set_slow_tap_seconds, set_tts_engine
from mathainoa1.ui.designs import (
    DESIGNS,
    background,
    build_theme,
    dark_designs,
    light_designs,
    preview_gradient,
)
from mathainoa1.ui.features import FEATURES
from mathainoa1.ui.scale import get_ui_scale, set_ui_scale, sz

# Akzentfarben des Altbestands (AppSettings.seed) — gelten nur noch, wenn
# kein Design gewählt ist (siehe apply_app_theme)
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


def _scaled_text_theme() -> ft.TextTheme:
    """Material-Textstile mit dem Zoomfaktor skaliert — damit auch Text,
    der nicht durch sz() läuft (Radio-/Switch-Labels, Buttons, AppBar),
    dem Zoom folgt. Größen/Gewichte = Material-Defaults, nur skaliert.

    Jeder Stil braucht explizit color=ON_SURFACE: ein gesetztes text_theme
    ERSETZT Flutters helligkeitsabhängige Typografie, und ohne Farbe fiele
    der Text auf Weiß zurück — im hellen Theme unleserlich. Das Token löst
    clientseitig je Theme-Helligkeit korrekt auf."""
    def st(size: int, weight=ft.FontWeight.W_400) -> ft.TextStyle:
        return ft.TextStyle(size=sz(size), weight=weight,
                            color=ft.Colors.ON_SURFACE)

    return ft.TextTheme(
        body_large=st(16), body_medium=st(14), body_small=st(12),
        label_large=st(14, ft.FontWeight.W_500),
        label_medium=st(12, ft.FontWeight.W_500),
        label_small=st(11, ft.FontWeight.W_500),
        title_large=st(22),
        title_medium=st(16, ft.FontWeight.W_500),
        title_small=st(14, ft.FontWeight.W_500),
    )


def apply_app_theme(page: ft.Page, s: AppSettings) -> None:
    """Setzt Design (Farben, Theme-Modus, Verlauf) und Zoomfaktor der
    ganzen App.

    Bei 100 % kein text_theme setzen — so bleibt die Darstellung exakt wie
    ohne Zoom-Funktion. Hell und Dunkel bekommen jeweils eine EIGENE
    TextTheme-Instanz — ein geteiltes Objekt kann beim Einhängen in den
    Control-Baum einem der beiden Themes verloren gehen."""
    set_ui_scale(s.ui_scale)
    scaled = get_ui_scale() != 1.0
    design = DESIGNS.get(s.design)
    if design is None:
        # Altbestand ohne Design: Hell/Dunkel/System + Akzentfarbe
        page.theme_mode = _THEME_MODES.get(s.theme, ft.ThemeMode.SYSTEM)
        seed = SEED_COLORS.get(s.seed, SEED_COLORS["blue"])[1]
        page.theme = ft.Theme(
            color_scheme_seed=seed,
            text_theme=_scaled_text_theme() if scaled else None)
        page.dark_theme = ft.Theme(
            color_scheme_seed=seed,
            text_theme=_scaled_text_theme() if scaled else None)
        decoration = None
    else:
        page.theme_mode = (ft.ThemeMode.DARK if design.dark
                           else ft.ThemeMode.LIGHT)
        page.theme = build_theme(
            design, _scaled_text_theme() if scaled else None)
        page.dark_theme = build_theme(
            design, _scaled_text_theme() if scaled else None)
        decoration = background(design)
    # Der Verlauf liegt hinter dem Inhalt der (einzigen) View; das
    # Gerüst ist im Design-Thema durchsichtig
    views = getattr(page, "views", None)
    if views:
        views[0].decoration = decoration


def _wrapping_radio_group(value: str, options: list[tuple[str, str]],
                          on_select, page: ft.Page) -> ft.RadioGroup:
    """RadioGroup mit umbruchfähigen Labels.

    Flet-Radio-Labels sind reine Strings ohne Umbruch und werden auf
    schmalen Displays abgeschnitten — deshalb Radio ohne Label plus
    Text(expand=True) in einer antippbaren Zeile. on_select(wert) ist
    der eine Speicher-Callback für beide Wege (Radio-Tap über
    rg.on_change, Zeilen-Klick programmatisch — das feuert kein
    on_change von selbst)."""
    rg: ft.RadioGroup

    def pick(v: str):
        def handler(e):
            rg.value = v
            on_select(v)
            page.update()
        return handler

    rows = [
        ft.Container(
            ft.Row([ft.Radio(value=v),
                    ft.Text(label, size=sz(14), expand=True)],
                   spacing=6,
                   vertical_alignment=ft.CrossAxisAlignment.START),
            on_click=pick(v), ink=True)
        for v, label in options
    ]
    rg = ft.RadioGroup(value=value, content=ft.Column(rows, spacing=4))
    rg.on_change = lambda e: on_select(rg.value)
    return rg


def _switch_row(sw: ft.Switch, label: str, page: ft.Page) -> ft.Control:
    """Switch mit umbruchfähigem Label (Flet-Switch-Labels brechen nicht
    um): Switch ohne Label + Text(expand=True); Klick auf die ganze
    Zeile schaltet um und feuert den on_change-Handler des Switch."""
    def toggle(e):
        sw.value = not sw.value
        if sw.on_change:
            sw.on_change(None)
        page.update()

    return ft.Container(
        ft.Row([sw, ft.Text(label, size=sz(14), expand=True)],
               spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        on_click=toggle, ink=True)


def _h(text: str) -> ft.Text:
    return ft.Text(text, size=sz(16), weight=ft.FontWeight.BOLD)


def _sub(text: str) -> ft.Text:
    return ft.Text(text, size=sz(13))


def _hint(text: str) -> ft.Text:
    return ft.Text(text, size=sz(13), italic=True)


def _reload(nav, key: str, store, progress) -> None:
    """Die offene Kategorieseite in place neu aufbauen (z.B. nach Zoom-
    oder Design-Wechsel, damit die Änderung sofort sichtbar ist)."""
    title = nav.stack[-1][0]
    nav.stack[-1] = (title, settings_category_view(nav, key, store, progress))
    nav._show()


# --- Darstellung: Design, Zoom, Hauptmenü-Reihenfolge ----------------------

def _display_controls(nav, s: AppSettings, store, progress) -> list[ft.Control]:
    page = nav.page

    def choose_design(key: str):
        def handler(e):
            s.design = key
            apply_app_theme(page, s)
            save_app_settings(s)
            _reload(nav, "darstellung", store, progress)
        return handler

    def tile(d) -> ft.Control:
        chosen = d.key == s.design
        return ft.Container(
            width=84, on_click=choose_design(d.key), ink=True,
            border_radius=12, padding=4,
            content=ft.Column(
                [ft.Container(
                    width=76, height=56, border_radius=12,
                    gradient=preview_gradient(d),
                    border=ft.Border.all(
                        3 if chosen else 1,
                        ft.Colors.PRIMARY if chosen
                        else ft.Colors.with_opacity(0.25, ft.Colors.ON_SURFACE)),
                    content=ft.Container(
                        width=22, height=22, border_radius=11,
                        bgcolor=d.seed, alignment=ft.Alignment.CENTER),
                    alignment=ft.Alignment.CENTER,
                 ),
                 ft.Text(d.name, size=sz(12),
                         weight=ft.FontWeight.BOLD if chosen else None,
                         text_align=ft.TextAlign.CENTER)],
                spacing=4, tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )

    # --- Zoomfaktor (echte Schriftgrößen-Skalierung) ---
    _zoom_steps = ("0.7", "0.8", "0.9", "1", "1.1", "1.25", "1.5")
    dd_zoom = ft.Dropdown(
        label="Zoom",
        value=(f"{s.ui_scale:g}" if f"{s.ui_scale:g}" in _zoom_steps
               else "1"),
        options=[ft.DropdownOption(key=k, text=f"{round(float(k) * 100)} %")
                 for k in _zoom_steps],
    )

    def on_zoom(e):
        try:
            s.ui_scale = float(dd_zoom.value)
        except (TypeError, ValueError):
            s.ui_scale = 1.0
        save_app_settings(s)
        apply_app_theme(page, s)
        # Seite in place neu aufbauen — der neue Zoom ist sofort
        # sichtbar; andere Ansichten folgen beim Navigieren
        _reload(nav, "darstellung", store, progress)

    dd_zoom.on_select = on_zoom  # Flet 0.85: Dropdowns feuern on_select

    # --- Reihenfolge der Hauptmenü-Kacheln (Drag & Drop) ---
    # Lazy-Import: app importiert dieses Modul (Importzirkel)
    from mathainoa1.ui.app import menu_tiles_meta, ordered_menu_keys
    from mathainoa1.ui.views.wordlist import drag_row
    tile_meta = {k: (title, icon) for k, title, icon in menu_tiles_meta(s)}
    menu_keys = ordered_menu_keys(list(tile_meta), s.menu_order)
    menu_list = ft.ReorderableListView(show_default_drag_handles=False)

    def rebuild_menu_rows():
        menu_list.controls = [
            drag_row(ft.Row([ft.Icon(tile_meta[k][1], size=sz(20)),
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

    return [
        _h("Design"),
        _hint("Vier helle und vier dunkle Farbpaletten — die Wahl setzt "
              "zugleich den hellen bzw. dunklen Modus. Der Punkt zeigt die "
              "Akzentfarbe."),
        _sub("Hell"),
        ft.Row([tile(d) for d in light_designs()], wrap=True,
               spacing=8, run_spacing=8),
        _sub("Dunkel"),
        ft.Row([tile(d) for d in dark_designs()], wrap=True,
               spacing=8, run_spacing=8),
        ft.Divider(),
        _h("Zoom"),
        _hint("Skaliert alle Schriften der App — kleiner, damit auf "
              "kleine Displays mehr passt, oder größer für bessere "
              "Lesbarkeit. Standard: 100 %."),
        dd_zoom,
        ft.Divider(),
        _h("Hauptmenü-Reihenfolge"),
        _hint("Kacheln am ≡ ziehen — die Startseite übernimmt die neue "
              "Reihenfolge sofort."),
        # Zeilenhöhe ist textgetrieben und skaliert mit dem Zoom;
        # der 480er-Deckel ist Bildschirmplatz und bleibt fix
        ft.Container(menu_list,
                     height=min(480, sz(60) * max(1, len(menu_keys)))),
    ]


# --- Stufe ------------------------------------------------------------------

def _level_controls(nav, s: AppSettings, store, progress) -> list[ft.Control]:
    seg_level = ft.SegmentedButton(
        selected=[s.level if s.level in LEVELS else LEVELS[0]],
        segments=[ft.Segment(value=lv, label=ft.Text(lv)) for lv in LEVELS],
    )

    def on_level(e):
        sel = seg_level.selected
        s.level = next(iter(sel)) if isinstance(sel, (list, set, tuple)) else sel
        save_app_settings(s)

    seg_level.on_change = on_level
    return [
        _h("Stufe"),
        _hint("Filtert, welche Listen in Training, Verwaltung, Suche "
              "und Statistik erscheinen. Die Stufen sind strikt "
              "getrennt — jede zeigt nur ihre eigenen Listen; zum "
              "Üben von A1-Listen hierher zurückschalten. Listen und "
              "Auswahllisten ohne Stufe sind immer sichtbar; neue "
              "erhalten die gerade aktive Stufe. Jede Stufe zeigt nur "
              "ihren Stoff (A2: dazu Vergangenheit und Imperativ)."),
        seg_level,
    ]


# --- Abfrage & Wertung ------------------------------------------------------

def _query_controls(nav, s: AppSettings, store, progress) -> list[ft.Control]:
    page = nav.page
    # Lange Schalter-/Radio-Labels laufen über _switch_row bzw.
    # _wrapping_radio_group, damit sie auf schmalen Displays umbrechen
    _strict_options = [
        ("reset", "Setzt die Box zurück (Box 1) — gilt auch in der "
                  "Fehlerrunde"),
        ("keep", "Box bleibt unverändert (Standard)"),
        ("repeat_correct", "In der Fehlerrunde wie richtig — "
                           "Box-Verschiebung nach der Fehlerrunden-Regel "
                           "(siehe unten)"),
        ("repeat_step_back", "In der Fehlerrunde eine Box zurück"),
    ]

    def save_accent_policy(v):
        s.accent_box_policy = v or "keep"
        save_app_settings(s)

    def save_case_policy(v):
        s.case_box_policy = v or "keep"
        save_app_settings(s)

    rg_accent_policy = _wrapping_radio_group(
        value=(s.accent_box_policy
               if s.accent_box_policy in STRICT_BOX_POLICIES else "keep"),
        options=_strict_options, on_select=save_accent_policy, page=page)
    rg_case_policy = _wrapping_radio_group(
        value=(s.case_box_policy
               if s.case_box_policy in STRICT_BOX_POLICIES else "keep"),
        options=_strict_options, on_select=save_case_policy, page=page)

    # --- Beschränkungen durch die Abfragemodi ---
    sw_high = ft.Switch(value=s.high_boxes_need_production)
    sw_top = ft.Switch(value=s.top_box_needs_typing)
    sw_infl = ft.Switch(value=s.top_box_needs_inflection)

    def on_high(e):
        s.high_boxes_need_production = sw_high.value
        save_app_settings(s)

    def on_top(e):
        s.top_box_needs_typing = sw_top.value
        save_app_settings(s)

    def on_infl(e):
        s.top_box_needs_inflection = sw_infl.value
        save_app_settings(s)

    sw_high.on_change = on_high
    sw_top.on_change = on_top
    sw_infl.on_change = on_infl

    # --- Statistik je Training ein-/ausschalten ---
    stat_switches = {
        "stats_vocab": (ft.Switch(value=s.stats_vocab), "Vokabeltraining"),
        "stats_nouns": (ft.Switch(value=s.stats_nouns), "Nomentraining"),
        "stats_adjectives": (ft.Switch(value=s.stats_adjectives),
                             "Adjektivtraining"),
        "stats_verbs": (ft.Switch(value=s.stats_verbs), "Verbtraining"),
    }

    def on_stats(key: str):
        def handler(e, key=key):
            setattr(s, key, stat_switches[key][0].value)
            save_app_settings(s)
        return handler

    for _key, (_sw, _label) in stat_switches.items():
        _sw.on_change = on_stats(_key)

    stats_rows = [_switch_row(sw, label, page)
                  for sw, label in stat_switches.values()]

    # --- Prüfbutton-Stil beim Schreiben ---
    sw_check = ft.Switch(value=s.check_beside_field)

    def on_check(e):
        s.check_beside_field = sw_check.value
        save_app_settings(s)

    sw_check.on_change = on_check

    # --- Boxen vorher/nachher in der Ergebnisliste ---
    sw_result_dots = ft.Switch(value=s.result_box_dots)

    def on_result_dots(e):
        s.result_box_dots = sw_result_dots.value
        save_app_settings(s)

    sw_result_dots.on_change = on_result_dots

    # --- Fehlerrunde und Leitner-Box ---
    def save_repeat(v):
        s.repeat_round_box_policy = v or "step_down"
        save_app_settings(s)

    rg_repeat = _wrapping_radio_group(
        value=(s.repeat_round_box_policy
               if s.repeat_round_box_policy in ("none", "box2", "original",
                                                "step_down") else "step_down"),
        options=[
            ("none", "Keine Verbesserung — Wort bleibt in Box 1"),
            ("box2", "Richtig in der Fehlerrunde → Box 2"),
            ("original", "Richtig in der Fehlerrunde → zurück in die "
                         "ursprüngliche Box"),
            ("step_down", "Richtig in der Fehlerrunde → eine Box zurück "
                          "(mindestens Box 2) (Standard)"),
        ],
        on_select=save_repeat, page=page)

    return [
        _h("Akzent- und Schreibungsfehler (sonst richtige Antwort)"),
        _hint("Greift nur, wenn beim Training „Akzentfehler tolerieren“ "
              "bzw. „Groß-/Kleinschreibung tolerieren“ ausgeschaltet "
              "ist. So ein Fehler zählt immer als Fehler der Runde und "
              "kommt in die Fehlerrunde — hier steht, was dabei mit "
              "der Leitner-Box passiert. Neue (graue) Wörter starten "
              "bei so einem Fehler immer normal in Box 1."),
        _sub("Akzentfehler"),
        rg_accent_policy,
        _sub("Schreibungsfehler (Groß-/Klein, nur Nomen)"),
        rg_case_policy,
        ft.Divider(),
        _h("Beschränkung durch die Abfragemodi"),
        _hint("Steuert, wie hoch eine Karte je nach Abfrageart steigen "
              "kann. Alle aus = jede Abfrageart erreicht Box 5. Ist "
              "„nur über das Beugungstraining“ an, rücken die übrigen "
              "Obergrenzen eine Box nach unten: Griechisch → Deutsch "
              "höchstens Box 2, Karteikarte Box 3, Schreiben Box 4 — "
              "Box 5 erreicht nur das Nomen-/Adjektiv-/Verbtraining "
              "mit Vorgabe Deutsch."),
        _switch_row(sw_high,
                    "Box 4 und 5 nur über Deutsch → Griechisch", page),
        _switch_row(sw_top,
                    "Box 5 nur über Deutsch → Griechisch mit Schreiben",
                    page),
        _switch_row(sw_infl,
                    "Box 5 nur über das Beugungstraining "
                    "(Nomen/Adjektiv/Verb, Vorgabe Deutsch)",
                    page),
        ft.Divider(),
        _h("Statistik einschalten für"),
        _hint("Bestimmt, welche Trainings den Lernstand bewegen "
              "dürfen. Ist ein Training aus, fällt es komplett aus "
              "der Statistik: keine Leitner-Boxen rauf oder runter, "
              "keine Fehlerzähler, keine Punkte in der Ergebnisliste. "
              "Welche Wörter gezogen werden, richtet sich weiterhin "
              "nach den Boxen. (Nomen/Adjektive/Verben zählen ohnehin "
              "nur bei Vorgabe „Deutsch“.)"),
        *stats_rows,
        ft.Divider(),
        _h("Fehlerrunde"),
        _hint("Ein Fehler setzt die Box sofort auf 1. Hier lässt sich "
              "einstellen, wohin ein Wort wandert, das in der "
              "Fehlerrunde richtig beantwortet wird — Leichtsinns"
              "fehler werden so weniger hart bestraft. „Ursprüngliche "
              "Box“ ist die Box vor dem Fehler; „eine Box zurück“ "
              "bedeutet eine Box unter der ursprünglichen."),
        rg_repeat,
        ft.Divider(),
        _h("Prüfen beim Schreiben"),
        _hint("Aus = „Prüfen“-Button mittig unter dem Antwortfeld, "
              "an = rundes Häkchen rechts daneben (spart Platz bei "
              "eingeblendeter Tastatur)."),
        _switch_row(sw_check,
                    "Prüf-Häkchen rechts neben dem Antwortfeld (kompakt)",
                    page),
        ft.Divider(),
        _h("Ergebnisliste"),
        _hint("Zeigt nach jeder Runde vor jedem Wort einen "
              "zweigeteilten Farbpunkt: linke Hälfte = Leitner-Box "
              "vor der Runde, rechte Hälfte = Box danach (grau = "
              "noch nicht trainiert). Gilt für alle Trainings "
              "gleichermaßen."),
        _switch_row(sw_result_dots,
                    "Boxen vorher/nachher in der Ergebnisliste anzeigen",
                    page),
    ]


# --- Beugungstraining: Adjektiv- und Verbtraining ---------------------------

def _inflection_controls(nav, s: AppSettings, store, progress) -> list[ft.Control]:
    page = nav.page

    def save_adjective(v):
        s.adjective_combos_mode = v or "whitelist"
        save_app_settings(s)

    rg_adjective = _wrapping_radio_group(
        value=(s.adjective_combos_mode
               if s.adjective_combos_mode in ("whitelist", "blacklist")
               else "whitelist"),
        options=[
            ("whitelist", "Whitelisting — nur festgelegte Verbindungen "
                          "werden abgefragt (Standard)"),
            ("blacklist", "Blacklisting — alle Kombinationen außer "
                          "festgelegten Ausnahmen"),
        ],
        on_select=save_adjective, page=page)

    def save_verb_base(v):
        s.verb_base_form = v or "both"
        save_app_settings(s)

    # Ab A2 gilt die Auswahl auch für den Aorist (έγραψα (γράφω))
    aorist_level = "aorist" in tenses_for_level(s.level)
    rg_verb_base = _wrapping_radio_group(
        value=(s.verb_base_form
               if s.verb_base_form in VERB_BASE_FORM_MODES else "both"),
        options=[
            ("present", "Nur Präsensform — z. B. „γράφω“"),
            ("stem2", ("Nur Grundform der Zeitform — z. B. „θα γράψω“, "
                       "„έγραψα“") if aorist_level
             else "Nur 2. Stamm — z. B. „θα γράψω“"),
            ("both", "Beides — z. B. „θα γράψω (γράφω)“ (Standard)"),
        ],
        on_select=save_verb_base, page=page)

    return [
        _h("Adjektivtraining"),
        _hint("Whitelisting fragt nur selbst festgelegte Adjektiv↔"
              "Nomen-Verbindungen ab. Blacklisting kombiniert die "
              "Adjektive der gewählten Liste mit ihren Nomen — außer "
              "den festgelegten Ausnahmen; enthält die Liste keine "
              "Nomen, werden alle Nomen der App verwendet."),
        rg_adjective,
        ft.Divider(),
        _h("Verbtraining"),
        _sub("Grundform nach der Lösung"),
        _hint("Bestimmt, welche Grundform nach dem Aufdecken unter "
              "der Lösung steht — nur bei Vorgabe „Deutsch“ (bei "
              "griechischer Vorgabe ist die Präsensform schon die "
              "Aufgabe). Die Auswahl wirkt bei Futur-Aufgaben"
              + (" und Vergangenheits-Aufgaben; bei Präsens- und "
                 "Imperativ-Aufgaben" if aorist_level
                 else "; bei Präsens-Aufgaben")
              + " erscheint immer die Präsensform."),
        rg_verb_base,
    ]


# --- Sprachausgabe ----------------------------------------------------------

def _tts_controls(nav, s: AppSettings, store, progress) -> list[ft.Control]:
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

    rg_tts = ft.RadioGroup(
        value=(s.tts_engine if s.tts_engine in (TTS_SYSTEM, TTS_GOOGLE)
               else TTS_SYSTEM),
        content=ft.Column([
            ft.Radio(value=TTS_SYSTEM, label="Systemstimme (Standard)"),
            _hint("Spricht offline über die Sprachausgabe des Geräts — "
                  "es werden keine Daten übertragen. Braucht eine "
                  "installierte griechische Stimme (Android: meist schon "
                  "dabei; Windows: Sprachpaket „Ελληνικά“ hinzufügen). "
                  "Nicht verfügbar in der Entwicklungs-Vorschau und "
                  "unter Linux."),
            ft.Radio(value=TTS_GOOGLE, label="Google (online)"),
            _hint("Holt das Audio von Google-Servern — dabei werden der "
                  "gesprochene Text und die IP-Adresse an Google (USA) "
                  "übertragen. Danach liegt das Audio im lokalen Cache "
                  "und spielt offline. Für Geräte ohne griechische "
                  "Systemstimme; „Audio vorbereiten“ im Listenmenü lädt "
                  "ganze Listen vor."),
        ], spacing=4),
    )

    def on_tts(e):
        set_tts_engine(rg_tts.value or TTS_SYSTEM)
        s.tts_engine = rg_tts.value or TTS_SYSTEM

    rg_tts.on_change = on_tts

    return [
        _h("Sprachausgabe"),
        rg_tts,
        _hint("Doppeltipp auf einen Lautsprecher (oder langes "
              "Drücken) schaltet die langsame Wiedergabe an/aus — "
              "das Symbol wird dann zur Schildkröte 🐢."),
        dd_tap,
    ]


# --- Backup: Export/Import der Nutzerdaten (kategorieweise) -----------------

def _backup_controls(nav, s: AppSettings, store, progress) -> list[ft.Control]:
    page = nav.page
    picker = ft.FilePicker()
    if picker not in page.services:
        page.services.append(picker)

    def part_boxes(available: set[str] | None = None
                   ) -> dict[str, ft.Checkbox]:
        """Eine Checkbox je Kategorie; nicht verfügbare (beim Import:
        nicht im Backup enthaltene) sind deaktiviert. Fortschritt
        hängt an den Karten-IDs der Vokabeln — nur gemeinsam wählbar."""
        boxes = {}
        for key, label in backup.PARTS:
            ok = available is None or key in available
            boxes[key] = ft.Checkbox(
                label=label if ok else f"{label} – nicht im Backup",
                value=ok, disabled=not ok)
        progress_ok = available is None or "progress" in available

        def sync(e=None):
            if not boxes["vocab"].value:
                boxes["progress"].value = False
            boxes["progress"].disabled = (not progress_ok
                                          or not boxes["vocab"].value)
            page.update()

        boxes["vocab"].on_change = sync
        return boxes

    def create_dialog(e):
        boxes = part_boxes()

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
                [_sub("Was soll in die Backup-Datei?"),
                 *boxes.values(),
                 _hint("Heruntergeladenes Audio ist nie enthalten — "
                       "es wird bei Bedarf neu geladen.")],
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
        boxes = part_boxes(set(manifest["parts"]))
        select_error = ft.Text("", color=ft.Colors.ERROR, size=sz(13))
        chosen: list[str] = []

        def do_restore(e):
            labels = ", ".join(backup.part_label(p) for p in chosen)
            try:
                backup.restore_backup(data, store, progress, parts=chosen)
            except ValueError as exc:
                page.pop_dialog()
                page.show_dialog(ft.SnackBar(ft.Text(str(exc))))
                return
            # Wiederhergestellte Einstellungen sofort wirksam machen
            fresh = load_app_settings()
            apply_app_theme(page, fresh)
            set_tts_engine(fresh.tts_engine)
            page.pop_dialog()
            _reload(nav, "backup", store, progress)
            page.show_dialog(ft.SnackBar(ft.Text(
                f"Backup wiederhergestellt: {labels}.")))

        def confirm(e):
            chosen[:] = [k for k, cb in boxes.items() if cb.value]
            if not chosen:
                select_error.value = "Bitte mindestens eine Kategorie wählen."
                page.update()
                return
            labels = ", ".join(backup.part_label(p) for p in chosen)
            page.pop_dialog()
            page.show_dialog(ft.AlertDialog(
                title=ft.Text("Wirklich wiederherstellen?"),
                content=ft.Text(
                    f"Ersetzt auf diesem Gerät: {labels}. Das lässt "
                    "sich nicht rückgängig machen — nicht gewählte "
                    "Bereiche bleiben unverändert."),
                actions=[ft.TextButton("Abbrechen",
                                       on_click=lambda e: page.pop_dialog()),
                         ft.FilledButton("Wiederherstellen",
                                         on_click=do_restore)],
            ))

        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Backup wiederherstellen"),
            content=ft.Column(
                [_sub("Welche Bereiche sollen zurückgespielt werden?"),
                 *boxes.values(),
                 _hint("Gewählte Bereiche werden auf diesem Gerät "
                       "komplett ersetzt."),
                 select_error],
                tight=True, spacing=6, width=420,
                scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Abbrechen",
                                   on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Weiter", on_click=confirm)],
        ))

    return [
        _h("Backup"),
        _hint("Sichert die gewählten Bereiche als eine ZIP-Datei — "
              "für Sicherungskopien und den Umzug auf ein neues "
              "Gerät. Beim Wiederherstellen wählst du, welche der "
              "enthaltenen Bereiche ersetzt werden."),
        ft.Row([
            ft.FilledButton("Backup erstellen", icon=ft.Icons.ARCHIVE,
                            on_click=create_dialog),
            ft.OutlinedButton("Backup wiederherstellen",
                              icon=ft.Icons.UNARCHIVE,
                              on_click=pick_restore),
        ], spacing=8, wrap=True),
    ]


# --- Erweiterte Funktionen: einzeln zuschaltbare Features -------------------

def _features_controls(nav, s: AppSettings, store, progress) -> list[ft.Control]:
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
        feature_rows.append(_hint(f.subtitle))
    if not feature_rows:
        feature_rows.append(_hint(
            "Noch keine Zusatzfunktionen verfügbar — weitere folgen in "
            "künftigen Versionen."))
    return [
        _h("Erweiterte Funktionen"),
        _hint("Zusatzfunktionen für Fortgeschrittene. Eingeschaltete "
              "Funktionen erscheinen als eigene Karte im Hauptmenü "
              "und gelten für alle Stufen."),
        *feature_rows,
    ]


# --- Übersicht: Kategorien --------------------------------------------------

def _summary(key: str, s: AppSettings) -> str:
    """Kurzfassung des aktuellen Stands für die Kategorie-Kachel."""
    if key == "darstellung":
        design = DESIGNS.get(s.design)
        name = design.name if design else "Standard"
        return f"Design {name} · Zoom {round(s.ui_scale * 100)} %"
    if key == "stufe":
        return f"Aktiv: {s.level}"
    if key == "abfrage":
        return "Akzent-/Schreibungsfehler, Boxen, Fehlerrunde, Statistik"
    if key == "beugung":
        return "Adjektivtraining, Verbtraining"
    if key == "sprachausgabe":
        return ("Google (online)" if s.tts_engine == TTS_GOOGLE
                else "Systemstimme")
    if key == "backup":
        return "Sichern und wiederherstellen"
    if key == "funktionen":
        n = sum(1 for f in FEATURES if f.key in s.enabled_features)
        return f"{n} von {len(FEATURES)} eingeschaltet"
    return ""


# (key, Titel, Icon, Builder, braucht Stores)
CATEGORIES = [
    ("darstellung", "Darstellung", ft.Icons.PALETTE_OUTLINED,
     _display_controls, False),
    ("stufe", "Stufe", ft.Icons.SCHOOL_OUTLINED, _level_controls, False),
    ("abfrage", "Abfrage & Wertung", ft.Icons.RULE, _query_controls, False),
    ("beugung", "Beugungstraining", ft.Icons.TABLE_CHART_OUTLINED,
     _inflection_controls, False),
    ("sprachausgabe", "Sprachausgabe", ft.Icons.VOLUME_UP, _tts_controls,
     False),
    ("backup", "Backup", ft.Icons.ARCHIVE_OUTLINED, _backup_controls, True),
    ("funktionen", "Erweiterte Funktionen", ft.Icons.EXTENSION_OUTLINED,
     _features_controls, False),
]


def settings_category_view(nav, key: str, store=None,
                           progress=None) -> ft.Control:
    """Die Unterseite einer Kategorie (alle Einstellungen des Bereichs)."""
    s = load_app_settings()
    for k, _title, _icon, builder, needs_stores in CATEGORIES:
        if k == key:
            if needs_stores and (store is None or progress is None):
                return ft.Text("Backup ist hier nicht verfügbar.")
            return ft.Column(builder(nav, s, store, progress), spacing=12,
                             scroll=ft.ScrollMode.AUTO)
    return ft.Text("Unbekannte Kategorie.")


def settings_view(nav, store=None, progress=None) -> ft.Control:
    """Übersicht: eine Kachel je Kategorie, öffnet die Unterseite."""

    def tile(key: str, title: str, icon: str) -> ft.Control:
        s = load_app_settings()
        return ft.Card(content=ft.ListTile(
            leading=ft.Icon(icon, color=ft.Colors.PRIMARY),
            title=ft.Text(title, size=sz(15), weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(_summary(key, s), size=sz(13)),
            trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
            on_click=lambda e: nav.go(
                title, settings_category_view(nav, key, store, progress)),
        ))

    def build_tiles() -> list[ft.Control]:
        return [tile(key, title, icon)
                for key, title, icon, _b, needs_stores in CATEGORIES
                if not needs_stores or (store is not None
                                        and progress is not None)]

    root = ft.Column(build_tiles(), spacing=4, scroll=ft.ScrollMode.AUTO)

    def refresh():
        # Kurzfassungen beim Zurückkehren aus einer Unterseite auffrischen
        root.controls = build_tiles()

    root.on_reappear = refresh
    return root
