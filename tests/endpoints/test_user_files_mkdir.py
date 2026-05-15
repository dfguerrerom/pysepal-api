from pathlib import PurePosixPath

import httpx
import pytest
import respx

from pysepal_api.endpoints.user_files import UserFilesEndpoint


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_mkdir_posts_create_folder(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/user-files/createFolder").respond(200, json={})
        endpoint = UserFilesEndpoint(http)
        path = endpoint.mkdir("module_results/app", parents=True)
        last = route.calls.last.request
        assert last.url.params["path"] == "module_results/app"
        assert last.url.params["recursive"] == "true"
        assert path == PurePosixPath("module_results/app")


def test_mkdir_idempotent_on_409(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(409, text="exists")
        endpoint = UserFilesEndpoint(http)
        path = endpoint.mkdir("module_results/app")
        assert path == PurePosixPath("module_results/app")


def test_mkdir_idempotent_on_403(http: httpx.Client) -> None:
    """Legacy pysepal treated 403 on createFolder as 'already exists'."""
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(403, text="exists")
        endpoint = UserFilesEndpoint(http)
        path = endpoint.mkdir("module_results/app")
        assert path == PurePosixPath("module_results/app")


def test_module_dir_creates_under_base(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/user-files/createFolder").respond(200, json={})
        endpoint = UserFilesEndpoint(http)
        path = endpoint.module_dir("my_app")
        assert path == PurePosixPath("/home/sepal-user/module_results/my_app")
        assert route.calls.last.request.url.params["path"] == (
            "module_results/my_app"
        )
