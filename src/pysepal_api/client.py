"""Sync and async SEPAL HTTP clients.

`SepalClient` (sync) and `AsyncSepalClient` (async) are twins with an identical
surface — same endpoints, same method names, same generic escape hatch. The
only thing that differs is `await`. Both build on the shared request core in
`transport.py` and the shared config resolution below.

Construction and `create()` are pure, so building a client is safe anywhere —
including a UI render path:

    with SepalClient(module_name="my_module") as sepal:                    # sync
        sepal.files.list("/")

    async with AsyncSepalClient.create(module_name="my_module") as sepal:  # async
        await sepal.files.list("/")

`results_path` is derived arithmetically from `module_name`, and
`ensure_results_dir()` creates that directory on the server. It is the one setup
call that does I/O — make it once at app startup, and before anything writes
into `results_path`.

For long-lived clients skip the context manager: `sepal = SepalClient.create(...)`
or `sepal = await AsyncSepalClient.create(...)`, then `close()` / `aclose()`.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import PurePosixPath
from typing import Any

import httpx

from .auth import AuthMode, CookieAuth, _validate_auth_mode, detect_auth
from .endpoints.ee_exports import AsyncEEExportsEndpoint, EEExportsEndpoint
from .endpoints.recipes import AsyncRecipesEndpoint, RecipesEndpoint
from .endpoints.tasks import AsyncTasksEndpoint, TasksEndpoint
from .endpoints.user_files import AsyncUserFilesEndpoint, UserFilesEndpoint
from .host import detect_base_url, normalize_base_url
from .origin import detect_origin
from .paths import BASE_REMOTE_PATH, module_results_path
from .transport import send_with_error_mapping, send_with_error_mapping_async

# Hosts that legitimately serve self-signed certs in local development. TLS
# verification is skipped only for these (matched on the parsed host, never a
# substring) or for hosts explicitly listed in `PYSEPAL_INSECURE_TLS_HOSTS` —
# never for arbitrary or production hosts.
_LOCAL_INSECURE_HOSTS = {"host.docker.internal"}


def _insecure_tls_hosts() -> set[str]:
    """Local-dev defaults plus the comma-separated `PYSEPAL_INSECURE_TLS_HOSTS`
    env opt-in. Matching is on the exact parsed host, case-insensitive."""
    env = os.getenv("PYSEPAL_INSECURE_TLS_HOSTS", "")
    return _LOCAL_INSECURE_HOSTS | {h.strip().lower() for h in env.split(",") if h.strip()}


def _should_verify_tls(base_url: str) -> bool:
    """Whether to verify TLS for `base_url`. Secure by default."""
    host = httpx.URL(base_url).host
    return host.lower() not in _insecure_tls_hosts()


def _resolve_config(
    session_id: str | None,
    auth: httpx.Auth | None,
    auth_mode: AuthMode,
    base_url: str | None,
    verify: bool | None,
) -> tuple[str, httpx.Auth, bool]:
    """Resolve base URL, auth, and TLS verification once for both clients.

    Auth precedence: explicit `auth=` → `session_id=` (wrapped in CookieAuth)
    → `detect_auth(mode=auth_mode)`. Host precedence: explicit `base_url=` (a
    bare host is accepted and normalized to https) → `detect_base_url()`.

    `auth_mode` is validated up front rather than inside `detect_auth`, so a
    typo still raises on the two paths that never reach it.
    """
    _validate_auth_mode(auth_mode)
    resolved_base_url = normalize_base_url(base_url or detect_base_url())
    resolved_auth = auth or (CookieAuth(session_id) if session_id else detect_auth(mode=auth_mode))
    resolved_verify = verify if verify is not None else _should_verify_tls(resolved_base_url)
    return resolved_base_url, resolved_auth, resolved_verify


class SepalClient:
    """Synchronous HTTP client for SEPAL services."""

    BASE_REMOTE_PATH = BASE_REMOTE_PATH

    def __init__(
        self,
        *,
        session_id: str | None = None,
        module_name: str | None = None,
        auth: httpx.Auth | None = None,
        auth_mode: AuthMode = "auto",
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
        app_name: str | None = None,
    ) -> None:
        base, resolved_auth, resolved_verify = _resolve_config(
            session_id, auth, auth_mode, base_url, verify
        )
        self.module_name = module_name
        self.base_url = base
        self.verify = resolved_verify
        self.results_path: PurePosixPath | None = (
            module_results_path(module_name) if module_name else None
        )
        self._http = httpx.Client(
            base_url=base,
            auth=resolved_auth,
            verify=resolved_verify,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self.files = UserFilesEndpoint(self._http)
        self.tasks = TasksEndpoint(self._http)
        self.recipes = RecipesEndpoint(self._http)
        self.ee_exports = EEExportsEndpoint(
            self.tasks,
            origin=detect_origin(
                app_name=app_name,
                module_name=module_name,
                browser_session=isinstance(resolved_auth, CookieAuth),
            ),
        )
        self.exports = self.ee_exports

    def __repr__(self) -> str:
        return f"SepalClient(base_url={self.base_url!r}, module_name={self.module_name!r})"

    @classmethod
    def create(
        cls,
        *,
        session_id: str | None = None,
        module_name: str | None = None,
        auth: httpx.Auth | None = None,
        auth_mode: AuthMode = "auto",
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
        app_name: str | None = None,
    ) -> SepalClient:
        """Build a ready-to-use client. Pure.

        ``results_path`` is derived arithmetically from ``module_name``; call
        `ensure_results_dir()` off the UI render path to materialise it.
        """
        return cls(
            session_id=session_id,
            module_name=module_name,
            auth=auth,
            auth_mode=auth_mode,
            base_url=base_url,
            timeout=timeout,
            verify=verify,
            app_name=app_name,
        )

    def ensure_results_dir(self) -> PurePosixPath | None:
        """Create the module results directory on the server.

        Network I/O — never call this on a UI render path, and call it once at
        startup rather than before every write: it re-issues the request each
        time. Returns the absolute results path, or ``None`` when the client
        has no ``module_name``. Idempotent: `files.mkdir` swallows 409/403.
        """
        if not self.module_name:
            return None
        return self.files.module_dir(self.module_name)

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Issue an arbitrary authenticated request to any SEPAL route.

        The typed endpoints (`files`, `tasks`, `recipes`) cover the common
        cases; this is the escape hatch for routes the library doesn't model.
        Returns the raw `httpx.Response` with errors mapped to typed exceptions.
        `kwargs` are forwarded to `httpx.Client.build_request` (`params`,
        `json`, `content`, `files`, `headers`, …).
        """
        return send_with_error_mapping(self._http, self._http.build_request(method, url, **kwargs))

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> SepalClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class AsyncSepalClient:
    """Asynchronous twin of `SepalClient`."""

    BASE_REMOTE_PATH = BASE_REMOTE_PATH

    def __init__(
        self,
        *,
        session_id: str | None = None,
        module_name: str | None = None,
        auth: httpx.Auth | None = None,
        auth_mode: AuthMode = "auto",
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
        app_name: str | None = None,
    ) -> None:
        base, resolved_auth, resolved_verify = _resolve_config(
            session_id, auth, auth_mode, base_url, verify
        )
        self.module_name = module_name
        self.base_url = base
        self.verify = resolved_verify
        self.results_path: PurePosixPath | None = (
            module_results_path(module_name) if module_name else None
        )
        self._http = httpx.AsyncClient(
            base_url=base,
            auth=resolved_auth,
            verify=resolved_verify,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self.files = AsyncUserFilesEndpoint(self._http)
        self.tasks = AsyncTasksEndpoint(self._http)
        self.recipes = AsyncRecipesEndpoint(self._http)
        self.ee_exports = AsyncEEExportsEndpoint(
            self.tasks,
            origin=detect_origin(
                app_name=app_name,
                module_name=module_name,
                browser_session=isinstance(resolved_auth, CookieAuth),
            ),
        )
        self.exports = self.ee_exports

    def __repr__(self) -> str:
        return f"AsyncSepalClient(base_url={self.base_url!r}, module_name={self.module_name!r})"

    @classmethod
    def create(
        cls,
        *,
        session_id: str | None = None,
        module_name: str | None = None,
        auth: httpx.Auth | None = None,
        auth_mode: AuthMode = "auto",
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
        app_name: str | None = None,
    ) -> _AwaitableClient:
        """Build a ready-to-use client. Pure. The result can be awaited *or*
        used as an async context manager — both spellings work:

            sepal = await AsyncSepalClient.create(...)      # long-lived
            async with AsyncSepalClient.create(...) as sepal:   # scoped

        ``results_path`` is derived arithmetically from ``module_name``; call
        `ensure_results_dir()` off the UI render path to materialise it.
        """
        client = cls(
            session_id=session_id,
            module_name=module_name,
            auth=auth,
            auth_mode=auth_mode,
            base_url=base_url,
            timeout=timeout,
            verify=verify,
            app_name=app_name,
        )
        return _AwaitableClient(client)

    async def ensure_results_dir(self) -> PurePosixPath | None:
        """Create the module results directory on the server.

        Network I/O — never call this on a UI render path, and call it once at
        startup rather than before every write: it re-issues the request each
        time. Returns the absolute results path, or ``None`` when the client
        has no ``module_name``. Idempotent: `files.mkdir` swallows 409/403.
        """
        if not self.module_name:
            return None
        return await self.files.module_dir(self.module_name)

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Async twin of `SepalClient.request`. Escape hatch for unmodeled routes."""
        return await send_with_error_mapping_async(
            self._http, self._http.build_request(method, url, **kwargs)
        )

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncSepalClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()


class _AwaitableClient:
    """Result of `AsyncSepalClient.create()`: awaitable and an async context
    manager, so `await create(...)` and `async with create(...)` both work."""

    def __init__(self, client: AsyncSepalClient) -> None:
        self._client = client

    async def _ready(self) -> AsyncSepalClient:
        return self._client

    def __await__(self) -> Generator[Any, None, AsyncSepalClient]:
        return self._ready().__await__()

    async def __aenter__(self) -> AsyncSepalClient:
        return self._client

    async def __aexit__(self, *exc: Any) -> None:
        await self._client.aclose()
