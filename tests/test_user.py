#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
from __future__ import annotations

import calendar
import datetime as dt
import inspect
import os
import re

import pytest

import pylast

from .test_pylast import TestPyLastWithLastFm


class TestPyLastUser(TestPyLastWithLastFm):
    def test_repr(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        representation = repr(user)

        # Assert
        assert representation.startswith("pylast.User('RJ',")

    def test_str(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        string = str(user)

        # Assert
        assert string == "RJ"

    def test_equality(self) -> None:
        # Arrange
        user_1a = self.network.get_user("RJ")
        user_1b = self.network.get_user("RJ")
        user_2 = self.network.get_user("Test User")
        not_a_user = self.network

        # Act / Assert
        assert user_1a == user_1b
        assert user_1a != user_2
        assert user_1a != not_a_user

    def test_get_name(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        name = user.get_name(properly_capitalized=True)

        # Assert
        assert name == "RJ"

    def test_get_user_registration(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        registered = user.get_registered()

        # Assert
        if int(registered):
            # Last.fm API broken? Used to be yyyy-mm-dd not Unix timestamp
            assert registered == "1037793040"
        else:  # pragma: no cover
            # Old way
            # Just check date because of timezones
            assert "2002-11-20 " in registered

    def test_get_user_unixtime_registration(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        unixtime_registered = user.get_unixtime_registered()

        # Assert
        # Just check date because of timezones
        assert unixtime_registered == 1037793040

    def test_get_countryless_user(self) -> None:
        # Arrange
        # Currently test_user has no country set:
        lastfm_user = self.network.get_user("test_user")

        # Act
        country = lastfm_user.get_country()

        # Assert
        assert country is None

    def test_user_get_country(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user("RJ")

        # Act
        country = lastfm_user.get_country()

        # Assert
        assert str(country) == "United Kingdom"

    def test_user_equals_none(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        value = lastfm_user is None

        # Assert
        assert not value

    def test_user_not_equal_to_none(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        value = lastfm_user is not None

        # Assert
        assert value

    def test_now_playing_user_with_no_scrobbles(self) -> None:
        # Arrange
        # Currently test-account has no scrobbles:
        user = self.network.get_user("test-account")

        # Act
        current_track = user.get_now_playing()

        # Assert
        assert current_track is None

    def test_love_limits(self) -> None:
        # Arrange
        # Currently test-account has at least 23 loved tracks:
        user = self.network.get_user("test-user")

        # Act/Assert
        assert len(user.get_loved_tracks(limit=20)) == 20
        assert len(user.get_loved_tracks(limit=100)) <= 100
        assert len(user.get_loved_tracks(limit=None)) >= 23
        assert len(user.get_loved_tracks(limit=0)) >= 23

    def test_user_is_hashable(self) -> None:
        # Arrange
        user = self.network.get_user(self.username)

        # Act/Assert
        self.helper_is_thing_hashable(user)

    # Commented out because (a) it'll take a long time and (b) it strangely
    # fails due Last.fm's complaining of hitting the rate limit, even when
    # limited to one call per second. The ToS allows 5 calls per second.
    # def test_get_all_scrobbles(self):
    #     # Arrange
    #     lastfm_user = self.network.get_user("RJ")
    #     self.network.enable_rate_limit() # this is going to be slow...
    #
    #     # Act
    #     tracks = lastfm_user.get_recent_tracks(limit=None)
    #
    #     # Assert
    #     self.assertGreaterEqual(len(tracks), 0)

    def test_pickle(self) -> None:
        # Arrange
        import pickle

        lastfm_user = self.network.get_user(self.username)
        filename = str(self.unix_timestamp()) + ".pkl"

        # Act
        with open(filename, "wb") as f:
            pickle.dump(lastfm_user, f)
        with open(filename, "rb") as f:
            loaded_user = pickle.load(f)
        os.remove(filename)

        # Assert
        assert lastfm_user == loaded_user

    @pytest.mark.xfail
    def test_cacheable_user(self) -> None:
        # Arrange
        lastfm_user = self.network.get_authenticated_user()

        # Act/Assert
        self.helper_validate_cacheable(lastfm_user, "get_friends")
        # no cover whilst xfail:
        self.helper_validate_cacheable(  # pragma: no cover
            lastfm_user, "get_loved_tracks"
        )
        self.helper_validate_cacheable(  # pragma: no cover
            lastfm_user, "get_recent_tracks"
        )

    def test_user_get_top_tags_with_limit(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        tags = user.get_top_tags(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(tags, pylast.Tag)

    def test_user_top_tracks(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user("RJ")

        # Act
        things = lastfm_user.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    def helper_assert_chart(self, chart, expected_type) -> None:
        # Assert
        assert chart is not None
        assert len(chart) > 0
        assert isinstance(chart[0], pylast.TopItem)
        assert isinstance(chart[0].item, expected_type)

    def helper_get_assert_charts(self, thing, date) -> None:
        # Arrange
        album_chart, track_chart = None, None
        (from_date, to_date) = date

        # Act
        artist_chart = thing.get_weekly_artist_charts(from_date, to_date)
        if type(thing) is not pylast.Tag:
            album_chart = thing.get_weekly_album_charts(from_date, to_date)
            track_chart = thing.get_weekly_track_charts(from_date, to_date)

        # Assert
        self.helper_assert_chart(artist_chart, pylast.Artist)
        if type(thing) is not pylast.Tag:
            self.helper_assert_chart(album_chart, pylast.Album)
            self.helper_assert_chart(track_chart, pylast.Track)

    def helper_dates_valid(self, dates) -> None:
        # Assert
        assert len(dates) >= 1
        assert isinstance(dates[0], tuple)
        (start, end) = dates[0]
        assert start < end

    def test_user_charts(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user("RJ")
        dates = lastfm_user.get_weekly_chart_dates()
        self.helper_dates_valid(dates)

        # Act/Assert
        self.helper_get_assert_charts(lastfm_user, dates[0])

    def test_user_top_artists(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        artists = lastfm_user.get_top_artists(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(artists, pylast.Artist)

    def test_user_top_albums(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        albums = user.get_top_albums(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(albums, pylast.Album)

        top_album = albums[0].item
        assert len(top_album.info["image"])
        assert re.search(r"^http.+$", top_album.info["image"][pylast.SIZE_LARGE])

    def test_user_tagged_artists(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user(self.username)
        tags = ["artisttagola"]
        artist = self.network.get_artist("Test Artist")
        artist.add_tags(tags)

        # Act
        artists = lastfm_user.get_tagged_artists("artisttagola", limit=1)

        # Assert
        self.helper_only_one_thing_in_list(artists, pylast.Artist)

    def test_user_tagged_albums(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user(self.username)
        tags = ["albumtagola"]
        album = self.network.get_album("Test Artist", "Test Album")
        album.add_tags(tags)

        # Act
        albums = lastfm_user.get_tagged_albums("albumtagola", limit=1)

        # Assert
        self.helper_only_one_thing_in_list(albums, pylast.Album)

    def test_user_tagged_tracks(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user(self.username)
        tags = ["tracktagola"]
        track = self.network.get_track("Test Artist", "test title")
        track.add_tags(tags)

        # Act
        tracks = lastfm_user.get_tagged_tracks("tracktagola", limit=1)

        # Assert
        self.helper_only_one_thing_in_list(tracks, pylast.Track)

    def test_user_subscriber(self) -> None:
        # Arrange
        subscriber = self.network.get_user("RJ")
        non_subscriber = self.network.get_user("Test User")

        # Act
        subscriber_is_subscriber = subscriber.is_subscriber()
        non_subscriber_is_subscriber = non_subscriber.is_subscriber()

        # Assert
        assert subscriber_is_subscriber
        assert not non_subscriber_is_subscriber

    def test_user_get_image(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        url = user.get_image()

        # Assert
        assert url.startswith("https://")

    def test_user_get_library(self) -> None:
        # Arrange
        user = self.network.get_user(self.username)

        # Act
        library = user.get_library()

        # Assert
        assert isinstance(library, pylast.Library)

    def test_get_recent_tracks_from_to(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user("RJ")
        start = dt.datetime(2011, 7, 21, 15, 10)
        end = dt.datetime(2011, 7, 21, 15, 15)

        utc_start = calendar.timegm(start.utctimetuple())
        utc_end = calendar.timegm(end.utctimetuple())

        # Act
        tracks = lastfm_user.get_recent_tracks(time_from=utc_start, time_to=utc_end)

        # Assert
        assert len(tracks) == 1
        assert str(tracks[0].track.artist) == "Johnny Cash"
        assert str(tracks[0].track.title) == "Ring of Fire"

    def test_get_recent_tracks_limit_none(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user("bbc6music")
        start = dt.datetime(2020, 2, 15, 15, 00)
        end = dt.datetime(2020, 2, 15, 15, 40)

        utc_start = calendar.timegm(start.utctimetuple())
        utc_end = calendar.timegm(end.utctimetuple())

        # Act
        tracks = lastfm_user.get_recent_tracks(
            time_from=utc_start, time_to=utc_end, limit=None
        )

        # Assert
        assert len(tracks) == 11
        assert str(tracks[0].track.artist) == "Seun Kuti & Egypt 80"
        assert str(tracks[0].track.title) == "Struggles Sounds"

    def test_get_recent_tracks_is_streamable(self) -> None:
        # Arrange
        lastfm_user = self.network.get_user("bbc6music")
        start = dt.datetime(2020, 2, 15, 15, 00)
        end = dt.datetime(2020, 2, 15, 15, 40)

        utc_start = calendar.timegm(start.utctimetuple())
        utc_end = calendar.timegm(end.utctimetuple())

        # Act
        tracks = lastfm_user.get_recent_tracks(
            time_from=utc_start, time_to=utc_end, limit=None, stream=True
        )

        # Assert
        assert inspect.isgenerator(tracks)

    def test_get_playcount(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        playcount = user.get_playcount()

        # Assert
        assert playcount >= 128387

    def test_get_image(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        image = user.get_image()

        # Assert
        assert image.startswith("https://")
        assert image.endswith(".png")

    def test_get_url(self) -> None:
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        url = user.get_url()

        # Assert
        assert url == "https://www.last.fm/user/rj"

    def test_get_weekly_artist_charts(self) -> None:
        # Arrange
        user = self.network.get_user("bbc6music")

        # Act
        charts = user.get_weekly_artist_charts()
        artist, weight = charts[0]

        # Assert
        assert artist is not None
        assert isinstance(artist.network, pylast.LastFMNetwork)

    def test_get_weekly_track_charts(self) -> None:
        # Arrange
        user = self.network.get_user("bbc6music")

        # Act
        charts = user.get_weekly_track_charts()
        track, weight = charts[0]

        # Assert
        assert track is not None
        assert isinstance(track.network, pylast.LastFMNetwork)

    def test_user_get_track_scrobbles(self) -> None:
        # Arrange
        artist = "France Gall"
        title = "Laisse Tomber Les Filles"
        user = self.network.get_user("bbc6music")

        # Act
        scrobbles = user.get_track_scrobbles(artist, title)

        # Assert
        assert len(scrobbles) > 0
        assert str(scrobbles[0].track.artist) == "France Gall"
        assert scrobbles[0].track.title == "Laisse Tomber Les Filles"

    def test_cacheable_user_get_track_scrobbles(self) -> None:
        # Arrange
        artist = "France Gall"
        title = "Laisse Tomber Les Filles"
        user = self.network.get_user("bbc6music")

        # Act
        result1 = user.get_track_scrobbles(artist, title, cacheable=False)
        result2 = list(user.get_track_scrobbles(artist, title, cacheable=True))
        result3 = list(user.get_track_scrobbles(artist, title))

        # Assert
        self.helper_validate_results(result1, result2, result3)
