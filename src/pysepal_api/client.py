"""Sync client. Async twin lives next to it once Phase 5 lands."""

from __future__ import annotations

from typing import Any

import httpx

from .auth import CookieAuth, detect_auth
from .endpoints.processing_recipes import AsyncProcessingRecipesEndpoint, ProcessingRecipesEndpoint
from .endpoints.tasks import AsyncTasksEndpoint, TasksEndpoint
from .endpoints.user_files import AsyncUserFilesEndpoint, UserFilesEndpoint
from .host import detect_base_url, normalize_base_url
from .paths import BASE_REMOTE_PATH

_LOCAL_HOSTS = ("host.docker.internal", "danielg.sepal.io")


def _verify_for(base_url: str) -> bool:
    """Reproduce pysepal v3 behavior: skip TLS verify for local/dev hosts."""
    return not any(h in base_url for h in _LOCAL_HOSTS)


class SepalClient:
    """HTTP client for SEPAL services.

    Auth precedence: explicit `auth=` → `session_id=` (wrapped in CookieAuth)
    → `detect_auth()` (env var, then sandbox key file).

    Host precedence: explicit `base_url=` → legacy `sepal_host=` →
    `detect_base_url()` (env vars).
    """

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
        resolved_base_url = normalize_base_url(
            base_url or (f"https://{sepal_host}" if sepal_host else None) or detect_base_url()
        )
        resolved_auth = auth or (CookieAuth(session_id) if session_id else detect_auth())
        resolved_verify = verify if verify is not None else _verify_for(resolved_base_url)

        self.module_name = module_name
        self.base_url = resolved_base_url
        self.verify_ssl = resolved_verify
        self._http = httpx.Client(
            base_url=resolved_base_url,
            auth=resolved_auth,
            verify=resolved_verify,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

        self.user_files = UserFilesEndpoint(self._http)
        self.tasks = TasksEndpoint(self._http)
        self.processing_recipes = ProcessingRecipesEndpoint(self._http)
        self.recipes = self.processing_recipes

        self.results_path: Any = None
        if module_name and create_base_dir:
            self.results_path = self.user_files.module_dir(module_name)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "SepalClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class AsyncSepalClient:
    """Async twin of `SepalClient`.

    `module_dir` creation is performed lazily on first await of
    `async with ...:` so we don't fire HTTP from a sync constructor.
    """

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
        resolved_base_url = normalize_base_url(
            base_url or (f"https://{sepal_host}" if sepal_host else None) or detect_base_url()
        )
        resolved_auth = auth or (CookieAuth(session_id) if session_id else detect_auth())
        resolved_verify = verify if verify is not None else _verify_for(resolved_base_url)
        self.module_name = module_name
        self.base_url = resolved_base_url
        self.verify_ssl = resolved_verify
        self._create_base_dir = create_base_dir
        self._http = httpx.AsyncClient(
            base_url=resolved_base_url,
            auth=resolved_auth,
            verify=resolved_verify,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self.user_files = AsyncUserFilesEndpoint(self._http)
        self.tasks = AsyncTasksEndpoint(self._http)
        self.processing_recipes = AsyncProcessingRecipesEndpoint(self._http)
        self.recipes = self.processing_recipes
        self.results_path: Any = None

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncSepalClient":
        if self.module_name and self._create_base_dir:
            self.results_path = await self.user_files.module_dir(self.module_name)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()
