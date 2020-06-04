class SmallDException(Exception):
    pass


class GatewayClosedException(SmallDException):
    def __init__(self, code, reason):
        super().__init__(f"{code}: {reason}")
        self.code = code
        self.reason = reason

    @staticmethod
    def parse(data):
        code = int.from_bytes(data[:2], "big")
        reason = data[2:].decode("utf-8")
        return GatewayClosedException(code, reason)


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
