# Options Reference

`five-clis` is a command group. The options below are **global**: they go
before the subcommand (`five-clis --theme rainbow greet`), are resolved once
against the config file, and are shared with every subcommand through a single
settings object — so new commands never need their own copies of these flags.

## Commands

### `greet [--name NAME]`

The demo business command (also the default when no subcommand is given).
Replace it with your own logic.

### `config show`

Print the resolved configuration.

### `config init`

Write a default config file to `~/.config/fiveclis/config.toml`.

### `config update`

Merge any options missing from your existing config file in from the
template, writing a timestamped backup first. Useful after upgrading to a
release that introduces new config keys.

### `completion [bash|zsh|fish]`

Print the shell completion script. Eval in your shell config:

```bash
eval "$(five-clis completion bash)"
```

## Display options

### `--theme`

Set the terminal colour theme. Choices: `default`, `dark`, `light`, `mono`, `rainbow`.

```bash
five-clis --theme rainbow
five-clis --theme mono      # no colour
```

Config key: `theme = "default"`

### `--seasonal-colours` / `--no-seasonal-colours`

Apply seasonal ANSI colours based on the current date (enabled by default).
The colour scheme changes automatically for holidays and cultural events.

Config key: `seasonal-colours = true`

### `--seasonal-calendar`

Choose which cultural calendar drives seasonal colours.

| Value | Calendar |
| ----- | -------- |
| `western` | Gregorian holidays (Christmas, Easter, Pride Month, Halloween) |
| `jewish` | Hanukkah, Passover, Rosh Hashanah, Sukkot |
| `islamic` | Eid al-Fitr, Eid al-Adha |
| `hindu` | Diwali, Holi |
| `sikh` | Vaisakhi, Bandi Chhor Divas |
| `east-asian` | Lunar New Year, Mid-Autumn, Songkran, Hanami |

Config key: `seasonal-calendar = "western"`

### `--no-colour`

Disable all ANSI colour output. Also honoured via `FIVE_CLIS_NO_COLOUR=1`.

## Config options

### `--config PATH`

Path to a TOML config file. Overrides the XDG default search paths.
It is an error if the file does not exist.

## Caching

### `--cache` / `--no-cache`

Enable disk caching of results (off by default).

Config key: `cache = false`

### `--cache-ttl`

How long to cache results. Accepts seconds (`300`), or suffixed strings (`5m`, `2h`). Default: 300s.

Config key: `cache-ttl = "300"`

## Other

### `--no-update-check`

Disable the automatic update check. Also honoured via `FIVE_CLIS_NO_UPDATE_CHECK=1`.

Config key: `no-update-check = false`

### `--version`

Show the installed version and exit.
