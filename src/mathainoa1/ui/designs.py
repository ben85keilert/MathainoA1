"""Designs: acht Farbpaletten (vier helle, vier dunkle) für die ganze App.

Material leitet aus einer Grundfarbe (Saat) ein komplettes Farbschema ab —
im Dunkeln aber ein fast schwarzes, im Hellen ein fast weißes. Darum
ersetzt jedes Design die Flächenstufen (``surface`` …
``surface_container_highest``) durch eigene, getönte Farben; Akzente
(Buttons, Chips, Primärfarbe) kommen weiter aus der Saat. Weil die App
ihre Flächen über Material-Rollen färbt (Cards, Dialoge, Felder), färbt
das alles, ohne dass eine Ansicht etwas davon weiß. Dazu ein sanfter
Verlauf von oben nach unten hinter dem Inhalt (``View.decoration``; das
Gerüst wird dafür durchsichtig).

Ein Design ist entweder hell oder dunkel — die Wahl setzt den
Theme-Modus gleich mit. Die Farbwerte folgen dem Muster der
Trainingsapp (Nachtblau/Petrol/Violett), ergänzt um helle Gegenstücke.
"""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft


@dataclass(frozen=True)
class Surfaces:
    """Flächenstufen eines Designs, von der untersten zur höchsten (Namen
    wie die Material-Rollen). ``gradient`` läuft von oben nach unten."""

    lowest: str
    surface: str
    low: str
    container: str
    high: str
    highest: str
    bright: str
    gradient: tuple[str, str] | None = None

    def tiers(self) -> tuple[str, ...]:
        return (self.lowest, self.surface, self.low, self.container,
                self.high, self.highest)


@dataclass(frozen=True)
class Design:
    key: str
    name: str
    dark: bool
    seed: str  # Grundfarbe, aus der Material die Akzente ableitet
    surfaces: Surfaces


DESIGNS: dict[str, Design] = {
    # --- hell ---
    "aegaeis": Design(
        "aegaeis", "Ägäis", False, "#3F6DB5",
        Surfaces("#FFFFFF", "#F4F7FC", "#EBF0F8", "#E4EAF5", "#DCE4F1",
                 "#D3DCEC", "#F9FBFE", ("#D3E1F7", "#F4F7FC"))),
    "olive": Design(
        "olive", "Olive", False, "#5B8C3A",
        Surfaces("#FFFFFF", "#F4F8F1", "#ECF3E6", "#E5EEDE", "#DDE8D5",
                 "#D4E1CB", "#F8FBF6", ("#D6E8C8", "#F4F8F1"))),
    "sand": Design(
        "sand", "Sand", False, "#B5651D",
        Surfaces("#FFFFFF", "#FBF6F0", "#F6EEE4", "#F1E7DA", "#ECDFD0",
                 "#E5D6C5", "#FDFAF6", ("#F3DEC6", "#FBF6F0"))),
    "lavendel": Design(
        "lavendel", "Lavendel", False, "#7A5EA8",
        Surfaces("#FFFFFF", "#F8F5FC", "#F0EBF7", "#EBE5F4", "#E5DEF0",
                 "#DDD5EA", "#FCFAFE", ("#E4D6F7", "#F8F5FC"))),
    # --- dunkel ---
    "petrol": Design(
        "petrol", "Petrol", True, "#2E7D6E",
        Surfaces("#08110F", "#0D1A17", "#12221F", "#162825", "#1D322E",
                 "#263E39", "#2E4842", ("#1F4740", "#0D1A17"))),
    "nachtblau": Design(
        "nachtblau", "Nachtblau", True, "#3F6DB5",
        Surfaces("#070C16", "#0C1424", "#111B2E", "#152034", "#1C293F",
                 "#25344C", "#2D3D57", ("#20386A", "#0C1424"))),
    "violett": Design(
        "violett", "Violett", True, "#7A5EA8",
        Surfaces("#0C0A12", "#14111C", "#1B1726", "#201B2C", "#282236",
                 "#322B42", "#3A324B", ("#36275E", "#14111C"))),
    # Echtes Schwarz spart auf OLED-Displays Strom; die Kacheln sind leicht
    # getönt, damit sie sich vom Grund abheben — ohne Verlauf.
    "graphit": Design(
        "graphit", "Graphit", True, "#4F8FBF",
        Surfaces("#000000", "#000000", "#0B0F0E", "#101513", "#171D1B",
                 "#202826", "#2A3330")),
}

DEFAULT_LIGHT = "aegaeis"
DEFAULT_DARK = "nachtblau"


def light_designs() -> list[Design]:
    return [d for d in DESIGNS.values() if not d.dark]


def dark_designs() -> list[Design]:
    return [d for d in DESIGNS.values() if d.dark]


def _scheme(s: Surfaces) -> ft.ColorScheme:
    return ft.ColorScheme(
        surface=s.surface,
        surface_dim=s.surface,
        surface_bright=s.bright,
        surface_container_lowest=s.lowest,
        surface_container_low=s.low,
        surface_container=s.container,
        surface_container_high=s.high,
        surface_container_highest=s.highest,
    )


def build_theme(design: Design, text_theme: ft.TextTheme | None = None) -> ft.Theme:
    """Das Flet-Thema eines Designs (für hell UND dunkel dasselbe — der
    Modus wird über page.theme_mode fest auf das Design gesetzt)."""
    s = design.surfaces
    with_gradient = s.gradient is not None
    return ft.Theme(
        color_scheme_seed=design.seed,
        color_scheme=_scheme(s),
        use_material3=True,
        text_theme=text_theme,
        scaffold_bgcolor=ft.Colors.TRANSPARENT if with_gradient else s.surface,
        appbar_theme=(ft.AppBarTheme(bgcolor=ft.Colors.TRANSPARENT)
                      if with_gradient else None),
    )


def background(design: Design) -> ft.BoxDecoration | None:
    """Der Verlauf hinter dem Inhalt — None = einfarbig (Graphit)."""
    if design.surfaces.gradient is None:
        return None
    top, bottom = design.surfaces.gradient
    return ft.BoxDecoration(gradient=ft.LinearGradient(
        begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
        colors=[top, bottom, bottom], stops=[0.0, 0.55, 1.0]))


def preview_gradient(design: Design) -> ft.LinearGradient:
    """Vorschau-Kachel im Einstellungsmenü: Verlauf oder Flächenfarbe."""
    top, bottom = design.surfaces.gradient or (design.surfaces.surface,
                                               design.surfaces.surface)
    return ft.LinearGradient(begin=ft.Alignment.TOP_CENTER,
                             end=ft.Alignment.BOTTOM_CENTER,
                             colors=[top, bottom])


# --- Kontrast nach WCAG 2.x (für die Tests der Paletten) ---

def luminance(color: str) -> float:
    """Relative Leuchtdichte einer #RRGGBB-Farbe (0 = schwarz, 1 = weiß)."""
    h = color.lstrip("#")
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
               for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """Kontrastverhältnis zweier Farben (1–21); Text braucht ≥ 4,5."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)
