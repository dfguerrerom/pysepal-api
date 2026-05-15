"""Path handling for SEPAL user-files routes.

SEPAL user-files write/create endpoints expect POSIX paths relative to the
sandbox user's home (`/home/sepal-user`). pysepal callers historically pass
either absolute paths under that home or already-relative paths; both must
work transparently. The listing endpoint additionally accepts `"/"` as a
shortcut for the workspace root, which the server understands as `"."`.
"""

from __future__ import annotations

from pathlib import PurePosixPath

BASE_REMOTE_PATH = "/home/sepal-user"


def sanitize_write_path(file_path: str | PurePosixPath) -> PurePosixPath:
    """Sanitize a path for write/create endpoints.

    Rules:
    - Absolute paths must live under `/home/sepal-user`; the prefix is stripped.
    - Relative paths pass through.
    - `..` traversal in either form is rejected.
    - Anything else absolute is rejected.
    """
    p = PurePosixPath(str(file_path))
    base = PurePosixPath(BASE_REMOTE_PATH)

    if p.is_absolute():
        try:
            rel = p.relative_to(base)
        except ValueError:
            raise ValueError(
                f"sanitize_write_path: expected absolute path under {base}, got {p}"
            ) from None
        if ".." in rel.parts:
            raise ValueError(f"sanitize_write_path: path traversal detected: {p}")
        return rel

    if ".." in p.parts:
        raise ValueError(f"sanitize_write_path: path traversal detected: {p}")
    return p


def normalize_list_folder(folder: str | PurePosixPath) -> str:
    """Normalize a folder argument for the `listFiles` endpoint.

    `/` is treated as a pysepal compatibility alias for the workspace root and
    becomes `"."`. Absolute paths under `/home/sepal-user` are stripped to
    relative form. Relative paths pass through.
    """
    s = str(folder)
    if s in ("", "/"):
        return "."
    p = PurePosixPath(s)
    base = PurePosixPath(BASE_REMOTE_PATH)
    if p.is_absolute():
        try:
            rel = p.relative_to(base)
        except ValueError:
            raise ValueError(
                f"normalize_list_folder: expected absolute path under {base}, got {p}"
            ) from None
        return str(rel) or "."
    return s
