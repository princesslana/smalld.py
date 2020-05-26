from enum import Flag
from functools import reduce
import json
import logging
import operator
import os
import time
from importlib.metadata import version

import requests
from attrdict import AttrDict

from websocket import WebSocket

from .standard_listeners import add_standard_listeners

logger = logging.getLogger("smalld")


__version__ = version("smalld")


class Intent(Flag):
    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_BANS = 1 << 2
    GUILD_EMOJIS = 1 << 3
    GUILD_INTEGRATIONS = 1 << 4
    GUILD_WEBHOOKS = 1 << 5
    GUILD_INVITES = 1 << 6
    GUILD_VOICE_STATES = 1 << 7
    GUILD_PRESENCES = 1 << 8
    GUILD_MESSAGES = 1 << 9
    GUILD_MESSAGE_REACTIONS = 1 << 10
    GUILD_MESSAGE_TYPING = 1 << 11
    DIRECT_MESSAGES = 1 << 12
    DIRECT_MESSAGE_REACTIONS = 1 << 13
    DIRECT_MESSAGE_TYPING = 1 << 14

    @staticmethod
    def all():
        return reduce(operator.ior, Intent.__members__.values())


class SmallD:
    def __init__(
        self,
        token=os.environ.get("SMALLD_TOKEN"),
        base_url="https://discord.com/api/v6",
        intents=Intent.all(),
    ):
        if not token:
            raise ValueError("No bot token provided")

        self.token = token
        self.base_url = base_url
        self.intents = intents 
        self.listeners = []

        self.http = HttpClient(token, base_url)

        self.get = self.http.get
        self.post = self.http.post
        self.put = self.http.put
        self.patch = self.http.patch
        self.delete = self.http.delete

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
        self.session = requests.Session()
        self.session.headers.update(self.headers())

    def headers(self):
        return {
            "Authorization": f"Bot {self.token}",
            "User-Agent": f"DiscordBot (https://github.com/princesslana/smalld.py, {__version__})",
        }

    def get(self, path):
        return self.send_request("GET", path)

    def post(self, path, payload="", attachments=None):
        return self.send_request("POST", path, payload, attachments)

    def put(self, path, payload=""):
        return self.send_request("PUT", path, payload)

    def patch(self, path, payload=""):
        return self.send_request("PATCH", path, payload)

    def delete(self, path):
        return self.send_request("DELETE", path)

    def send_request(self, method, path, payload="", attachments=None):
        if attachments:
            files = [(f"file{idx}", a) for idx, a in enumerate(attachments)]
            args = {"data": {"payload_json": json.dumps(payload)}, "files": files}
        elif payload:
            args = {"json": payload}
        else:
            args = {}

        r = self.session.request(method, f"{self.base_url}/{path}", **args)

        return AttrDict(r.json()) if r.status_code != 204 else AttrDict()

    def close(self):
        self.session.close()
