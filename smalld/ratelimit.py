import re
import time
from math import ceil

from pkg_resources import resource_string

from .exceptions import RateLimitError


class NoRateLimitBucket:
    def take(self):
        return

    def update(self, values):
        return


class ResourceRateLimitBucket:
    def __init__(self, bucket_id):
        self.bucket_id = bucket_id
        self.remaining = None
        self.reset = None

    def take(self):
        if (
            self.remaining is not None
            and self.remaining <= 0
            and time.time() < self.reset
        ):
            raise RateLimitError(self.reset)
        self.remaining -= 1

    def update(self, values):
        self.remaining = int(values["X-RateLimit-Remaining"])
        self.reset = int(values["X-RateLimit-Reset"])


class GlobalRateLimitBucket:
    def __init__(self):
        self.is_ratelimited = False
        self.reset = None

    def take(self):
        if self.is_ratelimited and time.time() < self.reset:
            raise RateLimitError(self.reset, is_global=True)

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
        # bucket id to bucket mapping
        self.buckets = {}
        # resource to bucket mapping
        self.resource_buckets = {}
        self.global_bucket = GlobalRateLimitBucket()

    def on_request(self, method, path):
        self.global_bucket.take()
        self.get_bucket(method, path).take()

    def on_response(self, method, path, headers, status_code):
        bucket = None
        if headers.get("X-RateLimit-Global"):
            bucket = self.global_bucket
        else:
            bucket_id = headers.get("X-RateLimit-Bucket")
            bucket = self.get_bucket(method, path, bucket_id)
        bucket.update(headers)

        if status_code == 429:
            raise RateLimitError(bucket.reset, is_global=bucket is self.global_bucket)

    def get_bucket(self, method, path, bucket_id=None):
        resource = get_resource(path)
        key = (method, resource)
        try:
            bucket = self.resource_buckets[key]
            if bucket_id is None or bucket_id == bucket.bucket_id:
                return bucket
        except KeyError:
            pass

        if not bucket_id:
            return self.no_ratelimit_bucket

        try:
            bucket = self.buckets[bucket_id]
        except KeyError:
            bucket = self.buckets[bucket_id] = ResourceRateLimitBucket(bucket_id)
        self.resource_buckets[key] = bucket
        return bucket


def extract_patterns(mappings):
    resources_patterns = []

    for mapping in mappings:
        mapping = mapping.strip()
        if not mapping or mapping.startswith("#"):
            continue

        pattern, resource = mapping.split("=")
        pattern = re.compile(pattern)
        resources_patterns.append((pattern, resource))

    return resources_patterns


mappings = resource_string("smalld.resources", "ratelimit_buckets").decode("utf-8")
mappings = extract_patterns(mappings.split("\n"))


def get_resource(path):
    path = path.strip().strip("/")
    for (pattern, template) in mappings:
        match = pattern.fullmatch(path)
        if not match:
            continue
        return match.expand(template)
    return path
