from pathlib import PurePosixPath

import pytest
import respx

from pysepal_api import AsyncSepalClient, SepalClient
from pysepal_api.auth import NoAuth
from pysepal_api.paths import module_results_path, module_results_relative


def test_module_results_path_is_derived_without_io() -> None:
    assert module_results_relative("demo") == PurePosixPath("module_results/demo")
    assert module_results_path("demo") == PurePosixPath("/home/sepal-user/module_results/demo")


def test_create_populates_results_path_without_network() -> None:
    """No respx mock: any HTTP call here raises ConnectError and fails the test."""
    client = SepalClient.create(base_url="https://sepal.test", auth=NoAuth(), module_name="demo")
    try:
        assert str(client.results_path) == "/home/sepal-user/module_results/demo"
    finally:
        client.close()


def test_context_entry_performs_no_network() -> None:
    with SepalClient(base_url="https://sepal.test", auth=NoAuth(), module_name="demo") as c:
        assert str(c.results_path) == "/home/sepal-user/module_results/demo"
    assert c._http.is_closed


def test_ensure_results_dir_is_the_only_thing_that_posts() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/user-files/createFolder").respond(200, json={})
        client = SepalClient.create(
            base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
        )
        try:
            assert route.call_count == 0
            path = client.ensure_results_dir()
            assert route.call_count == 1
            assert route.calls.last.request.url.params["path"] == "module_results/demo"
            assert route.calls.last.request.url.params["recursive"] == "true"
            assert str(path) == "/home/sepal-user/module_results/demo"
        finally:
            client.close()


def test_ensure_results_dir_without_module_name_is_a_no_op() -> None:
    client = SepalClient(base_url="https://sepal.test", auth=NoAuth())
    try:
        assert client.results_path is None
        assert client.ensure_results_dir() is None
    finally:
        client.close()


async def test_async_create_populates_results_path_without_network() -> None:
    client = await AsyncSepalClient.create(
        base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
    )
    try:
        assert str(client.results_path) == "/home/sepal-user/module_results/demo"
    finally:
        await client.aclose()


async def test_async_context_manager_form_still_works_and_does_no_io() -> None:
    async with AsyncSepalClient.create(
        base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
    ) as client:
        assert str(client.results_path) == "/home/sepal-user/module_results/demo"
    assert client._http.is_closed


async def test_async_ensure_results_dir_posts_once() -> None:
    async with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/user-files/createFolder").respond(200, json={})
        async with AsyncSepalClient.create(
            base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
        ) as client:
            assert route.call_count == 0
            await client.ensure_results_dir()
            assert route.call_count == 1


@pytest.mark.parametrize("module_name", ["se.plan", "sdg_indicators/15.4.2"])
def test_module_name_is_never_sanitised(module_name: str) -> None:
    assert str(module_results_path(module_name)) == (
        f"/home/sepal-user/module_results/{module_name}"
    )


@pytest.mark.parametrize("module_name", ["/etc/passwd", "../escape"])
def test_client_rejects_a_module_name_that_escapes_the_results_dir(module_name: str) -> None:
    """The escape used to surface as a hard error from create()'s mkdir. Now that
    nothing posts, construction itself has to catch it — otherwise `results_path`
    silently holds a path outside the workspace that only fails much later."""
    from pysepal_api.errors import InvalidPathError

    with pytest.raises(InvalidPathError):
        SepalClient(base_url="https://sepal.test", auth=NoAuth(), module_name=module_name)


def test_ensure_results_dir_matches_files_module_dir() -> None:
    """`ensure_results_dir()` is the client-level spelling of `files.module_dir()`;
    they must not drift apart."""
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(200, json={})
        client = SepalClient.create(
            base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
        )
        try:
            assert client.ensure_results_dir() == client.files.module_dir("demo")
        finally:
            client.close()
