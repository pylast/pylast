#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
import unittest

import pylast

from .test_pylast import TestPyLastWithLastFm


class TestPyLastTrack(TestPyLastWithLastFm):
    def test_love(self):
        # Arrange
        artist = "Test Artist"
        title = "test title"
        track = self.network.get_track(artist, title)
        lastfm_user = self.network.get_user(self.username)

        # Act
        track.love()

        # Assert
        loved = lastfm_user.get_loved_tracks(limit=1)
        self.assertEqual(str(loved[0].track.artist).lower(), "test artist")
        self.assertEqual(str(loved[0].track.title).lower(), "test title")

    def test_unlove(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)
        title = "test title"
        track = pylast.Track(artist, title, self.network)
        lastfm_user = self.network.get_user(self.username)
        track.love()

        # Act
        track.unlove()

        # Assert
        loved = lastfm_user.get_loved_tracks(limit=1)
        if len(loved):  # OK to be empty but if not:
            self.assertNotEqual(str(loved[0].track.artist), "Test Artist")
            self.assertNotEqual(str(loved[0].track.title), "test title")

    def test_user_play_count_in_track_info(self):
        # Arrange
        artist = "Test Artist"
        title = "test title"
        track = pylast.Track(
            artist=artist, title=title, network=self.network, username=self.username
        )

        # Act
        count = track.get_userplaycount()

        # Assert
        self.assertGreaterEqual(count, 0)

    def test_user_loved_in_track_info(self):
        # Arrange
        artist = "Test Artist"
        title = "test title"
        track = pylast.Track(
            artist=artist, title=title, network=self.network, username=self.username
        )

        # Act
        loved = track.get_userloved()

        # Assert
        self.assertIsNotNone(loved)
        self.assertIsInstance(loved, bool)
        self.assertNotIsInstance(loved, str)

    def test_track_is_hashable(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")
        track = artist.get_top_tracks()[0].item
        self.assertIsInstance(track, pylast.Track)

        # Act/Assert
        self.helper_is_thing_hashable(track)

    def test_track_wiki_content(self):
        # Arrange
        track = pylast.Track("Test Artist", "test title", self.network)

        # Act
        wiki = track.get_wiki_content()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    def test_track_wiki_summary(self):
        # Arrange
        track = pylast.Track("Test Artist", "test title", self.network)

        # Act
        wiki = track.get_wiki_summary()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    def test_track_get_duration(self):
        # Arrange
        track = pylast.Track("Nirvana", "Lithium", self.network)

        # Act
        duration = track.get_duration()

        # Assert
        self.assertGreaterEqual(duration, 200000)

    def test_track_is_streamable(self):
        # Arrange
        track = pylast.Track("Nirvana", "Lithium", self.network)

        # Act
        streamable = track.is_streamable()

        # Assert
        self.assertFalse(streamable)

    def test_track_is_fulltrack_available(self):
        # Arrange
        track = pylast.Track("Nirvana", "Lithium", self.network)

        # Act
        fulltrack_available = track.is_fulltrack_available()

        # Assert
        self.assertFalse(fulltrack_available)

    def test_track_get_album(self):
        # Arrange
        track = pylast.Track("Nirvana", "Lithium", self.network)

        # Act
        album = track.get_album()

        # Assert
        self.assertEqual(str(album), "Nirvana - Nevermind")

    def test_track_get_similar(self):
        # Arrange
        track = pylast.Track("Cher", "Believe", self.network)

        # Act
        similar = track.get_similar()

        # Assert
        found = False
        for track in similar:
            if str(track.item) == "Madonna - Vogue":
                found = True
                break
        self.assertTrue(found)

    def test_track_get_similar_limits(self):
        # Arrange
        track = pylast.Track("Cher", "Believe", self.network)

        # Act/Assert
        self.assertEqual(len(track.get_similar(limit=20)), 20)
        self.assertLessEqual(len(track.get_similar(limit=10)), 10)
        self.assertGreaterEqual(len(track.get_similar(limit=None)), 23)
        self.assertGreaterEqual(len(track.get_similar(limit=0)), 23)

    def test_tracks_notequal(self):
        # Arrange
        track1 = pylast.Track("Test Artist", "test title", self.network)
        track2 = pylast.Track("Test Artist", "Test Track", self.network)

        # Act
        # Assert
        self.assertNotEqual(track1, track2)

    def test_track_title_prop_caps(self):
        # Arrange
        track = pylast.Track("test artist", "test title", self.network)

        # Act
        title = track.get_title(properly_capitalized=True)

        # Assert
        self.assertEqual(title, "Test Title")

    def test_track_listener_count(self):
        # Arrange
        track = pylast.Track("test artist", "test title", self.network)

        # Act
        count = track.get_listener_count()

        # Assert
        self.assertGreater(count, 21)

    def test_album_tracks(self):
        # Arrange
        album = pylast.Album("Test Artist", "Test", self.network)

        # Act
        tracks = album.get_tracks()
        url = tracks[0].get_url()

        # Assert
        self.assertIsInstance(tracks, list)
        self.assertIsInstance(tracks[0], pylast.Track)
        self.assertEqual(len(tracks), 1)
        self.assertTrue(url.startswith("https://www.last.fm/music/test"))

    def test_track_eq_none_is_false(self):
        # Arrange
        track1 = None
        track2 = pylast.Track("Test Artist", "test title", self.network)

        # Act / Assert
        self.assertNotEqual(track1, track2)

    def test_track_ne_none_is_true(self):
        # Arrange
        track1 = None
        track2 = pylast.Track("Test Artist", "test title", self.network)

        # Act / Assert
        self.assertNotEqual(track1, track2)

    def test_track_get_correction(self):
        # Arrange
        track = pylast.Track("Guns N' Roses", "mrbrownstone", self.network)

        # Act
        corrected_track_name = track.get_correction()

        # Assert
        self.assertEqual(corrected_track_name, "Mr. Brownstone")

    def test_track_with_no_mbid(self):
        # Arrange
        track = pylast.Track("Static-X", "Set It Off", self.network)

        # Act
        mbid = track.get_mbid()

        # Assert
        self.assertIsNone(mbid)


if __name__ == "__main__":
    unittest.main(failfast=True)
