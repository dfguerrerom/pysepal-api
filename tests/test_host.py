import pytest

from pysepal_api.errors import MissingHostError
from pysepal_api.host import detect_base_url, normalize_base_url


def test_normalize_host_only() -> None:
    assert normalize_base_url("sepal.io") == "https://sepal.io"


def test_normalize_full_url_strips_trailing_slash() -> None:
    assert normalize_base_url("https://sepal.io/") == "https://sepal.io"


def test_normalize_keeps_port() -> None:
    assert normalize_base_url("sepal.io:8443") == "https://sepal.io:8443"


def test_normalize_keeps_https_explicit() -> None:
    assert normalize_base_url("https://sepal.io") == "https://sepal.io"


def test_normalize_keeps_http_for_localhost() -> None:
    assert normalize_base_url("http://localhost:9000") == "http://localhost:9000"


def test_detect_uses_sepal_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEPAL_ENDPOINT", raising=False)
    monkeypatch.setenv("SEPAL_HOST", "danielg.sepal.io")
    assert detect_base_url() == "https://danielg.sepal.io"


def test_detect_prefers_sepal_endpoint_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEPAL_ENDPOINT", "https://sepal.io")
    monkeypatch.setenv("SEPAL_HOST", "ignored.sepal.io")
    assert detect_base_url() == "https://sepal.io"


def test_detect_missing_host_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEPAL_HOST", raising=False)
    monkeypatch.delenv("SEPAL_ENDPOINT", raising=False)
    with pytest.raises(MissingHostError):
        detect_base_url()
