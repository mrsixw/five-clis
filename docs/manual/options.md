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

### `completions [bash|zsh|fish]`

Print the shell completion script. Eval in your shell config:

```bash
eval "$(five-clis completions bash)"
```

### `update`

Download the latest release and replace the running executable with it.

```bash
five-clis update
```

The replacement is atomic, so an interrupted download leaves the working
binary in place. Nothing is written unless a newer release actually exists.

The man page is not refreshed — re-run `install.sh` for that. Completion
scripts need no refresh: they call back into the binary, so they follow it
automatically.

Not to be confused with `config update`, which merges new keys into your
config file, or `--no-update-check`, which silences the passive notice.

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
| `rainbow` | The Pride cycle every day of the year, not just in June |
| `off` | No seasonal colours; the `--theme` colours apply instead |

`rainbow` and `off` are the two values that ignore the date. `off` is
equivalent to `--no-seasonal-colours`.

```bash
five-clis --seasonal-calendar rainbow
five-clis --seasonal-calendar off
```

Config key: `seasonal-calendar = "western"`

### `--no-colour`

Disable all ANSI colour output. Also honoured via the `FIVE_CLIS_NO_COLOUR`
environment variable, set to any non-empty value.

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

### `--no-update-check`

Disable the automatic update check. Also honoured via the
`FIVE_CLIS_NO_UPDATE_CHECK` environment variable, set to any non-empty value.

Config key: `no-update-check = false`

Any one of the flag, the environment variable, or the config key switching the
check off is enough; none of them can switch it back on.

### Environment variable semantics

Both `FIVE_CLIS_NO_COLOUR` and `FIVE_CLIS_NO_UPDATE_CHECK` are resolved by
**presence**, following the [no-color.org](https://no-color.org) convention:
any non-empty value switches the behaviour off, and only unset or empty leaves
it on. The value is never parsed, so `=0` and `=false` still disable — and a
stray `FIVE_CLIS_NO_COLOUR=maybe` in a shell profile is harmless rather than
fatal.

### `--update-summary` / `--no-update-summary`

Append a short summary of the release highlights to the update notice — the
first few bullet points of the GitHub release body, with headers and bare
URLs stripped, truncated to 200 characters:

```text
🍟 A fresh order is ready! v1.0.2 → v1.0.3 — update at https://github.com/…
  📋 - Added the doctor command - Fixed cache expiry on 32-bit systems
```

Off by default, and has no effect alongside `--no-update-check`. The body is
read from the same 24-hour cache as the version check, so turning this on
costs no extra network round trip.

Config key: `update-summary = false`

## Diagnostics

### `--debug-summary` / `--no-debug-summary`

Print a run summary to stderr once the command finishes — elapsed time, how
much work was done, cache state, and whatever rows the command itself adds:

```text
🐛 Debug summary
  Total elapsed:   0.04s
  Items processed: 1
  Cache:           enabled, ttl 7200s
  Greeted:         Steve
```

The last row comes from the `greet` command rather than the framework. Commands
pass their own rows through `_finish_run(settings, item_count=..., extra=...)`,
which is where a scaffolded CLI adds request counts, rate-limit headroom, or
bytes transferred.

Config key: `debug-summary = false`

## Other

### `--version`

Show the installed version and exit.
