import httpx
import pytest
import respx

from pysepal_api.endpoints.tasks import TasksEndpoint
from pysepal_api.errors import TaskCanceled, TaskFailed, TaskTimeout
from pysepal_api.models import TaskState


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_wait_returns_on_completed(http: httpx.Client, monkeypatch: pytest.MonkeyPatch) -> None:
    states = iter(["ACTIVE", "ACTIVE", "COMPLETED"])
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/tasks/task/t-1").mock(
            side_effect=lambda req: httpx.Response(200, json={"id": "t-1", "state": next(states)})
        )
        monkeypatch.setattr("time.sleep", lambda _: None)
        endpoint = TasksEndpoint(http)
        task = endpoint.wait("t-1", poll_interval=0.0)
        assert task.state.value == "COMPLETED"


def test_wait_failed_raises_with_task(http: httpx.Client, monkeypatch: pytest.MonkeyPatch) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/tasks/task/t-1").respond(
            200, json={"id": "t-1", "state": "FAILED", "statusDescription": "boom"}
        )
        monkeypatch.setattr("time.sleep", lambda _: None)
        endpoint = TasksEndpoint(http)
        with pytest.raises(TaskFailed) as ei:
            endpoint.wait("t-1", poll_interval=0.0)
        # the failed task rides along on the error, no re-fetch needed
        assert ei.value.task is not None
        assert ei.value.task.state is TaskState.FAILED
        assert ei.value.task.status_description == "boom"


def test_wait_canceled_raises(http: httpx.Client, monkeypatch: pytest.MonkeyPatch) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/tasks/task/t-1").respond(200, json={"id": "t-1", "state": "CANCELED"})
        monkeypatch.setattr("time.sleep", lambda _: None)
        endpoint = TasksEndpoint(http)
        with pytest.raises(TaskCanceled) as ei:
            endpoint.wait("t-1", poll_interval=0.0)
        assert ei.value.task is not None


def test_wait_timeout(http: httpx.Client, monkeypatch: pytest.MonkeyPatch) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/tasks/task/t-1").respond(200, json={"id": "t-1", "state": "ACTIVE"})
        monkeypatch.setattr("time.sleep", lambda _: None)
        # Fake monotonic clock: 0, 1, 2, 3, 4, …
        clock = iter([0, 1, 2, 3, 4, 5])
        monkeypatch.setattr("time.monotonic", lambda: next(clock))
        endpoint = TasksEndpoint(http)
        # catchable as the builtin TimeoutError, carrying the last-seen task
        with pytest.raises(TimeoutError) as ei:
            endpoint.wait("t-1", poll_interval=0.0, timeout=2)
        assert isinstance(ei.value, TaskTimeout)
        assert ei.value.task is not None
        assert ei.value.task.state is TaskState.ACTIVE
