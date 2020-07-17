# SmallD.py

[![PyPI version](https://badge.fury.io/py/smalld.svg)](https://badge.fury.io/py/smalld)
![Build](https://github.com/princesslana/smalld.py/workflows/Build/badge.svg?branch=master)
[![Maintainability](https://api.codeclimate.com/v1/badges/7916cdfc83bf0fb95fa0/maintainability)](https://codeclimate.com/github/princesslana/smalld.py/maintainability)
[![Discord](https://img.shields.io/discord/417389758470422538)](https://discord.gg/3aTVQtz)

SmallD aims to be a minmalist client for the Discord API. It aims to let you use the Discord API, without hiding or abstracting it.


## Table of Contents

  * [Installing](#installing)
  * [Getting Started](#getting-started)
  * [Guide](#guide)
     * [Creating and Configuring](#creating-and-configuring)
     * [Running](#running)
     * [Gateway Events](#gateway-events)
     * [Resources](#resources)
     * [Errors](#errors)
  * [Contact](#contact)
  * [Contributing](#contributing)
     * [Developing](#developing)
  * [Usages](#usages)

## Installing

SmallD can be install from pip.

```console
$ pip install smalld
```

## Getting Started

After [installing](#installing) SmallD, and we have a [bot token for discord](https://discordpy.readthedocs.io/en/latest/discord.html), we can get started on
making a bot.
This section will guide you through the creation of a Ping bot.
When someone types "++ping", it will respond with "pong".

To begin with, we import the SmallD class and create an instance of it.

```python
from smalld import SmallD

smalld = SmallD()
```

This is also where we could set the bot token or other configuration options.
By default the bot token will be read from the environment variable `SMALLD_TOKEN`.
We will set that when running our bot later.

Next, we want to add the ability to respond to messages.
To do this we want to listen for message create events from discord, and then send
a response if we received "++ping".
We do  receive events by using a decorator on a function.
We can use different decorators based upon what events we want to list.

```python
@smalld.on_message_create
def on_message(msg):
    pass
```

Our `on_message` function will now be called whenever a message create event is sent by discord.

Upon receiving this message we can check for "++ping" as the content by looking at the
`msg.content` property.
If it matches, we now send a message back via the appropriate Discord endpoint.
For sending messages, this is a POST request to "/channels/{channel.id}/messages". 
Since we are replaying to the message that was sent, we can get the channel id by using `msg.channel_id`.


```python
@smalld.on_message_create
def on_message(msg):
    if msg.content == "++ping":
        smalld.post(f"/channels/{msg.channel_id}/messages", {"content": "pong"})
```

The last step left in our ping bot is to actually run smalld.

```python
smalld.run()
```

When we actually run our script we will need to make sure we pass the token.
We can do this via the command line.

```console
$ SMALLD_TOKEN=<your token here> python ping_bot.py
```

The full code for the example can be found in (examples/ping_bot.py).

## Guide

This section outlines the API provided by SmallD.
It does not aim to outline what are valid payloads, events, etc.
For that, the [Discord developer documentation](https://discord.com/developers/docs/intro) is
always helpful.

### Creating and Configuring

```python
smalld.SmallD(
    token=os.environ.get("SMALLD_TOKEN"),
    base_url="https://discord.com/api/v6",
    intents=Intent.all(),
    shard=(0, 1),
)
```

Creates a SmallD instance using the provided configuration.
Intents are passed in using the `|` operator, for example
`Intent.GUILD_MESSAGES | Intent.DIRECT_MESSAGES`.
The `shard` configuration should be a tuple of (current shard, number of shards).

### Running

```python
SmallD.run()
```

Runs SmallD. Connects to the Gateway, authenticates, and will maintain the connection.
It will handle heartbeats and reconnections as necessary.

### Gateway Events

```python
@SmallD.on_*
SmallD.on_*(func=None)
@SmallD.on_gateway_payload(op=None, t=None)
SmallD.on_gateway_payload(func=None, *, op=None, t=None)
```

To listen to events from the Discord gateway use decorators that start with `on_`.
`on_gateway_payload` can be used to listen for raw payloads, optionally filtering
by the op and/or t fields of the payload.

To listen for specific dispatch events, simply use `on_` followed by the event
you wish to listen for.
For example `on_message_create` for MESSAGE_CREATE events, `on_message_reaction_add`
for MESSAGE_REACTION_ADD events, etc.

```python
SmallD.send_gateway_payload(data)
```

To send data to the Discord gateway use the `send_gateway_payload` method.

### Resources

```python
SmallD.<http method>(path, payload="", attachments=None, params=None)

SmallD.get(...)
SmallD.post(...)
SmallD.put(...)
SmallD.patch(...)
SmallD.delete(...)
```

These methods send a request to a discord resource and return the response.
All methods support the same parameters.
SmallD manages Discord's rate limits, throwing an exception if the rate limit would
be broken. An exception is raised on any non-2xx response.

The payload is serialized to JSON before being sent.
Typically `payload` will be passed in as a `dict` that matches the data expected
by the Discord API.

Attachments can be provided as a list of tuples.
Each tuple should be (file name, content, mime-type).
The file name and mime-type should be strings, with content being a file-like object.
An example of sending an attachment can be found in (examples/cat_bot.py).

Query parameters to be set on the request can be passed in `params`.

### Errors

```python
class SmallDError(Exception)
class HttpError(SmallDError)
class NetworkError(SmallDError)
class RateLimitError(SmallDError)
```

`SmallDError` is used as a base class for all errors raised by SmallD.

`HttpError` is raised when a non-2xx response is returned from a resources.
The response that caused the error can be accessed via the `response` attribute.

`NetworkError` is raised when there is a connectivity or other network related error.

`RateLimitError` is raised when hitting a Discord imposed rate limit. 
The reset time of this rate limit (i.e., when the rate limit will no longer apply) is available in the `reset` attribute.

## Contact

Reach out to the [Discord Projects Hub](https://discord.gg/3aTVQtz) on Discord and look for the smalld-py channels.

## Contributing

Checkout the issues, and jump right in!
If you have any questions, reach out via the details mentioned in [Contact](#contact).

* [Tox](https://tox.readthedocs.io/) is used for running tests.
  * Run `tox -e` to run tests with your installed python version
  * Run `tox -e fmt` to format the code
* [Emoji Log](https://github.com/ahmadawais/Emoji-Log) is used for commit messages and pull requests

### Developing

Tox is used to setup and manage virtual envs when working on SmallD.py

To run tests:
```console
$ tox
```

To run examples, ping_bot in this case:
```console
$ tox -e run -- examples/ping_bot.py
```

## Usages

* [Tsktsk](https://github.com/ianagbip1oti/tsktsk):
  A task list aimed at helping prioritize and categorize your tasks.
* [Tweenie](https://github.com/princesslana/tweenie):
  Add reacts to messages using the power of NLP.
* [SmallD-Click](https://github.com/aymanizz/smalld-click):
  A command dispatcher for your discord bot combining Click and SmallD.
* [Converse](https://github.com/aymanizz/converse):
  Anonymous (nameless) chat on discord.
