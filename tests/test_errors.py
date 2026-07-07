import pytest

from pysepal_api.errors import (
    ApiError,
    BadRequest,
    Conflict,
    Forbidden,
    MissingHostError,
    NoCredentialsError,
    NotFound,
    PysepalError,
    ServerError,
    TaskCanceled,
    TaskError,
    TaskFailed,
    TaskTimeout,
    TooManyRequests,
    TransportError,
    Unauthorized,
    error_for_status,
)
from pysepal_api.models import Task


def test_http_error_hierarchy() -> None:
    for cls in (
        BadRequest,
        Unauthorized,
        Forbidden,
        NotFound,
        Conflict,
        TooManyRequests,
        ServerError,
    ):
        assert issubclass(cls, ApiError)


def test_everything_descends_from_pysepal_error() -> None:
    for cls in (
        ApiError,
        TransportError,
        NoCredentialsError,
        MissingHostError,
        TaskFailed,
        TaskCanceled,
        TaskTimeout,
    ):
        assert issubclass(cls, PysepalError)


def test_non_http_errors_are_not_api_errors() -> None:
    assert not issubclass(TransportError, ApiError)
    assert not issubclass(TaskFailed, ApiError)
    assert not issubclass(TaskCanceled, ApiError)


def test_task_errors_share_a_base_and_timeout_is_a_timeouterror() -> None:
    for cls in (TaskFailed, TaskCanceled, TaskTimeout):
        assert issubclass(cls, TaskError)
    # TaskTimeout must stay catchable as the builtin TimeoutError too.
    assert issubclass(TaskTimeout, TimeoutError)


def test_task_errors_carry_the_observed_task() -> None:
    task = Task.model_validate({"id": "t1", "state": "FAILED"})
    err = TaskFailed("Task t1 failed", task=task)
    assert err.task is task
    # `task` is optional so the errors stay constructible from a bare message.
    assert TaskCanceled("canceled").task is None


def test_error_for_status_maps_known_codes() -> None:
    err = error_for_status(404, url="https://sepal.io/api/foo", body={"msg": "x"})
    assert isinstance(err, NotFound)
    assert err.status_code == 404
    assert err.url == "https://sepal.io/api/foo"
    assert err.body == {"msg": "x"}


def test_error_for_status_maps_429() -> None:
    assert isinstance(error_for_status(429, url="u", body=None), TooManyRequests)


def test_error_for_status_5xx() -> None:
    assert isinstance(error_for_status(503, url="u", body="boom"), ServerError)


def test_error_for_status_unknown_raises_generic() -> None:
    err = error_for_status(418, url="u", body=None)
    assert type(err) is ApiError
    assert err.status_code == 418


def test_repr_includes_status() -> None:
    err = error_for_status(401, url="https://x", body={"e": "nope"})
    assert "401" in str(err)


def test_missing_host_and_credentials() -> None:
    with pytest.raises(MissingHostError):
        raise MissingHostError("nope")
    with pytest.raises(NoCredentialsError):
        raise NoCredentialsError("nope")
    # Both catchable via the single library root.
    with pytest.raises(PysepalError):
        raise MissingHostError("nope")
