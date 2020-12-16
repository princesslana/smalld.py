import json
import os
import time
from enum import Flag
from threading import Event

from pkg_resources import get_distribution

import requests

from .exceptions import HttpError, NetworkError, SmallDError
from .gateway import Gateway
from .json_elements import JsonObject
from .logger import logger
from .ratelimit import RateLimiter
from .standard_listeners import add_standard_listeners

__version__ = get_distribution("smalld").version


MIN_SECONDS_BETWEEN_CONNECTIONS = 120


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
    4900,  # send when reconnecting
}


def is_recoverable_error(reason):
    if not reason or not reason.code:
        return True

    return reason.code in recoverable_error_codes


V6_BASE_URL = "https://discord.com/api/v6"
V8_BASE_URL = "https://discord.com/api/v8"


class SmallD:
    def __init__(
        self,
        token=os.environ.get("SMALLD_TOKEN"),
        base_url=V8_BASE_URL,
        intents=Intent.unprivileged(),
        shard=(0, 1),
    ):
        if not token:
            raise SmallDError("No bot token provided")

        self.token = token
        self.base_url = base_url
        self.intents = intents
        self.shard = shard

        self.listeners = []
        self.closed_event = Event()

        self.http = HttpClient(token, base_url)
        self.get = self.http.get
        self.post = self.http.post
        self.put = self.http.put
        self.patch = self.http.patch
        self.delete = self.http.delete

        add_standard_listeners(self)

    @staticmethod
    def v6(*args, **kwargs):
        return SmallD(base_url=V6_BASE_URL, *args, **kwargs)

    @staticmethod
    def v8(*args, **kwargs):
        return SmallD(base_url=V8_BASE_URL, *args, **kwargs)

    def __getattr__(self, name):
        if name.startswith("on_"):
            return lambda func=None: self.on_dispatch(func, t=name.strip("on_").upper())

        super().__getattr__(name)

    def on_dispatch(self, func=None, *, t=None):
        def decorator(f):
            self.on_gateway_payload(lambda payload: f(payload.d), op=0, t=t)
            return f

        return decorator if func is None else decorator(func)

    def on_gateway_payload(self, func=None, *, op=None, t=None):
        def decorator(f):
            def filtered_payload_listener(data):
                if op is not None and data.op != op:
                    return

                if t and data.t != t:
                    return

                f(data)

            self.listeners.append(filtered_payload_listener)
            return f

        return decorator if func is None else decorator(func)

    def send_gateway_payload(self, data):
        self.gateway.send(data)

    @property
    def closed(self):
        return self.closed_event.is_set()

    def reconnect(self):
        self.gateway.close(status=4900)

    def close(self):
        self.closed_event.set()
        self.http.close()
        self.gateway.close()

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
            connection_time = int(time.monotonic())

            try:
                gateway_url = self.get("/gateway/bot").url
            except (HttpError, NetworkError) as e:
                logger.info(f"Could not fetch gateway url. ({type(e).__name__}) {e}")
            else:
                self.gateway = Gateway(gateway_url)

                for data in self.gateway:
                    self.notify_listeners(data)

                if not is_recoverable_error(self.gateway.close_reason):
                    logger.fatal(
                        "Unrecoverable gateway closure: %s", self.gateway.close_reason
                    )
                    self.close()

            if not self.closed:
                logger.debug("Waiting to reconnect...")
                since_last_connection = int(time.monotonic()) - connection_time
                time.sleep(
                    max(5, MIN_SECONDS_BETWEEN_CONNECTIONS - since_last_connection)
                )

    def notify_listeners(self, data):
        try:
            for listener in self.listeners:
                listener(data)
        except:
            logger.warn("Exception in listener", exc_info=True)


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

        return JsonObject(content)

    def close(self):
        self.session.close()
