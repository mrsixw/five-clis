# GitHub Copilot Instructions

## Project Overview
- **five-clis** is a batteries-included Python CLI template.
- Built with Python and Click. Infrastructure: themes, seasonal colours, caching, config files, XDG dirs, shell completions, auto-update checks, CI, release pipeline.
- Package: `src/fiveclis/`. Tests: `tests/`. Package manager: **uv**.

## Common Commands
- `make test` — run tests
- `make lint` — check linting and formatting
- `make format` — auto-fix lint and formatting

## Testing
- Two layers. **If it fakes any part of the system under test, it is a unit test** (`monkeypatch`, `requests-mock`, `freezegun`, `CliRunner`) and belongs in `tests/`. End-to-end tests in `tests/e2e/` drive the **built binary as a subprocess** and fake nothing — `make e2e`.
- Add an e2e scenario only for what the real binary alone can prove: exit codes, stdout-versus-stderr, packaging, files on disk. Everything else belongs in `tests/test_cli.py`.
- The harness reads `APP_NAME`, `BINARY_NAME` and `ENVVAR_PREFIX` from `constants.py`. Rewrite the `.feature` files for your CLI; leave `conftest.py` and `steps/` alone.
- Full detail: [docs/design/testing.md](docs/design/testing.md).

## Code Quality
- **Before every commit:** `make format && make lint && make test`
- stdout for data; stderr for progress/warnings/errors
- No bare `except Exception`
