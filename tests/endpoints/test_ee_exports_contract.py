"""Golden-payload contract test.

Locks the exact ``ee.export`` task ``params`` emitted by the pysepal-api export
builder against the shape consumed by the SEPAL worker on branch
``feat/taskmanager-ee-export`` (see its ``eeExport.contract.test.js``). Any
client/server drift breaks this unit test.
"""

import json

import httpx
import pytest
import respx

from pysepal_api.endpoints.ee_exports import EEExportsEndpoint
from pysepal_api.endpoints.tasks import TasksEndpoint

# Cloud API expression dicts, matching the JS contract test fixtures.
IMAGE_EXPRESSION = {
    "result": "image",
    "values": {
        "image": {"functionInvocationValue": {"functionName": "Image.normalizedDifference"}}
    },
}
REGION_EXPRESSION = {
    "result": "region",
    "values": {
        "region": {"functionInvocationValue": {"functionName": "GeometryConstructors.Polygon"}}
    },
}
TABLE_EXPRESSION = {
    "result": "table",
    "values": {"table": {"functionInvocationValue": {"functionName": "Collection.loadTable"}}},
}

IMAGE_TO_SEPAL_GOLDEN = {
    "title": "Export ndvi to SEPAL",
    "description": "ndvi",
    "export": {
        "kind": "IMAGE",
        "destination": "SEPAL",
        "expression": IMAGE_EXPRESSION,
        "region": REGION_EXPRESSION,
        "scale": 30,
        "maxPixels": 10000000000000,
        "fileFormat": "GEO_TIFF",
        "workspacePath": "module_results/demo/exports",
        "filenamePrefix": "ndvi",
    },
    "taskInfo": {
        "destination": "SEPAL",
        "outputPath": "module_results/demo/exports",
        "source": "pysepal-api",
        "kind": "IMAGE",
    },
}

TABLE_TO_GEE_GOLDEN = {
    "title": "Export plots to GEE",
    "description": "plots",
    "export": {
        "kind": "TABLE",
        "destination": "GEE",
        "expression": TABLE_EXPRESSION,
        "fileFormat": "SHP",
        "assetId": "projects/my-project/assets/exports/plots",
        "selectors": ["id", "class"],
        "maxVertices": 1000000,
    },
    "taskInfo": {
        "destination": "GEE",
        "outputPath": "projects/my-project/assets/exports/plots",
        "source": "pysepal-api",
        "kind": "TABLE",
    },
}


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def _submitted_params(mock: respx.MockRouter) -> dict:
    body = json.loads(mock.calls.last.request.content)
    assert body["operation"] == "ee.export"
    return body["params"]


def test_image_to_sepal_matches_golden(http: httpx.Client) -> None:
    endpoint = EEExportsEndpoint(TasksEndpoint(http))
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/tasks").respond(200, json={"id": "t-1", "state": "PENDING"})
        endpoint.submit_image(
            image=IMAGE_EXPRESSION,
            region=REGION_EXPRESSION,
            destination="SEPAL",
            name="ndvi",
            scale=30,
            workspace_path="module_results/demo/exports",
            filename_prefix="ndvi",
        )
        assert _submitted_params(mock) == IMAGE_TO_SEPAL_GOLDEN


def test_table_to_gee_matches_golden(http: httpx.Client) -> None:
    endpoint = EEExportsEndpoint(TasksEndpoint(http))
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/tasks").respond(200, json={"id": "t-2", "state": "PENDING"})
        endpoint.submit_table(
            collection=TABLE_EXPRESSION,
            destination="GEE",
            name="plots",
            asset_id="projects/my-project/assets/exports/plots",
            selectors=["id", "class"],
            max_vertices=1000000,
        )
        assert _submitted_params(mock) == TABLE_TO_GEE_GOLDEN
