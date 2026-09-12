# Agent Instructions

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

## Module API contract
- A leading `_` means "internal to this module". Anything a sibling module
  imports must not have one, and must appear in that module's `__all__`.
- Every module in `src/fiveclis/` declares `__all__`. Add new public names to it.
- Reach other modules through their public names only. If you need something a
  module keeps private, widen that module's API deliberately — rename it and add
  it to `__all__` — rather than reaching past the underscore. A private name you
  had to import was never really private.
- The same applies to third-party libraries: depend on their documented API, not
  on internals that can change in a patch release.
- `tests/test_public_api.py` enforces the first two. Tests may still reach into
  the internals of the module they test — that boundary is not policed.

## Agent Instruction Files
`AGENTS.md` is the single source of truth. `CLAUDE.md`, `GEMINI.md` and
`.github/copilot-instructions.md` are symlinks to it, so there is one file to
edit and drift between them is impossible.

- `AGENTS.md` — canonical. Read natively by Codex and most other agents
- `CLAUDE.md` → symlink — Claude Code
- `GEMINI.md` → symlink — Gemini
- `.github/copilot-instructions.md` → symlink — GitHub Copilot

`AGENTS.md` is the canonical file because Codex, Copilot and others read that
name natively, and it is the emerging cross-tool convention. The three tools
that insist on their own filename get a symlink instead of a copy.

On Windows, git checks symlinks out as plain text files containing the target
path unless `core.symlinks=true` and Developer Mode are both enabled.

## Commit Messages
- Use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:`).

## Code Quality
- **Before every commit:** `make format && make lint && make test`
- stdout for data; stderr for progress/warnings/errors
- No bare `except Exception` — catch specific types
