import json

import httpx
import pytest
import respx

from pysepal_api.endpoints.tasks import TasksEndpoint
from pysepal_api.models import TaskState


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_submit_posts_task_body(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/tasks").respond(
            200,
            json={
                "id": "t-1",
                "operation": "imageAssetExport",
                "state": "PENDING",
            },
        )
        endpoint = TasksEndpoint(http)
        task = endpoint.submit(
            operation="imageAssetExport",
            params={"title": "demo"},
            recipe_id="r-1",
            instance_type="instance-medium",
        )
        body = json.loads(route.calls.last.request.content)
        assert body == {
            "operation": "imageAssetExport",
            "params": {"title": "demo"},
            "recipeId": "r-1",
            "instanceType": "instance-medium",
        }
        assert task.id == "t-1"
        assert task.state is TaskState.PENDING


def test_submit_omits_optional_keys(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/tasks").respond(200, json={"id": "t-2", "state": "PENDING"})
        endpoint = TasksEndpoint(http)
        endpoint.submit(operation="x", params={})
        body = json.loads(route.calls.last.request.content)
        assert body == {"operation": "x", "params": {}}
