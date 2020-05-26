import sys
import time
from threading import Thread


def add_standard_listeners(smalld):
    sequence = SequenceNumber(smalld)
    Identify(smalld, sequence)
    Heartbeat(smalld, sequence)


OP_HEARTBEAT = 1
OP_IDENTIFY = 2
OP_INVALID_SESSION = 9
OP_RESUME = 6
OP_HELLO = 10


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
        smalld.on_gateway_payload(op=OP_HELLO)(self.on_hello)
        smalld.on_gateway_payload(op=OP_INVALID_SESSION)(self.on_invalid_session)

    def on_ready(self, data):
        self.session_id = data.session_id

    def on_hello(self, data):
        if self.session_id and self.sequence.number:
            self.resume()
        else:
            self.identify()

    def on_invalid_session(self, data):
        self.session_id = None
        time.sleep(2)
        self.identify()

    def identify(self):
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
                    "intents": self.smalld.intents.value
                },
            }
        )

    def resume(self):
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

        smalld.on_gateway_payload(op=OP_HELLO)(self.on_hello)

    def on_hello(self, data):
        self.heartbeat_interval = data.d.heartbeat_interval

        if not self.thread or not self.thread.is_alive():
            self.thread = Thread(target=self.run_heartbeat_loop)
            self.thread.start()

    def run_heartbeat_loop(self):
        if self.heartbeat_interval:
            time.sleep(self.heartbeat_interval / 1000)
            self.send_heartbeat()
            self.run_heartbeat_loop()

    def send_heartbeat(self):
        self.smalld.send_gateway_payload(
            {"op": OP_HEARTBEAT, "d": self.sequence.number}
        )
