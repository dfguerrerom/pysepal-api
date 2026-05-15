import json

import httpx
import pytest
import respx

from pysepal_api.endpoints.processing_recipes import (
    ProcessingRecipesEndpoint,
)


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_list_returns_summaries(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/processing-recipes").respond(
            200,
            json=[
                {
                    "id": "r1",
                    "name": "Demo",
                    "type": "CLASSIFICATION",
                    "projectId": "p1",
                }
            ],
        )
        endpoint = ProcessingRecipesEndpoint(http)
        summaries = endpoint.list()
        assert summaries[0].id == "r1"
        assert summaries[0].project_id == "p1"


def test_get_parses_json_body_by_default(http: httpx.Client) -> None:
    body = {"id": "r1", "model": {"k": 1}}
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/processing-recipes/r1").respond(200, content=json.dumps(body).encode())
        endpoint = ProcessingRecipesEndpoint(http)
        result = endpoint.get("r1")
        assert result == body


def test_get_returns_bytes_when_requested(http: httpx.Client) -> None:
    raw = b'{"id": "r1"}'
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/processing-recipes/r1").respond(200, content=raw)
        endpoint = ProcessingRecipesEndpoint(http)
        assert endpoint.get("r1", parse_json=False) == raw
