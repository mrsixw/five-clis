"""Fixtures for the end-to-end suite.

These tests drive the **built** binary as a subprocess. Nothing here fakes any
part of ``fiveclis`` — if a test needs to, it is a unit test and belongs in
``tests/``. See ``docs/testing.md``.

**On the name.** ``conftest.py`` is not a name we chose and cannot be changed:
pytest hardcodes it. It is the only filename pytest loads fixtures and hooks
from without registering a plugin, and it applies them to every test in its
directory and below. Hence ``pytest_collection_modifyitems`` has to live here —
hooks come from ``conftest.py`` and plugins, nowhere else.

**Nothing in this file names the CLI.** It reads ``APP_NAME``, ``BINARY_NAME``
and ``ENVVAR_PREFIX`` from ``constants.py``, so a project scaffolded from this
template retargets the whole suite by editing those three values.
"""

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from fiveclis.constants import APP_NAME, BINARY_NAME, ENVVAR_PREFIX

# These star imports are load-bearing, not laziness. `@given`/`@when`/`@then`
# register a step by injecting a pytest fixture into the *defining* module's
# namespace, under a generated name (`pytestbdd_stepdef_*`). pytest only scans
# conftest and test modules for fixtures, so a step defined in a plain module is
# invisible until its namespace is pulled in here. Replace these with named
# imports and every scenario fails to find its steps.
from .steps.steps import *  # noqa: E402,F401,F403

REPO_ROOT = Path(__file__).resolve().parents[2]

#: `make build` writes the zipapp here.
DEFAULT_BINARY = REPO_ROOT / "dist" / BINARY_NAME

#: Knobs, named after this CLI so two scaffolded projects cannot collide.
ENV_BINARY = f"{ENVVAR_PREFIX}_E2E_BINARY"
ENV_REQUIRE = f"{ENVVAR_PREFIX}_E2E_REQUIRE"
ENV_TIMEOUT = f"{ENVVAR_PREFIX}_E2E_TIMEOUT"

# The zipapp shebang is `#!/usr/bin/env python3`, so PATH is load-bearing.
# Everything else is deliberately withheld: starting from an empty environment
# is what makes these runs reproducible.
_PASSTHROUGH = ("PATH", "TMPDIR")


def pytest_collection_modifyitems(items):
    """Stamp ``e2e`` on everything here, tagged or not.

    Feature-level ``@e2e`` tags already become markers, but an untagged feature
    file must never leak into ``make test``.
    """
    here = Path(__file__).parent
    for item in items:
        if here in Path(str(item.fspath)).parents:
            item.add_marker(pytest.mark.e2e)


@dataclass(frozen=True)
class RunResult:
    """One completed invocation of the binary."""

    argv: list[str]
    returncode: int
    stdout: str
    stderr: str


@pytest.fixture(scope="session")
def shiv_root(tmp_path_factory):
    """Extract the zipapp once per session, not once per scenario."""
    return tmp_path_factory.mktemp("shiv-root")


@pytest.fixture(scope="session")
def cli_binary():
    """Locate the built zipapp, or skip/fail with something actionable."""
    override = os.environ.get(ENV_BINARY)
    path = Path(override).resolve() if override else DEFAULT_BINARY
    if not path.is_file():
        message = f"binary not found at {path} — run `make build` first"
        if os.environ.get(ENV_REQUIRE):
            pytest.fail(message)
        pytest.skip(message)
    if not os.access(path, os.X_OK):
        pytest.fail(f"{path} is not executable — `chmod +x` it after download")
    return path


@pytest.fixture
def sandbox(tmp_path):
    """Per-scenario HOME, XDG dirs and cwd."""
    dirs = {n: tmp_path / n for n in ("home", "cache", "config", "state", "cwd")}
    for directory in dirs.values():
        directory.mkdir(parents=True)
    return dirs


@pytest.fixture
def cli_env(sandbox, shiv_root):
    """A hermetic environment for the subprocess."""
    env = {key: os.environ[key] for key in _PASSTHROUGH if key in os.environ}
    env.update(
        # xdg resolution ignores relative paths and falls back to Path.home(),
        # so every one of these must be absolute or the real cache leaks in.
        HOME=str(sandbox["home"]),
        XDG_CACHE_HOME=str(sandbox["cache"]),
        XDG_CONFIG_HOME=str(sandbox["config"]),
        XDG_STATE_HOME=str(sandbox["state"]),
        SHIV_ROOT=str(shiv_root),
        # ui honours COLUMNS; in a pipe without it, width falls back to 80.
        COLUMNS="200",
        LINES="50",
        LC_ALL="C.UTF-8",
        LANG="C.UTF-8",
        PYTHONIOENCODING="utf-8",
        PYTHONUNBUFFERED="1",
        TZ="UTC",
    )
    # Otherwise every run hits the releases API and may print a banner.
    env[f"{ENVVAR_PREFIX}_NO_UPDATE_CHECK"] = "1"
    return env


@pytest.fixture
def run_cli(cli_binary, cli_env, sandbox):
    """Run the binary and capture its real streams."""

    def _run(args, *, timeout=int(os.environ.get(ENV_TIMEOUT, "90"))):
        argv = [str(cli_binary), *args]
        try:
            completed = subprocess.run(
                argv,
                cwd=sandbox["cwd"],
                env=cli_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            pytest.fail(
                f"`{shlex.join(argv)}` timed out after {timeout}s\n"
                f"--- stdout ---\n{exc.stdout}\n--- stderr ---\n{exc.stderr}"
            )
        return RunResult(argv, completed.returncode, completed.stdout, completed.stderr)

    return _run


@pytest.fixture
def app_name():
    """The config/cache subdirectory name, for steps that look on disk."""
    return APP_NAME


@pytest.fixture
def binary_name():
    """What the user types, for steps that assert on help and version output."""
    return BINARY_NAME
