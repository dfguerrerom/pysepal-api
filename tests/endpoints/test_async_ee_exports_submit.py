import json

import httpx
import pytest
import respx

from pysepal_api.endpoints.ee_exports import AsyncEEExportsEndpoint
from pysepal_api.endpoints.tasks import AsyncTasksEndpoint


@pytest.fixture
def http() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url="https://sepal.test", timeout=5.0)


async def test_submit_image_to_drive(http: httpx.AsyncClient) -> None:
    expr = {"result": "0", "values": {}}
    endpoint = AsyncEEExportsEndpoint(AsyncTasksEndpoint(http))
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/tasks").respond(200, json={"id": "t-9", "state": "PENDING"})
        task = await endpoint.submit_image(
            image=expr,
            destination="DRIVE",
            name="ndvi_2026",
            scale=30,
            drive_folder="SEPAL/exports",
            filename_prefix="ndvi_2026",
        )
    body = json.loads(route.calls.last.request.content)
    assert body["operation"] == "ee.export"
    params = body["params"]
    assert params["export"] == {
        "kind": "IMAGE",
        "destination": "DRIVE",
        "expression": expr,
        "scale": 30,
        "maxPixels": 10000000000000,
        "fileFormat": "GEO_TIFF",
        "driveFolder": "SEPAL/exports",
        "filenamePrefix": "ndvi_2026",
    }
    assert params["taskInfo"] == {
        "destination": "DRIVE",
        "outputPath": "SEPAL/exports",
        "filenamePrefix": "ndvi_2026",
        "source": "pysepal-api",
        "kind": "IMAGE",
    }
    assert task.id == "t-9"


async def test_async_table_to_gee_requires_asset_id(http: httpx.AsyncClient) -> None:
    endpoint = AsyncEEExportsEndpoint(AsyncTasksEndpoint(http))
    with pytest.raises(ValueError):
        await endpoint.submit_table(
            collection={"result": "0", "values": {}}, destination="GEE", name="x"
        )
