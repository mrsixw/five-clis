import datetime

from freezegun import freeze_time

from fiveclis import ui as ui_mod
from fiveclis.constants import BIRTHDAY_NAME, BURGER_RECIPES, CAKE_RECIPES
from fiveclis.ui import (
    CALENDAR_NAMES,
    CALENDARS,
    HOLI_RAINBOW,
    PRIDE_RAINBOW,
    SEASONAL_PALETTES,
    THEME_NAMES,
    THEMES,
    apply_seasonal_colour,
    generate_terminal_url_anchor,
    get_random_burger_recipe,
    get_random_cake_recipe,
    get_theme,
    has_shown_holiday_gift,
    is_birthday,
    is_christmas,
    mark_holiday_gift_shown,
    render_burger_recipe,
    render_cake_recipe,
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


# ── Easter eggs ────────────────────────────────────────────────────────────


def test_recipe_collections_share_a_shape():
    burger_fields = {
        "title",
        "style",
        "patty",
        "toppings",
        "cook",
        "tip",
        "source",
        "source_url",
    }
    for recipe in BURGER_RECIPES:
        assert burger_fields <= set(recipe)
    for recipe in CAKE_RECIPES:
        assert {"title", "style", "batter", "frosting", "bake", "tip"} <= set(recipe)


def test_random_recipes_come_from_the_collections():
    assert get_random_burger_recipe() in BURGER_RECIPES
    assert get_random_cake_recipe() in CAKE_RECIPES


def test_is_birthday_matches_the_configured_date():
    assert is_birthday(datetime.date(2026, 1, 8))
    assert not is_birthday(datetime.date(2026, 1, 9))


def test_is_birthday_is_always_false_when_disabled(monkeypatch):
    # A scaffolded CLI switches the surprise off by setting BIRTHDAY = None.
    monkeypatch.setattr(ui_mod, "BIRTHDAY", None)
    assert not is_birthday(datetime.date(2026, 1, 8))


def test_is_christmas():
    assert is_christmas(datetime.date(2026, 12, 25))
    assert not is_christmas(datetime.date(2026, 12, 24))


def test_render_burger_recipe_credits_its_source():
    rendered = render_burger_recipe(BURGER_RECIPES[0])
    assert BURGER_RECIPES[0]["title"] in rendered
    assert BURGER_RECIPES[0]["source"] in rendered
    assert "Secret Burger Recipe" in rendered


def test_render_burger_recipe_links_the_title():
    recipe = BURGER_RECIPES[0]
    rendered = render_burger_recipe(recipe)
    anchor = generate_terminal_url_anchor(recipe["source_url"], recipe["title"])
    assert anchor in rendered


def test_render_burger_recipe_without_colour_shows_the_url_instead():
    # OSC 8 has no business in output that may be piped or logged, so the
    # credit falls back to a plain URL in the Source row rather than vanishing.
    recipe = BURGER_RECIPES[0]
    rendered = render_burger_recipe(recipe, colour=False)
    assert "\033]8;;" not in rendered
    assert recipe["source_url"] in rendered


def test_terminal_url_anchor_wraps_the_text_not_the_url():
    anchor = generate_terminal_url_anchor("https://example.com", "Click me")
    assert anchor.startswith("\033]8;;https://example.com\033\\")
    assert "Click me" in anchor
    assert anchor.endswith("\033]8;;\033\\")


def test_render_burger_recipe_christmas_header():
    rendered = render_burger_recipe(BURGER_RECIPES[0], occasion="christmas")
    assert "Merry Christmas" in rendered
    assert "Secret Burger Recipe" not in rendered


def test_render_cake_recipe_birthday_header():
    rendered = render_cake_recipe(CAKE_RECIPES[0], occasion="birthday")
    assert "birthday" in rendered
    assert BIRTHDAY_NAME in rendered


def test_holiday_gift_state_round_trips(tmp_path):
    today = datetime.date(2026, 12, 25)
    assert not has_shown_holiday_gift("christmas", today, state_dir=tmp_path)
    mark_holiday_gift_shown("christmas", today, state_dir=tmp_path)
    assert has_shown_holiday_gift("christmas", today, state_dir=tmp_path)


def test_holiday_gift_state_expires_the_following_year(tmp_path):
    mark_holiday_gift_shown(
        "christmas", datetime.date(2026, 12, 25), state_dir=tmp_path
    )
    assert not has_shown_holiday_gift(
        "christmas", datetime.date(2027, 12, 25), state_dir=tmp_path
    )


def test_holiday_gift_state_events_are_independent(tmp_path):
    today = datetime.date(2026, 1, 8)
    mark_holiday_gift_shown("birthday", today, state_dir=tmp_path)
    assert not has_shown_holiday_gift("christmas", today, state_dir=tmp_path)


def test_corrupt_holiday_gift_state_shows_the_gift_again(tmp_path):
    # Showing a gift twice beats swallowing it for a whole year.
    (tmp_path / "birthday_gift.json").write_text("{not json")
    assert not has_shown_holiday_gift("birthday", datetime.date(2026, 1, 8), tmp_path)
