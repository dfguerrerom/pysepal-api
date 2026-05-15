import pytest

from pysepal_api.errors import (
    BadRequest,
    Conflict,
    Forbidden,
    NoCredentialsError,
    NotFound,
    SepalApiError,
    SepalTransportError,
    ServerError,
    TaskCanceled,
    TaskFailed,
    Unauthorized,
    MissingHostError,
    error_for_status,
)


def test_error_hierarchy() -> None:
    for cls in (BadRequest, Unauthorized, Forbidden, NotFound, Conflict, ServerError):
        assert issubclass(cls, SepalApiError)
    assert not issubclass(SepalTransportError, SepalApiError)


def test_error_for_status_maps_known_codes() -> None:
    err = error_for_status(404, url="https://sepal.io/api/foo", body={"msg": "x"})
    assert isinstance(err, NotFound)
    assert err.status_code == 404
    assert err.url == "https://sepal.io/api/foo"
    assert err.body == {"msg": "x"}


def test_error_for_status_5xx() -> None:
    err = error_for_status(503, url="u", body="boom")
    assert isinstance(err, ServerError)


def test_error_for_status_unknown_raises_generic() -> None:
    err = error_for_status(418, url="u", body=None)
    assert type(err) is SepalApiError
    assert err.status_code == 418


def test_repr_redacts_nothing_but_includes_status() -> None:
    err = error_for_status(401, url="https://x", body={"e": "nope"})
    assert "401" in str(err)


def test_missing_host_and_credentials() -> None:
    with pytest.raises(MissingHostError):
        raise MissingHostError("nope")
    with pytest.raises(NoCredentialsError):
        raise NoCredentialsError("nope")


def test_task_errors() -> None:
    assert not issubclass(TaskFailed, SepalApiError)
    assert not issubclass(TaskCanceled, SepalApiError)
