#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
from __future__ import annotations

import os
import time

import pytest
from flaky import flaky

import pylast

WRITE_TEST = False


def load_secrets():  # pragma: no cover
    secrets_file = "test_pylast.yaml"
    if os.path.isfile(secrets_file):
        import yaml  # pip install pyyaml

        with open(secrets_file) as f:  # see example_test_pylast.yaml
            doc = yaml.load(f)
    else:
        doc = {}

        def get_env(var_name: str) -> str:
            return os.environ.get(var_name, "").strip()

        doc["username"] = get_env("PYLAST_USERNAME")
        doc["password_hash"] = get_env("PYLAST_PASSWORD_HASH")
        doc["api_key"] = get_env("PYLAST_API_KEY")
        doc["api_secret"] = get_env("PYLAST_API_SECRET")

    return doc


def _no_xfail_rerun_filter(err, name, test, plugin) -> bool:
    for _ in test.iter_markers(name="xfail"):
        return False


@pytest.mark.vcr
@flaky(max_runs=3, min_passes=1, rerun_filter=_no_xfail_rerun_filter)
class TestPyLastWithLastFm:
    secrets = None

    @staticmethod
    def unix_timestamp() -> int:
        return int(time.time())

    @classmethod
    def setup_class(cls) -> None:
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

    @staticmethod
    def helper_is_thing_hashable(thing) -> None:
        # Arrange
        things = set()

        # Act
        things.add(thing)

        # Assert
        assert thing is not None
        assert len(things) == 1

    @staticmethod
    def helper_validate_results(a, b, c) -> None:
        # Assert
        assert a is not None
        assert b is not None
        assert c is not None
        assert isinstance(len(a), int)
        assert isinstance(len(b), int)
        assert isinstance(len(c), int)
        assert a == b
        assert b == c

    def helper_validate_cacheable(self, thing, function_name) -> None:
        # Arrange
        # get thing.function_name()
        func = getattr(thing, function_name, None)

        # Act
        result1 = func(limit=1, cacheable=False)
        result2 = func(limit=1, cacheable=True)
        result3 = list(func(limit=1))

        # Assert
        self.helper_validate_results(result1, result2, result3)

    @staticmethod
    def helper_at_least_one_thing_in_top_list(things, expected_type) -> None:
        # Assert
        assert len(things) > 1
        assert isinstance(things, list)
        assert isinstance(things[0], pylast.TopItem)
        assert isinstance(things[0].item, expected_type)

    @staticmethod
    def helper_only_one_thing_in_top_list(things, expected_type) -> None:
        # Assert
        assert len(things) == 1
        assert isinstance(things, list)
        assert isinstance(things[0], pylast.TopItem)
        assert isinstance(things[0].item, expected_type)

    @staticmethod
    def helper_only_one_thing_in_list(things, expected_type) -> None:
        # Assert
        assert len(things) == 1
        assert isinstance(things, list)
        assert isinstance(things[0], expected_type)

    @staticmethod
    def helper_two_different_things_in_top_list(things, expected_type) -> None:
        # Assert
        assert len(things) == 2
        thing1 = things[0]
        thing2 = things[1]
        assert isinstance(thing1, pylast.TopItem)
        assert isinstance(thing2, pylast.TopItem)
        assert isinstance(thing1.item, expected_type)
        assert isinstance(thing2.item, expected_type)
        assert thing1 != thing2
