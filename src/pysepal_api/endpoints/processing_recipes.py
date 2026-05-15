"""SEPAL processing-recipes endpoint stub. Methods land in Phase 4."""

from __future__ import annotations

import httpx


class ProcessingRecipesEndpoint:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http
