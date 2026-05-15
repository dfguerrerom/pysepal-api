"""pysepal-api — UI-free HTTP client for SEPAL services."""

from .auth import ApiKeyAuth, CookieAuth, NoAuth, detect_auth
from .client import SepalClient
from .errors import (
    BadRequest,
    Conflict,
    Forbidden,
    MissingHostError,
    NoCredentialsError,
    NotFound,
    SepalApiError,
    SepalTransportError,
    ServerError,
    TaskCanceled,
    TaskFailed,
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

__version__ = "0.1.0.dev0"

__all__ = [
    "ApiKeyAuth",
    "CookieAuth",
    "NoAuth",
    "SepalClient",
    "detect_auth",
    "detect_base_url",
    "normalize_base_url",
    "DirectoryListing",
    "FileEntry",
    "FileWriteResult",
    "RecipeSummary",
    "Task",
    "TaskState",
    "BadRequest",
    "Conflict",
    "Forbidden",
    "MissingHostError",
    "NoCredentialsError",
    "NotFound",
    "SepalApiError",
    "SepalTransportError",
    "ServerError",
    "TaskCanceled",
    "TaskFailed",
    "Unauthorized",
    "__version__",
]
