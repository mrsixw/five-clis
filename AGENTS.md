# Agent Instructions

## Project Overview
- **five-clis** is a batteries-included Python CLI template.
- Built with Python and Click. Infrastructure: themes, seasonal colours, caching, config files, XDG dirs, shell completions, auto-update checks, CI, release pipeline.
- Package: `src/fiveclis/`. Tests: `tests/`. Package manager: **uv**.

## Common Commands
- `make test` — run tests
- `make bats` — run the shell script tests (`npx --yes bats tests/bats`)
- `make lint` — check linting and formatting (includes `shellcheck` and `spell`)
- `make shellcheck` — static analysis for every shell source
- `make spell` — spell check, the same `typos` version CI runs
- `make format` — auto-fix lint and formatting

## Testing the shell scripts
- `tests/bats/` covers `install.sh` and everything in `utils/`. Each test runs the real script as a subprocess with `gh`, `git`, `curl`, `tar` and `install` stubbed on `PATH` and `HOME` redirected into a temporary directory. Offline, and safe to run anywhere.
- **If it fakes any part of the system under test, it is a unit test** — these stubs qualify, which is why the suite lives in `tests/`.
- The helper reads `BINARY_NAME` from `constants.py`, so a CLI generated from this template inherits the suite working. Adapt the assertions in `install.bats` to your installer's messages; leave `helpers/common.bash` alone.
- Stubs record their arguments: assert *what the script asked for*, not only what it printed. `assert_called_arg` matches a whole argument, so a quoting bug cannot hide behind a flattened command line.

## Commit Messages
- Use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:`).

## Code Quality
- **Before every commit:** `make format && make lint && make test`
- stdout for data; stderr for progress/warnings/errors
- No bare `except Exception`
