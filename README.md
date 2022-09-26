# pyLast

[![PyPI version](https://img.shields.io/pypi/v/pylast.svg)](https://pypi.org/project/pylast/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/pylast.svg)](https://pypi.org/project/pylast/)
[![PyPI downloads](https://img.shields.io/pypi/dm/pylast.svg)](https://pypistats.org/packages/pylast)
[![Test](https://github.com/pylast/pylast/workflows/Test/badge.svg)](https://github.com/pylast/pylast/actions)
[![Coverage (Codecov)](https://codecov.io/gh/pylast/pylast/branch/main/graph/badge.svg)](https://codecov.io/gh/pylast/pylast)
[![Code style: Black](https://img.shields.io/badge/code%20style-Black-000000.svg)](https://github.com/psf/black)
[![DOI](https://zenodo.org/badge/7803088.svg)](https://zenodo.org/badge/latestdoi/7803088)

A Python interface to [Last.fm](https://www.last.fm/) and other API-compatible websites
such as [Libre.fm](https://libre.fm/).

Use the pydoc utility for help on usage or see [tests/](tests/) for examples.

## Installation

Install via pip:

```sh
python3 -m pip install pylast
```

Install latest development version:

```sh
python3 -m pip install -U git+https://github.com/pylast/pylast
```

Or from requirements.txt:

```txt
-e https://github.com/pylast/pylast.git#egg=pylast
```

Note:

* pyLast 5.1+ supports Python 3.7-3.11.
* pyLast 5.0+ supports Python 3.7-3.10.
* pyLast 4.3+ supports Python 3.6-3.10.
* pyLast 4.0 - 4.2 supports Python 3.6-3.9.
* pyLast 3.2 - 3.3 supports Python 3.5-3.8.
* pyLast 3.0 - 3.1 supports Python 3.5-3.7.
* pyLast 2.2 - 2.4 supports Python 2.7.10+, 3.4-3.7.
* pyLast 2.0 - 2.1 supports Python 2.7.10+, 3.4-3.6.
* pyLast 1.7 - 1.9 supports Python 2.7, 3.3-3.6.
* pyLast 1.0 - 1.6 supports Python 2.7, 3.3-3.4.
* pyLast 0.5 supports Python 2, 3.
* pyLast < 0.5 supports Python 2.

## Features

 * Simple public interface.
 * Access to all the data exposed by the Last.fm web services.
 * Scrobbling support.
 * Full object-oriented design.
 * Proxy support.
 * Internal caching support for some web services calls (disabled by default).
 * Support for other API-compatible networks like Libre.fm.


## Getting started

Here's some simple code example to get you started. In order to create any object from
pyLast, you need a `Network` object which represents a social music network that is
Last.fm or any other API-compatible one. You can obtain a pre-configured one for Last.fm
and use it as follows:

```python
import pylast

# You have to have your own unique two values for API_KEY and API_SECRET
# Obtain yours from https://www.last.fm/api/account/create for Last.fm
API_KEY = "b25b959554ed76058ac220b7b2e0a026"  # this is a sample key
API_SECRET = "425b55975eed76058ac220b7b4e8a054"

# In order to perform a write operation you need to authenticate yourself
username = "your_user_name"
password_hash = pylast.md5("your_password")

network = pylast.LastFMNetwork(
    api_key=API_KEY,
    api_secret=API_SECRET,
    username=username,
    password_hash=password_hash,
)

# Now you can use that object everywhere
track = network.get_track("Iron Maiden", "The Nomad")
track.love()
track.add_tags(("awesome", "favorite"))

# Type help(pylast.LastFMNetwork) or help(pylast) in a Python interpreter
# to get more help about anything and see examples of how it works
```

More examples in
<a href="https://github.com/hugovk/lastfm-tools">hugovk/lastfm-tools</a> and
[tests/](https://github.com/pylast/pylast/tree/main/tests).

## Testing

The [tests/](https://github.com/pylast/pylast/tree/main/tests) directory contains
integration and unit tests with Last.fm, and plenty of code examples.

For integration tests you need a test account at Last.fm that will become cluttered with
test data, and an API key and secret. Either copy
[example_test_pylast.yaml](example_test_pylast.yaml) to test_pylast.yaml and fill out
the credentials, or set them as environment variables like:

```sh
export PYLAST_USERNAME=TODO_ENTER_YOURS_HERE
export PYLAST_PASSWORD_HASH=TODO_ENTER_YOURS_HERE
export PYLAST_API_KEY=TODO_ENTER_YOURS_HERE
export PYLAST_API_SECRET=TODO_ENTER_YOURS_HERE
```

To run all unit and integration tests:

```sh
python3 -m pip install -e ".[tests]"
pytest
```

Or run just one test case:

```sh
pytest -k test_scrobble
```

To run with coverage:

```sh
pytest -v --cov pylast --cov-report term-missing
coverage report # for command-line report
coverage html   # for HTML report
open htmlcov/index.html
```

## Logging

To enable from your own code:

```python
import logging
import pylast

logging.basicConfig(level=logging.INFO)


network = pylast.LastFMNetwork(...)
```

To enable from pytest:

```sh
pytest --log-cli-level info -k test_album_search_images
```

To also see data returned from the API, use `level=logging.DEBUG` or
`--log-cli-level debug` instead.
