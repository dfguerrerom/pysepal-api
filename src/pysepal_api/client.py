"""Sync and async SEPAL HTTP clients.

`SepalClient` (sync) and `AsyncSepalClient` (async) are twins with an identical
surface — same endpoints, same method names, same generic escape hatch. The
only thing that differs is `await`. Both build on the shared request core in
`transport.py` and the shared config resolution below.

Construction never performs network I/O. Use the `create()` factory (or a
`with` / `async with` block) to eagerly create the module results directory:

    with SepalClient.create(session_id=...) as c:          # sync
        c.user_files.list("/")

    async with await AsyncSepalClient.create(session_id=...) as c:   # async
        await c.user_files.list("/")
"""

from __future__ import annotations

import os
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
# substring) or via an explicit `PYSEPAL_INSECURE_TLS` opt-in — never for
# arbitrary or production hosts.
_LOCAL_INSECURE_HOSTS = {"host.docker.internal"}


def _should_verify_tls(base_url: str) -> bool:
    """Whether to verify TLS for `base_url`. Secure by default."""
    if os.getenv("PYSEPAL_INSECURE_TLS", "").strip().lower() in {"1", "true", "yes"}:
        return False
    return httpx.URL(base_url).host not in _LOCAL_INSECURE_HOSTS


def _resolve_config(
    session_id: str | None,
    auth: httpx.Auth | None,
    base_url: str | None,
    sepal_host: str | None,
    verify: bool | None,
) -> tuple[str, httpx.Auth, bool]:
    """Resolve base URL, auth, and TLS verification once for both clients.

    Auth precedence: explicit `auth=` → `session_id=` (wrapped in CookieAuth)
    → `detect_auth()`. Host precedence: explicit `base_url=` → legacy
    `sepal_host=` → `detect_base_url()`.
    """
    resolved_base_url = normalize_base_url(
        base_url or (f"https://{sepal_host}" if sepal_host else None) or detect_base_url()
    )
    resolved_auth = auth or (CookieAuth(session_id) if session_id else detect_auth())
    resolved_verify = verify if verify is not None else _should_verify_tls(resolved_base_url)
    return resolved_base_url, resolved_auth, resolved_verify


class SepalClient:
    """Synchronous HTTP client for SEPAL services."""

    BASE_REMOTE_PATH = BASE_REMOTE_PATH

    def __init__(
        self,
        session_id: str | None = None,
        module_name: str | None = None,
        *,
        auth: httpx.Auth | None = None,
        base_url: str | None = None,
        sepal_host: str | None = None,
        create_base_dir: bool = True,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
    ) -> None:
        base, resolved_auth, resolved_verify = _resolve_config(
            session_id, auth, base_url, sepal_host, verify
        )
        self.module_name = module_name
        self.base_url = base
        self.verify_ssl = resolved_verify
        self._create_base_dir = create_base_dir
        self.results_path: PurePosixPath | None = None
        self._http = httpx.Client(
            base_url=base,
            auth=resolved_auth,
            verify=resolved_verify,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self.user_files = UserFilesEndpoint(self._http)
        self.tasks = TasksEndpoint(self._http)
        self.processing_recipes = ProcessingRecipesEndpoint(self._http)
        self.recipes = self.processing_recipes

    @classmethod
    def create(
        cls,
        session_id: str | None = None,
        module_name: str | None = None,
        *,
        auth: httpx.Auth | None = None,
        base_url: str | None = None,
        sepal_host: str | None = None,
        create_base_dir: bool = True,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
    ) -> SepalClient:
        """Build a client and eagerly create the module results dir (if any).

        The recommended entry point: `__init__` does no network I/O, so this is
        where `module_dir` creation happens (also triggered by entering `with`).
        """
        client = cls(
            session_id,
            module_name,
            auth=auth,
            base_url=base_url,
            sepal_host=sepal_host,
            create_base_dir=create_base_dir,
            timeout=timeout,
            verify=verify,
        )
        try:
            client._ensure_results_path()
        except BaseException:
            client.close()
            raise
        return client

    def _ensure_results_path(self) -> PurePosixPath | None:
        if self.results_path is None and self.module_name and self._create_base_dir:
            self.results_path = self.user_files.module_dir(self.module_name)
        return self.results_path

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Issue an arbitrary authenticated request to any SEPAL route.

        The typed endpoints (`user_files`, `tasks`, `recipes`) cover the common
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
        self._ensure_results_path()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class AsyncSepalClient:
    """Asynchronous twin of `SepalClient`."""

    BASE_REMOTE_PATH = BASE_REMOTE_PATH

    def __init__(
        self,
        session_id: str | None = None,
        module_name: str | None = None,
        *,
        auth: httpx.Auth | None = None,
        base_url: str | None = None,
        sepal_host: str | None = None,
        create_base_dir: bool = True,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
    ) -> None:
        base, resolved_auth, resolved_verify = _resolve_config(
            session_id, auth, base_url, sepal_host, verify
        )
        self.module_name = module_name
        self.base_url = base
        self.verify_ssl = resolved_verify
        self._create_base_dir = create_base_dir
        self.results_path: PurePosixPath | None = None
        self._http = httpx.AsyncClient(
            base_url=base,
            auth=resolved_auth,
            verify=resolved_verify,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self.user_files = AsyncUserFilesEndpoint(self._http)
        self.tasks = AsyncTasksEndpoint(self._http)
        self.processing_recipes = AsyncProcessingRecipesEndpoint(self._http)
        self.recipes = self.processing_recipes

    @classmethod
    async def create(
        cls,
        session_id: str | None = None,
        module_name: str | None = None,
        *,
        auth: httpx.Auth | None = None,
        base_url: str | None = None,
        sepal_host: str | None = None,
        create_base_dir: bool = True,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool | None = None,
    ) -> AsyncSepalClient:
        """Build a client and eagerly create the module results dir (if any)."""
        client = cls(
            session_id,
            module_name,
            auth=auth,
            base_url=base_url,
            sepal_host=sepal_host,
            create_base_dir=create_base_dir,
            timeout=timeout,
            verify=verify,
        )
        try:
            await client._ensure_results_path()
        except BaseException:
            await client.aclose()
            raise
        return client

    async def _ensure_results_path(self) -> PurePosixPath | None:
        if self.results_path is None and self.module_name and self._create_base_dir:
            self.results_path = await self.user_files.module_dir(self.module_name)
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
        await self._ensure_results_path()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()
