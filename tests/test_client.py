import httpx
import pytest
import respx

from pysepal_api import NotFound, SepalClient
from pysepal_api.auth import NoAuth
from pysepal_api.errors import MissingHostError


def test_client_uses_explicit_base_url_and_auth() -> None:
    client = SepalClient(base_url="https://sepal.test", auth=NoAuth(), create_base_dir=False)
    try:
        assert client.base_url == "https://sepal.test"
        assert isinstance(client._http, httpx.Client)
        assert client.results_path is None
    finally:
        client.close()


def test_init_performs_no_network() -> None:
    """Constructing with a module_name must NOT hit the network — only
    create()/context-entry create the results dir. (No respx mock here: if
    __init__ issued a request it would error.)"""
    client = SepalClient(base_url="https://sepal.test", auth=NoAuth(), module_name="demo")
    try:
        assert client.results_path is None
    finally:
        client.close()


def test_create_factory_makes_module_dir() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(200, json={})
        client = SepalClient.create(
            base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
        )
        try:
            assert str(client.results_path) == "/home/sepal-user/module_results/demo"
        finally:
            client.close()


def test_context_manager_creates_module_dir() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(200, json={})
        with SepalClient(
            base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
        ) as client:
            assert str(client.results_path) == "/home/sepal-user/module_results/demo"


def test_client_wraps_session_id_in_cookie_auth() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/user-files/listFiles").respond(
            200, json={"path": ".", "files": [], "count": 0}
        )
        with SepalClient(
            base_url="https://sepal.test", session_id="sid-xyz", create_base_dir=False
        ) as client:
            client.user_files.list(".")
            last = mock.routes[0].calls.last.request
            assert "SEPAL-SESSIONID=sid-xyz" in last.headers["Cookie"]


def test_client_normalizes_host_kwarg() -> None:
    with SepalClient(sepal_host="sepal.test", auth=NoAuth(), create_base_dir=False) as client:
        assert client.base_url == "https://sepal.test"


def test_client_raises_missing_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEPAL_HOST", raising=False)
    monkeypatch.delenv("SEPAL_ENDPOINT", raising=False)
    with pytest.raises(MissingHostError):
        SepalClient(auth=NoAuth())


# --- generic request escape hatch ---------------------------------------------


def test_request_hits_arbitrary_route_with_auth() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        route = mock.get("/api/gee/image/json").respond(200, json={"ok": True})
        with SepalClient(
            base_url="https://sepal.test", session_id="sid-xyz", create_base_dir=False
        ) as client:
            resp = client.get("/api/gee/image/json", params={"recipeId": "foo"})
            assert resp.json() == {"ok": True}
            req = route.calls.last.request
            assert req.url.params["recipeId"] == "foo"
            assert "SEPAL-SESSIONID=sid-xyz" in req.headers["Cookie"]


def test_request_maps_errors_to_typed_exceptions() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/gee/missing").respond(404, text="nope")
        with SepalClient(
            base_url="https://sepal.test", auth=NoAuth(), create_base_dir=False
        ) as client:
            with pytest.raises(NotFound):
                client.get("/api/gee/missing")


# --- TLS verification policy --------------------------------------------------


def test_verify_skipped_for_local_docker() -> None:
    client = SepalClient(
        base_url="https://host.docker.internal", auth=NoAuth(), create_base_dir=False
    )
    try:
        assert client.verify_ssl is False
    finally:
        client.close()


def test_verify_enabled_for_former_personal_host() -> None:
    """Security regression guard: danielg.sepal.io must now verify TLS, and the
    match is on the parsed host, not a substring."""
    for host in ("danielg.sepal.io", "danielg.sepal.io.attacker.com", "sepal.io"):
        client = SepalClient(base_url=f"https://{host}", auth=NoAuth(), create_base_dir=False)
        try:
            assert client.verify_ssl is True, host
        finally:
            client.close()


def test_verify_explicit_override() -> None:
    client = SepalClient(
        base_url="https://sepal.test", auth=NoAuth(), verify=False, create_base_dir=False
    )
    try:
        assert client.verify_ssl is False
    finally:
        client.close()


def test_verify_env_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYSEPAL_INSECURE_TLS", "1")
    client = SepalClient(base_url="https://sepal.test", auth=NoAuth(), create_base_dir=False)
    try:
        assert client.verify_ssl is False
    finally:
        client.close()
