"""Path handling for SEPAL user-files routes.

SEPAL user-files write/create endpoints expect POSIX paths relative to the
sandbox user's home (`/home/sepal-user`). pysepal callers historically pass
either absolute paths under that home or already-relative paths; both must
work transparently. The listing endpoint additionally accepts `"/"` as a
shortcut for the workspace root, which the server understands as `"."`.

All routes — read, write, create, *and* list — enforce the same sandbox
confinement: absolute paths must live under `/home/sepal-user`, and `..`
traversal is rejected everywhere via the shared `_reject_traversal` helper.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from .errors import InvalidPathError

BASE_REMOTE_PATH = "/home/sepal-user"


def _reject_traversal(path: PurePosixPath, *, origin: str) -> None:
    """Raise if `path` contains a `..` component."""
    if ".." in path.parts:
        raise InvalidPathError(f"{origin}: path traversal detected: {path}")


def _strip_home_prefix(path: PurePosixPath, *, origin: str) -> PurePosixPath:
    """Strip the `/home/sepal-user` prefix from an absolute path, or reject it."""
    base = PurePosixPath(BASE_REMOTE_PATH)
    try:
        return path.relative_to(base)
    except ValueError:
        raise InvalidPathError(
            f"{origin}: expected absolute path under {base}, got {path}"
        ) from None


def sanitize_write_path(file_path: str | PurePosixPath) -> PurePosixPath:
    """Sanitize a path for download/write/create endpoints.

    Rules:
    - Absolute paths must live under `/home/sepal-user`; the prefix is stripped.
    - Relative paths pass through.
    - `..` traversal in either form is rejected.
    - Anything else absolute is rejected.
    """
    p = PurePosixPath(str(file_path))
    if p.is_absolute():
        rel = _strip_home_prefix(p, origin="sanitize_write_path")
        _reject_traversal(rel, origin="sanitize_write_path")
        return rel
    _reject_traversal(p, origin="sanitize_write_path")
    return p


def normalize_list_folder(folder: str | PurePosixPath) -> str:
    """Normalize a folder argument for the `listFiles` endpoint.

    `/` is treated as a pysepal compatibility alias for the workspace root and
    becomes `"."`. Absolute paths under `/home/sepal-user` are stripped to
    relative form. Relative paths pass through. `..` traversal is rejected, so
    listing enforces the same sandbox confinement as the write/read routes.
    """
    s = str(folder)
    if s in ("", "/"):
        return "."
    p = PurePosixPath(s)
    if p.is_absolute():
        rel = _strip_home_prefix(p, origin="normalize_list_folder")
        _reject_traversal(rel, origin="normalize_list_folder")
        return str(rel) or "."
    _reject_traversal(p, origin="normalize_list_folder")
    return s
