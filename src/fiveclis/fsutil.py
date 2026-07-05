import os
import secrets
from pathlib import Path


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
    while True:
        tmp = path.parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
        try:
            fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, create_mode)
            break
        except FileExistsError:  # pragma: no cover — token collision
            continue
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
