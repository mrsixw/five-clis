# Testing Strategy

How this template is tested, and — more usefully — which layer a new test
belongs in. A project scaffolded from here inherits both the harness and this
rule; the rule is the more valuable half.

## The layers

| Layer | Location | Runs the binary? | Command |
| --- | --- | --- | --- |
| Unit | `tests/test_*.py` | no | `make test` |
| CLI | `tests/test_cli.py` | no (in-process `CliRunner`) | `make test` |
| End-to-end | `tests/e2e/` | **yes**, the built binary as a subprocess | `make e2e` |

### The rule

**If it fakes any part of the system under test, it is a unit test.** It belongs
in `tests/`, not `tests/e2e/`.

Faking means `monkeypatch`, but equally `requests-mock`, `freezegun` or
`CliRunner` — each replaces something the end-to-end layer exists to exercise
for real: the network, the clock, the process boundary.

### What end-to-end buys that the other layers cannot

- Real process exit codes, not `Result.exit_code`.
- Genuinely separate stdout and stderr. `CliRunner` merges them, so the
  stream-discipline rule in `AGENTS.md` is otherwise unenforceable by any test.
- The **shiv zipapp itself** — packaging, the `utils/preamble.py` version guard,
  the console entry point. Without this layer, `make build` produces an artifact
  that nothing then runs before `release` ships it.
- Real files on disk, at the real XDG paths.
- Completion scripts that are actually clean enough to `eval`.

## Retargeting it for your CLI

Nothing in the harness names this CLI. It reads three values from
`constants.py`:

```python
APP_NAME = "fiveclis"        # package, and the config/cache subdirectory
BINARY_NAME = "five-clis"    # what the user types, and dist/<BINARY_NAME>
ENVVAR_PREFIX = "FIVE_CLIS"  # FIVE_CLIS_E2E_BINARY, FIVE_CLIS_NO_UPDATE_CHECK
```

Change those and `tests/e2e/conftest.py` and `tests/e2e/steps/` follow with no
edits. The **`.feature` files are yours to rewrite** — they describe *this*
CLI's behaviour (`greet`, `--theme`, `config init`), and yours will differ.

## Layout

```text
tests/e2e/
  conftest.py          fixtures and the collection hook, nothing else
  steps/
    steps.py           step definitions
  features/            the .feature files — rewrite these for your CLI
  test_e2e.py          scenarios("features") — binds all of them
```

`scenarios()` walks directories, so **one** binding module covers every feature
file; there is no reason for one per feature.

`conftest.py` is the odd name in that tree, and it is not one we picked — pytest
hardcodes it. It is the only filename pytest loads fixtures and hooks from
without a registered plugin. That is also why `pytest_collection_modifyitems`
lives there: hooks come from `conftest.py` and plugins, nowhere else.

`conftest.py` ends with `from .steps.steps import *`, and that star import is
load-bearing. `@given`/`@when`/`@then` register a step by injecting a pytest
fixture into the *defining* module's namespace under a generated name
(`pytestbdd_stepdef_*`). pytest only scans conftest and test modules for
fixtures, so a step in a plain module stays invisible until that namespace is
pulled in. Rewrite it as named imports and every scenario loses its steps.

## Running them

```bash
make test      # unit + CLI. Fast. e2e is excluded by default.
make e2e       # builds the binary, then runs tests/e2e against it
make e2e-ci    # CI variant: uses the already-built artifact, fails not skips
```

`make test` stays fast because `addopts = "-m 'not e2e'"` in `pyproject.toml`.
A bare `uv run pytest` inherits that. `make e2e` passes `-m e2e` on the command
line, which overrides it.

### Skips versus failures

Locally, a missing binary **skips** with an actionable message — you have not
run `make build`. In CI, `FIVE_CLIS_E2E_REQUIRE` turns that into a hard failure,
so the suite cannot quietly rot to green.

| Variable | Effect |
| --- | --- |
| `FIVE_CLIS_E2E_BINARY` | Path to the binary under test (default: `dist/five-clis`) |
| `FIVE_CLIS_E2E_REQUIRE` | Missing binary fails instead of skipping |
| `FIVE_CLIS_E2E_TIMEOUT` | Per-invocation timeout in seconds (default: 90) |

## Offline by design

Unlike some CLIs, this suite makes **no network calls**. The only outbound
request in the codebase is `updater.py`'s release check, and the harness sets
`FIVE_CLIS_NO_UPDATE_CHECK=1` in every scenario's environment. That keeps the
suite free to run on every push: no API budget, no rate limits, no token secret,
and full coverage on pull requests from forks.

If your CLI does need live calls, add a `live` marker alongside `e2e` and gate
it on a token, so the offline scenarios still run everywhere.

## CI

The `e2e` job runs `needs: [build]` and `release` is gated behind it. It
downloads the artifact the `build` job produced rather than rebuilding, so the
bits under test are the bits that ship.

Two details that will otherwise cost an afternoon:

- Artifacts travel as zips and **do not preserve the executable bit**, hence the
  `chmod +x` step.
- `pytest` is pinned below 10. pytest-bdd 8.1.0 calls APIs pytest 9 flags as
  `PytestRemovedIn10Warning`; on pytest 10 the suite would stop collecting, and
  because `release` is gated on this job that blocks releases rather than merely
  failing a test. The warnings are deliberately **not** filtered — they are the
  signal that the upstream fix has landed and the pin can go.

## Why Gherkin

The `.feature` files describe behaviour in terms of what a user runs and what
they see, which suits a layer whose entire subject is observable CLI behaviour.
It also makes the boundary unmistakable: nothing in `tests/e2e/` looks like the
in-process suites, so the two are hard to confuse.
