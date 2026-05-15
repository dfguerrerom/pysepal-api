import httpx
import pytest
import respx

from pysepal_api.endpoints.tasks import TasksEndpoint
from pysepal_api.errors import TaskCanceled, TaskFailed


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
        task = endpoint.wait("t-1", poll=0.0)
        assert task.state.value == "COMPLETED"


def test_wait_failed_raises(http: httpx.Client, monkeypatch: pytest.MonkeyPatch) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/tasks/task/t-1").respond(200, json={"id": "t-1", "state": "FAILED"})
        monkeypatch.setattr("time.sleep", lambda _: None)
        endpoint = TasksEndpoint(http)
        with pytest.raises(TaskFailed):
            endpoint.wait("t-1", poll=0.0)


def test_wait_canceled_raises(http: httpx.Client, monkeypatch: pytest.MonkeyPatch) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/tasks/task/t-1").respond(200, json={"id": "t-1", "state": "CANCELED"})
        monkeypatch.setattr("time.sleep", lambda _: None)
        endpoint = TasksEndpoint(http)
        with pytest.raises(TaskCanceled):
            endpoint.wait("t-1", poll=0.0)


def test_wait_timeout(http: httpx.Client, monkeypatch: pytest.MonkeyPatch) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/tasks/task/t-1").respond(200, json={"id": "t-1", "state": "ACTIVE"})
        monkeypatch.setattr("time.sleep", lambda _: None)
        # Fake monotonic clock: 0, 1, 2, 3, 4, …
        clock = iter([0, 1, 2, 3, 4, 5])
        monkeypatch.setattr("time.monotonic", lambda: next(clock))
        endpoint = TasksEndpoint(http)
        with pytest.raises(TimeoutError):
            endpoint.wait("t-1", poll=0.0, timeout=2)
