"""Terminal colour, theming, and formatting utilities.

Ported from the breakfast project and extended with an explicit theme registry.
Two complementary systems:
  - Seasonal/cultural calendar colours (automatic, date-driven)
  - Explicit ``--theme`` override (user-controlled, persistent)
"""

import datetime
import math
from dataclasses import dataclass, field
from datetime import date as _real_date
from datetime import timedelta as _real_timedelta

import click

from .constants import (
    _DIWALI,
    _EID_AL_ADHA,
    _EID_AL_FITR,
    _HANUKKAH_START,
    _HOLI,
    _MID_AUTUMN,
    _PASSOVER_START,
    _ROSH_HASHANAH,
    _SUKKOT_START,
    HOLI_RAINBOW,
    PRIDE_RAINBOW,
    SEASONAL_PALETTES,
)

_RESET = "\033[0m"


# ---------------------------------------------------------------------------
# Explicit theme registry
# ---------------------------------------------------------------------------


@dataclass
class Theme:
    """A named terminal colour theme."""

    primary: str | None = "cyan"
    accent: str | None = "yellow"
    success: str | None = "green"
    warn: str | None = "yellow"
    error: str | None = "red"
    muted: str | None = None
    cycle: list[str] = field(default_factory=list)

    def apply(self, text: str, role: str = "primary") -> str:
        """Apply this theme's colour for *role* to *text* using click.style."""
        colour = getattr(self, role, self.primary)
        if colour is None:
            return text
        return click.style(text, fg=colour)

    def apply_cycle(self, text: str, index: int) -> str:
        """Apply a cycling colour from this theme's ``cycle`` list."""
        if not self.cycle:
            return self.apply(text)
        ansi = self.cycle[index % len(self.cycle)]
        return f"{ansi}{text}{_RESET}"


THEMES: dict[str, Theme] = {
    "default": Theme(
        primary="cyan",
        accent="yellow",
        success="green",
        warn="yellow",
        error="red",
        muted=None,
        cycle=[],
    ),
    "dark": Theme(
        primary="bright_blue",
        accent="bright_magenta",
        success="bright_green",
        warn="bright_yellow",
        error="bright_red",
        muted=None,
        cycle=[],
    ),
    "light": Theme(
        primary="blue",
        accent="green",
        success="green",
        warn="yellow",
        error="red",
        muted=None,
        cycle=[],
    ),
    "mono": Theme(
        primary=None,
        accent=None,
        success=None,
        warn=None,
        error=None,
        muted=None,
        cycle=[],
    ),
    "rainbow": Theme(
        primary="cyan",
        accent="yellow",
        success="green",
        warn="yellow",
        error="red",
        muted=None,
        cycle=PRIDE_RAINBOW,
    ),
}

THEME_NAMES = list(THEMES.keys())


def get_theme(name: str) -> Theme:
    """Return the named theme, falling back to ``"default"`` for unknown names."""
    return THEMES.get(name, THEMES["default"])


# ---------------------------------------------------------------------------
# Astronomical helpers for the seasonal calendar system
# ---------------------------------------------------------------------------


def _easter_month(year: int) -> int:
    """Return 3 (March) or 4 (April): the month Easter falls in for *year*.

    Uses the Anonymous Gregorian algorithm (Meeus/Jones/Butcher).
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    return (h + ll - 7 * m + 114) // 31


def _new_moon_jde(k: float) -> float:
    """Julian Ephemeris Day of new moon k (Meeus, Astronomical Algorithms, ch. 49)."""
    T = k / 1236.85
    jde = (
        2451550.09766
        + 29.530588861 * k
        + 0.00015437 * T**2
        - 0.000000150 * T**3
        + 0.00000000073 * T**4
    )
    M = math.radians(2.5534 + 29.10535670 * k - 0.0000014 * T**2)
    Mp = math.radians(
        201.5643 + 385.81693528 * k + 0.0107582 * T**2 + 0.00001238 * T**3
    )
    F = math.radians(160.7108 + 390.67050284 * k - 0.0016118 * T**2 - 0.00000227 * T**3)
    Om = math.radians(124.7746 - 1.56375588 * k + 0.0020672 * T**2)
    E = 1 - 0.002516 * T - 0.0000074 * T**2
    corr = (
        -0.40720 * math.sin(Mp)
        + 0.17241 * E * math.sin(M)
        + 0.01608 * math.sin(2 * Mp)
        + 0.01039 * math.sin(2 * F)
        + 0.00739 * E * math.sin(Mp - M)
        - 0.00514 * E * math.sin(Mp + M)
        + 0.00208 * E**2 * math.sin(2 * M)
        - 0.00111 * math.sin(Mp - 2 * F)
        - 0.00057 * math.sin(Mp + 2 * F)
        + 0.00056 * E * math.sin(2 * Mp + M)
        - 0.00042 * math.sin(3 * Mp)
        + 0.00042 * E * math.sin(M + 2 * F)
        + 0.00038 * E * math.sin(M - 2 * F)
        - 0.00024 * E * math.sin(2 * Mp - M)
        - 0.00017 * math.sin(Om)
    )
    return jde + corr


def _jde_to_date_cst(jde: float) -> tuple[int, int, int]:
    """Convert a Julian Ephemeris Day to Gregorian (year, month, day) in CST (UTC+8)."""
    jd = jde + 8.0 / 24.0
    Z = int(jd + 0.5)
    alpha = int((Z - 1867216.25) / 36524.25)
    A = Z + 1 + alpha - alpha // 4
    B = A + 1524
    C = int((B - 122.1) / 365.25)
    D = int(365.25 * C)
    E_val = int((B - D) / 30.6001)
    day = B - D - int(30.6001 * E_val)
    month = E_val - 1 if E_val < 14 else E_val - 13
    year = C - 4716 if month > 2 else C - 4715
    return year, month, day


def _lny_date(year: int) -> tuple[int, int]:
    """Return (month, day) of Lunar New Year for *year* in Chinese Standard Time."""
    k_approx = round((year - 2000) * 12.3685)
    for dk in range(-2, 4):
        jde = _new_moon_jde(k_approx + dk)
        y, m, d = _jde_to_date_cst(jde)
        if y == year and ((m == 1 and d >= 21) or (m == 2 and d <= 20)):
            return m, d
    raise ValueError(f"Could not calculate Lunar New Year for {year}")


# ---------------------------------------------------------------------------
# Seasonal calendar functions
# ---------------------------------------------------------------------------


def _in_holiday_window(
    today: datetime.date,
    table: dict[int, tuple[int, int]],
    days: int = 1,
) -> bool:
    """Return True if *today* falls within *days* days of the holiday in *table*."""
    entry = table.get(today.year)
    if entry is None:
        return False
    try:
        start = _real_date(today.year, entry[0], entry[1])
        return start <= today < start + _real_timedelta(days=days)
    except ValueError:
        return False


def _east_asian_calendar(today: datetime.date) -> "str | list[str] | None":
    if today.month == 4 and 13 <= today.day <= 15:
        return SEASONAL_PALETTES["blue"]
    if today.month == 4 and 1 <= today.day <= 7:
        return SEASONAL_PALETTES["pink"]
    try:
        lny_m, lny_d = _lny_date(today.year)
        lny_start = _real_date(today.year, lny_m, lny_d)
        if lny_start <= today < lny_start + _real_timedelta(days=3):
            return SEASONAL_PALETTES["lny"]
    except ValueError:
        pass
    if _in_holiday_window(today, _MID_AUTUMN, days=2):
        return SEASONAL_PALETTES["yellow"]
    return None


def _hindu_calendar(today: datetime.date) -> "str | list[str] | None":
    if _in_holiday_window(today, _DIWALI, days=5):
        return SEASONAL_PALETTES["gold"]
    if _in_holiday_window(today, _HOLI, days=2):
        return HOLI_RAINBOW
    return None


def _islamic_calendar(today: datetime.date) -> "str | list[str] | None":
    if _in_holiday_window(today, _EID_AL_FITR, days=3):
        return SEASONAL_PALETTES["green"]
    if _in_holiday_window(today, _EID_AL_ADHA, days=3):
        return SEASONAL_PALETTES["green"]
    return None


def _jewish_calendar(today: datetime.date) -> "str | list[str] | None":
    if _in_holiday_window(today, _HANUKKAH_START, days=8):
        return SEASONAL_PALETTES["blue"]
    if _in_holiday_window(today, _ROSH_HASHANAH, days=2):
        return SEASONAL_PALETTES["gold"]
    if _in_holiday_window(today, _PASSOVER_START, days=7):
        return SEASONAL_PALETTES["spring_green"]
    if _in_holiday_window(today, _SUKKOT_START, days=7):
        return SEASONAL_PALETTES["orange"]
    return None


def _sikh_calendar(today: datetime.date) -> "str | list[str] | None":
    if today.month == 4 and today.day == 13:
        return SEASONAL_PALETTES["spring_green"]
    if _in_holiday_window(today, _DIWALI, days=5):
        return SEASONAL_PALETTES["gold"]
    return None


def _western_calendar(today: datetime.date) -> "str | list[str] | None":
    """Return seasonal colour(s) for the western/Gregorian calendar."""
    month = today.month
    day = today.day

    if month == 1:
        return SEASONAL_PALETTES["purple"]
    if month == 12:
        return [SEASONAL_PALETTES["red"], SEASONAL_PALETTES["green"]]
    if month == 6:
        return PRIDE_RAINBOW
    if month == 2 and day == 14:
        return SEASONAL_PALETTES["pink"]
    if month == 2:
        try:
            if _lny_date(today.year) == (month, day):
                return SEASONAL_PALETTES["lny"]
        except ValueError:
            pass
    if month == _easter_month(today.year):
        return SEASONAL_PALETTES["yellow"]
    if month == 10:
        return SEASONAL_PALETTES["orange"]
    return None


CALENDARS: dict[str, object] = {
    "east-asian": _east_asian_calendar,
    "hindu": _hindu_calendar,
    "islamic": _islamic_calendar,
    "jewish": _jewish_calendar,
    "sikh": _sikh_calendar,
    "western": _western_calendar,
}

CALENDAR_NAMES = ["western", "jewish", "islamic", "hindu", "sikh", "east-asian"]


def apply_seasonal_colour(text: str, index: int, calendar: str = "western") -> str:
    """Wrap *text* in a seasonal ANSI colour based on the current date.

    Lists (December candy-cane, June Pride, Holi rainbow) cycle by *index*.
    Pass ``calendar="off"`` to disable entirely.
    """
    if calendar == "off":
        return text
    calendar_fn = CALENDARS.get(calendar)
    if calendar_fn is None:
        return text
    today = datetime.date.today()
    result = calendar_fn(today)
    if result is None:
        return text
    if isinstance(result, list):
        colour = result[index % len(result)]
    else:
        colour = result
    return f"{colour}{text}{_RESET}"


# ---------------------------------------------------------------------------
# Generic formatting helpers
# ---------------------------------------------------------------------------


def colour_grade_number(num: int | float) -> str:
    """Return *num* as a click-styled string graded green/yellow/orange/red."""
    colour: str | int = "red"
    if num < 10:
        colour = "green"
    elif num < 20:
        colour = "yellow"
    elif num < 50:
        colour = 208  # orange (256-colour)
    return click.style(str(num), fg=colour, bold=True)


def echo_err(msg: str, colour: bool = True, fg: str = "yellow") -> None:
    """Print *msg* to stderr with optional click styling."""
    click.echo(click.style(msg, fg=fg), err=True, color=colour)
