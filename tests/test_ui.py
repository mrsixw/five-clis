from freezegun import freeze_time

from fiveclis.ui import (
    CALENDAR_NAMES,
    CALENDARS,
    HOLI_RAINBOW,
    PRIDE_RAINBOW,
    SEASONAL_PALETTES,
    THEME_NAMES,
    THEMES,
    apply_seasonal_colour,
    get_theme,
)


def test_seasonal_palettes_has_expected_keys():
    expected = (
        "green",
        "purple",
        "yellow",
        "orange",
        "red",
        "pink",
        "lny",
        "blue",
        "spring_green",
        "gold",
    )
    for key in expected:
        assert key in SEASONAL_PALETTES


def test_pride_rainbow_has_six_colours():
    assert len(PRIDE_RAINBOW) == 6


def test_holi_rainbow_has_six_colours():
    assert len(HOLI_RAINBOW) == 6


def test_themes_registry_has_all_names():
    for name in ("default", "dark", "light", "mono", "rainbow"):
        assert name in THEMES


def test_theme_names_list():
    assert "rainbow" in THEME_NAMES
    assert "mono" in THEME_NAMES


def test_get_theme_known():
    t = get_theme("rainbow")
    assert t.cycle == PRIDE_RAINBOW


def test_get_theme_unknown_falls_back_to_default():
    t = get_theme("nonexistent")
    assert t is THEMES["default"]


def test_mono_theme_has_no_colours():
    t = get_theme("mono")
    assert t.primary is None
    assert t.accent is None


def test_theme_apply_mono_returns_plain(monkeypatch):
    t = get_theme("mono")
    result = t.apply("hello", role="primary")
    assert result == "hello"


def test_theme_apply_cycle(monkeypatch):
    t = get_theme("rainbow")
    result_0 = t.apply_cycle("a", 0)
    result_1 = t.apply_cycle("a", 1)
    assert result_0 != result_1


def test_apply_seasonal_colour_off():
    result = apply_seasonal_colour("hello", 0, calendar="off")
    assert result == "hello"


def test_apply_seasonal_colour_unknown_calendar():
    result = apply_seasonal_colour("hello", 0, calendar="martian")
    assert result == "hello"


@freeze_time("2026-01-15")
def test_apply_seasonal_colour_january():
    result = apply_seasonal_colour("hello", 0, calendar="western")
    assert SEASONAL_PALETTES["purple"] in result


@freeze_time("2031-01-23")
def test_january_does_not_shadow_other_calendars():
    # Lunar New Year 2031 falls on 23 January; the east-asian calendar must
    # see it rather than being overridden by the western New Year purple.
    result = apply_seasonal_colour("hello", 0, calendar="east-asian")
    assert SEASONAL_PALETTES["lny"] in result
    assert SEASONAL_PALETTES["purple"] not in result


@freeze_time("2026-06-15")
def test_apply_seasonal_colour_june_cycles():
    r0 = apply_seasonal_colour("a", 0, calendar="western")
    r1 = apply_seasonal_colour("a", 1, calendar="western")
    assert r0 != r1


# ── The two date-independent calendars ─────────────────────────────────────


def test_calendar_names_are_all_selectable():
    # Every name offered to click.Choice must actually resolve, or the flag
    # accepts a value that then silently does nothing. "off" is the one
    # exception: apply_seasonal_colour short-circuits before the lookup.
    for name in CALENDAR_NAMES:
        assert name == "off" or name in CALENDARS


@freeze_time("2026-03-04")
def test_rainbow_calendar_cycles_outside_june():
    # Plain March: the western calendar has no colour here, but rainbow does.
    assert apply_seasonal_colour("a", 0, calendar="western") == "a"
    r0 = apply_seasonal_colour("a", 0, calendar="rainbow")
    r1 = apply_seasonal_colour("a", 1, calendar="rainbow")
    assert PRIDE_RAINBOW[0] in r0
    assert PRIDE_RAINBOW[1] in r1
    assert r0 != r1


@freeze_time("2026-01-15")
def test_rainbow_calendar_ignores_the_january_purple():
    result = apply_seasonal_colour("hello", 0, calendar="rainbow")
    assert SEASONAL_PALETTES["purple"] not in result
    assert PRIDE_RAINBOW[0] in result


@freeze_time("2026-12-25")
def test_off_calendar_returns_text_untouched():
    # Christmas Day, when the western calendar is at its loudest.
    assert SEASONAL_PALETTES["red"] in apply_seasonal_colour("a", 0)
    assert apply_seasonal_colour("a", 0, calendar="off") == "a"
