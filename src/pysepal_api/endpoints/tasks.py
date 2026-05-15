"""SEPAL tasks endpoint.

Confirmed routes (v0):

- `POST   /api/tasks`
- `GET    /api/tasks`
- `GET    /api/tasks/task/{id}` (+ `/details`)
- `POST   /api/tasks/task/{id}/cancel`
- `POST   /api/tasks/task/{id}/remove`
- `POST   /api/tasks/task/{id}/execute`     (restart)
"""

from __future__ import annotations

from typing import Any

import httpx

from ..models import Task
from ..transport import parse_json, send_with_error_mapping


class TasksEndpoint:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def submit(
        self,
        operation: str,
        params: dict[str, Any],
        *,
        recipe_id: str | None = None,
        instance_type: str | None = None,
    ) -> Task:
        body: dict[str, Any] = {"operation": operation, "params": params}
        if recipe_id is not None:
            body["recipeId"] = recipe_id
        if instance_type is not None:
            body["instanceType"] = instance_type
        request = self._http.build_request("POST", "/api/tasks", json=body)
        response = send_with_error_mapping(self._http, request)
        return Task.model_validate(parse_json(response))
