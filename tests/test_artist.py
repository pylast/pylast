#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
import unittest

import pylast

from .test_pylast import TestPyLastWithLastFm


class TestPyLastArtist(TestPyLastWithLastFm):
    def test_repr(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        representation = repr(artist)

        # Assert
        self.assertTrue(representation.startswith("pylast.Artist('Test Artist',"))

    def test_artist_is_hashable(self):
        # Arrange
        test_artist = self.network.get_artist("Test Artist")
        artist = test_artist.get_similar(limit=2)[0].item
        self.assertIsInstance(artist, pylast.Artist)

        # Act/Assert
        self.helper_is_thing_hashable(artist)

    def test_bio_published_date(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        bio = artist.get_bio_published_date()

        # Assert
        self.assertIsNotNone(bio)
        self.assertGreaterEqual(len(bio), 1)

    def test_bio_content(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        bio = artist.get_bio_content(language="en")

        # Assert
        self.assertIsNotNone(bio)
        self.assertGreaterEqual(len(bio), 1)

    def test_bio_summary(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        bio = artist.get_bio_summary(language="en")

        # Assert
        self.assertIsNotNone(bio)
        self.assertGreaterEqual(len(bio), 1)

    def test_artist_top_tracks(self):
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    def test_artist_top_albums(self):
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_albums(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Album)

    def test_artist_top_albums_limit_1(self):
        # Arrange
        limit = 1
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_albums(limit=limit)

        # Assert
        self.assertEqual(len(things), 1)

    def test_artist_top_albums_limit_50(self):
        # Arrange
        limit = 50
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_albums(limit=limit)

        # Assert
        self.assertEqual(len(things), 50)

    def test_artist_top_albums_limit_100(self):
        # Arrange
        limit = 100
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_albums(limit=limit)

        # Assert
        self.assertEqual(len(things), 100)

    def test_artist_listener_count(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")

        # Act
        count = artist.get_listener_count()

        # Assert
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    def test_tag_artist(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")
        # artist.clear_tags()

        # Act
        artist.add_tag("testing")

        # Assert
        tags = artist.get_tags()
        self.assertGreater(len(tags), 0)
        found = False
        for tag in tags:
            if tag.name == "testing":
                found = True
                break
        self.assertTrue(found)

    def test_remove_tag_of_type_text(self):
        # Arrange
        tag = "testing"  # text
        artist = self.network.get_artist("Test Artist")
        artist.add_tag(tag)

        # Act
        artist.remove_tag(tag)

        # Assert
        tags = artist.get_tags()
        found = False
        for tag in tags:
            if tag.name == "testing":
                found = True
                break
        self.assertFalse(found)

    def test_remove_tag_of_type_tag(self):
        # Arrange
        tag = pylast.Tag("testing", self.network)  # Tag
        artist = self.network.get_artist("Test Artist")
        artist.add_tag(tag)

        # Act
        artist.remove_tag(tag)

        # Assert
        tags = artist.get_tags()
        found = False
        for tag in tags:
            if tag.name == "testing":
                found = True
                break
        self.assertFalse(found)

    def test_remove_tags(self):
        # Arrange
        tags = ["removetag1", "removetag2"]
        artist = self.network.get_artist("Test Artist")
        artist.add_tags(tags)
        artist.add_tags("1more")
        tags_before = artist.get_tags()

        # Act
        artist.remove_tags(tags)

        # Assert
        tags_after = artist.get_tags()
        self.assertEqual(len(tags_after), len(tags_before) - 2)
        found1, found2 = False, False
        for tag in tags_after:
            if tag.name == "removetag1":
                found1 = True
            elif tag.name == "removetag2":
                found2 = True
        self.assertFalse(found1)
        self.assertFalse(found2)

    def test_set_tags(self):
        # Arrange
        tags = ["sometag1", "sometag2"]
        artist = self.network.get_artist("Test Artist 2")
        artist.add_tags(tags)
        tags_before = artist.get_tags()
        new_tags = ["settag1", "settag2"]

        # Act
        artist.set_tags(new_tags)

        # Assert
        tags_after = artist.get_tags()
        self.assertNotEqual(tags_before, tags_after)
        self.assertEqual(len(tags_after), 2)
        found1, found2 = False, False
        for tag in tags_after:
            if tag.name == "settag1":
                found1 = True
            elif tag.name == "settag2":
                found2 = True
        self.assertTrue(found1)
        self.assertTrue(found2)

    def test_artists(self):
        # Arrange
        artist1 = self.network.get_artist("Radiohead")
        artist2 = self.network.get_artist("Portishead")

        # Act
        url = artist1.get_url()
        mbid = artist1.get_mbid()
        image = artist1.get_cover_image()
        playcount = artist1.get_playcount()
        streamable = artist1.is_streamable()
        name = artist1.get_name(properly_capitalized=False)
        name_cap = artist1.get_name(properly_capitalized=True)

        # Assert
        self.assertIn("https", image)
        self.assertGreater(playcount, 1)
        self.assertNotEqual(artist1, artist2)
        self.assertEqual(name.lower(), name_cap.lower())
        self.assertEqual(url, "https://www.last.fm/music/radiohead")
        self.assertEqual(mbid, "a74b1b7f-71a5-4011-9441-d0b5e4122711")
        self.assertIsInstance(streamable, bool)

    def test_artist_eq_none_is_false(self):
        # Arrange
        artist1 = None
        artist2 = pylast.Artist("Test Artist", self.network)

        # Act / Assert
        self.assertNotEqual(artist1, artist2)

    def test_artist_ne_none_is_true(self):
        # Arrange
        artist1 = None
        artist2 = pylast.Artist("Test Artist", self.network)

        # Act / Assert
        self.assertNotEqual(artist1, artist2)

    def test_artist_get_correction(self):
        # Arrange
        artist = pylast.Artist("guns and roses", self.network)

        # Act
        corrected_artist_name = artist.get_correction()

        # Assert
        self.assertEqual(corrected_artist_name, "Guns N' Roses")

    def test_get_userplaycount(self):
        # Arrange
        artist = pylast.Artist("John Lennon", self.network, username=self.username)

        # Act
        playcount = artist.get_userplaycount()

        # Assert
        self.assertGreaterEqual(playcount, 0)


if __name__ == "__main__":
    unittest.main(failfast=True)
