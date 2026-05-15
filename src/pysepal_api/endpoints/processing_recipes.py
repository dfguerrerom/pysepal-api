"""SEPAL processing-recipes endpoint.

Confirmed routes (v0):

- `GET    /api/processing-recipes`
- `GET    /api/processing-recipes/{id}`
- `POST   /api/processing-recipes/{id}`            (gzip body + query params)
- `DELETE /api/processing-recipes/{id}`
"""

from __future__ import annotations

import gzip
import json as _json
from typing import Any

import httpx

from ..models import RecipeSummary
from ..transport import parse_json, send_with_error_mapping, send_with_error_mapping_async


class ProcessingRecipesEndpoint:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def list(self) -> list[RecipeSummary]:
        request = self._http.build_request(
            "GET", "/api/processing-recipes"
        )
        response = send_with_error_mapping(self._http, request)
        return [
            RecipeSummary.model_validate(item)
            for item in parse_json(response) or []
        ]

    def get(self, recipe_id: str, *, parse_json: bool = True) -> Any:
        """Load a recipe. Returns the parsed JSON body unless `parse_json=False`."""
        request = self._http.build_request(
            "GET", f"/api/processing-recipes/{recipe_id}"
        )
        response = send_with_error_mapping(self._http, request)
        if not parse_json:
            return response.content
        return _json.loads(response.content)

    def save(
        self,
        recipe_id: str,
        *,
        project_id: str,
        type: str,
        name: str,
        contents: bytes | str | dict[str, Any] | list[Any],
    ) -> list[RecipeSummary]:
        """POST a recipe. SEPAL stores the gzipped body as-is; pass either
        already-encoded bytes/str or a JSON-serializable structure that the
        client will encode for you."""
        if isinstance(contents, (dict, list)):
            raw = _json.dumps(contents).encode("utf-8")
        elif isinstance(contents, str):
            raw = contents.encode("utf-8")
        else:
            raw = contents
        gz = gzip.compress(raw)
        request = self._http.build_request(
            "POST",
            f"/api/processing-recipes/{recipe_id}",
            params={"projectId": project_id, "type": type, "name": name},
            content=gz,
            headers={"Content-Type": "application/gzip"},
        )
        response = send_with_error_mapping(self._http, request)
        return [
            RecipeSummary.model_validate(item)
            for item in parse_json(response) or []
        ]

    def delete(self, recipe_id: str) -> list[RecipeSummary]:
        request = self._http.build_request(
            "DELETE", f"/api/processing-recipes/{recipe_id}"
        )
        response = send_with_error_mapping(self._http, request)
        return [
            RecipeSummary.model_validate(item)
            for item in parse_json(response) or []
        ]


class AsyncProcessingRecipesEndpoint:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def list(self) -> list[RecipeSummary]:
        request = self._http.build_request("GET", "/api/processing-recipes")
        response = await send_with_error_mapping_async(self._http, request)
        return [
            RecipeSummary.model_validate(item)
            for item in parse_json(response) or []
        ]

    async def get(self, recipe_id: str, *, parse_json: bool = True) -> Any:
        request = self._http.build_request(
            "GET", f"/api/processing-recipes/{recipe_id}"
        )
        response = await send_with_error_mapping_async(self._http, request)
        if not parse_json:
            return response.content
        return _json.loads(response.content)

    async def save(
        self,
        recipe_id: str,
        *,
        project_id: str,
        type: str,
        name: str,
        contents: bytes | str | dict[str, Any] | list[Any],
    ) -> list[RecipeSummary]:
        if isinstance(contents, (dict, list)):
            raw = _json.dumps(contents).encode("utf-8")
        elif isinstance(contents, str):
            raw = contents.encode("utf-8")
        else:
            raw = contents
        gz = gzip.compress(raw)
        request = self._http.build_request(
            "POST",
            f"/api/processing-recipes/{recipe_id}",
            params={"projectId": project_id, "type": type, "name": name},
            content=gz,
            headers={"Content-Type": "application/gzip"},
        )
        response = await send_with_error_mapping_async(self._http, request)
        return [
            RecipeSummary.model_validate(item)
            for item in parse_json(response) or []
        ]

    async def delete(self, recipe_id: str) -> list[RecipeSummary]:
        request = self._http.build_request(
            "DELETE", f"/api/processing-recipes/{recipe_id}"
        )
        response = await send_with_error_mapping_async(self._http, request)
        return [
            RecipeSummary.model_validate(item)
            for item in parse_json(response) or []
        ]
