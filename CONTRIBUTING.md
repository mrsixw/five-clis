# Contributing to five-clis

## Development setup

```bash
git clone https://github.com/mrsixw/five-clis
cd five-clis
uv sync --extra dev
```

## Before every commit

Run all three in order — no exceptions:

```bash
make format   # auto-fix formatting
make lint     # must exit clean (ruff, black, markdownlint, shellcheck, typos)
make test     # all tests must pass
```

If you touched a shell script, run `make bats` too.

## Testing the shell scripts

`install.sh` is the published `curl | bash` install path, and `utils/` holds the
scripts that cut releases. They are covered by a
[bats](https://github.com/bats-core/bats-core) suite in `tests/bats/`:

```bash
make bats        # the shell test suite
make shellcheck  # static analysis over every shell source
make spell       # the same spell check CI runs
```

Each test runs the **real script as a subprocess** with its collaborators —
`gh`, `git`, `curl`, `tar`, `install` — replaced by stubs on `PATH`, and with
`HOME` redirected into the test's temporary directory. Nothing reaches the
network, and an installer test cannot scribble on the machine running it. The
stubs record their arguments, so a test can assert *what the script asked for*
rather than only what it printed.

`bats` and `shellcheck` are fetched on demand with `npx`, and `typos` with
`uvx` — nothing to install by hand beyond `node`. Because five-clis is a
template, the suite reads `BINARY_NAME` from `constants.py` rather than
hardcoding it, so a CLI generated from this template inherits it working.

## Conventional commits

Use `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:` prefixes.

## Workflow

- Every branch must reference a GitHub issue
- Branch format: `issue-<N>_short_description`
- One issue = one branch = one PR
- PRs must include `Closes #N` in the body

## Code style

- `ruff` for linting and import sorting
- `black` for formatting (88-char line length)
- No bare `except Exception` — catch specific exception types
- stdout for data output; stderr for progress/warnings/errors
