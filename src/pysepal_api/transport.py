"""Shared response parsing and error mapping for endpoint methods.

This module deliberately does *not* own credentials, base URL, or TLS
verification — those are configured on the `httpx.Client` itself. Keeping
auth on the transport object instead of the client would build requests that
are never authenticated (a real bug we hit in an earlier draft).
"""

from __future__ import annotations

from typing import Any

import httpx

from .errors import SepalTransportError, error_for_status


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


def send_with_error_mapping(
    client: httpx.Client, request: httpx.Request
) -> httpx.Response:
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
