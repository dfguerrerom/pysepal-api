"""SEPAL user-files endpoint.

Confirmed routes (v0):

- `GET  /api/user-files/listFiles`
- `GET  /api/user-files/download`
- `POST /api/user-files/setFile`
- `POST /api/user-files/createFolder`

The request/response logic for each operation lives once in the module-level
``_*_spec`` builders and ``_parse_*`` helpers; the sync and async classes are
thin wrappers that differ only by ``await``.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Any, Literal, overload

from ..errors import Conflict, Forbidden
from ..models import DirectoryListing, FileWriteResult
from ..paths import BASE_REMOTE_PATH, normalize_list_folder, sanitize_write_path
from ..transport import RequestSpec
from ..transport import parse_json as _parse_json
from ._base import _AsyncEndpoint, _SyncEndpoint

_MIME_BY_EXT: dict[str, str] = {
    ".json": "application/json",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def _list_spec(folder: str, extensions: Sequence[str] | None, include_hidden: bool) -> RequestSpec:
    return RequestSpec(
        "GET",
        "/api/user-files/listFiles",
        params={
            "path": normalize_list_folder(folder),
            "extensions": ",".join(extensions or []),
            "includeHidden": "true" if include_hidden else "false",
        },
    )


def _download_spec(file_path: str) -> RequestSpec:
    return RequestSpec(
        "GET",
        "/api/user-files/download",
        params={"path": str(sanitize_write_path(file_path))},
    )


def _set_spec(file_path: str, content: str | bytes, overwrite: bool) -> RequestSpec:
    payload = content.encode("utf-8") if isinstance(content, str) else content
    relative = sanitize_write_path(file_path)
    mime = _MIME_BY_EXT.get(PurePosixPath(file_path).suffix.lower(), "application/octet-stream")
    return RequestSpec(
        "POST",
        "/api/user-files/setFile",
        params={"path": str(relative), "overwrite": "true" if overwrite else "false"},
        files={"file": (PurePosixPath(file_path).name, payload, mime)},
    )


def _mkdir_spec(path: str, parents: bool) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/api/user-files/createFolder",
        params={
            "path": str(sanitize_write_path(path)),
            "recursive": "true" if parents else "false",
        },
    )


def _module_dir_relative(module_name: str) -> PurePosixPath:
    return PurePosixPath("module_results") / module_name


class UserFilesEndpoint(_SyncEndpoint):
    def list(
        self,
        folder: str = ".",
        extensions: Sequence[str] | None = None,
        include_hidden: bool = False,
    ) -> DirectoryListing:
        resp = self._send(_list_spec(folder, extensions, include_hidden))
        return DirectoryListing.model_validate(_parse_json(resp))

    @overload
    def get(self, file_path: str, *, parse_json: Literal[False] = False) -> bytes: ...
    @overload
    def get(self, file_path: str, *, parse_json: Literal[True]) -> Any: ...

    def get(self, file_path: str, *, parse_json: bool = False) -> Any:
        """Download a file. Returns raw bytes unless `parse_json=True`."""
        resp = self._send(_download_spec(file_path))
        return resp.json() if parse_json else resp.content

    def set(
        self,
        file_path: str,
        content: str | bytes,
        *,
        overwrite: bool = False,
    ) -> FileWriteResult:
        """Upload a file via multipart/form-data. The form field is `file`.

        SEPAL returns 409 on `setFile` when the file exists and `overwrite` is
        false; legacy pysepal treated that as a soft success and so do we — an
        empty `FileWriteResult` is returned.
        """
        try:
            resp = self._send(_set_spec(file_path, content, overwrite))
        except Conflict:
            return FileWriteResult()
        return FileWriteResult.model_validate(_parse_json(resp) or {})

    def mkdir(self, path: str, *, parents: bool = True) -> PurePosixPath:
        """Create a folder under the user workspace; idempotent on 409/403.

        SEPAL returns 403 (not 409) for an already-existing folder in some
        deployments, so both are swallowed to keep `mkdir` idempotent.
        """
        relative = sanitize_write_path(path)
        try:
            self._send(_mkdir_spec(path, parents))
        except (Conflict, Forbidden):
            pass
        return relative

    def module_dir(self, module_name: str) -> PurePosixPath:
        """Create and return `/home/sepal-user/module_results/{module_name}`."""
        relative = _module_dir_relative(module_name)
        self.mkdir(str(relative), parents=True)
        return PurePosixPath(BASE_REMOTE_PATH) / relative


class AsyncUserFilesEndpoint(_AsyncEndpoint):
    async def list(
        self,
        folder: str = ".",
        extensions: Sequence[str] | None = None,
        include_hidden: bool = False,
    ) -> DirectoryListing:
        resp = await self._send(_list_spec(folder, extensions, include_hidden))
        return DirectoryListing.model_validate(_parse_json(resp))

    @overload
    async def get(self, file_path: str, *, parse_json: Literal[False] = False) -> bytes: ...
    @overload
    async def get(self, file_path: str, *, parse_json: Literal[True]) -> Any: ...

    async def get(self, file_path: str, *, parse_json: bool = False) -> Any:
        resp = await self._send(_download_spec(file_path))
        return resp.json() if parse_json else resp.content

    async def set(
        self,
        file_path: str,
        content: str | bytes,
        *,
        overwrite: bool = False,
    ) -> FileWriteResult:
        try:
            resp = await self._send(_set_spec(file_path, content, overwrite))
        except Conflict:
            return FileWriteResult()
        return FileWriteResult.model_validate(_parse_json(resp) or {})

    async def mkdir(self, path: str, *, parents: bool = True) -> PurePosixPath:
        relative = sanitize_write_path(path)
        try:
            await self._send(_mkdir_spec(path, parents))
        except (Conflict, Forbidden):
            pass
        return relative

    async def module_dir(self, module_name: str) -> PurePosixPath:
        relative = _module_dir_relative(module_name)
        await self.mkdir(str(relative), parents=True)
        return PurePosixPath(BASE_REMOTE_PATH) / relative
