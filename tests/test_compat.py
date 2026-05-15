import warnings
from pathlib import PurePosixPath

import httpx
import pytest
import respx

from pysepal_api.auth import NoAuth
from pysepal_api.compat import SepalClient as LegacySepalClient


@pytest.fixture
def base() -> str:
    return "https://sepal.test"


def test_legacy_constructor_positional(base: str) -> None:
    """Old call: `SepalClient(session_id, module_name)`."""
    with respx.mock(base_url=base) as mock:
        mock.post("/api/user-files/createFolder").respond(200, json={})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            client = LegacySepalClient(
                "sid",
                "demo",
                sepal_host="sepal.test",
            )
            try:
                assert any(
                    issubclass(w.category, DeprecationWarning) for w in caught
                )
                assert str(client.results_path) == (
                    "/home/sepal-user/module_results/demo"
                )
                assert client.BASE_REMOTE_PATH == "/home/sepal-user"
                assert client.module_name == "demo"
                assert client.base_url == "https://sepal.test"
                assert "SEPAL-SESSIONID=sid" in client.cookies
                assert client.headers["Accept"] == "application/json"
            finally:
                client.close()


def test_list_files_returns_dict_envelope(base: str) -> None:
    with respx.mock(base_url=base) as mock:
        mock.get("/api/user-files/listFiles").respond(
            200,
            json={
                "path": ".",
                "files": [
                    {
                        "name": "x.csv",
                        "path": "x.csv",
                        "type": "file",
                        "size": 1,
                    }
                ],
                "count": 1,
            },
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with LegacySepalClient(
                base_url=base, auth=NoAuth(), create_base_dir=False
            ) as client:
                result = client.list_files("/")
                assert isinstance(result, dict)
                assert result["path"] == "."
                assert result["files"][0]["name"] == "x.csv"


def test_get_file_returns_bytes(base: str) -> None:
    with respx.mock(base_url=base) as mock:
        mock.get("/api/user-files/download").respond(200, content=b"data")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with LegacySepalClient(
                base_url=base, auth=NoAuth(), create_base_dir=False
            ) as client:
                assert client.get_file("module_results/app/out.bin") == b"data"


def test_set_file_returns_dict(base: str) -> None:
    with respx.mock(base_url=base) as mock:
        mock.post("/api/user-files/setFile").respond(
            200, json={"path": "module_results/app/out.csv"}
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with LegacySepalClient(
                base_url=base, auth=NoAuth(), create_base_dir=False
            ) as client:
                result = client.set_file(
                    "module_results/app/out.csv", "hello", overwrite=False
                )
                assert isinstance(result, dict)
                assert result["path"] == "module_results/app/out.csv"


def test_get_remote_dir_returns_relative_path(base: str) -> None:
    with respx.mock(base_url=base) as mock:
        mock.post("/api/user-files/createFolder").respond(200, json={})
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with LegacySepalClient(
                base_url=base, auth=NoAuth(), create_base_dir=False
            ) as client:
                p = client.get_remote_dir("module_results/sub", parents=True)
                assert p == PurePosixPath("module_results/sub")


def test_sanitize_path_matches_legacy() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with LegacySepalClient(
            base_url="https://sepal.test",
            auth=NoAuth(),
            create_base_dir=False,
        ) as client:
            assert client.sanitize_path(
                "/home/sepal-user/module_results/app/out.csv"
            ) == PurePosixPath("module_results/app/out.csv")
