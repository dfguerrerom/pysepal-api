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
from ..transport import parse_json, send_with_error_mapping


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
