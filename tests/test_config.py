import tomllib

import pytest

from fiveclis.config import (
    _DEFAULT_CONFIG_CONTENT,
    _extract_option_blocks,
    _key_present_in_file,
    load_config,
    misplaced_settings,
    show_config,
    update_config,
    write_default_config,
)


def test_load_config_missing_explicit_path_raises(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        load_config(str(tmp_path / "nonexistent.toml"))


def test_load_config_no_search_path_hit_returns_empty(tmp_path, monkeypatch):
    from fiveclis import config as cfg_mod

    monkeypatch.setattr(cfg_mod, "get_config_paths", lambda: [tmp_path / "none.toml"])
    assert load_config() == {}


def test_load_config_reads_toml(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('theme = "rainbow"\ncache = true\n')
    result = load_config(str(cfg_file))
    assert result["theme"] == "rainbow"
    assert result["cache"] is True


def test_load_config_invalid_toml_raises(tmp_path):
    cfg_file = tmp_path / "bad.toml"
    cfg_file.write_text("not = [valid toml")
    with pytest.raises(ValueError, match="Config parse error"):
        load_config(str(cfg_file))


def test_write_default_config_creates_file(tmp_path, monkeypatch):
    from fiveclis import xdg

    monkeypatch.setattr(xdg, "get_config_dir", lambda: tmp_path / "fiveclis")
    from fiveclis import config as cfg_mod

    monkeypatch.setattr(cfg_mod, "get_config_dir", lambda: tmp_path / "fiveclis")
    path = write_default_config()
    assert path.exists()
    assert "theme" in path.read_text()


def test_default_config_content_has_all_keys():
    assert "theme" in _DEFAULT_CONFIG_CONTENT
    assert "cache" in _DEFAULT_CONFIG_CONTENT
    assert "seasonal-colours" in _DEFAULT_CONFIG_CONTENT
    assert "no-update-check" in _DEFAULT_CONFIG_CONTENT


def test_show_config_empty():
    output = show_config({})
    assert "no config keys set" in output


def test_show_config_with_values():
    output = show_config({"theme": "rainbow", "cache": True})
    assert "theme" in output
    assert "rainbow" in output


def test_extract_option_blocks_returns_all_keys():
    blocks = _extract_option_blocks(_DEFAULT_CONFIG_CONTENT)
    keys = [k for k, _ in blocks]
    assert "theme" in keys
    assert "cache" in keys
    assert "seasonal-colours" in keys
    assert "no-update-check" in keys


def test_extract_option_blocks_block_includes_comment():
    blocks = dict(_extract_option_blocks(_DEFAULT_CONFIG_CONTENT))
    assert "# theme =" in blocks["theme"]
    assert "Equivalent to:" in blocks["theme"]


def test_key_present_in_file_active():
    assert _key_present_in_file("theme", 'theme = "dark"\n')


def test_key_present_in_file_commented():
    assert _key_present_in_file("theme", '# theme = "default"\n')


def test_key_present_in_file_absent():
    assert not _key_present_in_file("theme", "cache = true\n")


def test_update_config_no_file(monkeypatch, tmp_path):
    from fiveclis import config as cfg_mod

    missing = tmp_path / "missing.toml"
    monkeypatch.setattr(cfg_mod, "get_config_paths", lambda: [missing])
    result = update_config()
    assert result is False


def test_update_config_already_up_to_date(monkeypatch, tmp_path):
    from fiveclis import config as cfg_mod

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(_DEFAULT_CONFIG_CONTENT)
    monkeypatch.setattr(cfg_mod, "get_config_paths", lambda: [cfg_file])
    result = update_config()
    assert result is True
    # No backup should be written
    assert not list(tmp_path.glob("*.bak.*"))


def test_update_config_adds_missing_keys(monkeypatch, tmp_path):
    from fiveclis import config as cfg_mod

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("# minimal config\n# theme = default\n")
    monkeypatch.setattr(cfg_mod, "get_config_paths", lambda: [cfg_file])
    result = update_config()
    assert result is True
    updated = cfg_file.read_text()
    # backup written
    assert list(tmp_path.glob("config.toml.bak.*"))
    # missing keys appended
    assert "cache" in updated
    assert "seasonal-colours" in updated
    assert "no-update-check" in updated
    # existing key not duplicated
    assert updated.count("# theme =") == 1


def test_update_config_preserves_modes(monkeypatch, tmp_path):
    from fiveclis import config as cfg_mod

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("# minimal config\n")
    cfg_file.chmod(0o600)
    monkeypatch.setattr(cfg_mod, "get_config_paths", lambda: [cfg_file])
    assert update_config() is True
    assert (cfg_file.stat().st_mode & 0o777) == 0o600
    backup = next(tmp_path.glob("config.toml.bak.*"))
    assert (backup.stat().st_mode & 0o777) == 0o600


def _update(monkeypatch, tmp_path, content):
    """Run config update on *content* and return the file it leaves."""
    from fiveclis import config as cfg_mod

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(content)
    monkeypatch.setattr(cfg_mod, "get_config_paths", lambda: [cfg_file])
    assert update_config() is True
    return cfg_file.read_text()


TABLE = '# my server\n[server]\nhost = "example.com"\n'


def test_update_config_adds_options_above_the_first_table(monkeypatch, tmp_path):
    """An option added below [server] would belong to that table."""
    updated = _update(monkeypatch, tmp_path, f'theme = "dark"\n\n{TABLE}')
    # The table, with the comment above it, is still last and unchanged.
    assert updated.endswith(TABLE)
    assert updated.index("# --- Added by config update") < updated.index("# my")
    # Uncommented where it was put, an option is top level.
    enabled = tomllib.loads(updated.replace("# cache = false", "cache = true"))
    assert enabled["cache"] is True
    assert misplaced_settings(enabled) == []


def test_update_config_without_tables_still_appends(monkeypatch, tmp_path):
    updated = _update(monkeypatch, tmp_path, 'theme = "dark"')
    assert updated.startswith('theme = "dark"\n\n# --- Added by config update')
    assert tomllib.loads(updated) == {"theme": "dark"}


def test_new_options_go_above_a_heading_that_introduces_the_tables(
    monkeypatch, tmp_path
):
    heading = "# ----- Servers -----\n# Tables come last.\n\n"
    updated = _update(monkeypatch, tmp_path, f'theme = "dark"\n\n{heading}{TABLE}')
    assert updated.endswith(heading + TABLE)


def test_a_heading_with_its_own_options_keeps_them_above_the_new_ones(
    monkeypatch, tmp_path
):
    content = '# ----- Display -----\n\n# theme = "default"\n\n' + TABLE
    updated = _update(monkeypatch, tmp_path, content)
    assert updated.startswith(
        '# ----- Display -----\n\n# theme = "default"\n\n# --- Added'
    )


def test_misplaced_settings_names_options_inside_any_table():
    cfg = {
        "theme": "dark",
        "server": {"host": "example.com", "cache": True},
        "deploy": {"prod": {"theme": "mono"}},
        "hooks": [{"run": "make"}, {"run": "test", "no-colour": True}],
        "themes": ["dark", "light"],
        "lists": {"cache-ttl": ["5m"], "theme": []},
    }
    assert misplaced_settings(cfg) == [
        ("server", "cache"),
        ("deploy.prod", "theme"),
        ("hooks", "no-colour"),
        ("lists", "cache-ttl"),
        ("lists", "theme"),
    ]


def test_a_second_update_adds_below_the_first_one(monkeypatch, tmp_path):
    first = "# --- Added by config update (five-clis v1.0.0) on 2026-11-26 ---\n"
    content = f'theme = "dark"\n\n{first}\n# cache = false\n\n{TABLE}'
    updated = _update(monkeypatch, tmp_path, content)
    assert updated.index(first) < updated.index("# cache = false")
    assert updated.index("# cache = false") < updated.rindex("# --- Added by")
    assert updated.endswith(TABLE)


def test_a_nested_array_row_is_not_mistaken_for_a_table(monkeypatch, tmp_path):
    content = 'theme = "dark"\nmatrix = [\n  ["a", "b"],\n]\n'
    updated = _update(monkeypatch, tmp_path, content)
    assert updated.startswith(content)
