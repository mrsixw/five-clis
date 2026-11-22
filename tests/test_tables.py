"""Tables, driven through the ``menu`` demo command.

``menu`` is the template's one table, so these tests cover what every app
built from it inherits: the default style, ``--table-style`` and its config
key, colour, and clipping to the terminal.
"""

import pytest
from click.testing import CliRunner
from wcwidth import wcswidth

from fiveclis.cli import main
from fiveclis.constants import DEFAULT_TABLE_STYLE, MENU, TABLE_STYLES

#: ANSI codes the default theme uses, as click.style writes them.
YELLOW = "\x1b[33m"
CYAN = "\x1b[36m"
BOLD = "\x1b[1m"


@pytest.fixture
def run(tmp_path, monkeypatch):
    """Invoke the CLI quietly, with an optional config file."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    def invoke(*args, config=None, color=False):
        prefix = ["--no-update-check"]
        if config is not None:
            cfg = tmp_path / "config.toml"
            cfg.write_text(config)
            prefix += ["--config", str(cfg)]
        return CliRunner().invoke(main, [*prefix, *args], color=color)

    return invoke


def cells(line):
    """Split one outline-table row into its stripped cell texts."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def test_menu_draws_an_outline_table_by_default(run):
    result = run("--no-colour", "menu")
    assert result.exit_code == 0, result.output
    lines = result.stdout.splitlines()
    assert DEFAULT_TABLE_STYLE == "outline"
    assert lines[0].startswith("+-") and lines[2].startswith("+=")
    assert lines[-1].startswith("+-")
    header, *rows = [cells(line) for line in lines if line.startswith("|")]
    assert header == ["", "ITEM", "DESCRIPTION"]
    assert [row[:2] for row in rows] == [
        [str(index), item] for index, (item, _) in enumerate(MENU)
    ]


@pytest.mark.parametrize("style", TABLE_STYLES)
def test_every_table_style_lists_every_item(run, style):
    result = run("--no-colour", "--table-style", style, "menu")
    assert result.exit_code == 0, result.output
    for item, _ in MENU:
        assert item in result.stdout


def test_table_style_comes_from_the_config_file(run):
    result = run("--no-colour", "menu", config='table-style = "plain"\n')
    assert result.exit_code == 0, result.output
    assert "+-" not in result.stdout and "|" not in result.stdout


def test_the_flag_beats_the_config_file(run):
    result = run(
        "--no-colour", "--table-style", "grid", "menu", config='table-style = "plain"\n'
    )
    assert result.stdout.startswith("+-")


def test_a_bad_table_style_in_config_names_the_choices(run):
    result = run("menu", config='table-style = "fancy"\n')
    assert result.exit_code != 0
    assert "Invalid table-style 'fancy' in config." in result.output
    assert ", ".join(TABLE_STYLES) in result.output


def test_a_bad_table_style_flag_is_refused_by_click(run):
    result = run("--table-style", "fancy", "menu")
    assert result.exit_code != 0
    assert "fancy" in result.output


@pytest.mark.parametrize("style", TABLE_STYLES)
def test_descriptions_are_clipped_to_fit_the_terminal(run, monkeypatch, style):
    width = 60
    monkeypatch.setenv("COLUMNS", str(width))
    result = run("--no-colour", "--table-style", style, "menu")
    lines = result.stdout.splitlines()
    assert max(wcswidth(line) for line in lines) <= width
    assert "…" in result.stdout


def test_nothing_is_clipped_when_the_terminal_is_wide_enough(run, monkeypatch):
    monkeypatch.setenv("COLUMNS", "200")
    result = run("--no-colour", "menu")
    assert "…" not in result.stdout
    for _, description in MENU:
        assert description in result.stdout


def test_the_table_wears_the_theme(run, monkeypatch):
    """A bold accent header and primary-coloured rows; borders stay plain,
    since the default theme sets no muted colour."""
    monkeypatch.delenv("FIVE_CLIS_NO_COLOUR", raising=False)
    result = run("--no-seasonal-colours", "menu", color=True)
    assert result.exit_code == 0, result.output
    top, header, rule, *rows, bottom = result.stdout.splitlines()
    assert BOLD in header and YELLOW in header
    assert all(row.startswith(CYAN) for row in rows)
    for border in (top, rule, bottom):
        assert "\x1b[" not in border


def test_no_colour_draws_no_escape_codes(run):
    result = run("--no-colour", "menu", color=True)
    assert "\x1b[" not in result.stdout
