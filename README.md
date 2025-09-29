# pyLast

[![PyPI version](https://img.shields.io/pypi/v/pylast.svg?logo=pypi&logoColor=FFE873)](https://pypi.org/project/pylast/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/pylast.svg?logo=python&logoColor=FFE873)](https://pypi.org/project/pylast/)
[![PyPI downloads](https://img.shields.io/pypi/dm/pylast.svg)](https://pypistats.org/packages/pylast)
[![GitHub Actions status](https://github.com/pylast/pylast/workflows/Test/badge.svg)](https://github.com/pylast/pylast/actions)
[![Codecov](https://codecov.io/gh/pylast/pylast/branch/main/graph/badge.svg)](https://codecov.io/gh/pylast/pylast)
[![Licence](https://img.shields.io/github/license/pylast/pylast.svg)](LICENSE.txt)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.11247604.svg)](https://doi.org/10.5281/zenodo.11247604)
[![Code style: Black](https://img.shields.io/badge/code%20style-Black-000000.svg)](https://github.com/psf/black)

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

## Features

- Simple public interface.
- Access to all the data exposed by the Last.fm web services.
- Scrobbling support.
- Full object-oriented design.
- Proxy support.
- Internal caching support for some web services calls (disabled by default).
- Support for other API-compatible networks like Libre.fm.

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
```

Alternatively, instead of creating `network` with a username and password, you can
authenticate with a session key:

```python
import pylast

SESSION_KEY_FILE = os.path.join(os.path.expanduser("~"), ".session_key")
network = pylast.LastFMNetwork(API_KEY, API_SECRET)
if not os.path.exists(SESSION_KEY_FILE):
    skg = pylast.SessionKeyGenerator(network)
    url = skg.get_web_auth_url()

    print(f"Please authorize this script to access your account: {url}\n")
    import time
    import webbrowser

    webbrowser.open(url)

    while True:
        try:
            session_key = skg.get_web_auth_session_key(url)
            with open(SESSION_KEY_FILE, "w") as f:
                f.write(session_key)
            break
        except pylast.WSError:
            time.sleep(1)
else:
    session_key = open(SESSION_KEY_FILE).read()

network.session_key = session_key
```

And away we go:

```python
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
[example_test_pylast.yaml](https://github.com/pylast/pylast/blob/main/example_test_pylast.yaml)
to test_pylast.yaml and fill out the credentials, or set them as environment variables
like:

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
