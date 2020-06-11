import json
import logging
import os
import time
from enum import Flag
from threading import Event

from pkg_resources import get_distribution

import requests
from attrdict import AttrDict

from .exceptions import HttpError, NetworkError
from .gateway import Gateway
from .ratelimit import RateLimiter
from .standard_listeners import add_standard_listeners

logger = logging.getLogger("smalld")


__version__ = get_distribution("smalld").version


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
        return ~Intent(0)

    @staticmethod
    def unprivileged():
        return ~(Intent.GUILD_PRESENCES | Intent.GUILD_MEMBERS)


recoverable_error_codes = {
    *range(1000, 1016),  # standard protocol error codes
    4000,  # unknown error
    4001,  # unknown opcode
    4002,  # decode error
    4005,  # already authenticated
    4007,  # invalid sequence
    4009,  # session timed out
}


class SmallD:
    def __init__(
        self,
        token=os.environ.get("SMALLD_TOKEN"),
        base_url="https://discord.com/api/v6",
        intents=Intent.unprivileged(),
    ):
        if not token:
            raise ValueError("No bot token provided")

        self.token = token
        self.base_url = base_url
        self.intents = intents
        self.listeners = []
        self.closed_event = Event()

        self.http = HttpClient(token, base_url)

        self.get = self.http.get
        self.post = self.http.post
        self.put = self.http.put
        self.patch = self.http.patch
        self.delete = self.http.delete

        add_standard_listeners(self)

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

    @property
    def closed(self):
        return self.closed_event.is_set()

    def reconnect(self):
        self.gateway.close()

    def close(self):
        self.closed_event.set()
        self.http.close()
        self.reconnect()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self.closed:
            self.close()

    def run(self):
        logger.info("Running (SmallD v%s)...", __version__)

        self.closed_event.clear()

        while not self.closed:
            logger.info("Gateway connecting...")
            gateway_url = self.get("/gateway/bot").url

            self.gateway = Gateway(gateway_url)

            for data in self.gateway:
                logger.debug("gateway payload received: %s", data)
                for listener in self.listeners:
                    listener(data)

            reason = self.gateway.close_reason
            if reason and not reason.code in recoverable_error_codes:
                logger.fatal(
                    "Unrecoverable gateway closure: %s", self.gateway.close_reason
                )
                self.close()

            if not self.closed:
                logger.info("Pausing before reconnect...")
                time.sleep(5)


class HttpClient:
    def __init__(self, token, base_url):
        self.token = token
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(self.headers())
        self.limiter = RateLimiter()

    def headers(self):
        return {
            "Authorization": f"Bot {self.token}",
            "User-Agent": f"DiscordBot (https://github.com/princesslana/smalld.py, {__version__})",
        }

    def get(self, *args, **kwargs):
        return self.send_request("GET", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.send_request("POST", *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.send_request("PUT", *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.send_request("PATCH", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.send_request("DELETE", *args, **kwargs)

    def send_request(self, method, path, payload="", attachments=None, params=None):
        if attachments:
            files = [(f"file{idx}", a) for idx, a in enumerate(attachments)]
            args = {"data": {"payload_json": json.dumps(payload)}, "files": files}
        elif payload:
            args = {"json": payload}
        else:
            args = {}

        if params:
            args["params"] = params

        self.limiter.on_request(method, path)

        try:
            res = self.session.request(method, f"{self.base_url}/{path}", **args)
        except (requests.ConnectionError, requests.Timeout):
            raise NetworkError
        except requests.RequestException:
            raise HttpError

        self.limiter.on_response(method, path, res.headers, res.status_code)

        if not res.ok:
            raise HttpError(response=res)

        try:
            content = res.json() if res.status_code != 204 else {}
        except json.JSONDecodeError:
            raise HttpError(response=res)

        return AttrDict(content)

    def close(self):
        self.session.close()
