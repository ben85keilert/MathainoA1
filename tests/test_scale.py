"""Zoomfaktor: sz()-Skalierung und Klemmen in ui/scale.py, plus das
skalierte TextTheme (Kontrastfix) aus ui/views/settings.py."""

from types import SimpleNamespace

import flet as ft
import pytest

from mathainoa1.storage.settings import AppSettings
from mathainoa1.ui import scale
from mathainoa1.ui.views.settings import _scaled_text_theme, apply_app_theme


@pytest.fixture(autouse=True)
def reset_scale():
    yield
    scale.set_ui_scale(1.0)


def test_default_is_unscaled():
    assert scale.get_ui_scale() == 1.0
    assert scale.sz(14) == 14


def test_sz_scales_and_rounds():
    scale.set_ui_scale(1.5)
    assert scale.sz(14) == 21
    scale.set_ui_scale(0.7)
    assert scale.sz(14) == 10  # round(9.8)
    assert scale.sz(1) >= 1


def test_set_ui_scale_clamps():
    scale.set_ui_scale(9)
    assert scale.get_ui_scale() == scale.MAX_SCALE
    scale.set_ui_scale(0.1)
    assert scale.get_ui_scale() == scale.MIN_SCALE


def test_set_ui_scale_tolerates_garbage():
    scale.set_ui_scale(None)
    assert scale.get_ui_scale() == 1.0
    scale.set_ui_scale("kaputt")
    assert scale.get_ui_scale() == 1.0
    scale.set_ui_scale("1.25")  # Strings mit Zahl sind ok
    assert scale.get_ui_scale() == 1.25


def _text_styles(tt: ft.TextTheme) -> list[ft.TextStyle]:
    import dataclasses
    values = [getattr(tt, f.name) for f in dataclasses.fields(tt)]
    return [v for v in values if isinstance(v, ft.TextStyle)]


def test_scaled_text_theme_carries_color_and_sizes():
    """Ohne explizite Farbe ersetzt das TextTheme die helligkeits-
    abhängige Standard-Typografie und Text würde im hellen Theme weiß.
    Der gerenderte Kontrast selbst ist nur manuell prüfbar."""
    scale.set_ui_scale(1.3)
    styles = _text_styles(_scaled_text_theme())
    assert styles, "TextTheme ohne Stile"
    assert all(s.color == ft.Colors.ON_SURFACE for s in styles)
    assert any(s.size == scale.sz(14) for s in styles)


def test_apply_app_theme_separate_text_theme_instances():
    page = SimpleNamespace(theme=None, dark_theme=None, theme_mode=None)
    apply_app_theme(page, AppSettings(ui_scale=1.3))
    assert page.theme.text_theme is not None
    assert page.dark_theme.text_theme is not None
    assert page.theme.text_theme is not page.dark_theme.text_theme


def test_apply_app_theme_no_text_theme_at_100_percent():
    page = SimpleNamespace(theme=None, dark_theme=None, theme_mode=None)
    apply_app_theme(page, AppSettings(ui_scale=1.0))
    assert page.theme.text_theme is None
    assert page.dark_theme.text_theme is None
