#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
from __future__ import annotations

import pylast

from .test_pylast import TestPyLastWithLastFm


class TestPyLastAlbum(TestPyLastWithLastFm):
    def test_album_tags_are_topitems(self) -> None:
        # Arrange
        album = self.network.get_album("Test Artist", "Test Album")

        # Act
        tags = album.get_top_tags(limit=1)

        # Assert
        assert len(tags) > 0
        assert isinstance(tags[0], pylast.TopItem)

    def test_album_is_hashable(self) -> None:
        # Arrange
        album = self.network.get_album("Test Artist", "Test Album")

        # Act/Assert
        self.helper_is_thing_hashable(album)

    def test_album_in_recent_tracks(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        # limit=2 to ignore now-playing:
        track = list(lastfm_user.get_recent_tracks(limit=2))[0]

        # Assert
        assert hasattr(track, "album")

    def test_album_wiki_content(self) -> None:
        # Arrange
        album = pylast.Album("Test Artist", "Test Album", self.network)

        # Act
        wiki = album.get_wiki_content()

        # Assert
        assert wiki is not None
        assert len(wiki) >= 1

    def test_album_wiki_published_date(self) -> None:
        # Arrange
        album = pylast.Album("Test Artist", "Test Album", self.network)

        # Act
        wiki = album.get_wiki_published_date()

        # Assert
        assert wiki is not None
        assert len(wiki) >= 1

    def test_album_wiki_summary(self) -> None:
        # Arrange
        album = pylast.Album("Test Artist", "Test Album", self.network)

        # Act
        wiki = album.get_wiki_summary()

        # Assert
        assert wiki is not None
        assert len(wiki) >= 1

    def test_album_eq_none_is_false(self) -> None:
        # Arrange
        album1 = None
        album2 = pylast.Album("Test Artist", "Test Album", self.network)

        # Act / Assert
        assert album1 != album2

    def test_album_ne_none_is_true(self) -> None:
        # Arrange
        album1 = None
        album2 = pylast.Album("Test Artist", "Test Album", self.network)

        # Act / Assert
        assert album1 != album2

    def test_get_cover_image(self) -> None:
        # Arrange
        album = self.network.get_album("Test Artist", "Test Album")

        # Act
        image = album.get_cover_image()

        # Assert
        assert image.startswith("https://")
        assert image.endswith((".gif", ".png"))

    def test_mbid(self) -> None:
        # Arrange
        album = self.network.get_album("Radiohead", "OK Computer")

        # Act
        mbid = album.get_mbid()

        # Assert
        assert mbid == "0b6b4ba0-d36f-47bd-b4ea-6a5b91842d29"

    def test_no_mbid(self) -> None:
        # Arrange
        album = self.network.get_album("Test Artist", "Test Album")

        # Act
        mbid = album.get_mbid()

        # Assert
        assert mbid is None
