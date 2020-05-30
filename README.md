# SmallD.py

![Build](https://github.com/princesslana/smalld.py/workflows/Build/badge.svg?branch=master)
[![Maintainability](https://api.codeclimate.com/v1/badges/7916cdfc83bf0fb95fa0/maintainability)](https://codeclimate.com/github/princesslana/smalld.py/maintainability)
[![emoji-log](https://cdn.rawgit.com/ahmadawais/stuff/ca97874/emoji-log/non-flat-round.svg)](https://github.com/ahmadawais/Emoji-Log/)

SmallD aims to be a minmalist client for the Discord API. It aims to let you use the Discord API, without hiding or abstracting it.

## Table of Contents

## Installing

SmallD.py can be install from pip.

```console
$ pip install smalld
```

## Getting Started

After [installing](#installing) smalld, and we have a [bot token for discord](https://discordpy.readthedocs.io/en/latest/discord.html), we can get started on
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
@smalld.on_message_create()
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
@smalld.on_message_create()
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
For that, the (Discord developer documentation)[https://discord.com/developers/docs/intro] is
always helpful.

### Creating and Configuring

```python
smalld.SmallD(
    token=os.environ.get("SMALLD_TOKEN"),
    base_url="https://discord.com/api/v6",
    intents=Intent.all(),
)
```

### Running

```python
SmallD.run()
```

### Gateway Events

```python
SmallD.on_*
SmallD.on_gateway_payload(op=None, t=None)
```

### Resources

```python
SmallD.get(path)
SmallD.post(path, payload="", attachments=None)
SmallD.put(path, payload="")
SmallD.patch(path, payload="")
SmallD.delete(path)
```

## Contact

The best way to reach out is on [The Programmer's Hangout](https://discord.gg/programming) on Discord  and look for Princess Lana (Lana#4231).

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

