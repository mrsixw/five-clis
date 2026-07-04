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

import click

from .cache import parse_ttl
from .config import load_config, show_config, write_default_config
from .logger import configure as configure_logging
from .settings import Settings
from .ui import APP_ITEMS, CALENDAR_NAMES, THEME_NAMES, get_theme
from .updater import check_for_update

_ENVVAR_PREFIX = "FIVE_CLIS"
_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
_DEFAULT_CACHE_TTL = 300


def _resolved(flag_value, cfg: dict, key: str, default):
    """Resolve an option: CLI flag beats config file beats *default*."""
    if flag_value is not None:
        return flag_value
    return cfg.get(key, default)


@click.group(context_settings=_CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(package_name="fiveclis")
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
    envvar=f"{_ENVVAR_PREFIX}_NO_COLOUR",
    help="Disable all ANSI colour output.",
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
    envvar=f"{_ENVVAR_PREFIX}_NO_UPDATE_CHECK",
    help="Disable the automatic update check.",
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
):
    """🍔 five-clis — a batteries-included Python CLI template.

    A working 'hello world' that demonstrates themes, seasonal colours,
    caching, config files, shell completions, and auto-update checks.
    Replace the ``greet`` command with your own business logic.

    Running with no subcommand is equivalent to ``five-clis greet``.
    """
    configure_logging()

    try:
        cfg = load_config(config_path)
        ttl = parse_ttl(_resolved(cache_ttl, cfg, "cache-ttl", _DEFAULT_CACHE_TTL))
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
    )

    if ctx.invoked_subcommand is None:
        ctx.invoke(greet)


def _notify_update(settings: Settings) -> None:
    """Print an update notice to stderr if a newer release is available."""
    if not settings.update_check:
        return
    update_msg = check_for_update()
    if update_msg:
        click.echo(
            click.style(update_msg, fg="cyan", bold=True),
            err=True,
            color=settings.colour,
        )


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

    _notify_update(settings)


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


# ── Shell completions ───────────────────────────────────────────────────────


@main.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell: str):
    """Print the shell completion script for SHELL.

    Eval it in your shell config, e.g. ``eval "$(five-clis completion bash)"``.
    """
    from click.shell_completion import get_completion_class

    comp_cls = get_completion_class(shell)
    comp = comp_cls(
        cli=main,
        ctx_args={},
        prog_name="five-clis",
        complete_var="_FIVE_CLIS_COMPLETE",
    )
    click.echo(comp.source(), nl=False)
