"""pysepal-api — UI-free HTTP client for SEPAL services."""

from .auth import ApiKeyAuth, CookieAuth, NoAuth, detect_auth
from .client import AsyncSepalClient, SepalClient
from .errors import (
    BadRequest,
    Conflict,
    Forbidden,
    InvalidPathError,
    MissingHostError,
    NoCredentialsError,
    NotFound,
    PysepalError,
    ResponseError,
    SepalApiError,
    SepalTransportError,
    ServerError,
    TaskCanceled,
    TaskError,
    TaskFailed,
    TaskTimeout,
    TooManyRequests,
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
    "SepalApiError",
    "SepalClient",
    "SepalTransportError",
    "ServerError",
    "Task",
    "TaskCanceled",
    "TaskError",
    "TaskFailed",
    "TaskState",
    "TaskTimeout",
    "TooManyRequests",
    "Unauthorized",
    "__version__",
    "detect_auth",
    "detect_base_url",
    "normalize_base_url",
]
