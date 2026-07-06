import pytest

from fiveclis.config import (
    _DEFAULT_CONFIG_CONTENT,
    _extract_option_blocks,
    _key_present_in_file,
    load_config,
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
