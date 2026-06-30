"""Shared request building and response handling for endpoint methods.

The sync and async clients share one *request core*: every operation describes
its HTTP call as a pure ``RequestSpec`` (method, url, params, body, …) built by
a module-level function, and the only thing that differs between the sync and
async surfaces is whether the spec is sent via ``send_with_error_mapping`` or
its ``_async`` twin. This keeps the request/response logic in one place so the
two surfaces cannot drift.

This module deliberately does *not* own credentials, base URL, or TLS
verification — those are configured on the ``httpx.Client`` itself. Keeping
auth on the transport object instead of the client would build requests that
are never authenticated (a real bug we hit in an earlier draft).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from .errors import SepalTransportError, error_for_status


@dataclass(frozen=True)
class RequestSpec:
    """A pure description of one HTTP call, shared by the sync and async paths."""

    method: str
    url: str
    params: Mapping[str, str] | None = None
    json: Any = None
    content: bytes | None = None
    files: Any = None
    headers: Mapping[str, str] | None = None

    def build(self, http: httpx.Client | httpx.AsyncClient) -> httpx.Request:
        return http.build_request(
            self.method,
            self.url,
            params=self.params,
            json=self.json,
            content=self.content,
            files=self.files,
            headers=self.headers,
        )


def _safe_url(request: httpx.Request) -> str:
    """Return the request URL without any password component."""
    url = request.url
    if url.password:
        url = url.copy_with(password=None)
    return str(url)


def parse_json(response: httpx.Response) -> Any:
    """Parse a JSON response body. Empty body returns None."""
    if not response.content:
        return None
    return response.json()


def _body_for_error(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if "json" in content_type:
        try:
            return response.json()
        except ValueError:
            pass
    text = response.text
    return text if len(text) <= 4096 else text[:4096] + "...[truncated]"


def send_with_error_mapping(client: httpx.Client, request: httpx.Request) -> httpx.Response:
    """Send a prepared request and translate failures to typed errors."""
    try:
        response = client.send(request)
    except httpx.TransportError as exc:
        raise SepalTransportError(f"{type(exc).__name__}: {exc}") from exc
    if response.is_success:
        return response
    raise error_for_status(
        response.status_code,
        url=_safe_url(request),
        body=_body_for_error(response),
    )


async def send_with_error_mapping_async(
    client: httpx.AsyncClient, request: httpx.Request
) -> httpx.Response:
    """Async twin of `send_with_error_mapping`."""
    try:
        response = await client.send(request)
    except httpx.TransportError as exc:
        raise SepalTransportError(f"{type(exc).__name__}: {exc}") from exc
    if response.is_success:
        return response
    raise error_for_status(
        response.status_code,
        url=_safe_url(request),
        body=_body_for_error(response),
    )
