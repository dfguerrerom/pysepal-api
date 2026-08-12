"""Auth providers for pysepal-api.

Three providers implement `httpx.Auth`:

- `ApiKeyAuth`  → HTTP Basic with empty user + sandbox key as password.
- `CookieAuth`  → `SEPAL-SESSIONID` cookie for Solara/session-header flows.
- `NoAuth`      → explicitly disable pysepal-api auth (tests / mock servers).

`detect_auth()` resolves the sandbox credential from `/var/run/sepal-api-key`:
`mode="sandbox_file"`, or the default `"auto"`, which means the same since that
file is the only source. `mode="none"` disables auth.
"""

from __future__ import annotations

import base64
from collections.abc import Generator
from pathlib import Path
from typing import Literal, get_args

import httpx

from .errors import NoCredentialsError

SANDBOX_KEY_PATH = "/var/run/sepal-api-key"

AuthMode = Literal["auto", "sandbox_file", "none"]

_AUTH_MODES: frozenset[str] = frozenset(get_args(AuthMode))


def _validate_auth_mode(mode: str) -> None:
    """Raise if `mode` is not a known `AuthMode`.

    Split out of `detect_auth` so the client can reject a bad mode even on the
    paths where it never resolves one (explicit `auth=` or `session_id=`).
    """
    if mode not in _AUTH_MODES:
        raise ValueError(f"unknown auth mode: {mode!r}")


class ApiKeyAuth(httpx.Auth):
    """HTTP Basic auth with empty username + sandbox API key as password."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("ApiKeyAuth requires a non-empty key")
        self._key = api_key
        token = base64.b64encode(f":{api_key}".encode()).decode()
        self._header = f"Basic {token}"

    def __repr__(self) -> str:
        return "ApiKeyAuth(***)"

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = self._header
        yield request

    @classmethod
    def from_sandbox(cls, path: str = SANDBOX_KEY_PATH) -> "ApiKeyAuth":
        text = Path(path).read_text().strip()
        return cls(text)


class CookieAuth(httpx.Auth):
    """SEPAL-SESSIONID cookie auth, used by the Solara container path."""

    def __init__(self, session_id: str) -> None:
        if not session_id:
            raise ValueError("CookieAuth requires a non-empty session id")
        self._session_id = session_id

    def __repr__(self) -> str:
        return "CookieAuth(***)"

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        existing = request.headers.get("Cookie", "")
        cookie = f"SEPAL-SESSIONID={self._session_id}"
        request.headers["Cookie"] = f"{existing}; {cookie}" if existing else cookie
        yield request


class NoAuth(httpx.Auth):
    """Explicitly disable auth (tests, mock servers)."""

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        yield request


def detect_auth(
    *,
    mode: AuthMode = "auto",
    sandbox_path: str = SANDBOX_KEY_PATH,
) -> httpx.Auth:
    """Build an auth provider for the sandbox credential.

    ``mode="none"`` disables auth. ``mode="sandbox_file"`` reads
    ``sandbox_path``, and ``mode="auto"`` (the default) does the same — the
    two are separate spellings of one behaviour because there is only one
    credential source to find. Raises `NoCredentialsError` when the key file is
    missing or empty.
    """
    _validate_auth_mode(mode)
    if mode == "none":
        return NoAuth()
    return _api_key_from_file(sandbox_path)


def _api_key_from_file(sandbox_path: str) -> ApiKeyAuth:
    """Read an API key from ``sandbox_path``; raise if absent or empty."""
    path = Path(sandbox_path)
    text = path.read_text().strip() if path.is_file() else ""
    if not text:
        raise NoCredentialsError(
            f"No SEPAL API key at {sandbox_path}. Pass auth=... explicitly when "
            "running outside a SEPAL sandbox."
        )
    return ApiKeyAuth(text)
