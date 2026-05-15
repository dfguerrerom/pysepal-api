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
from ..transport import parse_json, send_with_error_mapping


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
