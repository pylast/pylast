#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
import os
import sys
import time

import pylast
import pytest
from flaky import flaky

WRITE_TEST = sys.version_info[:2] == (3, 8)


def load_secrets():
    secrets_file = "test_pylast.yaml"
    if os.path.isfile(secrets_file):
        import yaml  # pip install pyyaml

        with open(secrets_file) as f:  # see example_test_pylast.yaml
            doc = yaml.load(f)
    else:
        doc = {}
        try:
            doc["username"] = os.environ["PYLAST_USERNAME"].strip()
            doc["password_hash"] = os.environ["PYLAST_PASSWORD_HASH"].strip()
            doc["api_key"] = os.environ["PYLAST_API_KEY"].strip()
            doc["api_secret"] = os.environ["PYLAST_API_SECRET"].strip()
        except KeyError:
            pytest.skip("Missing environment variables: PYLAST_USERNAME etc.")
    return doc


class PyLastTestCase:
    def assert_startswith(self, str, prefix, start=None, end=None):
        assert str.startswith(prefix, start, end)

    def assert_endswith(self, str, suffix, start=None, end=None):
        assert str.endswith(suffix, start, end)


@flaky(max_runs=3, min_passes=1)
class TestPyLastWithLastFm(PyLastTestCase):

    secrets = None

    def unix_timestamp(self):
        return int(time.time())

    @classmethod
    def setup_class(cls):
        if cls.secrets is None:
            cls.secrets = load_secrets()

        cls.username = cls.secrets["username"]
        password_hash = cls.secrets["password_hash"]

        api_key = cls.secrets["api_key"]
        api_secret = cls.secrets["api_secret"]

        cls.network = pylast.LastFMNetwork(
            api_key=api_key,
            api_secret=api_secret,
            username=cls.username,
            password_hash=password_hash,
        )

    def helper_is_thing_hashable(self, thing):
        # Arrange
        things = set()

        # Act
        things.add(thing)

        # Assert
        assert thing is not None
        assert len(things) == 1

    def helper_validate_results(self, a, b, c):
        # Assert
        assert a is not None
        assert b is not None
        assert c is not None
        assert len(a) >= 0
        assert len(b) >= 0
        assert len(c) >= 0
        assert a == b
        assert b == c

    def helper_validate_cacheable(self, thing, function_name):
        # Arrange
        # get thing.function_name()
        func = getattr(thing, function_name, None)

        # Act
        result1 = func(limit=1, cacheable=False)
        result2 = func(limit=1, cacheable=True)
        result3 = func(limit=1)

        # Assert
        self.helper_validate_results(result1, result2, result3)

    def helper_at_least_one_thing_in_top_list(self, things, expected_type):
        # Assert
        assert len(things) > 1
        assert isinstance(things, list)
        assert isinstance(things[0], pylast.TopItem)
        assert isinstance(things[0].item, expected_type)

    def helper_only_one_thing_in_top_list(self, things, expected_type):
        # Assert
        assert len(things) == 1
        assert isinstance(things, list)
        assert isinstance(things[0], pylast.TopItem)
        assert isinstance(things[0].item, expected_type)

    def helper_only_one_thing_in_list(self, things, expected_type):
        # Assert
        assert len(things) == 1
        assert isinstance(things, list)
        assert isinstance(things[0], expected_type)

    def helper_two_different_things_in_top_list(self, things, expected_type):
        # Assert
        assert len(things) == 2
        thing1 = things[0]
        thing2 = things[1]
        assert isinstance(thing1, pylast.TopItem)
        assert isinstance(thing2, pylast.TopItem)
        assert isinstance(thing1.item, expected_type)
        assert isinstance(thing2.item, expected_type)
        assert thing1 != thing2
