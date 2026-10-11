"""Tests for the pure colour helpers in the theme (no display needed)."""

from timetracker.ui.style import darken, is_valid_hex, readable_fg


def test_is_valid_hex():
    assert is_valid_hex("#aabbcc")
    assert is_valid_hex("#AABBCC")
    assert not is_valid_hex("aabbcc")
    assert not is_valid_hex("#abc")
    assert not is_valid_hex("#gggggg")
    assert not is_valid_hex(None)


def test_darken_scales_channels():
    assert darken("#c8c8c8", 0.5) == "#646464"
    assert darken("#000000") == "#000000"


def test_readable_fg_picks_contrast():
    assert readable_fg("#ffffff") != "#ffffff"
    assert readable_fg("#102030") == "#ffffff"
