import httpx
import pytest
import respx

from pysepal_api.endpoints.tasks import TasksEndpoint
from pysepal_api.models import TaskState


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_list_returns_tasks(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.get("/api/tasks").respond(
            200,
            json=[
                {"id": "t-1", "status": "PENDING"},
                {"id": "t-2", "status": "ACTIVE"},
            ],
        )
        endpoint = TasksEndpoint(http)
        tasks = endpoint.list(status=TaskState.PENDING)
        assert [t.id for t in tasks] == ["t-1", "t-2"]
        assert route.calls.last.request.url.params["status"] == "PENDING"


def test_list_optional_query_filters(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.get("/api/tasks").respond(200, json=[])
        endpoint = TasksEndpoint(http)
        endpoint.list(output_path="x", destination="DRIVE")
        params = route.calls.last.request.url.params
        assert params["outputPath"] == "x"
        assert params["destination"] == "DRIVE"
        assert "status" not in params


def test_get_basic(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/tasks/task/t-1").respond(200, json={"id": "t-1", "state": "ACTIVE"})
        endpoint = TasksEndpoint(http)
        task = endpoint.get("t-1")
        assert task.state is TaskState.ACTIVE


def test_get_details_route(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.get("/api/tasks/task/t-1/details").respond(
            200,
            json={"id": "t-1", "state": "ACTIVE", "params": {"k": 1}},
        )
        endpoint = TasksEndpoint(http)
        task = endpoint.get("t-1", details=True)
        assert task.params == {"k": 1}
        assert route.called
