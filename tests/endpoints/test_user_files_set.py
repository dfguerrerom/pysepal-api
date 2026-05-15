import httpx
import pytest
import respx

from pysepal_api.endpoints.user_files import UserFilesEndpoint


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_set_sends_multipart_file_field(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/user-files/setFile").respond(
            200, json={"path": "module_results/app/out.csv"}
        )
        endpoint = UserFilesEndpoint(http)
        endpoint.set("module_results/app/out.csv", "hello,world\n")

        last = route.calls.last.request
        content_type = last.headers["content-type"]
        assert content_type.startswith("multipart/form-data;")
        # multipart body must contain the file field name and inferred mime
        body = last.content
        assert b'name="file"' in body
        assert b'filename="out.csv"' in body
        assert b"text/csv" in body
        assert last.url.params["overwrite"] == "false"


def test_set_supports_overwrite_and_bytes(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/user-files/setFile").respond(200, json={})
        endpoint = UserFilesEndpoint(http)
        endpoint.set(
            "module_results/app/out.tif",
            b"\x00\x01\x02",
            overwrite=True,
        )
        last = route.calls.last.request
        assert last.url.params["overwrite"] == "true"
        assert b"image/tiff" in last.content


def test_set_treats_409_as_success(http: httpx.Client) -> None:
    """`setFile` returns 409 when overwrite is false and file exists; legacy
    pysepal swallowed it. The new client returns an empty FileWriteResult."""
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/setFile").respond(409, text="exists")
        endpoint = UserFilesEndpoint(http)
        result = endpoint.set("module_results/app/out.csv", "x")
        assert result.path is None
