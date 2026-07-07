import httpx
import pytest
import respx

from pysepal_api.errors import (
    ApiError,
    NotFound,
    TransportError,
    Unauthorized,
)
from pysepal_api.transport import parse_json, send_with_error_mapping


def _client() -> httpx.Client:
    return httpx.Client(base_url="https://example.test", timeout=5.0)


def test_parse_json_returns_payload() -> None:
    response = httpx.Response(200, json={"hello": "world"})
    assert parse_json(response) == {"hello": "world"}


def test_send_returns_response_on_2xx() -> None:
    with respx.mock(base_url="https://example.test") as mock:
        mock.get("/ok").respond(200, json={"ok": True})
        with _client() as c:
            req = c.build_request("GET", "/ok")
            resp = send_with_error_mapping(c, req)
            assert resp.json() == {"ok": True}


def test_send_maps_401_to_unauthorized() -> None:
    with respx.mock(base_url="https://example.test") as mock:
        mock.get("/nope").respond(401, json={"error": "no"})
        with _client() as c:
            req = c.build_request("GET", "/nope")
            with pytest.raises(Unauthorized) as ei:
                send_with_error_mapping(c, req)
            assert ei.value.status_code == 401
            assert ei.value.body == {"error": "no"}


def test_send_maps_404() -> None:
    with respx.mock(base_url="https://example.test") as mock:
        mock.get("/missing").respond(404, text="gone")
        with _client() as c:
            req = c.build_request("GET", "/missing")
            with pytest.raises(NotFound) as ei:
                send_with_error_mapping(c, req)
            assert ei.value.body == "gone"


def test_send_maps_5xx_generic() -> None:
    with respx.mock(base_url="https://example.test") as mock:
        mock.get("/oops").respond(503, text="x")
        with _client() as c:
            req = c.build_request("GET", "/oops")
            with pytest.raises(ApiError):
                send_with_error_mapping(c, req)


def test_send_maps_transport_error() -> None:
    with respx.mock(base_url="https://example.test") as mock:
        mock.get("/boom").mock(side_effect=httpx.ConnectError("dns"))
        with _client() as c:
            req = c.build_request("GET", "/boom")
            with pytest.raises(TransportError):
                send_with_error_mapping(c, req)


def test_parse_json_wraps_malformed_body() -> None:
    from pysepal_api.errors import PysepalError, ResponseError

    resp = httpx.Response(200, content=b"not json", headers={"content-type": "application/json"})
    with pytest.raises(ResponseError):
        parse_json(resp)
    # contract: a malformed response is catchable via the library root
    with pytest.raises(PysepalError):
        parse_json(resp)


def test_parse_one_wraps_validation_error() -> None:
    from pysepal_api.errors import PysepalError
    from pysepal_api.models import Task
    from pysepal_api.transport import parse_one

    resp = httpx.Response(200, json={"missing": "fields"})
    with pytest.raises(PysepalError):
        parse_one(resp, Task)


def test_parse_many_wraps_non_array_body() -> None:
    from pysepal_api.errors import PysepalError
    from pysepal_api.models import RecipeSummary
    from pysepal_api.transport import parse_many

    # a scalar body would raise a raw TypeError at iteration without the guard
    for body in (1, True, {"not": "a list"}):
        with pytest.raises(PysepalError):
            parse_many(httpx.Response(200, json=body), RecipeSummary)


def test_parse_many_empty_body_is_empty_list() -> None:
    from pysepal_api.models import RecipeSummary
    from pysepal_api.transport import parse_many

    assert parse_many(httpx.Response(200, content=b""), RecipeSummary) == []
    assert parse_many(httpx.Response(200, json=[]), RecipeSummary) == []
