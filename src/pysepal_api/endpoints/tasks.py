"""SEPAL tasks endpoint stub. Methods land in Phase 3."""

from __future__ import annotations

import httpx


class TasksEndpoint:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http
