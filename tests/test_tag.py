#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
import unittest

import pylast

from .test_pylast import TestPyLastWithLastFm


class TestPyLastTag(TestPyLastWithLastFm):
    def test_tag_is_hashable(self):
        # Arrange
        tag = self.network.get_top_tags(limit=1)[0]

        # Act/Assert
        self.helper_is_thing_hashable(tag)

    def test_tag_top_artists(self):
        # Arrange
        tag = self.network.get_tag("blues")

        # Act
        artists = tag.get_top_artists(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(artists, pylast.Artist)

    def test_tag_top_albums(self):
        # Arrange
        tag = self.network.get_tag("blues")

        # Act
        albums = tag.get_top_albums(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(albums, pylast.Album)

    def test_tags(self):
        # Arrange
        tag1 = self.network.get_tag("blues")
        tag2 = self.network.get_tag("rock")

        # Act
        tag_repr = repr(tag1)
        tag_str = str(tag1)
        name = tag1.get_name(properly_capitalized=True)
        url = tag1.get_url()

        # Assert
        self.assertEqual("blues", tag_str)
        self.assertIn("pylast.Tag", tag_repr)
        self.assertIn("blues", tag_repr)
        self.assertEqual("blues", name)
        self.assertEqual(tag1, tag1)
        self.assertNotEqual(tag1, tag2)
        self.assertEqual(url, "https://www.last.fm/tag/blues")


if __name__ == "__main__":
    unittest.main(failfast=True)
