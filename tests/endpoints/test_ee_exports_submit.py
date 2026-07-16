import json
import sys

import httpx
import pytest
import respx

from pysepal_api.endpoints.ee_exports import (
    EEExportsEndpoint,
    serialize_ee_object,
)
from pysepal_api.endpoints.tasks import TasksEndpoint
from pysepal_api.errors import MissingDependency, PysepalError


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def _endpoint(http: httpx.Client) -> EEExportsEndpoint:
    return EEExportsEndpoint(TasksEndpoint(http))


def test_submit_image_to_sepal(http: httpx.Client) -> None:
    expr = {"result": "0", "values": {}}
    region = {"result": "1", "values": {}}
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/tasks").respond(200, json={"id": "t-1", "state": "PENDING"})
        task = _endpoint(http).submit_image(
            image=expr,
            destination="SEPAL",
            name="ndvi_2026",
            region=region,
            scale=30,
            crs="EPSG:4326",
            workspace_path="module_results/my_module/exports",
            filename_prefix="ndvi_2026",
        )
    body = json.loads(route.calls.last.request.content)
    assert body["operation"] == "ee.export"
    params = body["params"]
    assert params["title"] == "Export ndvi_2026 to SEPAL"
    assert params["description"] == "ndvi_2026"
    assert params["export"] == {
        "kind": "IMAGE",
        "destination": "SEPAL",
        "expression": expr,
        "region": region,
        "scale": 30,
        "crs": "EPSG:4326",
        "maxPixels": 10000000000000,
        "fileFormat": "GEO_TIFF",
        "workspacePath": "module_results/my_module/exports",
        "filenamePrefix": "ndvi_2026",
    }
    assert params["taskInfo"] == {
        "destination": "SEPAL",
        "outputPath": "module_results/my_module/exports",
        "source": "pysepal-api",
        "kind": "IMAGE",
    }
    assert task.id == "t-1"


def test_submit_table_to_gee(http: httpx.Client) -> None:
    expr = {"result": "0", "values": {}}
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/tasks").respond(200, json={"id": "t-2", "state": "PENDING"})
        task = _endpoint(http).submit_table(
            collection=expr,
            destination="GEE",
            name="plots",
            asset_id="projects/my-project/assets/plots",
            selectors=["id"],
            max_vertices=1_000_000,
        )
    params = json.loads(route.calls.last.request.content)["params"]
    assert params["export"] == {
        "kind": "TABLE",
        "destination": "GEE",
        "expression": expr,
        "fileFormat": "SHP",
        "assetId": "projects/my-project/assets/plots",
        "selectors": ["id"],
        "maxVertices": 1_000_000,
    }
    assert params["taskInfo"] == {
        "destination": "GEE",
        "outputPath": "projects/my-project/assets/plots",
        "source": "pysepal-api",
        "kind": "TABLE",
    }
    assert task.id == "t-2"


def test_gee_image_requires_asset_id(http: httpx.Client) -> None:
    with pytest.raises(ValueError):
        _endpoint(http).submit_image(
            image={"result": "0", "values": {}}, destination="GEE", name="x"
        )


def test_gee_table_requires_asset_id(http: httpx.Client) -> None:
    with pytest.raises(ValueError):
        _endpoint(http).submit_table(
            collection={"result": "0", "values": {}}, destination="GEE", name="x"
        )


def test_serialize_passthrough_mapping_returns_plain_dict() -> None:
    expr = {"result": "0", "values": {}}
    out = serialize_ee_object(expr)
    assert out == expr
    assert type(out) is dict
    assert out is not expr


def test_serialize_without_ee_raises_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "ee", None)
    with pytest.raises(MissingDependency) as excinfo:
        serialize_ee_object(object())
    assert isinstance(excinfo.value, PysepalError)
    assert "pysepal-api[ee]" in str(excinfo.value)
