"""Error types raised by pysepal-api.

Every exception the library raises derives from a single root, ``PysepalError``,
so a caller can ``except PysepalError`` to catch *anything* this library throws.
Beneath that root:

- ``ApiError`` (and its status-specific subclasses) for non-2xx HTTP
  responses from a SEPAL service.
- ``TransportError`` / ``NoCredentialsError`` / ``MissingHostError`` for
  non-HTTP problems (network, missing config).
- ``TaskError`` (``TaskFailed`` / ``TaskCanceled`` / ``TaskTimeout``) for the
  terminal outcomes of ``tasks.wait``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Task


class PysepalError(Exception):
    """Root of every exception raised by pysepal-api."""


class ApiError(PysepalError):
    """Base for non-2xx responses from a SEPAL service.

    ``reason`` is the message the service gave for the failure, if its body
    carried one; the error text ends with it, so a traceback shows why.
    """

    def __init__(self, status_code: int, *, url: str, body: Any = None) -> None:
        self.status_code = status_code
        self.url = url
        self.body = body
        self.reason = _reason(body)
        suffix = f": {self.reason}" if self.reason else ""
        super().__init__(f"SEPAL API {status_code} for {url}{suffix}")


class BadRequest(ApiError):
    pass


class Unauthorized(ApiError):
    pass


class Forbidden(ApiError):
    pass


class NotFound(ApiError):
    pass


class Conflict(ApiError):
    pass


class TooManyRequests(ApiError):
    """429 — rate limited. Distinct so callers can back off programmatically."""


class ServerError(ApiError):
    pass


class MissingDependency(PysepalError):
    """An optional dependency needed for a feature is not installed.

    Raised when a code path needs a package from an extra (e.g. ``ee`` from
    ``pysepal-api[ee]``) that was not installed. The message carries the
    ``pip install`` hint to remedy it.
    """


class TransportError(PysepalError):
    """Network/send failure: DNS, connection, timeout, etc."""


class ResponseError(PysepalError):
    """A SEPAL response could not be parsed or did not match the expected shape.

    Wraps malformed JSON (`json.JSONDecodeError`) and pydantic `ValidationError`
    from response parsing; the underlying cause is available via `__cause__`.
    """


class NoCredentialsError(PysepalError):
    """No usable auth could be detected."""


class MissingHostError(PysepalError):
    """No SEPAL host could be detected."""


class InvalidPathError(PysepalError, ValueError):
    """A user-files path is outside the sandbox home or contains `..` traversal.

    Subclasses `ValueError` too, so existing `except ValueError` handlers keep
    working while the error is also catchable via the `PysepalError` root.
    """


class TaskError(PysepalError):
    """Base for a non-success terminal outcome of ``tasks.wait``.

    Carries the last-observed ``Task`` as ``task`` so callers can inspect
    ``status_description`` / ``task_info`` without re-fetching.
    """

    def __init__(self, message: str, *, task: Task | None = None) -> None:
        self.task = task
        super().__init__(message)


class TaskFailed(TaskError):
    """Raised by tasks.wait when a task reaches FAILED."""


class TaskCanceled(TaskError):
    """Raised by tasks.wait when a task reaches CANCELED."""


class TaskTimeout(TaskError, TimeoutError):
    """Raised by tasks.wait when a task does not reach a terminal state in time.

    Subclasses the builtin ``TimeoutError`` too, so ``except TimeoutError`` keeps
    working alongside ``except TaskError`` / ``except PysepalError``.
    """


_BY_STATUS: dict[int, type[ApiError]] = {
    400: BadRequest,
    401: Unauthorized,
    403: Forbidden,
    404: NotFound,
    409: Conflict,
    429: TooManyRequests,
}


# task-manager answers ``{"message": ...}``; services built on SEPAL's shared HTTP server answer
# ``{"defaultMessage": ..., "messageKey": ...}``.
_REASON_KEYS = ("message", "defaultMessage")


def _reason(body: Any) -> str | None:
    if not isinstance(body, Mapping):
        return None
    for key in _REASON_KEYS:
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def error_for_status(status_code: int, *, url: str, body: Any) -> ApiError:
    """Map an HTTP status code to the most specific ApiError."""
    cls = _BY_STATUS.get(status_code)
    if cls is None and 500 <= status_code < 600:
        cls = ServerError
    if cls is None:
        cls = ApiError
    return cls(status_code, url=url, body=body)
