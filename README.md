# SmallD.py

![Build](https://github.com/princesslana/smalld.py/workflows/Build/badge.svg?branch=master)
[![Maintainability](https://api.codeclimate.com/v1/badges/7916cdfc83bf0fb95fa0/maintainability)](https://codeclimate.com/github/princesslana/smalld.py/maintainability)
[![emoji-log](https://cdn.rawgit.com/ahmadawais/stuff/ca97874/emoji-log/non-flat-round.svg)](https://github.com/ahmadawais/Emoji-Log/)

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

## Contributing

Checkout the issues, and jump right in! If you have questions, go to [The Programmers Hangout](https://discord.gg/programming) and look for Princess Lana (Lana#4231).

* [Tox](https://tox.readthedocs.io/) is used for running tests.
  * Run `tox -e` to run tests with your installed python version
  * Run `tox -e fmt` to format the code
* [Emoji Log](https://github.com/ahmadawais/Emoji-Log) is used for commit messages and pull requests

