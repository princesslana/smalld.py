import re
import time
from math import ceil


class RateLimitException(Exception):
    def __init__(self, reset, *, is_global=False):
        super().__init__(f"rate limited until {reset}")
        self.reset = reset
        self.is_global = is_global


class NoRateLimitBucket:
    def take(self):
        return

    def update(self, values):
        return


class ResourceRateLimitBucket:
    buckets = {}

    def __init__(self, bucket_id):
        self.bucket_id = bucket_id
        self.remaining = None
        self.reset = None

    def __new__(cls, bucket_id):
        try:
            return cls.buckets[bucket_id]
        except KeyError:
            instance = super().__new__(cls)
            return cls.buckets.setdefault(bucket_id, instance)

    def take(self):
        if (
            self.remaining is not None
            and self.remaining <= 0
            and time.time() < self.reset
        ):
            raise RateLimitException(self.reset)
        self.remaining -= 1

    def update(self, values):
        self.remaining = int(values["X-RateLimit-Remaining"])
        self.reset = int(values["X-RateLimit-Reset"])

    def __eq__(self, other):
        return (
            isinstance(other, ResourceRateLimitBucket)
            and self.bucket_id == other.bucket_id
        )

    def __hash__(self):
        return hash(self.bucket_id)

    def __repr__(self):
        return f"<ResourceRateLimit ({self.bucket_id}, {self.remaining}, {self.reset})>"


class GlobalRateLimitBucket:
    def __init__(self):
        self.is_ratelimited = False
        self.reset = None

    def take(self):
        if self.is_ratelimited and time.time() < self.reset:
            raise RateLimitException(self.reset, is_global=True)

    def update(self, values):
        self.is_ratelimited = (
            values.get("X-RateLimit-Global", "false").lower() == "true"
        )
        if self.is_ratelimited:
            retry_after = ceil(int(values.get("Retry-After", 0)) / 1000)
            self.reset = time.time() + retry_after


class RateLimiter:
    no_ratelimit_bucket = NoRateLimitBucket()

    def __init__(self):
        self.resource_buckets = {}
        self.global_bucket = GlobalRateLimitBucket()

    def on_request(self, request):
        self.global_bucket.take()
        self.get_bucket(request.method, request.url).take()

    def on_response(self, response):
        request = response.request
        headers = response.headers
        bucket = None
        if headers.get("X-RateLimit-Global"):
            bucket = self.global_bucket
        else:
            bucket_id = headers.get("X-RateLimit-Bucket")
            bucket = self.get_bucket(request.method, request.url, bucket_id)
        bucket.update(headers)

        if response.status_code == 429:
            raise RateLimitException(
                bucket.reset, is_global=bucket is self.global_bucket
            )

    def get_bucket(self, method, url, bucket_id=None):
        key = (method, url)
        try:
            return self.resource_buckets[key]
        except KeyError:
            pass

        bucket_id = url_group(url) or bucket_id
        if bucket_id:
            return self.resource_buckets.setdefault(
                key, ResourceRateLimitBucket(bucket_id)
            )

        return self.no_ratelimit_bucket


groups = list(map(re.compile, [r"channels/(\d+)", r"guilds/(\d+)", r"webhooks/(\d+)"]))


def url_group(url):
    url = url.strip().strip("/")
    for group in groups:
        match = group.match(url)
        if match:
            return match.group()
    return None
