import httpx
import pytest
import respx

from pysepal_api.endpoints.user_files import UserFilesEndpoint


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_read_bytes(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.get("/api/user-files/download").respond(200, content=b"hello bytes")
        endpoint = UserFilesEndpoint(http)
        result = endpoint.read_bytes("module_results/app/out.bin")
        assert result == b"hello bytes"
        assert route.calls.last.request.url.params["path"] == ("module_results/app/out.bin")


def test_read_text(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/user-files/download").respond(200, content=b"hello,world\n")
        endpoint = UserFilesEndpoint(http)
        assert endpoint.read_text("module_results/app/out.csv") == "hello,world\n"


def test_read_json(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/user-files/download").respond(
            200, json={"k": 1}, headers={"content-type": "application/json"}
        )
        endpoint = UserFilesEndpoint(http)
        assert endpoint.read_json("module_results/app/x.json") == {"k": 1}


def test_read_strips_home_prefix(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.get("/api/user-files/download").respond(200, content=b"x")
        endpoint = UserFilesEndpoint(http)
        endpoint.read_bytes("/home/sepal-user/module_results/app/out.bin")
        assert route.calls.last.request.url.params["path"] == ("module_results/app/out.bin")
