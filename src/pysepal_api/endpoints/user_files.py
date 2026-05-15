"""SEPAL user-files endpoint.

Confirmed routes (v0):

- `GET  /api/user-files/listFiles`
- `GET  /api/user-files/download`
- `POST /api/user-files/setFile`
- `POST /api/user-files/createFolder`
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any

import httpx

from ..models import DirectoryListing, FileWriteResult
from ..paths import BASE_REMOTE_PATH, normalize_list_folder, sanitize_write_path
from ..transport import parse_json, send_with_error_mapping, send_with_error_mapping_async
from ..errors import Conflict, Forbidden


class UserFilesEndpoint:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def list(
        self,
        folder: str = ".",
        extensions: Sequence[str] | None = None,
        include_hidden: bool = False,
    ) -> DirectoryListing:
        request = self._http.build_request(
            "GET",
            "/api/user-files/listFiles",
            params={
                "path": normalize_list_folder(folder),
                "extensions": ",".join(extensions or []),
                "includeHidden": "true" if include_hidden else "false",
            },
        )
        response = send_with_error_mapping(self._http, request)
        return DirectoryListing.model_validate(parse_json(response))

    def get(self, file_path: str, *, parse_json: bool = False) -> Any:
        """Download a file. Returns raw bytes unless `parse_json=True`."""
        request = self._http.build_request(
            "GET",
            "/api/user-files/download",
            params={"path": str(sanitize_write_path(file_path))},
        )
        response = send_with_error_mapping(self._http, request)
        if parse_json:
            return response.json()
        return response.content

    _MIME_BY_EXT = {
        ".json": "application/json",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }

    def set(
        self,
        file_path: str,
        content: str | bytes,
        *,
        overwrite: bool = False,
    ) -> FileWriteResult:
        """Upload a file via multipart/form-data. The form field is `file`.

        Legacy pysepal treated a 409 on `setFile` (already exists, overwrite
        false) as a soft success. We preserve that behavior so existing
        notebooks keep working.
        """
        payload = content.encode("utf-8") if isinstance(content, str) else content
        relative = sanitize_write_path(file_path)
        suffix = PurePosixPath(file_path).suffix.lower()
        mime = self._MIME_BY_EXT.get(suffix, "application/octet-stream")

        request = self._http.build_request(
            "POST",
            "/api/user-files/setFile",
            params={
                "path": str(relative),
                "overwrite": "true" if overwrite else "false",
            },
            files={"file": (PurePosixPath(file_path).name, payload, mime)},
        )
        try:
            response = send_with_error_mapping(self._http, request)
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, Conflict):
                return FileWriteResult()
            raise
        body = parse_json(response) or {}
        return FileWriteResult.model_validate(body)

    def mkdir(
        self, path: str, *, parents: bool = True
    ) -> PurePosixPath:
        """Create a folder under the user workspace; idempotent on 409/403."""
        relative = sanitize_write_path(path)
        request = self._http.build_request(
            "POST",
            "/api/user-files/createFolder",
            params={
                "path": str(relative),
                "recursive": "true" if parents else "false",
            },
        )
        try:
            send_with_error_mapping(self._http, request)
        except (Conflict, Forbidden):
            pass
        return relative

    def module_dir(self, module_name: str) -> PurePosixPath:
        """Create and return `/home/sepal-user/module_results/{module_name}`."""
        relative = PurePosixPath("module_results") / module_name
        self.mkdir(str(relative), parents=True)
        return PurePosixPath(BASE_REMOTE_PATH) / relative


class AsyncUserFilesEndpoint:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    _MIME_BY_EXT = UserFilesEndpoint._MIME_BY_EXT  # share table

    async def list(
        self,
        folder: str = ".",
        extensions: Sequence[str] | None = None,
        include_hidden: bool = False,
    ) -> DirectoryListing:
        request = self._http.build_request(
            "GET",
            "/api/user-files/listFiles",
            params={
                "path": normalize_list_folder(folder),
                "extensions": ",".join(extensions or []),
                "includeHidden": "true" if include_hidden else "false",
            },
        )
        response = await send_with_error_mapping_async(self._http, request)
        return DirectoryListing.model_validate(parse_json(response))

    async def get(self, file_path: str, *, parse_json: bool = False) -> Any:
        request = self._http.build_request(
            "GET",
            "/api/user-files/download",
            params={"path": str(sanitize_write_path(file_path))},
        )
        response = await send_with_error_mapping_async(self._http, request)
        if parse_json:
            return response.json()
        return response.content

    async def set(
        self,
        file_path: str,
        content: str | bytes,
        *,
        overwrite: bool = False,
    ) -> FileWriteResult:
        payload = content.encode("utf-8") if isinstance(content, str) else content
        relative = sanitize_write_path(file_path)
        suffix = PurePosixPath(file_path).suffix.lower()
        mime = self._MIME_BY_EXT.get(suffix, "application/octet-stream")
        request = self._http.build_request(
            "POST",
            "/api/user-files/setFile",
            params={
                "path": str(relative),
                "overwrite": "true" if overwrite else "false",
            },
            files={"file": (PurePosixPath(file_path).name, payload, mime)},
        )
        try:
            response = await send_with_error_mapping_async(self._http, request)
        except Conflict:
            return FileWriteResult()
        body = parse_json(response) or {}
        return FileWriteResult.model_validate(body)

    async def mkdir(
        self, path: str, *, parents: bool = True
    ) -> PurePosixPath:
        relative = sanitize_write_path(path)
        request = self._http.build_request(
            "POST",
            "/api/user-files/createFolder",
            params={
                "path": str(relative),
                "recursive": "true" if parents else "false",
            },
        )
        try:
            await send_with_error_mapping_async(self._http, request)
        except (Conflict, Forbidden):
            pass
        return relative

    async def module_dir(self, module_name: str) -> PurePosixPath:
        relative = PurePosixPath("module_results") / module_name
        await self.mkdir(str(relative), parents=True)
        return PurePosixPath(BASE_REMOTE_PATH) / relative
