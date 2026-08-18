import re

from click.testing import CliRunner

from fiveclis import cli as cli_mod
from fiveclis.cli import main


def _invoke(*args, **kwargs):
    runner = CliRunner()
    return runner.invoke(main, list(args), **kwargs)


def test_version():
    result = _invoke("--version")
    assert result.exit_code == 0
    # Assert the shape, not a substring of one particular version. The old
    # check looked for "0.", which matched 1.0.2 by luck and not 1.1.0; and
    # for "fiveclis", which never matched, since CliRunner takes the prog name
    # from the callback function (`main`) rather than the console script.
    assert re.search(r"\bversion \d+\.\d+\.\d+", result.output), result.output


def test_help():
    result = _invoke("--help")
    assert result.exit_code == 0
    assert "--theme" in result.output
    assert "greet" in result.output
    assert "completions" in result.output
    assert "update" in result.output
    assert "config" in result.output


def test_bare_invocation_runs_greet(monkeypatch):
    monkeypatch.setattr(cli_mod, "check_for_update", lambda **_kw: None)
    result = _invoke("--no-colour")
    assert result.exit_code == 0
    assert "Hello" in result.output


def test_greet_default(monkeypatch):
    monkeypatch.setattr(cli_mod, "check_for_update", lambda **_kw: None)
    result = _invoke("--no-colour", "greet")
    assert result.exit_code == 0
    assert "Hello" in result.output


def test_greet_with_name(monkeypatch):
    monkeypatch.setattr(cli_mod, "check_for_update", lambda **_kw: None)
    result = _invoke("--no-colour", "greet", "--name", "Alice")
    assert result.exit_code == 0
    assert "Alice" in result.output


def test_completions_bash():
    result = _invoke("completions", "bash")
    assert result.exit_code == 0
    assert "_FIVE_CLIS_COMPLETE" in result.output


def test_completions_zsh():
    result = _invoke("completions", "zsh")
    assert result.exit_code == 0


def test_completions_fish():
    result = _invoke("completions", "fish")
    assert result.exit_code == 0


def test_completions_rejects_unknown_shell():
    result = _invoke("completions", "powershell")
    assert result.exit_code != 0


def test_completions_singular_name_is_gone():
    """The old spelling was removed outright — this is a template, not a product."""
    result = _invoke("completion", "bash")
    assert result.exit_code != 0


def test_shell_enum_members_are_their_lowercase_names():
    assert [s.value for s in cli_mod.Shell] == ["bash", "zsh", "fish"]
    assert cli_mod.Shell.BASH == "bash"


def test_config_init(tmp_path, monkeypatch):
    from fiveclis import config as cfg_mod

    monkeypatch.setattr(cfg_mod, "get_config_dir", lambda: tmp_path / "fiveclis")
    result = _invoke("config", "init")
    assert result.exit_code == 0
    assert "config.toml" in result.output


def test_config_show(monkeypatch):
    monkeypatch.setattr(cli_mod, "check_for_update", lambda **_kw: None)
    result = _invoke("config", "show")
    assert result.exit_code == 0
    assert "Config file" in result.output


def test_theme_rainbow(monkeypatch):
    monkeypatch.setattr(cli_mod, "check_for_update", lambda **_kw: None)
    result = _invoke("--theme", "rainbow", "greet")
    assert result.exit_code == 0


def test_no_update_check_skips_update(monkeypatch):
    called = {"n": 0}

    def counting_check(**kw):
        called["n"] += 1
        return None

    monkeypatch.setattr(cli_mod, "check_for_update", counting_check)
    _invoke("--no-update-check", "--no-colour", "greet")
    assert called["n"] == 0


def test_update_check_runs_by_default(monkeypatch):
    called = {"n": 0}

    def counting_check(**kw):
        called["n"] += 1
        return None

    monkeypatch.setattr(cli_mod, "check_for_update", counting_check)
    _invoke("--no-colour", "greet")
    assert called["n"] == 1


def test_update_check_not_run_for_config_show(monkeypatch):
    called = {"n": 0}

    def counting_check(**kw):
        called["n"] += 1
        return None

    monkeypatch.setattr(cli_mod, "check_for_update", counting_check)
    _invoke("config", "show")
    assert called["n"] == 0


def test_invalid_config_exits_with_error(tmp_path):
    bad_cfg = tmp_path / "bad.toml"
    bad_cfg.write_text("not = [valid toml")
    result = _invoke("--config", str(bad_cfg), "greet")
    assert result.exit_code == 1


def test_missing_explicit_config_exits_with_error(tmp_path):
    result = _invoke("--config", str(tmp_path / "nope.toml"), "greet")
    assert result.exit_code == 1
    assert "not found" in result.output


def test_invalid_cache_ttl_exits_with_error():
    result = _invoke("--cache-ttl", "banana", "greet")
    assert result.exit_code == 1


def test_settings_resolution_config_beats_default(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_mod, "check_for_update", lambda **_kw: None)
    cfg = tmp_path / "cfg.toml"
    cfg.write_text('theme = "rainbow"\n"cache-ttl" = "5m"\n')
    result = _invoke("--config", str(cfg), "--no-colour", "greet")
    assert result.exit_code == 0


def test_config_update_no_config_exits_1(tmp_path, monkeypatch):
    from fiveclis import config as cfg_mod

    missing = tmp_path / "missing.toml"
    monkeypatch.setattr(cfg_mod, "get_config_paths", lambda: [missing])
    result = _invoke("config", "update")
    assert result.exit_code == 1


def test_config_update_up_to_date_exits_0(tmp_path, monkeypatch):
    from fiveclis import config as cfg_mod
    from fiveclis.config import _DEFAULT_CONFIG_CONTENT

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(_DEFAULT_CONFIG_CONTENT)
    monkeypatch.setattr(cfg_mod, "get_config_paths", lambda: [cfg_file])
    result = _invoke("config", "update")
    assert result.exit_code == 0


# ── update ──────────────────────────────────────────────────────────────────


def _stub_update(monkeypatch, status, current="1.0.0", detail="2.0.0"):
    monkeypatch.setattr(
        cli_mod, "perform_update", lambda _path: (status, current, detail)
    )
    monkeypatch.setattr(cli_mod, "_current_executable_path", lambda: "/tmp/five-clis")


def test_update_reports_success(monkeypatch):
    _stub_update(monkeypatch, cli_mod.UpdateStatus.UPDATED)
    result = _invoke("--no-colour", "update")
    assert result.exit_code == 0
    assert "updated to v2.0.0" in result.output
    assert "install.sh" in result.output


def test_update_reports_already_current(monkeypatch):
    _stub_update(monkeypatch, cli_mod.UpdateStatus.UP_TO_DATE)
    result = _invoke("--no-colour", "update")
    assert result.exit_code == 0
    assert "Already up to date, v1.0.0" in result.output


def test_update_unreachable_github_fails_cleanly(monkeypatch):
    _stub_update(monkeypatch, cli_mod.UpdateStatus.UNKNOWN, detail=None)
    result = _invoke("--no-colour", "update")
    assert result.exit_code != 0
    assert "Could not reach GitHub" in result.output
    assert "Traceback" not in result.output


def test_update_error_surfaces_detail(monkeypatch):
    _stub_update(monkeypatch, cli_mod.UpdateStatus.ERROR, detail="Permission denied")
    result = _invoke("--no-colour", "update")
    assert result.exit_code != 0
    assert "Permission denied" in result.output
    assert "Traceback" not in result.output


def test_update_does_not_also_print_the_update_notice(monkeypatch):
    """The trailing 'a new version exists' notice would be noise here."""
    _stub_update(monkeypatch, cli_mod.UpdateStatus.UP_TO_DATE)
    monkeypatch.setattr(
        cli_mod, "check_for_update", lambda **_kw: "🍟 A fresh order is ready!"
    )
    result = _invoke("--no-colour", "update")
    assert "fresh order" not in result.output


def test_current_executable_path_is_absolute(monkeypatch):
    monkeypatch.setattr(cli_mod.shutil, "which", lambda _name: None)
    monkeypatch.setattr(cli_mod.sys, "argv", ["./five-clis"])
    assert cli_mod._current_executable_path().startswith("/")


def test_completions_survives_a_broken_config(tmp_path):
    """The shell runs this on every tab-press; a bad config must not leak in."""
    bad = tmp_path / "config.toml"
    bad.write_text('cache-ttl = "not-a-duration"\n')
    result = _invoke("--config", str(bad), "completions", "bash")
    assert result.exit_code == 0
    assert "_FIVE_CLIS_COMPLETE" in result.stdout
    assert "Invalid TTL" not in result.output


def test_update_survives_a_broken_config(tmp_path, monkeypatch):
    """A config bad enough to break the CLI must not block updating past it."""
    _stub_update(monkeypatch, cli_mod.UpdateStatus.UP_TO_DATE)
    bad = tmp_path / "config.toml"
    bad.write_text('cache-ttl = "not-a-duration"\n')
    result = _invoke("--config", str(bad), "update")
    assert result.exit_code == 0
    assert "Already up to date" in result.output


def test_config_update_still_resolves_config(tmp_path):
    """'config update' must not be mistaken for the top-level 'update'."""
    bad = tmp_path / "config.toml"
    bad.write_text('cache-ttl = "not-a-duration"\n')
    result = _invoke("--config", str(bad), "config", "update")
    assert result.exit_code != 0
    assert "Invalid TTL" in result.output


def test_seasonal_calendar_off_is_accepted():
    # Regression: "off" was handled by apply_seasonal_colour but missing from
    # CALENDAR_NAMES, so click.Choice rejected it before it ever got there.
    result = _invoke("--seasonal-calendar", "off", "greet", "--name", "x")
    assert result.exit_code == 0
    assert "Hello, x!" in result.output


def test_seasonal_calendar_rainbow_is_accepted():
    result = _invoke("--seasonal-calendar", "rainbow", "greet", "--name", "x")
    assert result.exit_code == 0
    assert "Hello, x!" in result.output


def test_seasonal_calendar_rejects_unknown_values():
    result = _invoke("--seasonal-calendar", "klingon", "greet")
    assert result.exit_code != 0


# ── Release summary in the update notice ───────────────────────────────────


def _stub_update_check(monkeypatch, calls):
    def fake(show_summary=False):
        calls.append(show_summary)
        notice = "🍟 A fresh order is ready!"
        return notice + "\n  📋 - Did a thing" if show_summary else notice

    monkeypatch.setattr(cli_mod, "check_for_update", fake)


def test_update_summary_defaults_to_off(monkeypatch):
    calls = []
    _stub_update_check(monkeypatch, calls)
    result = _invoke("greet", "--name", "x")
    assert result.exit_code == 0
    assert calls == [False]
    assert "📋" not in result.output


def test_update_summary_flag_shows_the_highlights(monkeypatch):
    calls = []
    _stub_update_check(monkeypatch, calls)
    result = _invoke("--update-summary", "greet", "--name", "x")
    assert result.exit_code == 0
    assert calls == [True]
    assert "📋 - Did a thing" in result.output


def test_update_summary_reads_from_the_config_file(monkeypatch, tmp_path):
    calls = []
    _stub_update_check(monkeypatch, calls)
    cfg = tmp_path / "config.toml"
    cfg.write_text("update-summary = true\n")
    result = _invoke("--config", str(cfg), "greet", "--name", "x")
    assert result.exit_code == 0
    assert calls == [True]


def test_no_update_summary_flag_beats_the_config_file(monkeypatch, tmp_path):
    calls = []
    _stub_update_check(monkeypatch, calls)
    cfg = tmp_path / "config.toml"
    cfg.write_text("update-summary = true\n")
    result = _invoke(
        "--config", str(cfg), "--no-update-summary", "greet", "--name", "x"
    )
    assert result.exit_code == 0
    assert calls == [False]


def test_update_summary_is_skipped_when_update_check_is_off(monkeypatch):
    calls = []
    _stub_update_check(monkeypatch, calls)
    result = _invoke("--no-update-check", "--update-summary", "greet", "--name", "x")
    assert result.exit_code == 0
    assert calls == []
