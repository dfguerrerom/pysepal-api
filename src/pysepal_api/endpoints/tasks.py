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

import time
from typing import Any

import httpx

from ..models import Task, TaskState
from ..transport import parse_json, send_with_error_mapping, send_with_error_mapping_async


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

    def cancel(self, task_id: str) -> None:
        request = self._http.build_request(
            "POST", f"/api/tasks/task/{task_id}/cancel"
        )
        send_with_error_mapping(self._http, request)

    def remove(self, task_id: str) -> None:
        request = self._http.build_request(
            "POST", f"/api/tasks/task/{task_id}/remove"
        )
        send_with_error_mapping(self._http, request)

    def restart(self, task_id: str) -> None:
        """Maps to SEPAL's `execute` route."""
        request = self._http.build_request(
            "POST", f"/api/tasks/task/{task_id}/execute"
        )
        send_with_error_mapping(self._http, request)

    def wait(
        self,
        task_id: str,
        *,
        poll: float = 5.0,
        timeout: float | None = None,
    ) -> Task:
        """Poll `get(task_id)` until terminal. Raises on FAILED/CANCELED.

        Terminal states: COMPLETED, FAILED, CANCELED. CANCELING is non-terminal
        because the server has not finished the cancel handshake yet.
        """
        from ..errors import TaskCanceled, TaskFailed

        start = time.monotonic()
        while True:
            task = self.get(task_id)
            if task.state is TaskState.COMPLETED:
                return task
            if task.state is TaskState.FAILED:
                raise TaskFailed(f"Task {task_id} failed: {task.status_description}")
            if task.state is TaskState.CANCELED:
                raise TaskCanceled(f"Task {task_id} was canceled")
            if timeout is not None and time.monotonic() - start >= timeout:
                raise TimeoutError(
                    f"Task {task_id} did not reach terminal state in {timeout}s"
                )
            time.sleep(poll)


class AsyncTasksEndpoint:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def submit(
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
        response = await send_with_error_mapping_async(self._http, request)
        return Task.model_validate(parse_json(response))

    async def list(
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
        response = await send_with_error_mapping_async(self._http, request)
        return [Task.model_validate(item) for item in parse_json(response) or []]

    async def get(self, task_id: str, *, details: bool = False) -> Task:
        suffix = "/details" if details else ""
        request = self._http.build_request(
            "GET", f"/api/tasks/task/{task_id}{suffix}"
        )
        response = await send_with_error_mapping_async(self._http, request)
        return Task.model_validate(parse_json(response))

    async def cancel(self, task_id: str) -> None:
        request = self._http.build_request(
            "POST", f"/api/tasks/task/{task_id}/cancel"
        )
        await send_with_error_mapping_async(self._http, request)

    async def remove(self, task_id: str) -> None:
        request = self._http.build_request(
            "POST", f"/api/tasks/task/{task_id}/remove"
        )
        await send_with_error_mapping_async(self._http, request)

    async def restart(self, task_id: str) -> None:
        request = self._http.build_request(
            "POST", f"/api/tasks/task/{task_id}/execute"
        )
        await send_with_error_mapping_async(self._http, request)

    async def wait(
        self,
        task_id: str,
        *,
        poll: float = 5.0,
        timeout: float | None = None,
    ) -> Task:
        import asyncio

        from ..errors import TaskCanceled, TaskFailed

        start = time.monotonic()
        while True:
            task = await self.get(task_id)
            if task.state is TaskState.COMPLETED:
                return task
            if task.state is TaskState.FAILED:
                raise TaskFailed(f"Task {task_id} failed: {task.status_description}")
            if task.state is TaskState.CANCELED:
                raise TaskCanceled(f"Task {task_id} was canceled")
            if timeout is not None and time.monotonic() - start >= timeout:
                raise TimeoutError(
                    f"Task {task_id} did not reach terminal state in {timeout}s"
                )
            await asyncio.sleep(poll)
