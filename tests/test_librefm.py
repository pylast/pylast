#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
from flaky import flaky

import pylast

from .test_pylast import PyLastTestCase, load_secrets


@flaky(max_runs=3, min_passes=1)
class TestPyLastWithLibreFm(PyLastTestCase):
    """Own class for Libre.fm because we don't need the Last.fm setUp"""

    def test_libre_fm(self):
        # Arrange
        secrets = load_secrets()
        username = secrets["username"]
        password_hash = secrets["password_hash"]

        # Act
        network = pylast.LibreFMNetwork(password_hash=password_hash, username=username)
        artist = network.get_artist("Radiohead")
        name = artist.get_name()

        # Assert
        assert name == "Radiohead"

    def test_repr(self):
        # Arrange
        secrets = load_secrets()
        username = secrets["username"]
        password_hash = secrets["password_hash"]
        network = pylast.LibreFMNetwork(password_hash=password_hash, username=username)

        # Act
        representation = repr(network)

        # Assert
        self.assert_startswith(representation, "pylast.LibreFMNetwork(")
