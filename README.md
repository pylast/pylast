pyLast
======

[![Build Status](https://travis-ci.org/pylast/pylast.png?branch=master)](https://travis-ci.org/pylast/pylast) [![PyPI version](https://pypip.in/version/pylast/badge.svg)](https://pypi.python.org/pypi/pylast/) [![PyPI downloads](https://pypip.in/download/pylast/badge.svg)](https://pypi.python.org/pypi/pylast/) [![Coverage Status](https://coveralls.io/repos/pylast/pylast/badge.png?branch=master)](https://coveralls.io/r/pylast/pylast?branch=master)


A Python interface to [Last.fm](http://www.last.fm/) and other api-compatible websites such as [Libre.fm](http://libre.fm/).

Try using the pydoc utility for help on usage or see [test_pylast.py](test_pylast.py) for examples.

Installation
------------

The easiest way is via pip:

    pip install pylast

Or copy [pylast.py](pylast.py) to somewhere your Python can see it. No other dependencies are needed.


Features
--------

 * Simple public interface.
 * Access to all the data exposed by the Last.fm web services.
 * Scrobbling support.
 * Full object-oriented design.
 * Proxy support.
 * Internal caching support for some web services calls (disabled by default).
 * No extra dependencies but Python itself.
 * Support for other API-compatible networks like Libre.fm.
 * Python 3-friendly (Starting from 0.5).


Getting Started
---------------

Here's a simple code example to get you started. In order to create any object from pyLast, you need a Network object which represents a social music network that is Last.fm or any other API-compatible one. You can obtain a pre-configured one for Last.fm and use it as follows:

```python
import pylast

# You have to have your own unique two values for API_KEY and API_SECRET
# Obtain yours from http://www.last.fm/api/account for Last.fm
API_KEY = "b25b959554ed76058ac220b7b2e0a026" # this is a sample key
API_SECRET = "425b55975eed76058ac220b7b4e8a054"

# In order to perform a write operation you need to authenticate yourself
username = "your_user_name"
password_hash = pylast.md5("your_password")

network = pylast.LastFMNetwork(api_key = API_KEY, api_secret =
    API_SECRET, username = username, password_hash = password_hash)

# now you can use that object everywhere
artist = network.get_artist("System of a Down")
artist.shout("<3")


track = network.get_track("Iron Maiden", "The Nomad")
track.love()
track.add_tags(("awesome", "favorite"))

# type help(pylast.LastFMNetwork) or help(pylast) in a Python interpreter to get more help
# about anything and see examples of how it works
```

More examples in <a href="https://github.com/hugovk/lastfm-tools">hugovk/lastfm-tools</a> and [test_pylast.py](test_pylast.py).

Testing
-------

[test_pylast.py](test_pylast.py) contains integration tests with Last.fm, and plenty of code examples.

You need a test account at Last.fm that will be cluttered with test data, and an API key and secret. Either copy [example_test_pylast.yaml](example_test_pylast.yaml) to test_pylast.yaml and fill out the credentials, or set them as environment variables like:

```sh
export PYLAST_USERNAME=TODO_ENTER_YOURS_HERE
export PYLAST_PASSWORD_HASH=TODO_ENTER_YOURS_HERE
export PYLAST_API_KEY=TODO_ENTER_YOURS_HERE
export PYLAST_API_SECRET=TODO_ENTER_YOURS_HERE
```

To run all:
```sh
pip install -r test_requirements.txt
./test_pylast.py
```

Or run just one:
```sh
./test_pylast.py -1 test_scrobble
```

Or all those tests matching a term:
```sh
./test_pylast.py -m geo
```

To run with coverage:
```sh
coverage run --source=pylast ./test_pylast.py
coverage report # for command-line report
coverage html   # for HTML report
open htmlcov/index.html
```

To perform some static analysis:
```sh
./check.sh
```
