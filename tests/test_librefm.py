#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
from __future__ import annotations

import pytest
from flaky import flaky

import pylast

from .test_pylast import load_secrets


@pytest.mark.vcr
@flaky(max_runs=3, min_passes=1)
class TestPyLastWithLibreFm:
    """Own class for Libre.fm because we don't need the Last.fm setUp"""

    def test_libre_fm(self) -> None:
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

    def test_repr(self) -> None:
        # Arrange
        secrets = load_secrets()
        username = secrets["username"]
        password_hash = secrets["password_hash"]
        network = pylast.LibreFMNetwork(password_hash=password_hash, username=username)

        # Act
        representation = repr(network)

        # Assert
        assert representation.startswith("pylast.LibreFMNetwork(")
