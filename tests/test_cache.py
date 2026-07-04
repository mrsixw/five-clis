from datetime import timedelta

import pytest
from freezegun import freeze_time

from fiveclis import cache as cache_mod


def test_parse_ttl_seconds():
    assert cache_mod.parse_ttl(300) == 300


def test_parse_ttl_string_int():
    assert cache_mod.parse_ttl("300") == 300


def test_parse_ttl_minutes():
    assert cache_mod.parse_ttl("5m") == 300


def test_parse_ttl_hours():
    assert cache_mod.parse_ttl("2h") == 7200


def test_parse_ttl_seconds_suffix():
    assert cache_mod.parse_ttl("30s") == 30


def test_parse_ttl_invalid_raises():
    with pytest.raises(ValueError):
        cache_mod.parse_ttl("bad")


def test_parse_ttl_zero_raises():
    with pytest.raises(ValueError):
        cache_mod.parse_ttl(0)


def test_parse_ttl_bool_raises():
    with pytest.raises(ValueError):
        cache_mod.parse_ttl(True)


def test_write_and_read_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "get_cache_dir", lambda: tmp_path)
    payload = {"answer": 42, "items": ["a", "b"]}
    cache_mod.write_cache("test_key", payload)
    result = cache_mod.read_cache("test_key", ttl=3600)
    assert result == payload


def test_read_cache_miss_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "get_cache_dir", lambda: tmp_path)
    assert cache_mod.read_cache("missing_key", ttl=300) is None


def test_read_cache_expired(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "get_cache_dir", lambda: tmp_path)
    payload = {"x": 1}
    with freeze_time("2026-01-01 12:00:00") as frozen:
        cache_mod.write_cache("expired_key", payload)
        assert cache_mod.read_cache("expired_key", ttl=300) == payload
        frozen.tick(timedelta(hours=2))
        assert cache_mod.read_cache("expired_key", ttl=300) is None


def test_clear_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "get_cache_dir", lambda: tmp_path)
    cache_mod.write_cache("clear_key", {"v": 1})
    assert cache_mod.clear_cache("clear_key") is True
    assert cache_mod.read_cache("clear_key", ttl=3600) is None


def test_clear_cache_missing_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "get_cache_dir", lambda: tmp_path)
    assert cache_mod.clear_cache("nonexistent") is False
