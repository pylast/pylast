"""
Integration (not unit) tests for pylast.py
"""

from __future__ import annotations

import time

import pytest

import pylast

from .test_pylast import WRITE_TEST, TestPyLastWithLastFm


class TestPyLastTrack(TestPyLastWithLastFm):
    @pytest.mark.skipif(not WRITE_TEST, reason="Only test once to avoid collisions")
    def test_love(self) -> None:
        # Arrange
        artist = "Test Artist"
        title = "test title"
        track = self.network.get_track(artist, title)
        lastfm_user = self.network.get_user(self.username)

        # Act
        track.love()

        # Assert
        loved = list(lastfm_user.get_loved_tracks(limit=1))
        assert str(loved[0].track.artist).lower() == "test artist"
        assert str(loved[0].track.title).lower() == "test title"

    @pytest.mark.skipif(not WRITE_TEST, reason="Only test once to avoid collisions")
    def test_unlove(self) -> None:
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)
        title = "test title"
        track = pylast.Track(artist, title, self.network)
        lastfm_user = self.network.get_user(self.username)
        track.love()

        # Act
        track.unlove()
        time.sleep(1)  # Delay, for Last.fm latency. TODO Can this be removed later?

        # Assert
        loved = list(lastfm_user.get_loved_tracks(limit=1))
        if len(loved):  # OK to be empty but if not:
            assert str(loved[0].track.artist) != "Test Artist"
            assert str(loved[0].track.title) != "test title"

    def test_user_play_count_in_track_info(self) -> None:
        # Arrange
        artist = "Labi Siffre"
        title = "I Got The..."
        track = pylast.Track(
            artist=artist, title=title, network=self.network, username="RJ"
        )

        # Act
        count = track.get_userplaycount()

        # Assert
        assert count >= 10

    def test_user_loved_in_track_info(self) -> None:
        # Arrange
        artist = "Labi Siffre"
        title = "I Got The..."
        track = pylast.Track(
            artist=artist, title=title, network=self.network, username="RJ"
        )

        # Act
        loved = track.get_userloved()

        # Assert
        assert loved is not None
        assert isinstance(loved, bool)
        assert not isinstance(loved, str)

    def test_track_is_hashable(self) -> None:
        # Arrange
        artist = self.network.get_artist("Test Artist")
        track = artist.get_top_tracks(stream=False)[0].item
        assert isinstance(track, pylast.Track)

        # Act/Assert
        self.helper_is_thing_hashable(track)

    def test_track_wiki_content(self) -> None:
        # Arrange
        track = pylast.Track("Test Artist", "test title", self.network)

        # Act
        wiki = track.get_wiki_content()

        # Assert
        assert wiki is not None
        assert len(wiki) >= 1

    def test_track_wiki_summary(self) -> None:
        # Arrange
        track = pylast.Track("Test Artist", "test title", self.network)

        # Act
        wiki = track.get_wiki_summary()

        # Assert
        assert wiki is not None
        assert len(wiki) >= 1

    def test_track_get_duration(self) -> None:
        # Arrange
        track = pylast.Track("Daft Punk", "Something About Us", self.network)

        # Act
        duration = track.get_duration()

        # Assert
        assert duration >= 100000

    def test_track_get_album(self) -> None:
        # Arrange
        track = pylast.Track("Nirvana", "Lithium", self.network)

        # Act
        album = track.get_album()

        # Assert
        assert str(album) == "Nirvana - Nevermind"

    def test_track_get_similar(self) -> None:
        # Arrange
        track = pylast.Track("Cher", "Believe", self.network)

        # Act
        similar = track.get_similar()

        # Assert
        found = any(str(track.item) == "Cher - Strong Enough" for track in similar)
        assert found

    def test_track_get_similar_limits(self) -> None:
        # Arrange
        track = pylast.Track("Cher", "Believe", self.network)

        # Act/Assert
        assert len(track.get_similar(limit=20)) == 20
        assert len(track.get_similar(limit=10)) <= 10
        assert len(track.get_similar(limit=None)) >= 23
        assert len(track.get_similar(limit=0)) >= 23

    def test_tracks_notequal(self) -> None:
        # Arrange
        track1 = pylast.Track("Test Artist", "test title", self.network)
        track2 = pylast.Track("Test Artist", "Test Track", self.network)

        # Act
        # Assert
        assert track1 != track2

    def test_track_title_prop_caps(self) -> None:
        # Arrange
        track = pylast.Track("test artist", "test title", self.network)

        # Act
        title = track.get_title(properly_capitalized=True)

        # Assert
        assert title == "Test Title"

    def test_track_listener_count(self) -> None:
        # Arrange
        track = pylast.Track("test artist", "test title", self.network)

        # Act
        count = track.get_listener_count()

        # Assert
        assert count > 21

    def test_album_tracks(self) -> None:
        # Arrange
        album = pylast.Album("Test Artist", "Test", self.network)

        # Act
        tracks = album.get_tracks()
        url = tracks[0].get_url()

        # Assert
        assert isinstance(tracks, list)
        assert isinstance(tracks[0], pylast.Track)
        assert len(tracks) == 1
        assert url.startswith("https://www.last.fm/music/test")

    def test_track_eq_none_is_false(self) -> None:
        # Arrange
        track1 = None
        track2 = pylast.Track("Test Artist", "test title", self.network)

        # Act / Assert
        assert track1 != track2

    def test_track_ne_none_is_true(self) -> None:
        # Arrange
        track1 = None
        track2 = pylast.Track("Test Artist", "test title", self.network)

        # Act / Assert
        assert track1 != track2

    def test_track_get_correction(self) -> None:
        # Arrange
        track = pylast.Track("Guns N' Roses", "mrbrownstone", self.network)

        # Act
        corrected_track_name = track.get_correction()

        # Assert
        assert corrected_track_name == "Mr. Brownstone"

    def test_track_with_no_mbid(self) -> None:
        # Arrange
        track = pylast.Track("Static-X", "Set It Off", self.network)

        # Act
        mbid = track.get_mbid()

        # Assert
        assert mbid is None
