from datetime import timedelta

import pytest
import requests
import requests_mock as req_mock
from freezegun import freeze_time

from fiveclis import updater as upd
from fiveclis.updater import UpdateStatus


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
                f"https://api.github.com/repos/{upd.UPDATE_CHECK_REPO}"
                "/releases/latest",
                json={"tag_name": "v2.0.0", "body": None},
            )
            result = upd.get_latest_version()
    assert result == "2.0.0"


# ── perform_update ──────────────────────────────────────────────────────────


@pytest.fixture
def installed_exe(tmp_path):
    """A stand-in for the installed five-clis binary."""
    exe = tmp_path / "bin" / "five-clis"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"old binary")
    exe.chmod(0o755)
    return exe


def _pin_versions(monkeypatch, current, latest):
    monkeypatch.setattr(upd, "pkg_version", lambda _name: current)
    monkeypatch.setattr(upd, "get_latest_version", lambda: latest)


def test_perform_update_replaces_the_binary(installed_exe, monkeypatch):
    _pin_versions(monkeypatch, current="1.0.0", latest="2.0.0")
    with req_mock.Mocker() as m:
        m.get(upd.RELEASE_ASSET_URL, content=b"new binary")
        status, current, detail = upd.perform_update(installed_exe)
    assert status is UpdateStatus.UPDATED
    assert (current, detail) == ("1.0.0", "2.0.0")
    assert installed_exe.read_bytes() == b"new binary"
    assert installed_exe.stat().st_mode & 0o755 == 0o755


def test_perform_update_leaves_no_temp_file_behind(installed_exe, monkeypatch):
    _pin_versions(monkeypatch, current="1.0.0", latest="2.0.0")
    with req_mock.Mocker() as m:
        m.get(upd.RELEASE_ASSET_URL, content=b"new binary")
        upd.perform_update(installed_exe)
    assert [f.name for f in installed_exe.parent.iterdir()] == ["five-clis"]


def test_perform_update_already_current(installed_exe, monkeypatch):
    _pin_versions(monkeypatch, current="2.0.0", latest="2.0.0")
    status, current, detail = upd.perform_update(installed_exe)
    assert status is UpdateStatus.UP_TO_DATE
    assert (current, detail) == ("2.0.0", "2.0.0")
    assert installed_exe.read_bytes() == b"old binary"


def test_perform_update_unknown_when_latest_cannot_be_resolved(
    installed_exe, monkeypatch
):
    _pin_versions(monkeypatch, current="1.0.0", latest=None)
    status, current, detail = upd.perform_update(installed_exe)
    assert status is UpdateStatus.UNKNOWN
    assert detail is None
    assert installed_exe.read_bytes() == b"old binary"


def test_perform_update_download_failure_leaves_binary_untouched(
    installed_exe, monkeypatch
):
    _pin_versions(monkeypatch, current="1.0.0", latest="2.0.0")
    with req_mock.Mocker() as m:
        m.get(upd.RELEASE_ASSET_URL, exc=requests.exceptions.ConnectTimeout("boom"))
        status, _current, detail = upd.perform_update(installed_exe)
    assert status is UpdateStatus.ERROR
    assert "boom" in detail
    assert installed_exe.read_bytes() == b"old binary"
    assert [f.name for f in installed_exe.parent.iterdir()] == ["five-clis"]


def test_perform_update_http_error_leaves_binary_untouched(installed_exe, monkeypatch):
    _pin_versions(monkeypatch, current="1.0.0", latest="2.0.0")
    with req_mock.Mocker() as m:
        m.get(upd.RELEASE_ASSET_URL, status_code=404)
        status, _current, _detail = upd.perform_update(installed_exe)
    assert status is UpdateStatus.ERROR
    assert installed_exe.read_bytes() == b"old binary"


def test_perform_update_permission_denied_reports_detail(installed_exe, monkeypatch):
    """A make-installed binary under /usr/local/bin is not writable by the user."""
    _pin_versions(monkeypatch, current="1.0.0", latest="2.0.0")
    installed_exe.parent.chmod(0o555)
    try:
        with req_mock.Mocker() as m:
            m.get(upd.RELEASE_ASSET_URL, content=b"new binary")
            status, _current, detail = upd.perform_update(installed_exe)
        assert status is UpdateStatus.ERROR
        assert "Permission denied" in detail
        assert installed_exe.read_bytes() == b"old binary"
    finally:
        installed_exe.parent.chmod(0o755)


def test_perform_update_refuses_to_overwrite_a_source_file(tmp_path, monkeypatch):
    """`python -m fiveclis.cli update` must not write a binary over cli.py."""
    _pin_versions(monkeypatch, current="1.0.0", latest="2.0.0")
    source = tmp_path / "cli.py"
    source.write_text("# the actual source\n")
    status, _current, detail = upd.perform_update(source)
    assert status is UpdateStatus.ERROR
    assert "source file" in detail
    assert source.read_text() == "# the actual source\n"


def test_perform_update_cleans_up_after_a_keyboard_interrupt(
    installed_exe, monkeypatch
):
    """Ctrl-C mid-download must not strand a temp file next to the binary."""
    _pin_versions(monkeypatch, current="1.0.0", latest="2.0.0")

    class _Interrupting:
        def __iter__(self):
            yield b"partial"
            raise KeyboardInterrupt

    with req_mock.Mocker() as m:
        m.get(upd.RELEASE_ASSET_URL, content=b"ignored")
        # The 3-arg form, not the dotted-string form: breakfast wraps
        # monkeypatch.setattr in an autouse fixture that only accepts it.
        monkeypatch.setattr(
            requests.Response, "iter_content", lambda self, **_kw: _Interrupting()
        )
        with pytest.raises(KeyboardInterrupt):
            upd.perform_update(installed_exe)

    assert installed_exe.read_bytes() == b"old binary"
    assert [f.name for f in installed_exe.parent.iterdir()] == ["five-clis"]
