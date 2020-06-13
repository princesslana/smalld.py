class SmallDError(Exception):
    pass


class HttpError(SmallDError):
    def __init__(self, *args, response=None, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)


class NetworkError(SmallDError):
    pass


class RateLimitError(SmallDError):
    def __init__(self, reset, *, is_global=False):
        super().__init__(f"rate limited until {reset}")
        self.reset = reset
        self.is_global = is_global
