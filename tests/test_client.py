import httpx
import pytest
import respx

from pysepal_api.auth import NoAuth
from pysepal_api.client import SepalClient
from pysepal_api.errors import MissingHostError


def test_client_uses_explicit_base_url_and_auth() -> None:
    client = SepalClient(
        base_url="https://sepal.test",
        auth=NoAuth(),
        create_base_dir=False,
    )
    try:
        assert client.base_url == "https://sepal.test"
        assert isinstance(client._http, httpx.Client)
    finally:
        client.close()


def test_client_wraps_session_id_in_cookie_auth() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/user-files/listFiles").respond(
            200, json={"path": ".", "files": [], "count": 0}
        )
        with SepalClient(
            base_url="https://sepal.test",
            session_id="sid-xyz",
            create_base_dir=False,
        ) as client:
            client.user_files.list(".")
            last = mock.routes[0].calls.last.request
            assert "SEPAL-SESSIONID=sid-xyz" in last.headers["Cookie"]


def test_client_normalizes_host_kwarg() -> None:
    with SepalClient(
        sepal_host="sepal.test",
        auth=NoAuth(),
        create_base_dir=False,
    ) as client:
        assert client.base_url == "https://sepal.test"


def test_client_raises_missing_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEPAL_HOST", raising=False)
    monkeypatch.delenv("SEPAL_ENDPOINT", raising=False)
    with pytest.raises(MissingHostError):
        SepalClient(auth=NoAuth())


def test_client_creates_module_dir() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(200, json={})
        with SepalClient(
            base_url="https://sepal.test",
            auth=NoAuth(),
            module_name="demo",
        ) as client:
            assert str(client.results_path) == ("/home/sepal-user/module_results/demo")


def test_client_disables_verify_for_localhost() -> None:
    """Existing pysepal heuristic: `host.docker.internal` and `danielg.sepal.io`
    have TLS verification disabled. Explicit `verify=` overrides."""
    client = SepalClient(
        base_url="https://host.docker.internal",
        auth=NoAuth(),
        create_base_dir=False,
    )
    try:
        # httpx exposes the configured verify via the internal transport;
        # we re-expose it on the client for test/inspection convenience.
        assert client.verify_ssl is False
    finally:
        client.close()
