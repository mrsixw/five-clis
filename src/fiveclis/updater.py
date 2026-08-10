import json
import os
import re
import time
from datetime import datetime, timezone
from enum import Enum, auto
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

import requests

from .fsutil import atomic_write_stream, atomic_write_text
from .logger import logger
from .xdg import get_cache_dir

_UPDATE_CHECK_REPO = "mrsixw/five-clis"
_PACKAGE_NAME = "fiveclis"
_BINARY_NAME = "five-clis"
_RELEASE_ASSET_URL = (
    f"https://github.com/{_UPDATE_CHECK_REPO}/releases/latest/download/{_BINARY_NAME}"
)

_CACHE_FILENAME = "latest_version.json"
_CACHE_TTL_SECONDS = 86400  # 24 hours


class UpdateStatus(Enum):
    """Outcome of a :func:`perform_update` attempt.

    The values are deliberately meaningless — nothing should serialise or
    compare against them, so call sites use ``is`` against the members.
    """

    UPDATED = auto()
    UP_TO_DATE = auto()
    UNKNOWN = auto()
    ERROR = auto()


def _read_version_cache() -> dict | None:
    """Return the whole cached update-check record if fresh, else None."""
    cache_file = get_cache_dir() / _CACHE_FILENAME
    try:
        if not cache_file.exists():
            return None
        data = json.loads(cache_file.read_text())
        cached_at = datetime.fromisoformat(data["checked_at"])
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        if age > _CACHE_TTL_SECONDS:
            return None
        return data
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.debug("version_cache_read_error error=%r", str(exc))
        return None


def _write_version_cache(latest_version, release_body=None):
    try:
        cache_dir = get_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "latest_version": latest_version,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        if release_body is not None:
            payload["release_body"] = release_body
        atomic_write_text(cache_dir / _CACHE_FILENAME, json.dumps(payload))
    except OSError as exc:
        logger.debug("version_cache_write_error error=%r", str(exc))


def get_latest_version():
    cached = _read_version_cache()
    if cached and cached.get("latest_version"):
        return cached["latest_version"]
    try:
        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        t0 = time.monotonic()
        resp = requests.get(
            f"https://api.github.com/repos/{_UPDATE_CHECK_REPO}/releases/latest",
            headers=headers,
            timeout=5,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        resp.raise_for_status()
        data = resp.json()
        tag = data.get("tag_name", "")
        latest = tag.lstrip("v")
        release_body = data.get("body") or None
        logger.debug(
            "update_check_response status=%d elapsed_ms=%d latest=%s",
            resp.status_code,
            elapsed_ms,
            latest,
        )
        _write_version_cache(latest, release_body=release_body)
        return latest
    except requests.exceptions.RequestException as exc:
        logger.debug("update_check_request_failed error=%r", str(exc))
        return None


def _parse_version_tuple(version_str):
    try:
        parts = []
        for segment in version_str.split("."):
            m = re.match(r"\d+", segment)
            if not m:
                break
            parts.append(int(m.group()))
        return tuple(parts)
    except (ValueError, AttributeError) as exc:
        logger.debug(
            "parse_version_failed version_str=%r error=%r", version_str, str(exc)
        )
        return ()


def _is_newer(latest: str, current: str) -> bool:
    """Compare versions with zero-padding so ``0.2.0`` is not newer than ``0.2``."""
    lt = _parse_version_tuple(latest)
    ct = _parse_version_tuple(current)
    width = max(len(lt), len(ct))
    return lt + (0,) * (width - len(lt)) > ct + (0,) * (width - len(ct))


def get_release_summary(body: str, max_chars: int = 200) -> str:
    """Extract a short human-readable summary from a GitHub release body."""
    if not body:
        return ""
    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith(("- ", "* ", "• ")):
            lines.append(stripped)
            if len(lines) >= 3:
                break
    if not lines:
        for line in body.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
                break
    summary = " ".join(lines)
    summary = re.sub(r"https?://\S+", "", summary).strip()
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1] + "…"
    return summary


def check_for_update(show_summary: bool = False):
    try:
        current = pkg_version(_PACKAGE_NAME)
        latest = get_latest_version()
        if not latest:
            return None
        if _is_newer(latest, current):
            msg = (
                f"🍟 A fresh order is ready! "
                f"v{current} → v{latest} "
                f"— update at https://github.com/{_UPDATE_CHECK_REPO}/releases/latest"
            )
            if show_summary:
                cached = _read_version_cache()
                body = cached.get("release_body") if cached else None
                if body:
                    summary = get_release_summary(body)
                    if summary:
                        msg += f"\n  📋 {summary}"
            return msg
        return None
    except PackageNotFoundError as exc:
        logger.debug("package_not_found error=%r", str(exc))
        return None


def perform_update(executable_path) -> tuple[UpdateStatus, str, str | None]:
    """Download the latest five-clis release and replace executable_path in place.

    Returns (status, current_version, detail):
      - UPDATED: executable_path now holds the release named by detail.
      - UP_TO_DATE: current_version already matches or exceeds detail (latest).
      - UNKNOWN: the latest version could not be determined; detail is None.
      - ERROR: the download or install failed; detail carries the error message.
    """
    current = pkg_version(_PACKAGE_NAME)
    executable_path = Path(executable_path)
    if executable_path.suffix == ".py":
        # Invoked from a source checkout (python -m <pkg>.cli), not an installed
        # release. Writing a downloaded binary here would destroy the source.
        return (
            UpdateStatus.ERROR,
            current,
            f"{executable_path} is a source file, not an installed binary — "
            "install a release before updating.",
        )

    latest = get_latest_version()
    if not latest:
        return UpdateStatus.UNKNOWN, current, None
    if not _is_newer(latest, current):
        return UpdateStatus.UP_TO_DATE, current, latest

    # Stream straight into atomic_write_stream: it writes to a sibling temp file
    # and os.replace()s it into position, so an interrupted download can never
    # leave a half-written binary where the working one used to be.
    try:
        with requests.get(_RELEASE_ASSET_URL, timeout=30, stream=True) as resp:
            resp.raise_for_status()
            atomic_write_stream(
                executable_path, resp.iter_content(chunk_size=65536), mode=0o755
            )
    except (OSError, requests.exceptions.RequestException) as exc:
        logger.debug("perform_update_failed error=%r", str(exc))
        return UpdateStatus.ERROR, current, str(exc)
    return UpdateStatus.UPDATED, current, latest
