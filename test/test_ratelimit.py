from unittest.mock import patch

import pytest
import requests
from smalld.ratelimit import *


class ControllableTime:
    def __init__(self):
        self.time = 0

    def __call__(self):
        return self.time

    def set_to(self, time):
        self.time = time


def make_request(method, url):
    return requests.Request(method, url)


default_request = make_request("GET", "url")


def make_response(status_code, headers, request=default_request):
    res = requests.Response()
    res.status_code = status_code
    res.headers.update(headers)
    res.url = request.url
    res.request = request
    return res


def make_ratelimit_headers(
    bucket="default", limit=10, remaining=1, reset=1, reset_after=1
):
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset),
        "X-RateLimit-Reset-After": str(reset_after),
        "X-RateLimit-Bucket": bucket,
    }


def make_global_ratelimit_headers(retry_after):
    return {"Retry-After": str(retry_after), "X-RateLimit-Global": "true"}


@pytest.fixture(autouse=True)
def time():
    with patch("time.time") as time_mock:
        time = ControllableTime()
        time_mock.side_effect = time
        yield time


def test_resource_ratelimit_bucket(time):
    time.set_to(1000)
    bucket = ResourceRateLimitBucket("abc123")
    bucket.update(make_ratelimit_headers(reset=1001, reset_after=1))

    assert bucket.bucket_id == "abc123"
    assert bucket.reset == 1001
    assert bucket.remaining == 1

    bucket.take()  # doesn't raise
    assert bucket.remaining == 0

    with pytest.raises(RateLimitException) as exc_info:
        bucket.take()

    e = exc_info.value
    assert e.reset == 1001 and e.is_global == False


def test_global_ratelimit_bucket(time):
    time.set_to(100)
    limit = GlobalRateLimitBucket()

    assert not limit.is_ratelimited
    limit.take()  # doesn't raise

    limit.update({"Retry-After": "100", "X-RateLimit-Global": "true"})

    assert limit.is_ratelimited

    with pytest.raises(RateLimitException) as exc_info:
        limit.take()

    e = exc_info.value
    assert e.reset == 101 and e.is_global == True


def test_ratelimit_passes_first_request():
    request = make_request("GET", "url")
    limiter = RateLimiter()
    limiter.intercept_request(request)  # doesn't raise


def test_ratelimit_passes_good_response(time):
    response = make_response(200, make_ratelimit_headers())
    limiter = RateLimiter()
    limiter.intercept_request(response)  # doesn't raise


@pytest.mark.parametrize(
    "start, reset, is_global, response",
    [
        (
            0,
            1,
            True,
            make_response(429, make_global_ratelimit_headers(100)),
        ),
        (
            1000,
            1001,
            False,
            make_response(
                429, make_ratelimit_headers("abc123", 10, 0, 1001, 1)
            ),
        ),
    ],
)
def test_ratelimit_raises_on_limit_exhausted_response(
    time, start, reset, is_global, response
):
    time.set_to(start)
    limiter = RateLimiter()
    with pytest.raises(RateLimitException) as exc_info:
        limiter.intercept_response(response)

    e = exc_info.value
    assert e.reset == reset and e.is_global == is_global


def test_ratelimit_raises_on_request_exhausted_resource(request, time):
    time.set_to(1000)
    request = make_request("GET", "url")
    limiter = RateLimiter()
    bucket = limiter.resource_buckets[
        (request.method, request.url)
    ] = ResourceRateLimitBucket("abc123")
    bucket.update(make_ratelimit_headers("abc123", 10, 0, 1002, 2))

    with pytest.raises(RateLimitException) as exc_info:
        bucket.take()

    assert exc_info.value.reset == 1002


@pytest.mark.parametrize(
    "url, group",
    [
        ("channels/2909267986263572999", "channels/2909267986263572999"),
        ("guilds/197038439483310086", "guilds/197038439483310086"),
        ("webhooks/223704706495545344", "webhooks/223704706495545344"),
        ("/channels/2909267986263572999/", "channels/2909267986263572999"),
        ("/guilds/197038439483310086/members/{user.id}", "guilds/197038439483310086"),
        ("/users/{user.id}", None),
        ("/users/@me/guilds", None),
        ("/invites/{invite.code}", None),
    ],
)
def test_url_group(url, group):
    assert url_group(url) == group
