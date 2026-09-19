# Troubleshooting

## No colour output

If you see no colours, check:

- Are you using `--no-colour` or `FIVE_CLIS_NO_COLOUR=1`?
- Does your terminal support ANSI colours?
- Try `--theme default` explicitly.

## Seasonal colours not showing

- Seasonal colours only appear on themed dates. Check today's date and the calendar you're using.
- Try `--seasonal-calendar western` to use the default calendar.
- Pass `--no-seasonal-colours` to disable entirely.

## Config file not found

Run `five-clis config init` to create a default config at `~/.config/fiveclis/config.toml`.

Use `five-clis config show` to see which config file is being used and what keys are set.

## Update check fails silently

The update check is non-fatal. If it fails (no network, GitHub rate limit),
five-clis continues normally. Pass `--no-update-check` to skip it entirely.

## Command not found after install

Add `~/.local/bin` to your PATH:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
```

## `Another five-clis shadows this install`

The installer put the binary in `~/.local/bin`, but a different copy sits earlier in your `PATH` and wins every invocation. The installer names both paths and exits non-zero rather than reporting a success you cannot use.

This is the usual cause of two otherwise baffling symptoms:

- `five-clis completions bash` fails with `No such command 'completions'` — the shadowing copy predates the subcommand.
- `five-clis update` appears to do nothing, because it updates a copy you never actually run.

Confirm which binary you are running, then remove the rogue copy:

```bash
command -v five-clis        # the one that actually runs
rm "$(command -v five-clis)"
```

Re-run `install.sh` afterwards to confirm the warning is gone. If you would rather keep the other copy, reorder `PATH` so `~/.local/bin` comes first instead.
