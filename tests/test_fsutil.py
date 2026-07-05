"""Tests for fiveclis.fsutil."""

import os
import re
from pathlib import Path

import pytest

from fiveclis import fsutil
from fiveclis.fsutil import atomic_write_text


def test_writes_new_file(tmp_path):
    target = tmp_path / "out.txt"
    atomic_write_text(target, "hello\n")
    assert target.read_text(encoding="utf-8") == "hello\n"


def test_overwrites_existing_file(tmp_path):
    target = tmp_path / "out.txt"
    target.write_text("old")
    atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"


def test_no_temp_file_left_behind(tmp_path):
    target = tmp_path / "out.txt"
    atomic_write_text(target, "hello")
    assert [p.name for p in tmp_path.iterdir()] == ["out.txt"]


def test_preserves_existing_mode(tmp_path):
    target = tmp_path / "out.txt"
    target.write_text("old")
    target.chmod(0o600)
    atomic_write_text(target, "new")
    assert (target.stat().st_mode & 0o777) == 0o600


def test_new_file_gets_umask_default_mode(tmp_path):
    old_umask = os.umask(0o022)
    try:
        target = tmp_path / "out.txt"
        atomic_write_text(target, "hello")
        assert (target.stat().st_mode & 0o777) == 0o644
    finally:
        os.umask(old_umask)


def test_explicit_mode_applied_to_new_file(tmp_path):
    target = tmp_path / "out.txt"
    atomic_write_text(target, "secret", mode=0o600)
    assert (target.stat().st_mode & 0o777) == 0o600


def test_temp_file_never_more_permissive_than_target(tmp_path, monkeypatch):
    """The temp file must carry the target's restricted mode from creation."""
    target = tmp_path / "out.txt"
    seen: list[int] = []
    real_replace = os.replace

    def spy(src, dst):
        seen.append(Path(src).stat().st_mode & 0o777)
        real_replace(src, dst)

    monkeypatch.setattr(fsutil.os, "replace", spy)
    atomic_write_text(target, "secret", mode=0o600)
    assert seen == [0o600]


def test_failure_leaves_original_intact(tmp_path, monkeypatch):
    target = tmp_path / "out.txt"
    target.write_text("original")

    def boom(src, dst):
        raise OSError("replace failed")

    monkeypatch.setattr(fsutil.os, "replace", boom)
    with pytest.raises(OSError):
        atomic_write_text(target, "new")
    assert target.read_text() == "original"
    # temp file cleaned up
    assert [p.name for p in tmp_path.iterdir()] == ["out.txt"]


def test_all_file_writes_go_through_atomic_helper():
    """Guard: no module may write files directly; use atomic_write_text."""
    src_dir = Path(fsutil.__file__).parent
    direct_write = re.compile(
        r"\.write_text\(|\.write_bytes\("
        r"|open\([^)]*[\"'][rwax]*[wax+]"  # open() in any writable mode
        r"|shutil\.(copy|move)"
    )
    offenders = [
        py.name
        for py in sorted(src_dir.glob("*.py"))
        if py.name != "fsutil.py" and direct_write.search(py.read_text())
    ]
    assert (
        offenders == []
    ), f"Direct file writes found in {offenders}; use fsutil.atomic_write_text"
