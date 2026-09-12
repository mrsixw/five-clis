import os
import secrets
from collections.abc import Iterable
from pathlib import Path

__all__ = [
    "atomic_write_stream",
    "atomic_write_text",
]


def _reserve_temp(path: Path, create_mode: int) -> tuple[int, Path]:
    """Create an exclusive temp file alongside *path*; return its fd and path.

    Alongside so the eventual rename never crosses a filesystem boundary.
    """
    while True:
        tmp = path.parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
        try:
            return os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, create_mode), tmp
        except FileExistsError:  # pragma: no cover — token collision
            continue


def atomic_write_stream(
    path: Path, chunks: Iterable[bytes], mode: int | None = None
) -> None:
    """Write the *chunks* to *path* atomically via temp file + os.replace.

    The binary, streaming counterpart to :func:`atomic_write_text`, for content
    too large to hold in memory as a single string — a downloaded release
    binary, say. Same guarantees: the temp file lives alongside *path*, is never
    more permissive than the final target, and is removed on failure leaving
    *path* untouched. Raises ``OSError``.
    """
    if mode is None and path.exists():
        mode = path.stat().st_mode
    create_mode = mode if mode is not None else 0o666
    fd, tmp = _reserve_temp(path, create_mode)
    try:
        with os.fdopen(fd, "wb") as f:
            for chunk in chunks:
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        # finally, not except OSError: *chunks* is usually a live network
        # stream, so the window here is long enough for a Ctrl-C, and the
        # randomised temp name means a leak is never reclaimed by a later run.
        # A successful os.replace leaves nothing behind, so this is a no-op on
        # the happy path.
        tmp.unlink(missing_ok=True)


def atomic_write_text(path: Path, content: str, mode: int | None = None) -> None:
    """Write *content* to *path* atomically via temp file + os.replace.

    The temp file lives alongside *path* so the final rename never crosses
    a filesystem boundary. Permissions: *mode* if given, else an existing
    file's bits are preserved, else the umask applies as it would for a
    plain ``open()``. The temp file is never more permissive than the final
    target, so restricted content is not briefly exposed. On failure the
    temp file is removed and *path* is untouched. If *path* is a symlink,
    the link itself is replaced by a regular file. Raises ``OSError``.
    """
    if mode is None and path.exists():
        mode = path.stat().st_mode
    # the umask masks the requested bits at creation; never touch the
    # process-wide umask (not thread-safe)
    create_mode = mode if mode is not None else 0o666
    fd, tmp = _reserve_temp(path, create_mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        if mode is not None:
            # restore any bits the umask cleared at creation; content is
            # destined for this mode anyway, so no exposure window
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
