# GitHub Copilot Instructions

## Project Overview
- **five-clis** is a batteries-included Python CLI template.
- Built with Python and Click. Infrastructure: themes, seasonal colours, caching, config files, XDG dirs, shell completions, auto-update checks, CI, release pipeline.
- Package: `src/fiveclis/`. Tests: `tests/`. Package manager: **uv**.

## Common Commands
- `make test` — run tests
- `make lint` — check linting and formatting
- `make format` — auto-fix lint and formatting

## Code Quality
- **Before every commit:** `make format && make lint && make test`
- stdout for data; stderr for progress/warnings/errors
- No bare `except Exception`
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

