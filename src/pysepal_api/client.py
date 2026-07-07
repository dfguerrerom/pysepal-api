"""Sync and async SEPAL HTTP clients.

`SepalClient` (sync) and `AsyncSepalClient` (async) are twins with an identical
surface — same endpoints, same method names, same generic escape hatch. The
only thing that differs is `await`. Both build on the shared request core in
`transport.py` and the shared config resolution below.

Construction never performs network I/O; entering the context (or awaiting
`create()`) is what eagerly creates the module results directory:

    with SepalClient(module_name="my_module") as sepal:                    # sync
        sepal.files.list("/")

    async with AsyncSepalClient.create(module_name="my_module") as sepal:  # async
        await sepal.files.list("/")

For long-lived clients skip the context manager: `sepal = SepalClient.create(...)`
or `sepal = await AsyncSepalClient.create(...)`, then `close()` / `aclose()`.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import PurePosixPath
from typing import Any

import httpx

from .auth import CookieAuth, detect_auth
from .endpoints.processing_recipes import AsyncProcessingRecipesEndpoint, ProcessingRecipesEndpoint
from .endpoints.tasks import AsyncTasksEndpoint, TasksEndpoint
from .endpoints.user_files import AsyncUserFilesEndpoint, UserFilesEndpoint
from .host import detect_base_url, normalize_base_url
from .paths import BASE_REMOTE_PATH
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
    base_url: str | None,
    verify: bool | None,
) -> tuple[str, httpx.Auth, bool]:
    """Resolve base URL, auth, and TLS verification once for both clients.

    Auth precedence: explicit `auth=` → `session_id=` (wrapped in CookieAuth)
    → `detect_auth()`. Host precedence: explicit `base_url=` (a bare host is
    accepted and normalized to https) → `detect_base_url()`.
    """
    resolved_base_url = normalize_base_url(base_url or detect_base_url())
    resolved_auth = auth or (CookieAuth(session_id) if session_id else detect_auth())
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
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
    ) -> None:
        base, resolved_auth, resolved_verify = _resolve_config(session_id, auth, base_url, verify)
        self.module_name = module_name
        self.base_url = base
        self.verify = resolved_verify
        self.results_path: PurePosixPath | None = None
        self._http = httpx.Client(
            base_url=base,
            auth=resolved_auth,
            verify=resolved_verify,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self.files = UserFilesEndpoint(self._http)
        self.tasks = TasksEndpoint(self._http)
        self.recipes = ProcessingRecipesEndpoint(self._http)

    def __repr__(self) -> str:
        return f"SepalClient(base_url={self.base_url!r}, module_name={self.module_name!r})"

    @classmethod
    def create(
        cls,
        *,
        session_id: str | None = None,
        module_name: str | None = None,
        auth: httpx.Auth | None = None,
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
    ) -> SepalClient:
        """Build a ready-to-use client, eagerly creating the module results dir
        (if `module_name` is given). Entry point for long-lived clients; for
        scoped use, `with SepalClient(...)` does the same setup on entry."""
        client = cls(
            session_id=session_id,
            module_name=module_name,
            auth=auth,
            base_url=base_url,
            timeout=timeout,
            verify=verify,
        )
        return client._setup()

    def _setup(self) -> SepalClient:
        """Run eager setup, closing the client instead of leaking it on failure."""
        try:
            self._ensure_results_path()
        except BaseException:
            self.close()
            raise
        return self

    def _ensure_results_path(self) -> PurePosixPath | None:
        if self.results_path is None and self.module_name:
            self.results_path = self.files.module_dir(self.module_name)
        return self.results_path

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
        return self._setup()

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
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
    ) -> None:
        base, resolved_auth, resolved_verify = _resolve_config(session_id, auth, base_url, verify)
        self.module_name = module_name
        self.base_url = base
        self.verify = resolved_verify
        self.results_path: PurePosixPath | None = None
        self._http = httpx.AsyncClient(
            base_url=base,
            auth=resolved_auth,
            verify=resolved_verify,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self.files = AsyncUserFilesEndpoint(self._http)
        self.tasks = AsyncTasksEndpoint(self._http)
        self.recipes = AsyncProcessingRecipesEndpoint(self._http)

    def __repr__(self) -> str:
        return f"AsyncSepalClient(base_url={self.base_url!r}, module_name={self.module_name!r})"

    @classmethod
    def create(
        cls,
        *,
        session_id: str | None = None,
        module_name: str | None = None,
        auth: httpx.Auth | None = None,
        base_url: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
    ) -> _AwaitableClient:
        """Build a ready-to-use client, eagerly creating the module results dir
        (if `module_name` is given). The result can be awaited *or* used as an
        async context manager — both spellings work:

            sepal = await AsyncSepalClient.create(...)      # long-lived
            async with AsyncSepalClient.create(...) as sepal:   # scoped
        """
        client = cls(
            session_id=session_id,
            module_name=module_name,
            auth=auth,
            base_url=base_url,
            timeout=timeout,
            verify=verify,
        )
        return _AwaitableClient(client)

    async def _setup(self) -> AsyncSepalClient:
        """Run eager setup, closing the client instead of leaking it on failure."""
        try:
            await self._ensure_results_path()
        except BaseException:
            await self.aclose()
            raise
        return self

    async def _ensure_results_path(self) -> PurePosixPath | None:
        if self.results_path is None and self.module_name:
            self.results_path = await self.files.module_dir(self.module_name)
        return self.results_path

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
        return await self._setup()

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()


class _AwaitableClient:
    """Result of `AsyncSepalClient.create()`: awaitable and an async context
    manager, so `await create(...)` and `async with create(...)` both work."""

    def __init__(self, client: AsyncSepalClient) -> None:
        self._client = client

    def __await__(self) -> Generator[Any, None, AsyncSepalClient]:
        return self._client._setup().__await__()

    async def __aenter__(self) -> AsyncSepalClient:
        return await self._client._setup()

    async def __aexit__(self, *exc: Any) -> None:
        await self._client.aclose()
