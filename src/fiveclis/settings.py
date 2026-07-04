"""Resolved runtime settings shared across commands.

The CLI group callback builds one :class:`Settings` from flags + config file
and stores it on ``ctx.obj``; subcommands receive it via ``@click.pass_obj``.
Business modules can accept a ``Settings`` instead of a pile of loose
parameters.
"""

from dataclasses import dataclass, field

from .ui import Theme, apply_seasonal_colour


@dataclass
class Settings:
    """Runtime settings resolved from CLI flags, config file, and defaults."""

    cfg: dict = field(default_factory=dict)
    config_path: str | None = None
    theme_name: str = "default"
    theme: Theme = field(default_factory=Theme)
    seasonal_colours: bool = True
    seasonal_calendar: str = "western"
    colour: bool = True
    cache_enabled: bool = False
    cache_ttl: int = 300
    update_check: bool = True

    def paint(self, text: str, *, index: int = 0, role: str = "primary") -> str:
        """Colour *text* per the resolved colour/seasonal/theme settings.

        Seasonal colours win over the theme when enabled; ``--no-colour``
        disables both. *index* drives cycling palettes (Pride, Holi, …).
        """
        if not self.colour:
            return text
        if self.seasonal_colours:
            return apply_seasonal_colour(text, index, calendar=self.seasonal_calendar)
        return self.theme.apply(text, role=role)
