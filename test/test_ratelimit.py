from unittest.mock import patch

import pytest
from smalld.ratelimit import *


class ControllableTime:
    def __init__(self):
        self.time = 0

    def __call__(self):
        return self.time

    def set_to(self, time):
        self.time = time


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

    with pytest.raises(RateLimitError) as exc_info:
        bucket.take()

    e = exc_info.value
    assert e.reset == 1001 and e.is_global == False


def test_global_ratelimit_bucket(time):
    time.set_to(100)
    limit = GlobalRateLimitBucket()

    assert not limit.is_ratelimited
    limit.take()  # doesn't raise

    limit.update(make_global_ratelimit_headers(100))

    assert limit.is_ratelimited

    with pytest.raises(RateLimitError) as exc_info:
        limit.take()

    e = exc_info.value
    assert e.reset == 101 and e.is_global == True


def test_ratelimit_passes_first_request():
    limiter = RateLimiter()
    limiter.on_request("GET", "/path/to/resource")  # doesn't raise


def test_ratelimit_passes_good_response(time):
    limiter = RateLimiter()
    limiter.on_response(
        "GET", "/path/to/resource", make_ratelimit_headers(), 200
    )  # doesn't raise


@pytest.mark.parametrize(
    "start, reset, is_global, response",
    [
        (
            0,
            1,
            True,
            ("GET", "/path/to/resource", make_global_ratelimit_headers(100), 429),
        ),
        (
            1000,
            1001,
            False,
            (
                "GET",
                "/path/to/resource",
                make_ratelimit_headers("abc123", 10, 0, 1001, 1),
                429,
            ),
        ),
    ],
)
def test_ratelimit_raises_on_limit_exhausted_response(
    time, start, reset, is_global, response
):
    time.set_to(start)
    limiter = RateLimiter()
    with pytest.raises(RateLimitError) as exc_info:
        limiter.on_response(*response)

    e = exc_info.value
    assert e.reset == reset and e.is_global == is_global


def test_ratelimit_raises_on_request_exhausted_resource(time):
    time.set_to(1000)
    limiter = RateLimiter()
    bucket = limiter.resource_buckets[
        ("GET", "path/to/resource")
    ] = ResourceRateLimitBucket("abc123")
    bucket.update(make_ratelimit_headers("abc123", 10, 0, 1002, 2))

    with pytest.raises(RateLimitError) as exc_info:
        limiter.on_request("GET", "path/to/resource")

    assert exc_info.value.reset == 1002


@pytest.mark.parametrize(
    "path, resource",
    [
        ("channels/2909267986263572999", "channels/2909267986263572999"),
        ("guilds/197038439483310086", "guilds/197038439483310086"),
        ("webhooks/223704706495545344", "webhooks/223704706495545344"),
        ("/channels/2909267986263572999/", "channels/2909267986263572999"),
        (
            "/guilds/197038439483310086/members/63269852323648",
            "guilds/197038439483310086/members/{user.id}",
        ),
        ("/users/9864325349523", "users/{user.id}"),
        ("/users/@me/guilds", "users/@me/guilds"),
        ("/invites/0vCdhLbwjZZTWZLD", "invites/{invite.code}"),
        ("/unknown/path", "unknown/path"),
    ],
)
def test_get_resource(path, resource):
    assert get_resource(path) == resource
