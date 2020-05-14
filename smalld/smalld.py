import json
import logging
import os
import time

import requests
from attrdict import AttrDict

from websocket import WebSocket

from .standard_listeners import add_standard_listeners

logger = logging.getLogger("smalld")


class SmallD:
    def __init__(
        self,
        token=os.environ.get("SMALLD_TOKEN"),
        base_url="https://discord.com/api/v6",
    ):
        if not token:
            raise ValueError("No bot token provided")

        self.token = token
        self.base_url = base_url
        self.listeners = []

        self.http = HttpClient(token, base_url)

        self.get = self.http.get
        self.post = self.http.post

    def __getattr__(self, name):
        if name.startswith("on_"):
            return lambda: self.on_dispatch(t=name.strip("on_").upper())

        super().__getattr__(name)

    def on_dispatch(self, t):
        def decorator(f):
            self.on_gateway_payload(op=0, t=t)(lambda payload: f(payload.d))

        return decorator

    def on_gateway_payload(self, op=None, t=None):
        def decorator(f):
            def filtered_payload_listener(data):
                if op and data.op != op:
                    return

                if t and data.t != t:
                    return

                f(data)

            self.listeners.append(filtered_payload_listener)

        return decorator

    def send_gateway_payload(self, data):
        payload = json.dumps(data)
        logger.debug("gateway payload sent: %s", payload)
        self.gateway.send(payload)

    def reconnect(self):
        self.gateway.close()

    def run(self):
        add_standard_listeners(self)

        while True:
            gateway_url = self.get("/gateway/bot").url

            self.gateway = Gateway(gateway_url)

            for data in self.gateway:
                logger.debug("gateway payload received: %s", data)
                for listener in self.listeners:
                    listener(AttrDict(json.loads(data)))

            time.sleep(5)


class Gateway:
    def __init__(self, url):
        self.url = url
        self.ws = WebSocket()

    def __iter__(self):
        self.ws.connect(self.url)

        for data in self.ws:
            if data:
                yield data

            if not self.ws.connected:
                break

    def send(self, data):
        self.ws.send(data)

    def close(self):
        self.ws.close()


class HttpClient:
    def __init__(self, token, base_url):
        self.token = token
        self.base_url = base_url

    def headers(self):
        return {
            "Authorization": f"Bot {self.token}",
            "User-Agent": "DiscordBot (http://github.com/princesslana/smalld.py, 0.1.0)",
        }

    def get(self, path):
        r = requests.get(f"{self.base_url}/{path}", headers=self.headers())
        return AttrDict(r.json())

    def post(self, path, payload="", attachments=None):
        if attachments:
            files = [(f"file{idx}", a) for idx, a in enumerate(attachments)]
            args = {"data": {"payload_json": json.dumps(payload)}, "files": files}
        else:
            args = {"json": payload}

        r = requests.post(f"{self.base_url}/{path}", headers=self.headers(), **args)

        return AttrDict(r.json())
