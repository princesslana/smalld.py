import json

from websocket import ABNF, WebSocket, WebSocketException

from .exceptions import NetworkError
from .json_elements import JsonObject
from .logger import logger
from .ratelimit import GatewayRateLimiter

WebSocketError = (WebSocketException, OSError)


class CloseReason:
    def __init__(self, code=None, reason=""):
        self.code = code
        self.reason = reason

    def __str__(self):
        return f"{self.code}: {self.reason}"

    @staticmethod
    def parse(data):
        code = int.from_bytes(data[:2], "big")
        reason = data[2:].decode("utf-8")
        return CloseReason(code, reason)

    @staticmethod
    def exception(e):
        return CloseReason(reason=f"{type(e).__name__}: {e}")


class Gateway:
    def __init__(self, url):
        self.url = url
        self.ws = WebSocket()
        self.close_reason = None
        self.limiter = GatewayRateLimiter()

    def __iter__(self):
        try:
            self.ws.connect(self.url)
        except WebSocketError:
            raise NetworkError

        while self.ws.connected:
            try:
                with self.ws.readlock:
                    opcode, data = self.ws.recv_data()
            except WebSocketError as e:
                logger.debug("Exception receiving gateway data.", exc_info=True)
                self.close_reason = CloseReason.exception(e)
                break

            if data and opcode == ABNF.OPCODE_CLOSE:
                self.close_reason = CloseReason.parse(data)
                break

            if data and opcode == ABNF.OPCODE_TEXT:
                decoded_data = data.decode("utf-8")
                logger.debug("Gateway payload received: %s", decoded_data)
                yield JsonObject(json.loads(decoded_data))

        logger.info("Gateway Closed: %s", self.close_reason)

    def send(self, data):
        self.limiter.on_send()
        payload = json.dumps(data)
        logger.debug("Gateway payload sent: %s", payload)
        try:
            self.ws.send(payload)
        except WebSocketError:
            logger.debug("Error sending payload.", exc_info=True)
            raise NetworkError

    def close(self):
        self.ws.close()
