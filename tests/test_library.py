#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
from __future__ import annotations

import pylast

from .test_pylast import TestPyLastWithLastFm


class TestPyLastLibrary(TestPyLastWithLastFm):
    def test_repr(self) -> None:
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)

        # Act
        representation = repr(library)

        # Assert
        assert representation.startswith("pylast.Library(")

    def test_str(self) -> None:
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)

        # Act
        string = str(library)

        # Assert
        assert string.endswith("'s Library")

    def test_library_is_hashable(self) -> None:
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)

        # Act/Assert
        self.helper_is_thing_hashable(library)

    def test_cacheable_library(self) -> None:
        # Arrange
        library = pylast.Library(self.username, self.network)

        # Act/Assert
        self.helper_validate_cacheable(library, "get_artists")

    def test_get_user(self) -> None:
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)
        user_to_get = self.network.get_user(self.username)

        # Act
        library_user = library.get_user()

        # Assert
        assert library_user == user_to_get
