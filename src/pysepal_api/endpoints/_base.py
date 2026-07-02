"""Sync/async endpoint bases.

Every endpoint operation builds a shared :class:`~pysepal_api.transport.RequestSpec`
and sends it through ``_send``. ``_send`` is the *only* place the sync and async
surfaces diverge — everything else (URL, params, body, parsing) is shared.
"""

from __future__ import annotations

import httpx

from ..transport import (
    RequestSpec,
    send_with_error_mapping,
    send_with_error_mapping_async,
)


class _SyncEndpoint:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def _send(self, spec: RequestSpec) -> httpx.Response:
        return send_with_error_mapping(self._http, spec.build(self._http))


class _AsyncEndpoint:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def _send(self, spec: RequestSpec) -> httpx.Response:
        return await send_with_error_mapping_async(self._http, spec.build(self._http))
