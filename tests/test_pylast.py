#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
import os
import time
import unittest

import pytest
from flaky import flaky

import pylast


def load_secrets():
    secrets_file = "test_pylast.yaml"
    if os.path.isfile(secrets_file):
        import yaml  # pip install pyyaml

        with open(secrets_file, "r") as f:  # see example_test_pylast.yaml
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


class PyLastTestCase(unittest.TestCase):
    def assert_startswith(self, str, prefix, start=None, end=None):
        self.assertTrue(str.startswith(prefix, start, end))

    def assert_endswith(self, str, suffix, start=None, end=None):
        self.assertTrue(str.endswith(suffix, start, end))


@flaky(max_runs=3, min_passes=1)
class TestPyLastWithLastFm(PyLastTestCase):

    secrets = None

    def unix_timestamp(self):
        return int(time.time())

    def setUp(self):
        if self.__class__.secrets is None:
            self.__class__.secrets = load_secrets()

        self.username = self.__class__.secrets["username"]
        password_hash = self.__class__.secrets["password_hash"]

        api_key = self.__class__.secrets["api_key"]
        api_secret = self.__class__.secrets["api_secret"]

        self.network = pylast.LastFMNetwork(
            api_key=api_key,
            api_secret=api_secret,
            username=self.username,
            password_hash=password_hash,
        )

    def helper_is_thing_hashable(self, thing):
        # Arrange
        things = set()

        # Act
        things.add(thing)

        # Assert
        self.assertIsNotNone(thing)
        self.assertEqual(len(things), 1)

    def helper_validate_results(self, a, b, c):
        # Assert
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertIsNotNone(c)
        self.assertGreaterEqual(len(a), 0)
        self.assertGreaterEqual(len(b), 0)
        self.assertGreaterEqual(len(c), 0)
        self.assertEqual(a, b)
        self.assertEqual(b, c)

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
        self.assertGreater(len(things), 1)
        self.assertIsInstance(things, list)
        self.assertIsInstance(things[0], pylast.TopItem)
        self.assertIsInstance(things[0].item, expected_type)

    def helper_only_one_thing_in_top_list(self, things, expected_type):
        # Assert
        self.assertEqual(len(things), 1)
        self.assertIsInstance(things, list)
        self.assertIsInstance(things[0], pylast.TopItem)
        self.assertIsInstance(things[0].item, expected_type)

    def helper_only_one_thing_in_list(self, things, expected_type):
        # Assert
        self.assertEqual(len(things), 1)
        self.assertIsInstance(things, list)
        self.assertIsInstance(things[0], expected_type)

    def helper_two_different_things_in_top_list(self, things, expected_type):
        # Assert
        self.assertEqual(len(things), 2)
        thing1 = things[0]
        thing2 = things[1]
        self.assertIsInstance(thing1, pylast.TopItem)
        self.assertIsInstance(thing2, pylast.TopItem)
        self.assertIsInstance(thing1.item, expected_type)
        self.assertIsInstance(thing2.item, expected_type)
        self.assertNotEqual(thing1, thing2)


if __name__ == "__main__":
    unittest.main(failfast=True)
