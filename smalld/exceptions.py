class SmallDException(Exception):
    pass


class HttpError(SmallDException):
    def __init__(self, *args, response=None, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)


class ConnectionError(SmallDException):
    pass


class RateLimitException(SmallDException):
    def __init__(self, reset, *, is_global=False):
        super().__init__(f"rate limited until {reset}")
        self.reset = reset
        self.is_global = is_global
