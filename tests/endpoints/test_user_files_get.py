import httpx
import pytest
import respx

from pysepal_api.endpoints.user_files import UserFilesEndpoint


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_get_returns_bytes_by_default(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.get("/api/user-files/download").respond(200, content=b"hello bytes")
        endpoint = UserFilesEndpoint(http)
        result = endpoint.get("module_results/app/out.bin")
        assert result == b"hello bytes"
        assert route.calls.last.request.url.params["path"] == ("module_results/app/out.bin")


def test_get_parses_json_when_requested(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/user-files/download").respond(
            200, json={"k": 1}, headers={"content-type": "application/json"}
        )
        endpoint = UserFilesEndpoint(http)
        result = endpoint.get("module_results/app/x.json", parse_json=True)
        assert result == {"k": 1}


def test_get_strips_home_prefix(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.get("/api/user-files/download").respond(200, content=b"x")
        endpoint = UserFilesEndpoint(http)
        endpoint.get("/home/sepal-user/module_results/app/out.bin")
        assert route.calls.last.request.url.params["path"] == ("module_results/app/out.bin")
