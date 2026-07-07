"""pysepal-api — UI-free HTTP client for SEPAL services."""

from .auth import ApiKeyAuth, CookieAuth, NoAuth, detect_auth
from .client import AsyncSepalClient, SepalClient
from .errors import (
    ApiError,
    BadRequest,
    Conflict,
    Forbidden,
    InvalidPathError,
    MissingHostError,
    NoCredentialsError,
    NotFound,
    PysepalError,
    ResponseError,
    ServerError,
    TaskCanceled,
    TaskError,
    TaskFailed,
    TaskTimeout,
    TooManyRequests,
    TransportError,
    Unauthorized,
)
from .host import detect_base_url, normalize_base_url
from .models import (
    DirectoryListing,
    FileEntry,
    FileWriteResult,
    RecipeSummary,
    Task,
    TaskState,
)

__version__ = "0.1.0"

__all__ = [
    "ApiError",
    "ApiKeyAuth",
    "AsyncSepalClient",
    "BadRequest",
    "Conflict",
    "CookieAuth",
    "DirectoryListing",
    "FileEntry",
    "FileWriteResult",
    "Forbidden",
    "InvalidPathError",
    "MissingHostError",
    "NoAuth",
    "NoCredentialsError",
    "NotFound",
    "PysepalError",
    "RecipeSummary",
    "ResponseError",
    "SepalClient",
    "ServerError",
    "Task",
    "TaskCanceled",
    "TaskError",
    "TaskFailed",
    "TaskState",
    "TaskTimeout",
    "TooManyRequests",
    "TransportError",
    "Unauthorized",
    "__version__",
    "detect_auth",
    "detect_base_url",
    "normalize_base_url",
]
