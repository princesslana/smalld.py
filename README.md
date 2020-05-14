# SmallD.py

[![Maintainability](https://api.codeclimate.com/v1/badges/64e4ea90f38d177c0c99/maintainability)](https://codeclimate.com/github/princesslana/smalld.py/maintainability)

SmallD aims to be a minmalist client for the Discord API. It aims to let you use the Discord API, without hiding or abstracting it.

## Usage

SmallD.py will be published to pypi, meaning you'll be able to use all your usual
pip related tools to fetch it.

Until then, if you're interested in using it please contact me.
The best way is on The Programmer's Hangout on Discord (https://discord.gg/programming) and look for Princess Lana (Lana#4231).

## Running

Tox is used to setup an manage virtual envs when working on SmallD.py

To run tests:
```bash
  $ tox
```

To run examples, ping_bot in this case:
```bash
  $ tox -e run -- examples/ping_bot.py
```

