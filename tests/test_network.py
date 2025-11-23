"""
Integration (not unit) tests for pylast.py
"""

from __future__ import annotations

import re
import time
import uuid

import pytest

import pylast

from .test_pylast import WRITE_TEST, TestPyLastWithLastFm


class TestPyLastNetwork(TestPyLastWithLastFm):
    @pytest.mark.skipif(not WRITE_TEST, reason="Only test once to avoid collisions")
    def test_scrobble(self) -> None:
        # Arrange
        artist = "test artist"
        title = "test title"
        timestamp = self.unix_timestamp()
        lastfm_user = self.network.get_user(self.username)

        # Act
        self.network.scrobble(artist=artist, title="test title 2", timestamp=timestamp)
        self.network.scrobble(artist=artist, title=title, timestamp=timestamp)

        # Assert
        # limit=2 to ignore now-playing:
        last_scrobble = list(lastfm_user.get_recent_tracks(limit=2))[0]
        assert str(last_scrobble.track.artist).lower() == artist
        assert str(last_scrobble.track.title).lower() == title

    @pytest.mark.skipif(not WRITE_TEST, reason="Only test once to avoid collisions")
    def test_update_now_playing(self) -> None:
        # Arrange
        artist = "Test Artist"
        title = "test title"
        album = "Test Album"
        track_number = 1
        lastfm_user = self.network.get_user(self.username)

        # Act
        self.network.update_now_playing(
            artist=artist, title=title, album=album, track_number=track_number
        )

        # Assert
        current_track = lastfm_user.get_now_playing()
        assert current_track is not None
        assert str(current_track.title).lower() == "test title"
        assert str(current_track.artist).lower() == "test artist"
        assert current_track.info["album"] == "Test Album"
        assert current_track.get_album().title == "Test Album"

        assert len(current_track.info["image"])
        assert re.search(r"^http.+$", current_track.info["image"][pylast.SIZE_LARGE])

    def test_enable_rate_limiting(self) -> None:
        # Arrange
        assert not self.network.is_rate_limited()

        # Act
        self.network.enable_rate_limit()
        then = time.time()
        # Make some network call, limit not applied first time
        self.network.get_top_artists()
        # Make a second network call, limiting should be applied
        self.network.get_top_artists()
        now = time.time()

        # Assert
        assert self.network.is_rate_limited()
        assert now - then >= 0.2

    def test_disable_rate_limiting(self) -> None:
        # Arrange
        self.network.enable_rate_limit()
        assert self.network.is_rate_limited()

        # Act
        self.network.disable_rate_limit()
        # Make some network call, limit not applied first time
        self.network.get_user(self.username)
        # Make a second network call, limiting should be applied
        self.network.get_top_artists()

        # Assert
        assert not self.network.is_rate_limited()

    def test_lastfm_network_name(self) -> None:
        # Act
        name = str(self.network)

        # Assert
        assert name == "Last.fm Network"

    def test_geo_get_top_artists(self) -> None:
        # Arrange
        # Act
        artists = self.network.get_geo_top_artists(country="United Kingdom", limit=1)

        # Assert
        assert len(artists) == 1
        assert isinstance(artists[0], pylast.TopItem)
        assert isinstance(artists[0].item, pylast.Artist)

    def test_geo_get_top_tracks(self) -> None:
        # Arrange
        # Act
        tracks = self.network.get_geo_top_tracks(
            country="United Kingdom", location="Manchester", limit=1
        )

        # Assert
        assert len(tracks) == 1
        assert isinstance(tracks[0], pylast.TopItem)
        assert isinstance(tracks[0].item, pylast.Track)

    def test_network_get_top_artists_with_limit(self) -> None:
        # Arrange
        # Act
        artists = self.network.get_top_artists(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(artists, pylast.Artist)

    def test_network_get_top_tags_with_limit(self) -> None:
        # Arrange
        # Act
        tags = self.network.get_top_tags(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(tags, pylast.Tag)

    def test_network_get_top_tags_with_no_limit(self) -> None:
        # Arrange
        # Act
        tags = self.network.get_top_tags()

        # Assert
        self.helper_at_least_one_thing_in_top_list(tags, pylast.Tag)

    def test_network_get_top_tracks_with_limit(self) -> None:
        # Arrange
        # Act
        tracks = self.network.get_top_tracks(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(tracks, pylast.Track)

    def test_country_top_tracks(self) -> None:
        # Arrange
        country = self.network.get_country("Croatia")

        # Act
        things = country.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    def test_country_network_top_tracks(self) -> None:
        # Arrange
        # Act
        things = self.network.get_geo_top_tracks("Croatia", limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    def test_tag_top_tracks(self) -> None:
        # Arrange
        tag = self.network.get_tag("blues")

        # Act
        things = tag.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    def test_album_data(self) -> None:
        # Arrange
        thing = self.network.get_album("Test Artist", "Test Album")

        # Act
        stringed = str(thing)
        rep = thing.__repr__()
        title = thing.get_title()
        name = thing.get_name()
        playcount = thing.get_playcount()
        url = thing.get_url()

        # Assert
        assert stringed == "Test Artist - Test Album"
        assert "pylast.Album('Test Artist', 'Test Album'," in rep
        assert title == name
        assert isinstance(playcount, int)
        assert playcount > 1
        assert "https://www.last.fm/music/test%2bartist/test%2balbum" == url

    def test_track_data(self) -> None:
        # Arrange
        thing = self.network.get_track("Test Artist", "test title")

        # Act
        stringed = str(thing)
        rep = thing.__repr__()
        title = thing.get_title()
        name = thing.get_name()
        playcount = thing.get_playcount()
        url = thing.get_url(pylast.DOMAIN_FRENCH)

        # Assert
        assert stringed == "Test Artist - test title"
        assert "pylast.Track('Test Artist', 'test title'," in rep
        assert title == "test title"
        assert title == name
        assert isinstance(playcount, int)
        assert playcount > 1
        assert "https://www.last.fm/fr/music/test%2bartist/_/test%2btitle" == url

    def test_country_top_artists(self) -> None:
        # Arrange
        country = self.network.get_country("Ukraine")

        # Act
        artists = country.get_top_artists(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(artists, pylast.Artist)

    def test_caching(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        self.network.enable_caching()
        tags1 = user.get_top_tags(limit=1, cacheable=True)
        tags2 = user.get_top_tags(limit=1, cacheable=True)

        # Assert
        assert self.network.is_caching_enabled()
        assert tags1 == tags2
        self.network.disable_caching()
        assert not self.network.is_caching_enabled()

    def test_album_mbid(self) -> None:
        # Arrange
        mbid = "03c91c40-49a6-44a7-90e7-a700edf97a62"

        # Act
        album = self.network.get_album_by_mbid(mbid)
        album_mbid = album.get_mbid()

        # Assert
        assert isinstance(album, pylast.Album)
        assert album.title == "Believe"
        assert album_mbid == mbid

    def test_artist_mbid(self) -> None:
        # Arrange
        mbid = "7e84f845-ac16-41fe-9ff8-df12eb32af55"

        # Act
        artist = self.network.get_artist_by_mbid(mbid)

        # Assert
        assert isinstance(artist, pylast.Artist)
        assert artist.name in ("MusicBrainz Test Artist", "MusicBrainzz Test Artist")

    def test_track_mbid(self) -> None:
        # Arrange
        mbid = "8e99ebff-c706-33a0-8e73-9c8c6e15035b"

        # Act
        track = self.network.get_track_by_mbid(mbid)
        track_mbid = track.get_mbid()

        # Assert
        assert isinstance(track, pylast.Track)
        assert track.title == "Believe"
        assert len(track_mbid) == 36
        # MBID should be a UUID and raise no exception
        # https://musicbrainz.org/doc/MusicBrainz_Identifier
        uuid.UUID(track_mbid)

    def test_init_with_token(self) -> None:
        # Arrange/Act
        msg = None
        try:
            pylast.LastFMNetwork(
                api_key=self.__class__.secrets["api_key"],
                api_secret=self.__class__.secrets["api_secret"],
                token="invalid",
            )
        except pylast.WSError as exc:
            msg = str(exc)

        # Assert
        assert msg == "Unauthorized Token - This token has not been issued"

    def test_proxy(self) -> None:
        # Arrange
        proxy = "http://example.com:1234"

        # Act / Assert
        self.network.enable_proxy(proxy)
        assert self.network.is_proxy_enabled()
        assert self.network.proxy == {"https://": "http://example.com:1234"}

        self.network.disable_proxy()
        assert not self.network.is_proxy_enabled()

    def test_album_search(self) -> None:
        # Arrange
        album = "Nevermind"

        # Act
        search = self.network.search_for_album(album)
        results = search.get_next_page()

        # Assert
        assert isinstance(results, list)
        assert isinstance(results[0], pylast.Album)

    def test_album_search_images(self) -> None:
        # Arrange
        album = "Nevermind"
        search = self.network.search_for_album(album)

        # Act
        results = search.get_next_page()
        images = results[0].info["image"]

        # Assert
        assert len(images) == 4

        assert images[pylast.SIZE_SMALL].startswith("https://")
        assert images[pylast.SIZE_SMALL].endswith(".png")
        assert "/34s/" in images[pylast.SIZE_SMALL]

        assert images[pylast.SIZE_EXTRA_LARGE].startswith("https://")
        assert images[pylast.SIZE_EXTRA_LARGE].endswith(".png")
        assert "/300x300/" in images[pylast.SIZE_EXTRA_LARGE]

    def test_artist_search(self) -> None:
        # Arrange
        artist = "Nirvana"

        # Act
        search = self.network.search_for_artist(artist)
        results = search.get_next_page()

        # Assert
        assert isinstance(results, list)
        assert isinstance(results[0], pylast.Artist)

    def test_artist_search_images(self) -> None:
        # Arrange
        artist = "Nirvana"
        search = self.network.search_for_artist(artist)

        # Act
        results = search.get_next_page()
        images = results[0].info["image"]

        # Assert
        assert len(images) == 4

        assert images[pylast.SIZE_SMALL].startswith("https://")
        assert images[pylast.SIZE_SMALL].endswith(".png")
        assert "/34s/" in images[pylast.SIZE_SMALL]

        assert images[pylast.SIZE_EXTRA_LARGE].startswith("https://")
        assert images[pylast.SIZE_EXTRA_LARGE].endswith(".png")
        assert "/300x300/" in images[pylast.SIZE_EXTRA_LARGE]

    def test_track_search(self) -> None:
        # Arrange
        artist = "Nirvana"
        track = "Smells Like Teen Spirit"

        # Act
        search = self.network.search_for_track(artist, track)
        results = search.get_next_page()

        # Assert
        assert isinstance(results, list)
        assert isinstance(results[0], pylast.Track)

    def test_track_search_images(self) -> None:
        # Arrange
        artist = "Nirvana"
        track = "Smells Like Teen Spirit"
        search = self.network.search_for_track(artist, track)

        # Act
        results = search.get_next_page()
        images = results[0].info["image"]

        # Assert
        assert len(images) == 4

        assert images[pylast.SIZE_SMALL].startswith("https://")
        assert images[pylast.SIZE_SMALL].endswith(".png")
        assert "/34s/" in images[pylast.SIZE_SMALL]

        assert images[pylast.SIZE_EXTRA_LARGE].startswith("https://")
        assert images[pylast.SIZE_EXTRA_LARGE].endswith(".png")
        assert "/300x300/" in images[pylast.SIZE_EXTRA_LARGE]

    def test_search_get_total_result_count(self) -> None:
        # Arrange
        artist = "Nirvana"
        track = "Smells Like Teen Spirit"
        search = self.network.search_for_track(artist, track)

        # Act
        total = search.get_total_result_count()

        # Assert
        assert int(total) > 10000
