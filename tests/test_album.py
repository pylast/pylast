#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
import unittest

import pylast

from .test_pylast import TestPyLastWithLastFm


class TestPyLastAlbum(TestPyLastWithLastFm):
    def test_album_tags_are_topitems(self):
        # Arrange
        albums = self.network.get_user("RJ").get_top_albums()

        # Act
        tags = albums[0].item.get_top_tags(limit=1)

        # Assert
        self.assertGreater(len(tags), 0)
        self.assertIsInstance(tags[0], pylast.TopItem)

    def test_album_is_hashable(self):
        # Arrange
        album = self.network.get_album("Test Artist", "Test Album")

        # Act/Assert
        self.helper_is_thing_hashable(album)

    def test_album_in_recent_tracks(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        # limit=2 to ignore now-playing:
        track = lastfm_user.get_recent_tracks(limit=2)[0]

        # Assert
        self.assertTrue(hasattr(track, "album"))

    def test_album_in_artist_tracks(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        track = lastfm_user.get_artist_tracks(artist="Test Artist")[0]

        # Assert
        self.assertTrue(hasattr(track, "album"))

    def test_album_wiki_content(self):
        # Arrange
        album = pylast.Album("Test Artist", "Test Album", self.network)

        # Act
        wiki = album.get_wiki_content()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    def test_album_wiki_published_date(self):
        # Arrange
        album = pylast.Album("Test Artist", "Test Album", self.network)

        # Act
        wiki = album.get_wiki_published_date()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    def test_album_wiki_summary(self):
        # Arrange
        album = pylast.Album("Test Artist", "Test Album", self.network)

        # Act
        wiki = album.get_wiki_summary()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    def test_album_eq_none_is_false(self):
        # Arrange
        album1 = None
        album2 = pylast.Album("Test Artist", "Test Album", self.network)

        # Act / Assert
        self.assertNotEqual(album1, album2)

    def test_album_ne_none_is_true(self):
        # Arrange
        album1 = None
        album2 = pylast.Album("Test Artist", "Test Album", self.network)

        # Act / Assert
        self.assertNotEqual(album1, album2)

    def test_get_cover_image(self):
        # Arrange
        album = self.network.get_album("Test Artist", "Test Album")

        # Act
        image = album.get_cover_image()

        # Assert
        self.assert_startswith(image, "https://")
        self.assert_endswith(image, ".png")


if __name__ == "__main__":
    unittest.main(failfast=True)
