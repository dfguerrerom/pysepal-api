import httpx
import pytest
import respx

from pysepal_api.errors import (
    NotFound,
    SepalApiError,
    SepalTransportError,
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
            with pytest.raises(SepalApiError):
                send_with_error_mapping(c, req)


def test_send_maps_transport_error() -> None:
    with respx.mock(base_url="https://example.test") as mock:
        mock.get("/boom").mock(side_effect=httpx.ConnectError("dns"))
        with _client() as c:
            req = c.build_request("GET", "/boom")
            with pytest.raises(SepalTransportError):
                send_with_error_mapping(c, req)
