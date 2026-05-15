"""Auth providers for pysepal-api.

Three providers implement `httpx.Auth`:

- `ApiKeyAuth`  → HTTP Basic with empty user + sandbox key as password.
- `CookieAuth`  → `SEPAL-SESSIONID` cookie for Solara/session-header flows.
- `NoAuth`      → explicitly disable pysepal-api auth (tests / mock servers).

`detect_auth()` follows the spec precedence:

1. `SEPAL_API_KEY` env var.
2. `/var/run/sepal-api-key` file.
3. raise `NoCredentialsError`.
"""

from __future__ import annotations

import base64
import os
from collections.abc import Generator
from pathlib import Path

import httpx

from .errors import NoCredentialsError

SANDBOX_KEY_PATH = "/var/run/sepal-api-key"


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

    @classmethod
    def from_env(cls, var: str = "SEPAL_API_KEY") -> "ApiKeyAuth":
        value = os.environ.get(var, "").strip()
        if not value:
            raise NoCredentialsError(f"Environment variable {var} is empty or unset")
        return cls(value)


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
    env_var: str = "SEPAL_API_KEY",
    sandbox_path: str = SANDBOX_KEY_PATH,
) -> httpx.Auth:
    """Auto-detect auth: env var → key file → NoCredentialsError."""
    value = os.environ.get(env_var, "").strip()
    if value:
        return ApiKeyAuth(value)
    p = Path(sandbox_path)
    if p.is_file():
        text = p.read_text().strip()
        if text:
            return ApiKeyAuth(text)
    raise NoCredentialsError(
        "No SEPAL credentials found. Pass auth=..., set SEPAL_API_KEY, "
        f"or ensure {sandbox_path} exists."
    )
