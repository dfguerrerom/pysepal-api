import gzip
import json

import httpx
import pytest
import respx

from pysepal_api.endpoints.recipes import (
    RecipesEndpoint,
)


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_save_gzips_contents_and_passes_query(http: httpx.Client) -> None:
    payload = {"layers": [{"id": "l1"}]}
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/processing-recipes/r1").respond(
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
        endpoint = RecipesEndpoint(http)
        summaries = endpoint.save(
            recipe_id="r1",
            project_id="p1",
            type="CLASSIFICATION",
            name="Demo",
            contents=payload,
        )
        request = route.calls.last.request
        assert request.url.params["projectId"] == "p1"
        assert request.url.params["type"] == "CLASSIFICATION"
        assert request.url.params["name"] == "Demo"
        assert request.headers["content-type"] == "application/gzip"
        decoded = gzip.decompress(request.content).decode()
        assert json.loads(decoded) == payload
        assert summaries[0].id == "r1"


def test_save_accepts_bytes_payload(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/processing-recipes/r1").respond(200, json=[])
        endpoint = RecipesEndpoint(http)
        endpoint.save(
            recipe_id="r1",
            project_id="p1",
            type="X",
            name="N",
            contents=b'{"already": "encoded"}',
        )
        body = gzip.decompress(route.calls.last.request.content)
        assert body == b'{"already": "encoded"}'


def test_delete_returns_updated_summaries(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.delete("/api/processing-recipes/r1").respond(
            200,
            json=[{"id": "r2", "name": "X", "type": "Y"}],
        )
        endpoint = RecipesEndpoint(http)
        summaries = endpoint.delete("r1")
        assert summaries[0].id == "r2"
