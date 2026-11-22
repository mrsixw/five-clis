"""Tables: tabulate's drawing, in the theme's colours, fitted to the terminal.

Every table the CLI prints goes through :func:`render_table`, so the
``--table-style`` choice, the colours and the clipping are the same for each.
The ``menu`` demo command shows it in use.
"""

import shutil

import click
from tabulate import tabulate
from wcwidth import wcswidth

from .settings import Settings

__all__ = ["render_table"]

#: What shutil assumes when stdout is not a terminal (a pipe, a test runner).
_FALLBACK_TERMINAL_SIZE = (120, 24)
#: The narrowest a shrunk column gets, so titles stay readable in a tiny window.
_MIN_SHRINK_WIDTH = 20
#: Cells taken by the "…" that marks a clipped cell.
_ELLIPSIS_WIDTH = 1
#: breakfast numbers its rows; every app built from this template does too.
_SHOW_INDEX = True


def _clip(text: str, width: int) -> str:
    """Clip *text* to *width* terminal cells, ending in an ellipsis if cut."""
    if wcswidth(text) <= width:
        return text
    clipped = ""
    for char in text:
        if wcswidth(clipped + char) > width - _ELLIPSIS_WIDTH:
            break
        clipped += char
    return clipped + "…"


def _is_rule(line: str) -> bool:
    """Report whether *line* is a table border rather than a header or row.

    Every header and row holds at least one letter or digit (a ticket ref, a
    source name); borders are punctuation and box-drawing characters only.
    This holds for every style in TABLE_STYLES without knowing its layout.
    """
    return not any(char.isalnum() for char in line)


def _paint_table(settings: Settings, table: str) -> str:
    """Colour a rendered table: muted borders, a bold accent header, and
    rows in the primary colour (cycling, for themes and seasons that cycle).
    """
    if not settings.colour:
        return table
    lines = []
    header_done = False
    row = 0
    for line in table.splitlines():
        if _is_rule(line):
            lines.append(settings.theme.apply(line, role="muted"))
        elif not header_done:
            header_done = True
            lines.append(click.style(settings.paint(line, role="accent"), bold=True))
        else:
            lines.append(settings.paint(line, index=row))
            row += 1
    return "\n".join(lines)


def render_table(
    settings: Settings,
    headers: list[str],
    rows: list[list[str]],
    *,
    shrink: int | None = None,
) -> str:
    """Draw *rows* in the configured table style, coloured per the theme.

    tabulate does the drawing: ``settings.table_style`` is passed straight
    through as ``tablefmt``. This adds the two things tabulate lacks:

    - **Colour.** Each drawn line is painted afterwards: muted borders, a bold
      accent header, and rows in the theme's colour (cycling, when it cycles).
    - **Fitting the terminal.** *shrink* names the column to clip, with "…",
      when the table is wider than the terminal. The drawn table is measured
      and the overflow taken out of that column, which avoids depending on how
      each style pads its cells. The column never shrinks below
      ``_MIN_SHRINK_WIDTH``, so in a very narrow terminal the table can still
      be too wide and the terminal wraps it. tabulate's own ``maxcolwidths``
      wraps the cell instead, in every style on offer, which would spread
      one row over several lines.
    """
    columns = shutil.get_terminal_size(_FALLBACK_TERMINAL_SIZE).columns

    def draw(body: list[list[str]]) -> str:
        return tabulate(
            body,
            headers=headers,
            tablefmt=settings.table_style,
            showindex=_SHOW_INDEX,
            disable_numparse=True,
        )

    # tabulate strips each cell, so measure and clip the text it will draw.
    rows = [[str(cell).strip() for cell in row] for row in rows]
    table = draw(rows)
    if shrink is not None and rows:
        width = max(wcswidth(line) for line in table.splitlines())
        overflow = width - columns
        if overflow > 0:
            longest = max(wcswidth(row[shrink]) for row in rows)
            budget = max(_MIN_SHRINK_WIDTH, longest - overflow)
            clipped = [
                [*row[:shrink], _clip(row[shrink], budget), *row[shrink + 1 :]]
                for row in rows
            ]
            table = draw(clipped)
    return _paint_table(settings, table)
