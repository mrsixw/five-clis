"""Step definitions for the end-to-end suite.

Split out of ``conftest.py``, which is for fixtures. Nothing here names the CLI:
steps that need the binary or app name take the ``binary_name`` / ``app_name``
fixtures, so renaming the template's constants retargets these too.
"""

import json
import re
import shlex
from pathlib import Path

from pytest_bdd import given, parsers, then, when

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Matches an ANSI SGR escape, for asserting --no-colour really is colourless.
ANSI = re.compile(r"\x1b\[[0-9;]*m")


# ── Running it ─────────────────────────────────────────────────────────────


@when(parsers.parse("I run the CLI with `{args}`"), target_fixture="result")
def _run_with_args(run_cli, args):
    return run_cli(shlex.split(args))


@when("I run the CLI with no arguments", target_fixture="result")
def _run_bare(run_cli):
    return run_cli([])


# ── Exit codes and streams ─────────────────────────────────────────────────


@then(parsers.parse("the exit code is {code:d}"))
def _exit_code(result, code):
    assert result.returncode == code, f"stderr was:\n{result.stderr}"


@then("stdout is empty")
def _stdout_empty(result):
    assert result.stdout.strip() == "", f"stdout was:\n{result.stdout}"


@then(parsers.parse('stdout contains "{text}"'))
def _stdout_contains(result, text):
    assert text in result.stdout, f"stdout was:\n{result.stdout}"


@then(parsers.parse('stdout does not contain "{text}"'))
def _stdout_lacks(result, text):
    assert text not in result.stdout, f"{text!r} leaked onto stdout:\n{result.stdout}"


@then(parsers.parse('stderr contains "{text}"'))
def _stderr_contains(result, text):
    assert text in result.stderr, f"stderr was:\n{result.stderr}"


@then("stderr is empty")
def _stderr_empty(result):
    assert result.stderr.strip() == "", f"stderr was:\n{result.stderr}"


@then("stdout carries no ANSI colour")
def _stdout_uncoloured(result):
    found = ANSI.findall(result.stdout)
    assert not found, f"--no-colour still emitted {len(found)} escapes"


@then("stdout is valid JSON", target_fixture="payload")
def _stdout_json(result):
    return json.loads(result.stdout)


@then("stdout reports the version from the VERSION file")
def _version_matches(result):
    expected = (REPO_ROOT / "VERSION").read_text().strip()
    assert result.stdout.strip().endswith(
        expected
    ), f"expected version {expected!r}, stdout was:\n{result.stdout}"


@then("stdout names the binary")
def _names_binary(result, binary_name):
    assert binary_name in result.stdout, f"stdout was:\n{result.stdout}"


# ── The config file on disk ────────────────────────────────────────────────


@given("no config file exists")
def _no_config(sandbox, app_name):
    path = sandbox["config"] / app_name / "config.toml"
    assert not path.exists(), f"{path} existed before the scenario started"


@then("the config file exists in the sandbox")
def _config_written(sandbox, app_name):
    path = sandbox["config"] / app_name / "config.toml"
    assert path.is_file(), f"{path} was not created — is XDG_CONFIG_HOME honoured?"


@given("a config file with a hand-edited marker")
def _seed_config(run_cli, sandbox, app_name):
    """Write a real config, then add a line no template would produce."""
    assert run_cli(["config", "init"]).returncode == 0
    path = sandbox["config"] / app_name / "config.toml"
    path.write_text(path.read_text() + '\n# hand-edited-marker\ntheme = "mono"\n')


@then("the hand-edited marker is still in the config file")
def _marker_survived(sandbox, app_name):
    path = sandbox["config"] / app_name / "config.toml"
    body = path.read_text()
    assert (
        "hand-edited-marker" in body
    ), f"`config init` clobbered a config the user had edited:\n{body}"


@then(parsers.parse("the completion script is evaluable by {shell}"))
def _completion_evaluable(result, shell, binary_name):
    """A completion script must be pure script on stdout, nothing else.

    Anything printed alongside it lands in the user's shell config via
    ``eval "$(... completions bash)"`` and is executed.
    """
    assert result.stdout.strip(), f"{shell} completion produced no stdout"
    assert "Usage:" not in result.stdout, f"usage text leaked into the {shell} script"
    assert "Error" not in result.stdout, f"an error leaked into the {shell} script"
