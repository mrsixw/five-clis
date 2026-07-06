from datetime import timedelta

import requests_mock as req_mock
from freezegun import freeze_time

from fiveclis import updater as upd


def test_parse_version_tuple_basic():
    assert upd._parse_version_tuple("1.2.3") == (1, 2, 3)


def test_parse_version_tuple_prerelease():
    assert upd._parse_version_tuple("1.0.0a1") == (1, 0, 0)


def test_parse_version_tuple_empty():
    assert upd._parse_version_tuple("") == ()


def test_is_newer_basic():
    assert upd._is_newer("2.0.0", "1.0.0")
    assert not upd._is_newer("1.0.0", "2.0.0")


def test_is_newer_pads_missing_segments():
    assert not upd._is_newer("0.2.0", "0.2")
    assert not upd._is_newer("0.2", "0.2.0")
    assert upd._is_newer("0.2.1", "0.2")


def test_get_release_summary_bullets():
    body = "## What's new\n- Fix A\n- Fix B\n- Fix C\n- Fix D"
    summary = upd.get_release_summary(body)
    assert "Fix A" in summary
    assert "Fix D" not in summary  # only first 3


def test_get_release_summary_strips_urls():
    body = "- See https://example.com for details"
    summary = upd.get_release_summary(body)
    assert "https://" not in summary


def test_get_release_summary_truncates():
    body = "- " + "x" * 300
    summary = upd.get_release_summary(body, max_chars=50)
    assert len(summary) <= 50


def test_get_release_summary_empty():
    assert upd.get_release_summary("") == ""


def test_get_latest_version_from_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(upd, "get_cache_dir", lambda: tmp_path)
    with freeze_time("2026-01-01 12:00:00") as frozen:
        upd._write_version_cache("9.9.9")
        frozen.tick(timedelta(hours=1))
        assert upd.get_latest_version() == "9.9.9"


def test_get_latest_version_expired_cache_fetches_api(tmp_path, monkeypatch):
    monkeypatch.setattr(upd, "get_cache_dir", lambda: tmp_path)
    with freeze_time("2026-01-01 12:00:00") as frozen:
        upd._write_version_cache("0.0.1")
        frozen.tick(timedelta(days=2))
        with req_mock.Mocker() as m:
            m.get(
                f"https://api.github.com/repos/{upd._UPDATE_CHECK_REPO}"
                "/releases/latest",
                json={"tag_name": "v2.0.0", "body": None},
            )
            result = upd.get_latest_version()
    assert result == "2.0.0"
