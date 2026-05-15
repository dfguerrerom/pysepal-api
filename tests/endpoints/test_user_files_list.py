import httpx
import pytest
import respx

from pysepal_api.endpoints.user_files import UserFilesEndpoint


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_list_root_sends_dot(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.get("/api/user-files/listFiles").respond(
            200,
            json={"path": ".", "files": [], "count": 0},
        )
        endpoint = UserFilesEndpoint(http)
        result = endpoint.list("/")
        assert result.path == "."
        assert result.files == []
        assert route.calls.last.request.url.params["path"] == "."
        assert route.calls.last.request.url.params["extensions"] == ""
        assert route.calls.last.request.url.params["includeHidden"] == "false"


def test_list_with_extensions(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.get("/api/user-files/listFiles").respond(
            200,
            json={
                "path": "module_results/app",
                "files": [
                    {
                        "name": "out.csv",
                        "path": "module_results/app/out.csv",
                        "type": "file",
                        "size": 42,
                        "modifiedTime": "2026-05-14T10:00:00Z",
                    }
                ],
                "count": 1,
            },
        )
        endpoint = UserFilesEndpoint(http)
        result = endpoint.list("module_results/app", extensions=["csv", "json"])
        assert result.files[0].name == "out.csv"
        assert route.calls.last.request.url.params["extensions"] == "csv,json"
        assert route.calls.last.request.url.params["path"] == "module_results/app"
