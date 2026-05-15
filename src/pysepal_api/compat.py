"""pysepal v3 compatibility surface.

`pysepal_api.compat.SepalClient` is a drop-in replacement for
`pysepal.scripts.sepal_client.SepalClient`. It subclasses the new
`SepalClient`, restores legacy method names, return shapes, and attributes
(`cookies`, `headers`, `verify_ssl`, …), and emits a `DeprecationWarning` at
construction time pointing callers at the new import path.

This class is the only public surface inside `pysepal_api` that wraps the
modern client to match pysepal v3 behavior. The pysepal shim file (Phase 6)
re-exports it.
"""

from __future__ import annotations

import warnings
from pathlib import PurePosixPath
from typing import Any

import httpx

from .auth import NoAuth
from .client import SepalClient as _ModernSepalClient
from .errors import Forbidden
from .paths import sanitize_write_path

_DEPRECATION_MESSAGE = (
    "pysepal.scripts.sepal_client.SepalClient is now provided by "
    "pysepal_api.compat.SepalClient as a thin compatibility shim. "
    "Import `pysepal_api.SepalClient` directly for new code; this shim "
    "will be removed in pysepal v4."
)


class SepalClient(_ModernSepalClient):
    """Legacy SepalClient surface for pysepal v3 callers."""

    def __init__(
        self,
        session_id: str | None = None,
        module_name: str | None = None,
        sepal_host: str | None = None,
        create_base_dir: bool = True,
        *,
        auth: httpx.Auth | None = None,
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
    ) -> None:
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
        super().__init__(
            session_id=session_id,
            module_name=module_name,
            auth=auth,
            base_url=base_url,
            sepal_host=sepal_host,
            create_base_dir=create_base_dir,
            timeout=timeout,
            verify=verify,
        )
        # Legacy attributes re-exposed for export_engine.py / FileInput / etc.
        self.cookies = (
            {"SEPAL-SESSIONID": session_id} if session_id else {}
        )
        self.headers = {"Accept": "application/json"}

    # ---- Legacy method shapes ------------------------------------------------

    def list_files(
        self, folder: str = "/", extensions: list[str] | None = None
    ) -> dict[str, Any]:
        listing = self.user_files.list(folder, extensions=extensions or [])
        return listing.model_dump(by_alias=True)

    def get_file(self, file_path: str, parse_json: bool = False) -> Any:
        return self.user_files.get(file_path, parse_json=parse_json)

    def set_file(
        self,
        file_path: str,
        content: str | bytes,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        result = self.user_files.set(file_path, content, overwrite=overwrite)
        return result.model_dump(by_alias=True, exclude_none=False)

    def get_remote_dir(
        self, folder: str, parents: bool = False
    ) -> PurePosixPath:
        return self.user_files.mkdir(folder, parents=parents)

    def sanitize_path(self, file_path: str) -> PurePosixPath:
        return sanitize_write_path(file_path)

    # ---- Hooks the legacy class exposed; keep for safety ---------------------

    @property
    def rest_call_supported(self) -> bool:
        """Legacy compatibility flag. Always True in the new client."""
        return True
