"""pysepal-api — UI-free HTTP client for SEPAL services."""

from .auth import ApiKeyAuth, AuthMode, CookieAuth, NoAuth, detect_auth
from .client import AsyncSepalClient, SepalClient
from .endpoints.ee_exports import (
    AsyncEEExportsEndpoint,
    EEExportDestination,
    EEExportKind,
    EEExportsEndpoint,
    serialize_ee_object,
)
from .errors import (
    ApiError,
    BadRequest,
    Conflict,
    Forbidden,
    InvalidPathError,
    MissingDependency,
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
from .paths import module_results_path

__version__ = "0.4.0"

__all__ = [
    "ApiError",
    "ApiKeyAuth",
    "AsyncEEExportsEndpoint",
    "AsyncSepalClient",
    "AuthMode",
    "BadRequest",
    "Conflict",
    "CookieAuth",
    "DirectoryListing",
    "EEExportDestination",
    "EEExportKind",
    "EEExportsEndpoint",
    "FileEntry",
    "FileWriteResult",
    "Forbidden",
    "InvalidPathError",
    "MissingDependency",
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
    "module_results_path",
    "normalize_base_url",
    "serialize_ee_object",
]
