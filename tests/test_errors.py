import pickle

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


@pytest.mark.parametrize(
    "body",
    [
        {"message": "Unsupported table export fileFormat: TIFF"},
        {"defaultMessage": "Unsupported table export fileFormat: TIFF", "messageKey": "x"},
    ],
)
def test_error_text_ends_with_the_reason_the_service_gave(body: dict[str, str]) -> None:
    reason = "Unsupported table export fileFormat: TIFF"
    err = error_for_status(400, url="https://x/api/tasks", body=body)
    assert err.reason == reason
    assert str(err) == f"SEPAL API 400 for https://x/api/tasks: {reason}"


@pytest.mark.parametrize(
    "body", [None, "<html>Bad Gateway</html>", {"message": "  "}, {"message": 42}, {"error": "no"}]
)
def test_error_text_has_no_reason_when_the_body_gives_none(body: object) -> None:
    err = error_for_status(502, url="https://x/api/tasks", body=body)
    assert err.reason is None
    assert str(err) == "SEPAL API 502 for https://x/api/tasks"


def test_error_text_shows_a_multiline_reason_on_one_line() -> None:
    err = error_for_status(500, url="https://x/api/tasks", body={"message": "Boom\n  at a()\n"})
    assert err.reason == "Boom\n  at a()"
    assert str(err) == "SEPAL API 500 for https://x/api/tasks: Boom at a()"


def test_error_text_shortens_a_long_reason() -> None:
    reason = "x" * 5000
    err = error_for_status(500, url="https://x/api/tasks", body={"message": reason})
    assert err.reason == reason
    assert len(str(err)) < 400
    assert str(err).endswith("…")


@pytest.mark.parametrize("status_code", [400, 418, 503])
def test_api_errors_survive_pickling(status_code: int) -> None:
    err = error_for_status(status_code, url="https://x/api/tasks", body={"message": "No such task"})
    err.__notes__ = ["while exporting"]  # what add_note() does on 3.11+
    copy = pickle.loads(pickle.dumps(err))
    assert type(copy) is type(err)
    assert (copy.status_code, copy.url, copy.body, copy.reason) == (
        status_code,
        "https://x/api/tasks",
        {"message": "No such task"},
        "No such task",
    )
    assert str(copy) == str(err)
    assert copy.__notes__ == ["while exporting"]


def test_missing_host_and_credentials() -> None:
    with pytest.raises(MissingHostError):
        raise MissingHostError("nope")
    with pytest.raises(NoCredentialsError):
        raise NoCredentialsError("nope")
    # Both catchable via the single library root.
    with pytest.raises(PysepalError):
        raise MissingHostError("nope")
