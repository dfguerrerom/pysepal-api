"""The ``taskInfo.origin`` an export carries, so SEPAL's task list can show
where it came from: the notebook, script or app that submitted it."""

import json
import sys
import types
from typing import Any

import pytest
import respx

from pysepal_api import AsyncSepalClient, NoAuth, SepalClient

HOME = "/home/alice"


@pytest.fixture(autouse=True)
def sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    """A sandbox with no notebook, script or app context unless a test adds one."""
    monkeypatch.setenv("HOME", HOME)
    monkeypatch.delenv("JPY_SESSION_NAME", raising=False)
    monkeypatch.setitem(sys.modules, "__main__", types.ModuleType("__main__"))


def test_notebook_export_names_the_notebook_relative_to_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JPY_SESSION_NAME", f"{HOME}/module_results/2024/analysis.ipynb")

    origin = submitted_origin(SepalClient(base_url="https://sepal.test", auth=NoAuth()))

    assert origin == {"type": "NOTEBOOK", "path": "module_results/2024/analysis.ipynb"}


def test_notebook_path_already_relative_to_the_jupyter_root_is_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JPY_SESSION_NAME", "work/analysis.ipynb")

    origin = submitted_origin(SepalClient(base_url="https://sepal.test", auth=NoAuth()))

    assert origin == {"type": "NOTEBOOK", "path": "work/analysis.ipynb"}


def test_vscode_notebook_export_names_the_notebook() -> None:
    sys.modules["__main__"].__vsc_ipynb_file__ = f"{HOME}/work/explore.ipynb"  # type: ignore[attr-defined]

    origin = submitted_origin(SepalClient(base_url="https://sepal.test", auth=NoAuth()))

    assert origin == {"type": "NOTEBOOK", "path": "work/explore.ipynb"}


def test_script_export_names_the_script_relative_to_home() -> None:
    sys.modules["__main__"].__file__ = f"{HOME}/scripts/export.py"

    origin = submitted_origin(SepalClient(base_url="https://sepal.test", auth=NoAuth()))

    assert origin == {"type": "SCRIPT", "path": "scripts/export.py"}


def test_script_outside_home_keeps_its_absolute_path() -> None:
    sys.modules["__main__"].__file__ = "/opt/jobs/export.py"

    origin = submitted_origin(SepalClient(base_url="https://sepal.test", auth=NoAuth()))

    assert origin == {"type": "SCRIPT", "path": "/opt/jobs/export.py"}


def test_app_signed_in_with_a_browser_session_is_an_app() -> None:
    origin = submitted_origin(SepalClient(base_url="https://sepal.test", session_id="sid-xyz"))

    assert origin == {"type": "APP"}


def test_app_name_identifies_the_app_over_any_notebook_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JPY_SESSION_NAME", f"{HOME}/apps/ui.ipynb")

    origin = submitted_origin(
        SepalClient.create(base_url="https://sepal.test", auth=NoAuth(), app_name="se.plan")
    )

    assert origin == {"type": "APP", "name": "se.plan"}


def test_export_without_notebook_script_or_app_comes_from_the_sandbox() -> None:
    origin = submitted_origin(SepalClient(base_url="https://sepal.test", auth=NoAuth()))

    assert origin == {"type": "SANDBOX"}


async def test_async_client_sends_the_same_origin() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/tasks").respond(200, json={"id": "t-1", "state": "PENDING"})
        async with AsyncSepalClient.create(
            base_url="https://sepal.test", auth=NoAuth(), app_name="se.plan"
        ) as client:
            await client.ee_exports.submit_table(
                collection={"result": "0", "values": {}}, destination="SEPAL", name="plots"
            )

    assert task_info(route)["origin"] == {"type": "APP", "name": "se.plan"}


def submitted_origin(client: SepalClient) -> Any:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/tasks").respond(200, json={"id": "t-1", "state": "PENDING"})
        with client:
            client.ee_exports.submit_image(
                image={"result": "0", "values": {}}, destination="SEPAL", name="ndvi"
            )
    return task_info(route).get("origin")


def task_info(route: respx.Route) -> Any:
    return json.loads(route.calls.last.request.content)["params"]["taskInfo"]
