"""five-clis — a batteries-included Python CLI template.

Replace the ``greet`` command with your own business logic.
All infrastructure (themes, caching, update checks, shell completions,
config file, XDG dirs, logging) is already wired up.

Structure: ``main`` is a Click group. Its callback resolves global flags
against the config file once, into a single :class:`Settings` object stored
on ``ctx.obj``. Subcommands declare ``@click.pass_obj`` and receive that one
object — add new commands without threading individual option values
through every function signature.
"""

import os
import random
import shutil
import sys
import time
from enum import StrEnum, auto

import click

from .cache import parse_ttl
from .config import load_config, show_config, update_config, write_default_config
from .constants import (
    APP_ITEMS,
    APP_NAME,
    BINARY_NAME,
    DEFAULT_CACHE_TTL,
    ENVVAR_PREFIX,
)
from .logger import configure as configure_logging
from .settings import Settings
from .ui import (
    CALENDAR_NAMES,
    THEME_NAMES,
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
from .updater import UpdateStatus, check_for_update, perform_update

_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

# Subcommands that must run before, and independently of, config resolution.
_CONFIG_FREE_COMMANDS = frozenset({"completions", "update"})


def _env_flag_is_set(name: str) -> bool:
    """Report whether an environment variable is set to any non-empty value.

    This is the no-color.org convention: presence is the signal and the value
    is deliberately ignored, so ``FIVE_CLIS_NO_COLOUR=0`` disables colour just
    as ``=1`` does.

    Click's ``envvar=`` on a boolean flag cannot express this. It routes the
    value through the BOOL converter, so ``=false`` reads as "leave it on" —
    the opposite of the spec — and an unrecognised value aborts the run
    outright. A typo in a shell profile should be ignored, not fatal.
    """
    return bool(os.environ.get(name))


def _resolved(flag_value, cfg: dict, key: str, default):
    """Resolve an option: CLI flag beats config file beats *default*."""
    if flag_value is not None:
        return flag_value
    return cfg.get(key, default)


@click.group(context_settings=_CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(package_name=APP_NAME)
# ── Config ─────────────────────────────────────────────────────────────────
@click.option(
    "--config",
    "config_path",
    default=None,
    metavar="PATH",
    help="Path to a TOML config file.",
)
# ── Display ─────────────────────────────────────────────────────────────────
@click.option(
    "--theme",
    type=click.Choice(THEME_NAMES, case_sensitive=False),
    default=None,
    help=f"Colour theme. Choices: {', '.join(THEME_NAMES)}.",
)
@click.option(
    "--seasonal-colours/--no-seasonal-colours",
    default=None,
    help="Apply seasonal ANSI colours based on the current date.",
)
@click.option(
    "--seasonal-calendar",
    type=click.Choice(CALENDAR_NAMES, case_sensitive=False),
    default=None,
    help="Which cultural calendar drives seasonal colours (default: western).",
)
@click.option(
    "--no-colour",
    "no_colour",
    is_flag=True,
    default=False,
    # No envvar= here: Click would route FIVE_CLIS_NO_COLOUR through its BOOL
    # converter, so unrecognised values abort the run. Resolved by presence in
    # the callback instead — see _env_flag_is_set.
    help=(
        "Disable all ANSI colour output."
        f" Also honoured via {ENVVAR_PREFIX}_NO_COLOUR, set to any"
        " non-empty value."
    ),
)
# ── Caching ─────────────────────────────────────────────────────────────────
@click.option(
    "--cache/--no-cache",
    "cache_enabled",
    default=None,
    help="Enable disk caching of results (off by default).",
)
@click.option(
    "--cache-ttl",
    default=None,
    metavar="TTL",
    help="Cache TTL: seconds (300), or suffixed (5m, 2h). Default: 300.",
)
# ── Updates ─────────────────────────────────────────────────────────────────
@click.option(
    "--no-update-check",
    is_flag=True,
    default=False,
    # No envvar= here — see the note on --no-colour.
    help=(
        "Disable the automatic update check."
        f" Also honoured via {ENVVAR_PREFIX}_NO_UPDATE_CHECK, set to any"
        " non-empty value."
    ),
)
@click.option(
    "--update-summary/--no-update-summary",
    default=None,
    help="Include release highlights in the update notice.",
)
# ── Diagnostics ─────────────────────────────────────────────────────────────
@click.option(
    "--debug-summary/--no-debug-summary",
    default=None,
    help="Print a run summary (timing, work done) to stderr when finished.",
)
# ── Easter eggs ─────────────────────────────────────────────────────────────
@click.option(
    "--burger",
    is_flag=True,
    default=False,
    hidden=True,
    help="Secret burger recipe easter egg.",
)
@click.option(
    "--cake",
    is_flag=True,
    default=False,
    hidden=True,
    help="Secret cake recipe easter egg.",
)
@click.pass_context
def main(
    ctx,
    config_path,
    theme,
    seasonal_colours,
    seasonal_calendar,
    no_colour,
    cache_enabled,
    cache_ttl,
    no_update_check,
    update_summary,
    debug_summary,
    burger,
    cake,
):
    """🍔 five-clis — a batteries-included Python CLI template.

    A working 'hello world' that demonstrates themes, seasonal colours,
    caching, config files, shell completions, and auto-update checks.
    Replace the ``greet`` command with your own business logic.

    Running with no subcommand is equivalent to ``five-clis greet``.
    """
    # Before anything else, so the elapsed row covers config resolution too.
    started_at = time.monotonic()
    configure_logging()

    # Resolved by presence, not parsed: see _env_flag_is_set. Composed with
    # the flag, and for the update check with the config key below too, so any
    # one of them switching it off is enough and none can switch it back on.
    no_colour = no_colour or _env_flag_is_set(f"{ENVVAR_PREFIX}_NO_COLOUR")
    no_update_check = no_update_check or _env_flag_is_set(
        f"{ENVVAR_PREFIX}_NO_UPDATE_CHECK"
    )

    # completions and update must stay usable when the config file is broken.
    # The shell runs the completion script on every tab-press, so a config error
    # would spew into the user's prompt; and if a bad config could block update,
    # there would be no way to install the release that fixes it.
    if ctx.invoked_subcommand in _CONFIG_FREE_COMMANDS:
        return

    try:
        cfg = load_config(config_path)
        ttl = parse_ttl(_resolved(cache_ttl, cfg, "cache-ttl", DEFAULT_CACHE_TTL))
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    theme_name = _resolved(theme, cfg, "theme", "default")
    ctx.obj = Settings(
        cfg=cfg,
        config_path=config_path,
        theme_name=theme_name,
        theme=get_theme(theme_name),
        seasonal_colours=_resolved(seasonal_colours, cfg, "seasonal-colours", True),
        seasonal_calendar=_resolved(
            seasonal_calendar, cfg, "seasonal-calendar", "western"
        ),
        colour=not no_colour,
        cache_enabled=_resolved(cache_enabled, cfg, "cache", False),
        cache_ttl=ttl,
        update_check=not (no_update_check or cfg.get("no-update-check", False)),
        update_summary=_resolved(update_summary, cfg, "update-summary", False),
        debug_summary=_resolved(debug_summary, cfg, "debug-summary", False),
        burger=burger,
        cake=cake,
        started_at=started_at,
    )

    if ctx.invoked_subcommand is None:
        ctx.invoke(greet)


def _notify_update(settings: Settings) -> None:
    """Print an update notice to stderr if a newer release is available."""
    if not settings.update_check:
        return
    update_msg = check_for_update(show_summary=settings.update_summary)
    if update_msg:
        click.echo(
            click.style(update_msg, fg="cyan", bold=True),
            err=True,
            color=settings.colour,
        )


def _serve_easter_eggs(settings: Settings) -> None:
    """Print the recipe easter eggs, if today or the flags have earned one.

    The once-a-year gifts are gated on colour: they are pure decoration, so a
    user who asked for plain output should not have them appear unbidden.
    The explicit --burger/--cake flags are not gated — the user asked.
    All of it goes to stderr, so a piped stdout is never polluted.
    """
    if settings.colour and is_birthday() and not has_shown_holiday_gift("birthday"):
        recipe = get_random_cake_recipe()
        click.echo(
            render_cake_recipe(recipe, occasion="birthday", colour=settings.colour),
            err=True,
            color=settings.colour,
        )
        mark_holiday_gift_shown("birthday")
    elif settings.cake:
        click.echo(
            render_cake_recipe(get_random_cake_recipe(), colour=settings.colour),
            err=True,
            color=settings.colour,
        )

    if settings.colour and is_christmas() and not has_shown_holiday_gift("christmas"):
        recipe = get_random_burger_recipe()
        click.echo(
            render_burger_recipe(recipe, occasion="christmas", colour=settings.colour),
            err=True,
            color=settings.colour,
        )
        mark_holiday_gift_shown("christmas")
    elif settings.burger:
        click.echo(
            render_burger_recipe(get_random_burger_recipe(), colour=settings.colour),
            err=True,
            color=settings.colour,
        )


def _print_debug_summary(
    settings: Settings, item_count: int, extra: dict[str, str] | None = None
) -> None:
    """Print a run summary to stderr: timing, work done, and app-specific rows.

    *extra* is where a scaffolded CLI adds its own rows — request counts, rate
    limit headroom, bytes transferred. breakfast's equivalent is spelled
    ``--api-stats`` and fills this slot with REST and GraphQL counters; here
    the flag is named for what it prints, since a template has no API to count.
    """
    elapsed = time.monotonic() - settings.started_at
    rows = {
        "Total elapsed": f"{elapsed:.2f}s",
        "Items processed": str(item_count),
        "Cache": (
            f"enabled, ttl {settings.cache_ttl}s"
            if settings.cache_enabled
            else "disabled"
        ),
        **(extra or {}),
    }
    width = max(len(label) for label in rows)
    lines = [click.style("🐛 Debug summary", fg="cyan", bold=True)]
    lines += [f"  {label + ':':<{width + 1}} {value}" for label, value in rows.items()]
    click.echo("\n".join(lines), err=True, color=settings.colour)


def _finish_run(
    settings: Settings,
    item_count: int = 0,
    extra: dict[str, str] | None = None,
) -> None:
    """Run the end-of-invocation chores every command shares.

    Call this last from any command that produces user-facing output, so the
    notices land after the command's own output rather than interleaved.
    """
    _notify_update(settings)
    _serve_easter_eggs(settings)
    if settings.debug_summary:
        _print_debug_summary(settings, item_count, extra)


# ── Greeting (demo command — replace with your own) ─────────────────────────


@main.command()
@click.option(
    "--name",
    default=None,
    metavar="NAME",
    help="Name to greet. Defaults to the current user.",
)
@click.pass_obj
def greet(settings: Settings, name: str | None):
    """Greet someone (the demo business logic — replace with your own)."""
    spinner = random.choice(APP_ITEMS)
    click.echo(
        click.style(f"Cooking up your CLI... {spinner}", fg="cyan"),
        err=True,
        color=settings.colour,
    )

    if name is None:
        name = os.environ.get("USER", os.environ.get("USERNAME", "world"))
    click.echo(settings.paint(f"Hello, {name}! 🍔"))

    if settings.colour:
        click.echo(
            settings.theme.apply(f"  Theme: {settings.theme_name}", role="accent")
        )

    # Demonstrate rainbow cycling
    if settings.theme_name == "rainbow" and settings.colour:
        items = ["burgers", "shakes", "fries", "nuggets", "sodas"]
        for i, item in enumerate(items):
            click.echo(settings.theme.apply_cycle(f"  • {item}", i))

    # item_count and the extra rows are the demo's stand-in for whatever your
    # command actually did — swap them for real counters.
    _finish_run(settings, item_count=1, extra={"Greeted": name})


# ── Config management ───────────────────────────────────────────────────────


@main.group("config")
def config_group():
    """Manage the five-clis configuration file."""


@config_group.command("show")
@click.pass_obj
def config_show(settings: Settings):
    """Print the resolved configuration."""
    click.echo(show_config(settings.cfg, settings.config_path))


@config_group.command("init")
def config_init():
    """Write a default config file to the XDG config directory."""
    path = write_default_config()
    click.echo(f"✅ Default config written to: {path}")


@config_group.command("update")
@click.pass_obj
def config_update(settings: Settings):
    """Merge missing keys from the template into your config file (with backup)."""
    if not update_config(settings.config_path):
        raise SystemExit(1)


# ── Shell completions ───────────────────────────────────────────────────────


class Shell(StrEnum):
    """A shell that ``completions`` can emit a completion script for.

    ``StrEnum`` + ``auto()`` yields the lowercase member name as the value, so
    members pass straight into Click's completion machinery and into f-strings
    without a trail of ``.value``.
    """

    BASH = auto()
    ZSH = auto()
    FISH = auto()


# Click matches enum choices on member *names*, so click.Choice(Shell) would
# demand "BASH" rather than "bash" — pass the values explicitly instead.
_SHELL_CHOICES = [shell.value for shell in Shell]


@main.command()
@click.argument("shell", type=click.Choice(_SHELL_CHOICES))
def completions(shell: str):
    """Print the shell completion script for SHELL.

    Eval it in your shell config, e.g. ``eval "$(five-clis completions bash)"``.
    """
    from click.shell_completion import get_completion_class

    comp_cls = get_completion_class(Shell(shell))
    comp = comp_cls(
        cli=main,
        ctx_args={},
        prog_name=BINARY_NAME,
        complete_var=f"_{ENVVAR_PREFIX}_COMPLETE",
    )
    click.echo(comp.source(), nl=False)


# ── Self-update ─────────────────────────────────────────────────────────────


def _current_executable_path() -> str:
    """Resolve the absolute path of the running five-clis executable.

    ``sys.argv[0]`` is what the user actually invoked, so prefer it whenever it
    names a real file: ``./five-clis update`` must update *that* copy, not a
    different one that happens to sit earlier on PATH. Fall back to a PATH
    lookup for the usual case, where argv[0] is the bare console-script name.

    ``abspath`` rather than ``resolve`` so a symlinked install has its link
    replaced and not the file it points at, and so a relative argv[0] cannot
    send ``os.replace()`` to the current working directory.
    """
    invoked = sys.argv[0]
    if os.sep in invoked and os.path.isfile(invoked):
        return os.path.abspath(invoked)
    return os.path.abspath(shutil.which(BINARY_NAME) or invoked)


@main.command()
def update():
    """Download and install the latest five-clis release over this executable."""
    click.echo(
        click.style("🔍 Checking for a newer release...", fg="cyan"),
        err=True,
    )
    status, current, detail = perform_update(_current_executable_path())

    if status is UpdateStatus.UNKNOWN:
        raise click.ClickException("Could not reach GitHub to check for a new release.")
    if status is UpdateStatus.ERROR:
        raise click.ClickException(f"Update failed: {detail}")
    if status is UpdateStatus.UP_TO_DATE:
        click.echo(
            click.style(f"✅ Already up to date, v{current}.", fg="green"),
            err=True,
        )
        return

    click.echo(
        click.style(f"✅ five-clis has been updated to v{detail}.", fg="green"),
        err=True,
    )
    # The completion scripts re-invoke the binary, so they track it for free.
    # The man page is a static file and may sit somewhere needing privileges,
    # so point at the installer rather than trying to rewrite it here.
    click.echo(
        click.style(
            "   Re-run install.sh if you also want a refreshed man page.", fg="cyan"
        ),
        err=True,
    )
