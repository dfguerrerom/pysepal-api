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

from ..models import Task, TaskState
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

    def list(
        self,
        status: TaskState | str | None = None,
        *,
        output_path: str | None = None,
        destination: str | None = None,
    ) -> list[Task]:
        params: dict[str, str] = {}
        if status is not None:
            params["status"] = status.value if isinstance(status, TaskState) else status
        if output_path is not None:
            params["outputPath"] = output_path
        if destination is not None:
            params["destination"] = destination
        request = self._http.build_request("GET", "/api/tasks", params=params)
        response = send_with_error_mapping(self._http, request)
        return [Task.model_validate(item) for item in parse_json(response) or []]

    def get(self, task_id: str, *, details: bool = False) -> Task:
        suffix = "/details" if details else ""
        request = self._http.build_request(
            "GET", f"/api/tasks/task/{task_id}{suffix}"
        )
        response = send_with_error_mapping(self._http, request)
        return Task.model_validate(parse_json(response))
