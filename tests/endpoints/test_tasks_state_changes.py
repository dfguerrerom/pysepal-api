import httpx
import pytest
import respx

from pysepal_api.endpoints.tasks import TasksEndpoint


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_cancel_posts(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/tasks/task/t-1/cancel").respond(204)
        endpoint = TasksEndpoint(http)
        endpoint.cancel("t-1")
        assert route.called


def test_remove_posts(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/tasks/task/t-1/remove").respond(204)
        endpoint = TasksEndpoint(http)
        endpoint.remove("t-1")
        assert route.called


def test_restart_posts_execute_route(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/tasks/task/t-1/execute").respond(204)
        endpoint = TasksEndpoint(http)
        endpoint.restart("t-1")
        assert route.called
