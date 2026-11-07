import time

from starlette.requests import Request

from emporio.api.guards import SlidingWindow, client_ip
from tests.api.helpers import PROXY_PHRASE, make_settings


def test_expired_key_is_removed():
    window = SlidingWindow(1, 0.01)
    assert window.allow("a")
    time.sleep(0.03)
    assert window.allow("b")
    assert "a" not in window._hits  # pyright: ignore[reportPrivateUsage]  # whitebox: no leak


def _request(headers: dict[str, str], client: tuple[str, int] | None = ("10.0.0.1", 1)) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": client})


def test_client_ip_trusts_header_with_the_right_secret():
    request = _request({"X-Client-IP": "203.0.113.7", "X-Proxy-Auth": PROXY_PHRASE})
    assert client_ip(request, make_settings(proxy_secret=PROXY_PHRASE)) == "203.0.113.7"


def test_client_ip_ignores_header_with_a_wrong_secret():
    request = _request({"X-Client-IP": "203.0.113.7", "X-Proxy-Auth": "guess"})
    assert client_ip(request, make_settings(proxy_secret=PROXY_PHRASE)) == "10.0.0.1"


def test_client_ip_ignores_header_without_a_secret_header():
    request = _request({"X-Client-IP": "203.0.113.7"})
    assert client_ip(request, make_settings(proxy_secret=PROXY_PHRASE)) == "10.0.0.1"


def test_client_ip_ignores_header_when_no_secret_is_configured():
    request = _request({"X-Client-IP": "203.0.113.7", "X-Proxy-Auth": ""})
    assert client_ip(request, make_settings()) == "10.0.0.1"


def test_client_ip_empty_trusted_header_falls_back_to_the_peer():
    request = _request({"X-Client-IP": "", "X-Proxy-Auth": PROXY_PHRASE})
    assert client_ip(request, make_settings(proxy_secret=PROXY_PHRASE)) == "10.0.0.1"


def test_client_ip_without_a_peer_is_unknown():
    assert client_ip(_request({}, client=None), make_settings()) == "unknown"
