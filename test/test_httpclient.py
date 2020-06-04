from unittest.mock import patch

import pytest
import responses
from smalld import ConnectionError, HttpError
from smalld.smalld import HttpClient


@pytest.fixture(autouse=True)
def limiter():
    with patch("smalld.smalld.RateLimiter") as ratelimiter_cls:
        yield ratelimiter_cls.return_value


@responses.activate
@pytest.mark.parametrize(
    "method, path, client_method",
    [
        ("GET", "/get", HttpClient.get),
        ("POST", "/post", HttpClient.post),
        ("PUT", "/put", HttpClient.put),
        ("PATCH", "/patch", HttpClient.patch),
        ("DELETE", "/delete", HttpClient.delete),
    ],
)
def test_httpclient_returns_successful_responses(method, path, client_method):
    url = f"https://domain.com/{path}"
    responses.add(method, url, json={"data": "some data"}, status=200)
    client = HttpClient("token", "https://domain.com")

    res = client_method(client, path)

    assert hasattr(res, "data") and res.data == "some data"
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == url
    assert responses.calls[0].request.method == method


@responses.activate
def test_httpclient_raises_for_non_2xx_status():
    statuses = [400, 403, 404, 500, 501, 502]  # sample non 2xx statuses
    client = HttpClient("token", "https://domain.com")

    for status in statuses:
        responses.add(responses.GET, "https://domain.com/get", status=status)
        with pytest.raises(HttpError):
            res = client.send_request("GET", "get")
        responses.remove(responses.GET, "https://domain.com/get")


@responses.activate
def test_httpclient_raises_for_connection_errors():
    client = HttpClient("token", "https://domain.com")

    with pytest.raises(ConnectionError):
        client.get("path")


@responses.activate
def test_httpclient_calls_limiter_before_and_after_request(limiter):
    def assert_called_before_request(*args, **kwargs):
        assert len(responses.calls) == 0

    limiter.on_request.side_effect = assert_called_before_request

    headers = {"X-Header": "value"}
    responses.add(
        responses.GET, "https://domain.com/get", json={"data": "value"}, headers=headers
    )
    extra_headers = {"Content-Type": "application/json"}  # added by responses

    client = HttpClient("token", "https://domain.com")
    client.get("get")

    limiter.on_request.assert_called_once_with("GET", "get")
    limiter.on_response.assert_called_once_with(
        "GET", "get", dict(**headers, **extra_headers), 200
    )
    assert len(responses.calls) == 1


@responses.activate
def test_httpclient_handles_no_content():
    responses.add(responses.GET, "https://domain.com/get", status=204)
    client = HttpClient("token", "https://domain.com")
    res = client.get("get")
    assert res == {}


@responses.activate
@pytest.mark.parametrize("invalid_json", ["", "invalid json", '{"key": value}'])
def test_httpclient_raises_for_response_decoding_errors(invalid_json):
    responses.add(responses.GET, "https://domain.com/get", body=invalid_json)

    client = HttpClient("token", "https://domain.com")
    with pytest.raises(HttpError):
        client.get("get")
