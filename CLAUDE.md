# Claude Instructions

## Project Overview
- **five-clis** is a batteries-included Python CLI template (named after Five Guys: burgers, shakes & fries → five CLI essentials).
- Built with Python and Click. Full infrastructure: themes, seasonal colours, caching, config files, XDG dirs, shell completions, auto-update checks, CI, release pipeline.
- Package structure: code in `src/fiveclis/`, tests in `tests/`.
- Use this as a GitHub template to scaffold new CLI apps.

## Project Structure
- `src/fiveclis/` — package source code
  - `cli.py` — Click group entrypoint; subcommands share one `Settings` via `ctx.obj` (replace `greet` with your own commands)
  - `settings.py` — `Settings` dataclass resolved from flags + config file, received by subcommands via `@click.pass_obj`
  - `ui.py` — Terminal themes, seasonal colour system (SEASONAL_PALETTES, PRIDE_RAINBOW, HOLI_RAINBOW, THEMES registry)
  - `config.py` — TOML configuration loader
  - `cache.py` — Generic TTL disk cache
  - `updater.py` — GitHub release update checker
  - `logger.py` — File logging setup
  - `xdg.py` — XDG base directory support
- `tests/` — pytest suite mirroring src modules
- `pyproject.toml` — project metadata, dependencies, tool config
- `VERSION` — static file containing the current version string
- `Makefile` — build, test, lint, format targets
- `utils/` — helper scripts for release management

## Environment
- Python >= 3.11
- Package manager: **uv** (not pip). Use `uv sync`, `uv run`, etc.

## Common Commands
- `make test` — run tests (`uv run pytest -v`)
- `make lint` — check linting and formatting
- `make format` — auto-fix lint and formatting
- `make build` — build a shiv executable
- `make e2e` — build, then run the end-to-end suite against the built binary

## Testing
- Two layers. **If it fakes any part of the system under test, it is a unit test** (`monkeypatch`, `requests-mock`, `freezegun`, `CliRunner`) and belongs in `tests/`. End-to-end tests in `tests/e2e/` drive the **built binary as a subprocess** and fake nothing — `make e2e`.
- Add an e2e scenario only for what the real binary alone can prove: exit codes, stdout-versus-stderr, packaging, files on disk. Everything else belongs in `tests/test_cli.py`.
- The harness reads `APP_NAME`, `BINARY_NAME` and `ENVVAR_PREFIX` from `constants.py`. Rewrite the `.feature` files for your CLI; leave `conftest.py` and `steps/` alone.
- Full detail: [docs/design/testing.md](docs/design/testing.md).

## Commit Messages
- Use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:`).

## Code Quality
- **Before every commit:** `make format && make lint && make test`
- stdout for data; stderr for progress/warnings/errors
- No bare `except Exception` — catch specific types
