import httpx
import pytest
import respx

from pysepal_api.endpoints.user_files import UserFilesEndpoint
from pysepal_api.errors import Conflict, PysepalError


@pytest.fixture
def http() -> httpx.Client:
    return httpx.Client(base_url="https://sepal.test", timeout=5.0)


def test_write_sends_multipart_file_field(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/user-files/setFile").respond(
            200, json={"path": "module_results/app/out.csv"}
        )
        endpoint = UserFilesEndpoint(http)
        endpoint.write("module_results/app/out.csv", "hello,world\n")

        last = route.calls.last.request
        content_type = last.headers["content-type"]
        assert content_type.startswith("multipart/form-data;")
        # multipart body must contain the file field name and inferred mime
        body = last.content
        assert b'name="file"' in body
        assert b'filename="out.csv"' in body
        assert b"text/csv" in body
        assert last.url.params["overwrite"] == "false"


def test_write_supports_overwrite_and_bytes(http: httpx.Client) -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.post("/api/user-files/setFile").respond(200, json={})
        endpoint = UserFilesEndpoint(http)
        endpoint.write(
            "module_results/app/out.tif",
            b"\x00\x01\x02",
            overwrite=True,
        )
        last = route.calls.last.request
        assert last.url.params["overwrite"] == "true"
        assert b"image/tiff" in last.content


def test_write_conflict_raises(http: httpx.Client) -> None:
    """`setFile` returns 409 when overwrite is false and the file exists. That
    must surface as `Conflict` — a silent no-op would let callers believe the
    write succeeded."""
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/setFile").respond(409, text="exists")
        endpoint = UserFilesEndpoint(http)
        with pytest.raises(Conflict):
            endpoint.write("module_results/app/out.csv", "x")
        # and it stays catchable via the library root
        with pytest.raises(PysepalError):
            endpoint.write("module_results/app/out.csv", "x")
