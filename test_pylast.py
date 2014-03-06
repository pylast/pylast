#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
import os
from random import choice
import time
import unittest

import pylast


def load_secrets():
    secrets_file = "test_pylast.yaml"
    if os.path.isfile(secrets_file):
        import yaml  # pip install pyyaml
        with open(secrets_file, "r") as f:  # see example_test_pylast.yaml
            doc = yaml.load(f)
    else:
        doc = {}
        doc["username"] = os.environ['PYLAST_USERNAME'].strip()
        doc["password_hash"] = os.environ['PYLAST_PASSWORD_HASH'].strip()
        doc["api_key"] = os.environ['PYLAST_API_KEY'].strip()
        doc["api_secret"] = os.environ['PYLAST_API_SECRET'].strip()
    return doc


class TestPyLast(unittest.TestCase):

    secrets = None

    def unix_timestamp(self):
        return int(time.time())

    def setUp(self):
        if self.__class__.secrets is None:
            self.__class__.secrets = load_secrets()

        self.username = self.__class__.secrets["username"]
        password_hash = self.__class__.secrets["password_hash"]

        API_KEY = self.__class__.secrets["api_key"]
        API_SECRET = self.__class__.secrets["api_secret"]

        self.network = pylast.LastFMNetwork(
            api_key=API_KEY, api_secret=API_SECRET,
            username=self.username, password_hash=password_hash)

    def test_scrobble(self):
        # Arrange
        artist = "Test Artist"
        title = "Test Title"
        timestamp = self.unix_timestamp()
        lastfm_user = self.network.get_user(self.username)

        # Act
        self.network.scrobble(artist=artist, title=title, timestamp=timestamp)

        # Assert
        # limit=2 to ignore now-playing:
        last_scrobble = lastfm_user.get_recent_tracks(limit=2)[0]
        self.assertEqual(str(last_scrobble.track.artist), str(artist))
        self.assertEqual(str(last_scrobble.track.title),  str(title))
        self.assertEqual(str(last_scrobble.timestamp),    str(timestamp))

    def test_unscrobble(self):
        # Arrange
        artist = "Test Artist 2"
        title = "Test Title 2"
        timestamp = self.unix_timestamp()
        library = pylast.Library(user=self.username, network=self.network)
        self.network.scrobble(artist=artist, title=title, timestamp=timestamp)
        lastfm_user = self.network.get_user(self.username)

        # Act
        library.remove_scrobble(
            artist=artist, title=title, timestamp=timestamp)

        # Assert
        # limit=2 to ignore now-playing:
        last_scrobble = lastfm_user.get_recent_tracks(limit=2)[0]
        self.assertNotEqual(str(last_scrobble.timestamp), str(timestamp))

    def test_add_album(self):
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)
        album = self.network.get_album("Test Artist", "Test Album")

        # Act
        library.add_album(album)

        # Assert
        my_albums = library.get_albums()
        for my_album in my_albums:
            value = (album == my_album[0])
            if value:
                break
        self.assertTrue(value)

    def test_remove_album(self):
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)
        # Pick an artist with plenty of albums
        artist = self.network.get_top_artists(limit=1)[0].item
        albums = artist.get_top_albums()
        # Pick a random one to avoid problems running concurrent tests
        album = choice(albums)[0]
        library.add_album(album)

        # Act
        library.remove_album(album)

        # Assert
        my_albums = library.get_albums()
        for my_album in my_albums:
            value = (album == my_album[0])
            if value:
                break
        self.assertFalse(value)

    def test_add_artist(self):
        # Arrange
        artist = "Test Artist 2"
        library = pylast.Library(user=self.username, network=self.network)

        # Act
        library.add_artist(artist)

        # Assert
        artists = library.get_artists()
        for artist in artists:
            value = (str(artist[0]) == "Test Artist 2")
            if value:
                break
        self.assertTrue(value)

    def test_remove_artist(self):
        # Arrange
        # Get plenty of artists
        artists = self.network.get_top_artists()
        # Pick a random one to avoid problems running concurrent tests
        my_artist = choice(artists).item
        library = pylast.Library(user=self.username, network=self.network)
        library.add_artist(my_artist)

        # Act
        library.remove_artist(my_artist)

        # Assert
        artists = library.get_artists()
        for artist in artists:
            value = (artist[0] == my_artist)
            if value:
                break
        self.assertFalse(value)

    def test_get_venue(self):
        # Arrange
        venue_name = "Last.fm Office"
        country_name = "United Kingdom"

        # Act
        venue_search = self.network.search_for_venue(venue_name, country_name)
        venue = venue_search.get_next_page()[0]

        # Assert
        self.assertEqual(str(venue.id), "8778225")

    def test_get_user_registration(self):
        # Arrange
        username = "RJ"
        user = self.network.get_user(username)

        # Act
        registered = user.get_registered()

        # Assert
        # Just check date because of timezones
        self.assertIn(u"2002-11-20 ", registered)

    def test_get_user_unixtime_registration(self):
        # Arrange
        username = "RJ"
        user = self.network.get_user(username)

        # Act
        unixtime_registered = user.get_unixtime_registered()

        # Assert
        # Just check date because of timezones
        self.assertEqual(unixtime_registered, u"1037793040")

    def test_get_genderless_user(self):
        # Arrange
        # Currently test_user has no gender set:
        lastfm_user = self.network.get_user("test_user")

        # Act
        gender = lastfm_user.get_gender()

        # Assert
        self.assertIsNone(gender)

    def test_get_countryless_user(self):
        # Arrange
        # Currently test_user has no country set:
        lastfm_user = self.network.get_user("test_user")

        # Act
        country = lastfm_user.get_country()

        # Assert
        self.assertIsNone(country)

    def test_love(self):
        # Arrange
        artist = "Test Artist"
        title = "Test Title"
        track = self.network.get_track(artist, title)
        lastfm_user = self.network.get_user(self.username)

        # Act
        track.love()

        # Assert
        loved = lastfm_user.get_loved_tracks(limit=1)
        self.assertEqual(str(loved[0].track.artist), "Test Artist")
        self.assertEqual(str(loved[0].track.title), "Test Title")

    def test_unlove(self):
        # Arrange
        artist = "Test Artist"
        title = "Test Title"
        track = pylast.Track(artist, title, self.network)
        lastfm_user = self.network.get_user(self.username)
        track.love()

        # Act
        track.unlove()

        # Assert
        loved = lastfm_user.get_loved_tracks(limit=1)
        if len(loved):  # OK to be empty but if not:
            self.assertNotEqual(str(loved.track.artist), "Test Artist")
            self.assertNotEqual(str(loved.track.title), "Test Title")

    def test_get_100_albums(self):
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)

        # Act
        albums = library.get_albums(limit=100)

        # Assert
        self.assertGreaterEqual(len(albums), 0)

    def test_get_limitless_albums(self):
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)

        # Act
        albums = library.get_albums(limit=None)

        # Assert
        self.assertGreaterEqual(len(albums), 0)

    def test_user_equals_none(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        value = (lastfm_user is None)

        # Assert
        self.assertFalse(value)

    def test_user_not_equal_to_none(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        value = (lastfm_user is not None)

        # Assert
        self.assertTrue(value)

    def test_now_playing_user_with_no_scrobbles(self):
        # Arrange
        # Currently test-account has no scrobbles:
        user = self.network.get_user('test-account')

        # Act
        current_track = user.get_now_playing()

        # Assert
        self.assertIsNone(current_track)

    def test_love_limits(self):
        # Arrange
        # Currently test-account has at least 23 loved tracks:
        user = self.network.get_user("test-user")

        # Act/Assert
        self.assertEqual(len(user.get_loved_tracks(limit=20)), 20)
        self.assertLessEqual(len(user.get_loved_tracks(limit=100)), 100)
        self.assertGreaterEqual(len(user.get_loved_tracks(limit=None)), 23)
        self.assertGreaterEqual(len(user.get_loved_tracks(limit=0)), 23)

    def test_update_now_playing(self):
        # Arrange
        artist = "Test Artist"
        title = "Test Title"
        album = "Test Album"
        track_number = 1
        lastfm_user = self.network.get_user(self.username)

        # Act
        self.network.update_now_playing(
            artist=artist, title=title, album=album, track_number=track_number)

        # Assert
        current_track = lastfm_user.get_now_playing()
        self.assertIsNotNone(current_track)
        self.assertEqual(str(current_track.title), "Test Title")
        self.assertEqual(str(current_track.artist), "Test Artist")

    def test_libre_fm(self):
        # Arrange
        username = self.__class__.secrets["username"]
        password_hash = self.__class__.secrets["password_hash"]

        # Act
        network = pylast.LibreFMNetwork(
            password_hash=password_hash, username=username)
        tags = network.get_top_tags(limit=1)

        # Assert
        self.assertGreater(len(tags), 0)
        self.assertEqual(type(tags[0]), pylast.TopItem)

    def test_album_tags_are_topitems(self):
        # Arrange
        albums = self.network.get_user('RJ').get_top_albums()

        # Act
        tags = albums[0].item.get_top_tags(limit=1)

        # Assert
        self.assertGreater(len(tags), 0)
        self.assertEqual(type(tags[0]), pylast.TopItem)

    def helper_is_thing_hashable(self, thing):
        # Arrange
        things = set()

        # Act
        things.add(thing)

        # Assert
        self.assertIsNotNone(thing)
        self.assertEqual(len(things), 1)

    def test_album_is_hashable(self):
        # Arrange
        album = self.network.get_album("Test Artist", "Test Album")

        # Act/Assert
        self.helper_is_thing_hashable(album)

    def test_artist_is_hashable(self):
        # Arrange
        test_artist = self.network.get_artist("Test Artist")
        artist = test_artist.get_similar(limit=1)[0].item
        self.assertEqual(type(artist), pylast.Artist)

        # Act/Assert
        self.helper_is_thing_hashable(artist)

    def test_country_is_hashable(self):
        # Arrange
        country = self.network.get_country("Italy")

        # Act/Assert
        self.helper_is_thing_hashable(country)

    def test_metro_is_hashable(self):
        # Arrange
        metro = self.network.get_metro("Helsinki", "Finland")

        # Act/Assert
        self.helper_is_thing_hashable(metro)

    def test_event_is_hashable(self):
        # Arrange
        user = self.network.get_user("RJ")
        event = user.get_past_events(limit=1)[0]

        # Act/Assert
        self.helper_is_thing_hashable(event)

    def test_group_is_hashable(self):
        # Arrange
        group = self.network.get_group("Audioscrobbler Beta")

        # Act/Assert
        self.helper_is_thing_hashable(group)

    def test_library_is_hashable(self):
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)

        # Act/Assert
        self.helper_is_thing_hashable(library)

    def test_playlist_is_hashable(self):
        # Arrange
        playlist = pylast.Playlist(
            user="RJ", id="1k1qp_doglist", network=self.network)

        # Act/Assert
        self.helper_is_thing_hashable(playlist)

    def test_tag_is_hashable(self):
        # Arrange
        tag = self.network.get_top_tags(limit=1)[0]

        # Act/Assert
        self.helper_is_thing_hashable(tag)

    def test_track_is_hashable(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")
        track = artist.get_top_tracks()[0].item
        self.assertEqual(type(track), pylast.Track)

        # Act/Assert
        self.helper_is_thing_hashable(track)

    def test_user_is_hashable(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")
        user = artist.get_top_fans(limit=1)[0].item
        self.assertEqual(type(user), pylast.User)

        # Act/Assert
        self.helper_is_thing_hashable(user)

    def test_venue_is_hashable(self):
        # Arrange
        venue_id = "8778225"  # Last.fm office
        venue = pylast.Venue(venue_id, self.network)

        # Act/Assert
        self.helper_is_thing_hashable(venue)

    def test_xspf_is_hashable(self):
        # Arrange
        xspf = pylast.XSPF(
            uri="lastfm://playlist/1k1qp_doglist", network=self.network)

        # Act/Assert
        self.helper_is_thing_hashable(xspf)

    def test_invalid_xml(self):
        # Arrange
        # Currently causes PCDATA invalid Char value 25
        artist = "Blind Willie Johnson"
        title = "It's nobody's fault but mine"

        # Act
        search = self.network.search_for_track(artist, title)
        total = search.get_total_result_count()

        # Assert
        self.assertGreaterEqual(int(total), 0)

    def test_user_play_count_in_track_info(self):
        # Arrange
        artist = "Test Artist"
        title = "Test Title"
        track = pylast.Track(
            artist=artist, title=title,
            network=self.network, username=self.username)

        # Act
        count = track.get_userplaycount()

        # Assert
        self.assertGreaterEqual(count, 0)

    def test_user_loved_in_track_info(self):
        # Arrange
        artist = "Test Artist"
        title = "Test Title"
        track = pylast.Track(
            artist=artist, title=title,
            network=self.network, username=self.username)

        # Act
        loved = track.get_userloved()

        # Assert
        self.assertIsNotNone(loved)
        self.assertIsInstance(loved, bool)
        self.assertNotIsInstance(loved, str)

    def test_album_in_recent_tracks(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        # limit=2 to ignore now-playing:
        track = lastfm_user.get_recent_tracks(limit=2)[0]

        # Assert
        self.assertTrue(hasattr(track, 'album'))

    def test_album_in_artist_tracks(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        track = lastfm_user.get_artist_tracks(artist="Test Artist")[0]

        # Assert
        self.assertTrue(hasattr(track, 'album'))

    def test_enable_rate_limiting(self):
        # Arrange
        self.assertFalse(self.network.is_rate_limited())

        # Act
        self.network.enable_rate_limit()
        then = time.time()
        # Make some network call, limit not applied first time
        self.network.get_user(self.username)
        # Make a second network call, limiting should be applied
        self.network.get_top_artists()
        now = time.time()

        # Assert
        self.assertTrue(self.network.is_rate_limited())
        self.assertGreaterEqual(now - then, 0.2)

    def test_disable_rate_limiting(self):
        # Arrange
        self.network.enable_rate_limit()
        self.assertTrue(self.network.is_rate_limited())

        # Act
        self.network.disable_rate_limit()
        # Make some network call, limit not applied first time
        self.network.get_user(self.username)
        # Make a second network call, limiting should be applied
        self.network.get_top_artists()

        # Assert
        self.assertFalse(self.network.is_rate_limited())

    # Commented out because (a) it'll take a long time and (b) it strangely
    # fails due Last.fm's complaining of hitting the rate limit, even when
    # limited to one call per second. The ToS allows 5 calls per second.
    # def test_get_all_scrobbles(self):
        # # Arrange
        # lastfm_user = self.network.get_user("RJ")
        # self.network.enable_rate_limit() # this is going to be slow...

        # # Act
        # tracks = lastfm_user.get_recent_tracks(limit=None)

        # # Assert
        # self.assertGreaterEqual(len(tracks), 0)

    def helper_past_events_have_valid_ids(self, thing):
        # Act
        events = thing.get_past_events()

        # Assert
        self.helper_assert_events_have_valid_ids(events)

    def helper_upcoming_events_have_valid_ids(self, thing):
        # Act
        events = thing.get_upcoming_events()

        # Assert
        self.helper_assert_events_have_valid_ids(events)

    def helper_assert_events_have_valid_ids(self, events):
        # Assert
        # If fails, add past/future event for user/Test Artist:
        self.assertGreaterEqual(len(events), 1)
        for event in events[:2]:  # checking first two should be enough
            self.assertIsInstance(event.get_headliner(), pylast.Artist)

    def test_artist_upcoming_events_returns_valid_ids(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act/Assert
        self.helper_upcoming_events_have_valid_ids(artist)

    def test_user_past_events_returns_valid_ids(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act/Assert
        self.helper_past_events_have_valid_ids(lastfm_user)

    def test_user_recommended_events_returns_valid_ids(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        events = lastfm_user.get_upcoming_events()

        # Assert
        self.helper_assert_events_have_valid_ids(events)

    def test_user_upcoming_events_returns_valid_ids(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act/Assert
        self.helper_upcoming_events_have_valid_ids(lastfm_user)

    def test_venue_past_events_returns_valid_ids(self):
        # Arrange
        venue_id = "8778225"  # Last.fm office
        venue = pylast.Venue(venue_id, self.network)

        # Act/Assert
        self.helper_past_events_have_valid_ids(venue)

    def test_venue_upcoming_events_returns_valid_ids(self):
        # Arrange
        venue_id = "8778225"  # Last.fm office
        venue = pylast.Venue(venue_id, self.network)

        # Act/Assert
        self.helper_upcoming_events_have_valid_ids(venue)

    def test_pickle(self):
        # Arrange
        import pickle
        lastfm_user = self.network.get_user(self.username)

        # Act
        with open("lastfm.txt.pkl", "wb") as f:
            pickle.dump(lastfm_user, f)
        with open("lastfm.txt.pkl", "rb") as f:
            loaded_user = pickle.load(f)

        # Assert
        self.assertEqual(lastfm_user, loaded_user)

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

    def test_album_wiki_content(self):
        # Arrange
        album = pylast.Album("Test Artist", "Test Album", self.network)

        # Act
        wiki = album.get_wiki_content()

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

    def test_track_wiki_content(self):
        # Arrange
        track = pylast.Track("Test Artist", "Test Title", self.network)

        # Act
        wiki = track.get_wiki_content()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    def test_track_wiki_summary(self):
        # Arrange
        track = pylast.Track("Test Artist", "Test Title", self.network)

        # Act
        wiki = track.get_wiki_summary()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    def test_lastfm_network_name(self):
        # Act
        name = str(self.network)

        # Assert
        self.assertEqual(name, "Last.fm Network")

    def test_artist_get_images_deprecated(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")

        # Act/Assert
        with self.assertRaisesRegexp(pylast.WSError, 'deprecated'):
            artist.get_images()

    def helper_validate_results(self, a, b, c):
        # Assert
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertIsNotNone(c)
        self.assertGreaterEqual(len(a), 0)
        self.assertGreaterEqual(len(b), 0)
        self.assertGreaterEqual(len(c), 0)
        self.assertEqual(a, b)
        self.assertEqual(b, c)

    def helper_validate_cacheable(self, thing, function_name):
        # Arrange
        # get thing.function_name()
        func = getattr(thing, function_name, None)

        # Act
        result1 = func(limit=1, cacheable=False)
        result2 = func(limit=1, cacheable=True)
        result3 = func(limit=1)

        # Assert
        self.helper_validate_results(result1, result2, result3)

    def test_cacheable_artist_get_shouts(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")

        # Act/Assert
        self.helper_validate_cacheable(artist, "get_shouts")

    def test_cacheable_event_get_shouts(self):
        # Arrange
        user = self.network.get_user("RJ")
        event = user.get_past_events(limit=1)[0]

        # Act/Assert
        self.helper_validate_cacheable(event, "get_shouts")

    def test_cacheable_track_get_shouts(self):
        # Arrange
        track = self.network.get_top_tracks()[0].item

        # Act/Assert
        self.helper_validate_cacheable(track, "get_shouts")

    def test_cacheable_group_get_members(self):
        # Arrange
        group = self.network.get_group("Audioscrobbler Beta")

        # Act/Assert
        self.helper_validate_cacheable(group, "get_members")

    def test_cacheable_library(self):
        # Arrange
        library = pylast.Library(self.username, self.network)

        # Act/Assert
        self.helper_validate_cacheable(library, "get_albums")
        self.helper_validate_cacheable(library, "get_artists")
        self.helper_validate_cacheable(library, "get_tracks")

    def test_cacheable_user_artist_tracks(self):
        # Arrange
        lastfm_user = self.network.get_authenticated_user()

        # Act
        result1 = lastfm_user.get_artist_tracks("Test Artist", cacheable=False)
        result2 = lastfm_user.get_artist_tracks("Test Artist", cacheable=True)
        result3 = lastfm_user.get_artist_tracks("Test Artist")

        # Assert
        self.helper_validate_results(result1, result2, result3)

    def test_cacheable_user(self):
        # Arrange
        lastfm_user = self.network.get_authenticated_user()

        # Act/Assert
        self.helper_validate_cacheable(lastfm_user, "get_friends")
        self.helper_validate_cacheable(lastfm_user, "get_loved_tracks")
        self.helper_validate_cacheable(lastfm_user, "get_past_events")
        self.helper_validate_cacheable(lastfm_user, "get_recent_tracks")
        self.helper_validate_cacheable(lastfm_user, "get_recommended_artists")
        self.helper_validate_cacheable(lastfm_user, "get_recommended_events")
        self.helper_validate_cacheable(lastfm_user, "get_shouts")

    def test_geo_get_events_in_location(self):
        # Arrange
        # Act
        events = self.network.get_geo_events(
            location="London", tag="blues", limit=1)

        # Assert
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(type(event), pylast.Event)
        self.assertEqual(event.get_venue().location['city'], "London")

    def test_geo_get_events_in_latlong(self):
        # Arrange
        # Act
        events = self.network.get_geo_events(
            lat=40.67, long=-73.94, distance=5, limit=1)

        # Assert
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(type(event), pylast.Event)
        self.assertEqual(event.get_venue().location['city'], "New York")

    def test_geo_get_events_festival(self):
        # Arrange
        # Act
        events = self.network.get_geo_events(
            location="Reading", festivalsonly=True, limit=1)

        # Assert
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(type(event), pylast.Event)
        self.assertEqual(event.get_venue().location['city'], "Reading")

    def helper_dates_valid(self, dates):
        # Assert
        self.assertGreaterEqual(len(dates), 1)
        self.assertEqual(type(dates[0]), tuple)
        (start, end) = dates[0]
        self.assertLess(start, end)

    def test_get_metro_weekly_chart_dates(self):
        # Arrange
        # Act
        dates = self.network.get_metro_weekly_chart_dates()

        # Assert
        self.helper_dates_valid(dates)

    def helper_geo_chart(self, function_name, expected_type=pylast.Artist):
        # Arrange
        metro = self.network.get_metro("Madrid", "Spain")
        dates = self.network.get_metro_weekly_chart_dates()
        (from_date, to_date) = dates[0]

        # get metro.function_name()
        func = getattr(metro, function_name, None)

        # Act
        chart = func(from_date=from_date, to_date=to_date, limit=1)

        # Assert
        self.assertEqual(len(chart), 1)
        self.assertEqual(type(chart[0]), pylast.TopItem)
        self.assertEqual(type(chart[0].item), expected_type)

    def test_get_metro_artist_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart("get_artist_chart")

    def test_get_metro_hype_artist_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart("get_hype_artist_chart")

    def test_get_metro_unique_artist_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart("get_unique_artist_chart")

    def test_get_metro_track_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart("get_track_chart", expected_type=pylast.Track)

    def test_get_metro_hype_track_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart(
            "get_hype_track_chart", expected_type=pylast.Track)

    def test_get_metro_unique_track_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart(
            "get_unique_track_chart", expected_type=pylast.Track)

    def test_geo_get_metros(self):
        # Arrange
        # Act
        metros = self.network.get_metros(country="Poland")

        # Assert
        self.assertGreaterEqual(len(metros), 1)
        self.assertEqual(type(metros[0]), pylast.Metro)
        self.assertEqual(metros[0].get_country(), "Poland")

    def test_geo_get_top_artists(self):
        # Arrange
        # Act
        artists = self.network.get_geo_top_artists(
            country="United Kingdom", limit=1)

        # Assert
        self.assertEqual(len(artists), 1)
        self.assertEqual(type(artists[0]), pylast.TopItem)
        self.assertEqual(type(artists[0].item), pylast.Artist)

    def test_geo_get_top_tracks(self):
        # Arrange
        # Act
        tracks = self.network.get_geo_top_tracks(
            country="United Kingdom", location="Manchester", limit=1)

        # Assert
        self.assertEqual(len(tracks), 1)
        self.assertEqual(type(tracks[0]), pylast.TopItem)
        self.assertEqual(type(tracks[0].item), pylast.Track)

    def test_metro_class(self):
        # Arrange
        # Act
        metro = self.network.get_metro("Bergen", "Norway")

        # Assert
        self.assertEqual(metro.get_name(), "Bergen")
        self.assertEqual(metro.get_country(), "Norway")
        self.assertEqual(str(metro), "Bergen, Norway")
        self.assertEqual(metro, pylast.Metro("Bergen", "Norway", self.network))
        self.assertNotEqual(
            metro,
            pylast.Metro("Wellington", "New Zealand", self.network))

    def test_get_album_play_links(self):
        # Arrange
        album1 = self.network.get_album("Portishead", "Dummy")
        album2 = self.network.get_album("Radiohead", "OK Computer")
        albums = [album1, album2]

        # Act
        links = self.network.get_album_play_links(albums)

        # Assert
        self.assertEqual(type(links), list)
        self.assertEqual(len(links), 2)
        self.assertIn("spotify:album:", links[0])
        self.assertIn("spotify:album:", links[1])

    def test_get_artist_play_links(self):
        # Arrange
        artists = ["Portishead", "Radiohead"]
        # Act
        links = self.network.get_artist_play_links(artists)

        # Assert
        self.assertEqual(type(links), list)
        self.assertEqual(len(links), 2)
        self.assertIn("spotify:artist:", links[0])
        self.assertIn("spotify:artist:", links[1])

    def test_get_track_play_links(self):
        # Arrange
        track1 = self.network.get_track(artist="Portishead", title="Mysterons")
        track2 = self.network.get_track(artist="Radiohead", title="Creep")
        tracks = [track1, track2]

        # Act
        links = self.network.get_track_play_links(tracks)

        # Assert
        self.assertEqual(type(links), list)
        self.assertEqual(len(links), 2)
        self.assertIn("spotify:track:", links[0])
        self.assertIn("spotify:track:", links[1])

    def helper_at_least_one_thing_in_top_list(self, things, expected_type):
        # Assert
        self.assertGreater(len(things), 1)
        self.assertEqual(type(things), list)
        self.assertEqual(type(things[0]), pylast.TopItem)
        self.assertEqual(type(things[0].item), expected_type)

    def helper_only_one_thing_in_top_list(self, things, expected_type):
        # Assert
        self.assertEqual(len(things), 1)
        self.assertEqual(type(things), list)
        self.assertEqual(type(things[0]), pylast.TopItem)
        self.assertEqual(type(things[0].item), expected_type)

    def helper_two_different_things_in_top_list(self, things, expected_type):
        # Assert
        self.assertEqual(len(things), 2)
        thing1 = things[0]
        thing2 = things[1]
        self.assertEqual(type(thing1), pylast.TopItem)
        self.assertEqual(type(thing2), pylast.TopItem)
        self.assertEqual(type(thing1.item), expected_type)
        self.assertEqual(type(thing2.item), expected_type)
        self.assertNotEqual(thing1, thing2)

    def test_user_get_top_tags_with_limit(self):
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        tags = user.get_top_tags(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(tags, pylast.Tag)

    def test_network_get_top_artists_with_limit(self):
        # Arrange
        # Act
        artists = self.network.get_top_artists(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(artists, pylast.Artist)

    def test_network_get_top_tags_with_limit(self):
        # Arrange
        # Act
        tags = self.network.get_top_tags(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(tags, pylast.Tag)

    def test_network_get_top_tracks_with_limit(self):
        # Arrange
        # Act
        tracks = self.network.get_top_tracks(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(tracks, pylast.Track)

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

    def test_artist_top_fans(self):
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_fans(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.User)

    def test_country_top_tracks(self):
        # Arrange
        country = self.network.get_country("Croatia")

        # Act
        things = country.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    def test_country_network_top_tracks(self):
        # Arrange
        # Act
        things = self.network.get_geo_top_tracks("Croatia", limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    def test_tag_top_tracks(self):
        # Arrange
        tag = self.network.get_tag("blues")

        # Act
        things = tag.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    def test_user_top_tracks(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        things = lastfm_user.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    def helper_assert_chart(self, chart, expected_type):
        # Assert
        self.assertIsNotNone(chart)
        self.assertGreater(len(chart), 0)
        self.assertEqual(type(chart[0]), pylast.TopItem)
        self.assertEqual(type(chart[0].item), expected_type)

    def helper_get_assert_charts(self, thing, date):
        # Arrange
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

    def test_group_charts(self):
        # Arrange
        group = self.network.get_group("mnml")
        dates = group.get_weekly_chart_dates()
        self.helper_dates_valid(dates)

        # Act/Assert
        self.helper_get_assert_charts(group, dates[-1])

    def test_tag_charts(self):
        # Arrange
        tag = self.network.get_tag("rock")
        dates = tag.get_weekly_chart_dates()
        self.helper_dates_valid(dates)

        # Act/Assert
        self.helper_get_assert_charts(tag, dates[-1])


    def test_user_charts(self):
        # Arrange
        lastfm_user = self.network.get_user("RJ")
        dates = lastfm_user.get_weekly_chart_dates()
        self.helper_dates_valid(dates)

        # Act/Assert
        self.helper_get_assert_charts(lastfm_user, dates[-1])


    def test_artist_top_fans(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")

        # Act
        fans = artist.get_top_fans()

        # Assert
        self.helper_at_least_one_thing_in_top_list(fans, pylast.User)

    def test_track_top_fans(self):
        # Arrange
        track = self.network.get_track("The Cinematic Orchestra", "Postlude")

        # Act
        fans = track.get_top_fans()

        # Assert
        self.helper_at_least_one_thing_in_top_list(fans, pylast.User)

    # Commented out to avoid spamming
    # def test_share_spam(self):
        # # Arrange
        # users_to_spam = [TODO_ENTER_SPAMEES_HERE]
        # spam_message = "Dig the krazee sound!"
        # artist = self.network.get_top_artists(limit=1)[0].item
        # track = artist.get_top_tracks(limit=1)[0].item
        # event = artist.get_upcoming_events()[0]

        # # Act
        # artist.share(users_to_spam, spam_message)
        # track.share(users_to_spam, spam_message)
        # event.share(users_to_spam, spam_message)

        # Assert
        # Check inbox for spam!


if __name__ == '__main__':

    # For quick testing of a single case (eg. test = "test_scrobble")
    test = ""

    if test is not None and len(test):
        suite = unittest.TestSuite()
        suite.addTest(TestPyLast(test))
        unittest.TextTestRunner().run(suite)
    else:
        unittest.main()

# End of file
