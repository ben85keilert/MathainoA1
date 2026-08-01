"""Zoomfaktor: sz()-Skalierung und Klemmen in ui/scale.py."""

import pytest

from mathainoa1.ui import scale


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
