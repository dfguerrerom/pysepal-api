import os
from pathlib import Path

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


def test_api_key_auth_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEPAL_API_KEY", "envkey")
    auth = ApiKeyAuth.from_env()
    assert isinstance(auth, ApiKeyAuth)


def test_cookie_auth_sets_session_cookie() -> None:
    auth = CookieAuth("sid-xyz")
    req = _run_auth(auth)
    assert "SEPAL-SESSIONID=sid-xyz" in req.headers["Cookie"]


def test_no_auth_passes_request_through() -> None:
    auth = NoAuth()
    req = _run_auth(auth)
    assert "Authorization" not in req.headers
    assert "Cookie" not in req.headers


def test_detect_prefers_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SEPAL_API_KEY", "envkey")
    auth = detect_auth(sandbox_path=str(tmp_path / "nope"))
    assert isinstance(auth, ApiKeyAuth)


def test_detect_falls_back_to_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SEPAL_API_KEY", raising=False)
    key_file = tmp_path / "sepal-api-key"
    key_file.write_text("fkey")
    auth = detect_auth(sandbox_path=str(key_file))
    assert isinstance(auth, ApiKeyAuth)


def test_detect_no_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SEPAL_API_KEY", raising=False)
    with pytest.raises(NoCredentialsError):
        detect_auth(sandbox_path=str(tmp_path / "missing"))
