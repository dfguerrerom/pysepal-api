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

import asyncio
import time
from typing import Any

from ..errors import TaskCanceled, TaskFailed, TaskTimeout
from ..models import Task, TaskState
from ..transport import RequestSpec, parse_many, parse_one
from ._base import _AsyncEndpoint, _SyncEndpoint


def _submit_spec(
    operation: str,
    params: dict[str, Any],
    recipe_id: str | None,
    instance_type: str | None,
) -> RequestSpec:
    body: dict[str, Any] = {"operation": operation, "params": params}
    if recipe_id is not None:
        body["recipeId"] = recipe_id
    if instance_type is not None:
        body["instanceType"] = instance_type
    return RequestSpec("POST", "/api/tasks", json=body)


def _list_spec(
    status: TaskState | str | None,
    output_path: str | None,
    destination: str | None,
) -> RequestSpec:
    params: dict[str, str] = {}
    if status is not None:
        params["status"] = status.value if isinstance(status, TaskState) else status
    if output_path is not None:
        params["outputPath"] = output_path
    if destination is not None:
        params["destination"] = destination
    return RequestSpec("GET", "/api/tasks", params=params)


def _get_spec(task_id: str, details: bool) -> RequestSpec:
    suffix = "/details" if details else ""
    return RequestSpec("GET", f"/api/tasks/task/{task_id}{suffix}")


def _action_spec(task_id: str, action: str) -> RequestSpec:
    return RequestSpec("POST", f"/api/tasks/task/{task_id}/{action}")


def _wait_step(task: Task, task_id: str) -> Task | None:
    """Shared terminal-state logic: return the task if done, raise on
    FAILED/CANCELED, or return None to keep polling.

    CANCELING is non-terminal — the server has not finished the cancel
    handshake yet.
    """
    if task.state is TaskState.COMPLETED:
        return task
    if task.state is TaskState.FAILED:
        raise TaskFailed(f"Task {task_id} failed: {task.status_description}")
    if task.state is TaskState.CANCELED:
        raise TaskCanceled(f"Task {task_id} was canceled")
    return None


class TasksEndpoint(_SyncEndpoint):
    def submit(
        self,
        operation: str,
        params: dict[str, Any],
        *,
        recipe_id: str | None = None,
        instance_type: str | None = None,
    ) -> Task:
        resp = self._send(_submit_spec(operation, params, recipe_id, instance_type))
        return parse_one(resp, Task)

    def list(
        self,
        status: TaskState | str | None = None,
        *,
        output_path: str | None = None,
        destination: str | None = None,
    ) -> list[Task]:
        resp = self._send(_list_spec(status, output_path, destination))
        return parse_many(resp, Task)

    def get(self, task_id: str, *, details: bool = False) -> Task:
        resp = self._send(_get_spec(task_id, details))
        return parse_one(resp, Task)

    def cancel(self, task_id: str) -> None:
        self._send(_action_spec(task_id, "cancel"))

    def remove(self, task_id: str) -> None:
        self._send(_action_spec(task_id, "remove"))

    def restart(self, task_id: str) -> None:
        """Maps to SEPAL's `execute` route."""
        self._send(_action_spec(task_id, "execute"))

    def wait(self, task_id: str, *, poll: float = 5.0, timeout: float | None = None) -> Task:
        """Poll `get(task_id)` until terminal. Raises on FAILED/CANCELED/timeout."""
        start = time.monotonic()
        while True:
            done = _wait_step(self.get(task_id), task_id)
            if done is not None:
                return done
            if timeout is not None and time.monotonic() - start >= timeout:
                raise TaskTimeout(f"Task {task_id} did not reach terminal state in {timeout}s")
            time.sleep(poll)


class AsyncTasksEndpoint(_AsyncEndpoint):
    async def submit(
        self,
        operation: str,
        params: dict[str, Any],
        *,
        recipe_id: str | None = None,
        instance_type: str | None = None,
    ) -> Task:
        resp = await self._send(_submit_spec(operation, params, recipe_id, instance_type))
        return parse_one(resp, Task)

    async def list(
        self,
        status: TaskState | str | None = None,
        *,
        output_path: str | None = None,
        destination: str | None = None,
    ) -> list[Task]:
        resp = await self._send(_list_spec(status, output_path, destination))
        return parse_many(resp, Task)

    async def get(self, task_id: str, *, details: bool = False) -> Task:
        resp = await self._send(_get_spec(task_id, details))
        return parse_one(resp, Task)

    async def cancel(self, task_id: str) -> None:
        await self._send(_action_spec(task_id, "cancel"))

    async def remove(self, task_id: str) -> None:
        await self._send(_action_spec(task_id, "remove"))

    async def restart(self, task_id: str) -> None:
        await self._send(_action_spec(task_id, "execute"))

    async def wait(self, task_id: str, *, poll: float = 5.0, timeout: float | None = None) -> Task:
        start = time.monotonic()
        while True:
            done = _wait_step(await self.get(task_id), task_id)
            if done is not None:
                return done
            if timeout is not None and time.monotonic() - start >= timeout:
                raise TaskTimeout(f"Task {task_id} did not reach terminal state in {timeout}s")
            await asyncio.sleep(poll)
