import logging
import sys
import time
from threading import Event, Thread

from .exceptions import NetworkError

logger = logging.getLogger("smalld")


def add_standard_listeners(smalld):
    sequence = SequenceNumber(smalld)
    Identify(smalld, sequence)
    Heartbeat(smalld, sequence)


OP_HEARTBEAT = 1
OP_IDENTIFY = 2
OP_INVALID_SESSION = 9
OP_RESUME = 6
OP_RECONNECT = 7
OP_HELLO = 10
OP_HEARTBEAT_ACK = 11


class SequenceNumber:
    def __init__(self, smalld):
        self.smalld = smalld
        self.number = None

        smalld.on_gateway_payload()(self.on_payload)

    def on_payload(self, data):
        if data.s:
            self.number = data.s


class Identify:
    def __init__(self, smalld, sequence):
        self.smalld = smalld
        self.sequence = sequence
        self.session_id = None

        smalld.on_ready()(self.on_ready)
        smalld.on_resumed()(self.on_resumed)
        smalld.on_gateway_payload(op=OP_HELLO)(self.on_hello)
        smalld.on_gateway_payload(op=OP_INVALID_SESSION)(self.on_invalid_session)
        smalld.on_gateway_payload(op=OP_RECONNECT)(self.on_reconnect)

    def on_ready(self, data):
        logger.info("Ready.")
        self.session_id = data.session_id

    def on_resumed(self, data):
        logger.info("Resumed.")

    def on_hello(self, data):
        if self.session_id and self.sequence.number:
            self.resume()
        else:
            self.identify()

    def on_invalid_session(self, data):
        self.session_id = None
        time.sleep(2)
        self.identify()

    def on_reconnect(self, data):
        self.smalld.reconnect()

    def identify(self):
        logger.info("Identifying...")
        self.smalld.send_gateway_payload(
            {
                "op": OP_IDENTIFY,
                "d": {
                    "token": self.smalld.token,
                    "properties": {
                        "$os": sys.platform,
                        "$browser": "smalld.py",
                        "$device": "smalld.py",
                    },
                    "compress": False,
                    "intents": self.smalld.intents.value,
                },
            }
        )

    def resume(self):
        logger.info("Resuming...")
        self.smalld.send_gateway_payload(
            {
                "op": OP_RESUME,
                "d": {
                    "token": self.smalld.token,
                    "session_id": self.session_id,
                    "seq": self.sequence.number,
                },
            }
        )


class Heartbeat:
    def __init__(self, smalld, sequence):
        self.smalld = smalld
        self.sequence = sequence
        self.thread = None
        self.heartbeat_interval = None
        self.received_ack = Event()

        smalld.on_gateway_payload(op=OP_HELLO)(self.on_hello)
        smalld.on_gateway_payload(op=OP_HEARTBEAT)(self.on_heartbeat)
        smalld.on_gateway_payload(op=OP_HEARTBEAT_ACK)(self.on_heartbeat_ack)

    def on_hello(self, data):
        self.heartbeat_interval = data.d.heartbeat_interval

        if not self.thread or not self.thread.is_alive():
            self.thread = Thread(target=self.run_heartbeat_loop)
            self.thread.start()

    def on_heartbeat(self, data):
        self.send_heartbeat()

    def on_heartbeat_ack(self, data):
        self.received_ack.set()

    def run_heartbeat_loop(self):
        interval = self.heartbeat_interval / 1000
        time.sleep(interval)
        while not self.smalld.closed:
            try:
                self.send_heartbeat()
            except NetworkError:
                continue
            finally:
                time.sleep(interval)

            if self.received_ack.is_set():
                self.received_ack.clear()
            else:
                self.smalld.reconnect()
                break

    def send_heartbeat(self):
        self.smalld.send_gateway_payload(
            {"op": OP_HEARTBEAT, "d": self.sequence.number}
        )
