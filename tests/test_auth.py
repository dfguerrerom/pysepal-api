from pathlib import Path
from typing import Any

import httpx
import pytest

from pysepal_api.auth import (
    ApiKeyAuth,
    CookieAuth,
    NoAuth,
    detect_auth,
)
from pysepal_api.errors import NoCredentialsError


def _run_auth(auth: httpx.Auth) -> httpx.Request:
    """Drive the httpx.Auth flow once and return the prepared request."""
    request = httpx.Request("GET", "https://example.test/x")
    flow = auth.auth_flow(request)
    return next(flow)


def test_api_key_auth_sets_basic_header() -> None:
    auth = ApiKeyAuth("hunter2")
    req = _run_auth(auth)
    # Basic + base64("" + ":" + "hunter2")
    assert req.headers["Authorization"].startswith("Basic ")


def test_api_key_auth_redacted_in_repr() -> None:
    auth = ApiKeyAuth("hunter2")
    assert "hunter2" not in repr(auth)


def test_api_key_auth_from_sandbox_strips_whitespace(tmp_path: Path) -> None:
    key_file = tmp_path / "sepal-api-key"
    key_file.write_text("  abc-123  \n")
    auth = ApiKeyAuth.from_sandbox(str(key_file))
    req = _run_auth(auth)
    import base64

    expected = base64.b64encode(b":abc-123").decode()
    assert req.headers["Authorization"] == f"Basic {expected}"


def test_cookie_auth_sets_session_cookie() -> None:
    auth = CookieAuth("sid-xyz")
    req = _run_auth(auth)
    assert "SEPAL-SESSIONID=sid-xyz" in req.headers["Cookie"]


def test_no_auth_passes_request_through() -> None:
    auth = NoAuth()
    req = _run_auth(auth)
    assert "Authorization" not in req.headers
    assert "Cookie" not in req.headers


def test_detect_reads_the_sandbox_file(tmp_path: Path) -> None:
    key_file = tmp_path / "sepal-api-key"
    key_file.write_text("fkey")
    assert isinstance(detect_auth(sandbox_path=str(key_file)), ApiKeyAuth)


def test_detect_no_credentials(tmp_path: Path) -> None:
    with pytest.raises(NoCredentialsError):
        detect_auth(sandbox_path=str(tmp_path / "missing"))


@pytest.mark.parametrize("mode", ["auto", "sandbox_file"])
def test_detect_auth_ignores_the_environment_entirely(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEPAL unsets SEPAL_API_KEY before user code runs, so reading it could only
    ever pick up a stray local export and let it outrank the real credential. No
    mode may fall back to it."""
    monkeypatch.setenv("SEPAL_API_KEY", "from-env")
    with pytest.raises(NoCredentialsError):
        detect_auth(mode=mode, sandbox_path=str(tmp_path / "missing"))  # type: ignore[arg-type]


def test_detect_auth_sandbox_mode_reads_the_file(tmp_path: Path) -> None:
    key_file = tmp_path / "sepal-api-key"
    key_file.write_text(" k \n")
    assert isinstance(detect_auth(mode="sandbox_file", sandbox_path=str(key_file)), ApiKeyAuth)


def test_detect_auth_none_mode_disables_auth() -> None:
    assert isinstance(detect_auth(mode="none"), NoAuth)


@pytest.mark.parametrize("mode", ["magic", "env"])
def test_detect_auth_rejects_an_unknown_mode(mode: str) -> None:
    """The mode "env" is named explicitly because it used to be valid — it must
    raise now that the source is gone, not quietly resolve to something else."""
    with pytest.raises(ValueError, match="unknown auth mode"):
        detect_auth(mode=mode)  # type: ignore[arg-type]


def test_detect_auth_auto_is_the_sandbox_file(tmp_path: Path) -> None:
    key_file = tmp_path / "sepal-api-key"
    key_file.write_text("from-file")
    assert isinstance(detect_auth(mode="auto", sandbox_path=str(key_file)), ApiKeyAuth)


def test_client_forwards_auth_mode() -> None:
    from pysepal_api import SepalClient

    client = SepalClient(base_url="https://sepal.test", auth_mode="none")
    try:
        assert isinstance(client._http.auth, NoAuth)
    finally:
        client.close()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"session_id": "sid"},
        {"auth": NoAuth()},
        {},
    ],
)
def test_client_rejects_an_unknown_auth_mode_on_every_path(kwargs: dict[str, Any]) -> None:
    """A typo'd mode must raise even when auth is resolved from `auth=`/`session_id=`
    and `detect_auth` — which owns the mode check — is never reached."""
    from pysepal_api import SepalClient

    bad_mode: Any = "magic"
    with pytest.raises(ValueError, match="unknown auth mode"):
        SepalClient(base_url="https://sepal.test", auth_mode=bad_mode, **kwargs)
