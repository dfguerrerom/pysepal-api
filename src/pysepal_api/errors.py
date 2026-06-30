"""Error types raised by pysepal-api.

Every exception the library raises derives from a single root, ``PysepalError``,
so a caller can ``except PysepalError`` to catch *anything* this library throws.
Beneath that root:

- ``SepalApiError`` (and its status-specific subclasses) for non-2xx HTTP
  responses from a SEPAL service.
- ``SepalTransportError`` / ``NoCredentialsError`` / ``MissingHostError`` for
  non-HTTP problems (network, missing config).
- ``TaskError`` (``TaskFailed`` / ``TaskCanceled`` / ``TaskTimeout``) for the
  terminal outcomes of ``tasks.wait``.
"""

from __future__ import annotations

from typing import Any


class PysepalError(Exception):
    """Root of every exception raised by pysepal-api."""


class SepalApiError(PysepalError):
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


class TooManyRequests(SepalApiError):
    """429 — rate limited. Distinct so callers can back off programmatically."""


class ServerError(SepalApiError):
    pass


class SepalTransportError(PysepalError):
    """Network/send failure: DNS, connection, timeout, etc."""


class NoCredentialsError(PysepalError):
    """No usable auth could be detected."""


class MissingHostError(PysepalError):
    """No SEPAL host could be detected."""


class TaskError(PysepalError):
    """Base for a non-success terminal outcome of ``tasks.wait``."""


class TaskFailed(TaskError):
    """Raised by tasks.wait when a task reaches FAILED."""


class TaskCanceled(TaskError):
    """Raised by tasks.wait when a task reaches CANCELED."""


class TaskTimeout(TaskError, TimeoutError):
    """Raised by tasks.wait when a task does not reach a terminal state in time.

    Subclasses the builtin ``TimeoutError`` too, so ``except TimeoutError`` keeps
    working alongside ``except TaskError`` / ``except PysepalError``.
    """


_BY_STATUS: dict[int, type[SepalApiError]] = {
    400: BadRequest,
    401: Unauthorized,
    403: Forbidden,
    404: NotFound,
    409: Conflict,
    429: TooManyRequests,
}


def error_for_status(status_code: int, *, url: str, body: Any) -> SepalApiError:
    """Map an HTTP status code to the most specific SepalApiError."""
    cls = _BY_STATUS.get(status_code)
    if cls is None and 500 <= status_code < 600:
        cls = ServerError
    if cls is None:
        cls = SepalApiError
    return cls(status_code, url=url, body=body)
