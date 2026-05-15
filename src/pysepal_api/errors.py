"""Error types raised by pysepal-api.

Two roots:

- `SepalApiError` for non-2xx HTTP responses from SEPAL.
- Standalone exceptions for non-HTTP problems (transport, missing config,
  failed tasks).
"""

from __future__ import annotations

from typing import Any


class SepalApiError(Exception):
    """Base for non-2xx responses from a SEPAL service."""

    def __init__(self, status_code: int, *, url: str, body: Any = None) -> None:
        self.status_code = status_code
        self.url = url
        self.body = body
        super().__init__(f"SEPAL API {status_code} for {url}")


class BadRequest(SepalApiError):
    pass


class Unauthorized(SepalApiError):
    pass


class Forbidden(SepalApiError):
    pass


class NotFound(SepalApiError):
    pass


class Conflict(SepalApiError):
    pass


class ServerError(SepalApiError):
    pass


class SepalTransportError(Exception):
    """Network/send failure: DNS, connection, timeout, etc."""


class NoCredentialsError(Exception):
    """No usable auth could be detected."""


class MissingHostError(Exception):
    """No SEPAL host could be detected."""


class TaskFailed(Exception):
    """Raised by tasks.wait when a task reaches FAILED."""


class TaskCanceled(Exception):
    """Raised by tasks.wait when a task reaches CANCELED."""


_BY_STATUS: dict[int, type[SepalApiError]] = {
    400: BadRequest,
    401: Unauthorized,
    403: Forbidden,
    404: NotFound,
    409: Conflict,
}


def error_for_status(status_code: int, *, url: str, body: Any) -> SepalApiError:
    """Map an HTTP status code to the most specific SepalApiError."""
    cls = _BY_STATUS.get(status_code)
    if cls is None and 500 <= status_code < 600:
        cls = ServerError
    if cls is None:
        cls = SepalApiError
    return cls(status_code, url=url, body=body)
