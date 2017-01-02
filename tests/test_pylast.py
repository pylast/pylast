#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
from flaky import flaky
import os
import pytest
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
        try:
            doc["username"] = os.environ['PYLAST_USERNAME'].strip()
            doc["password_hash"] = os.environ['PYLAST_PASSWORD_HASH'].strip()
            doc["api_key"] = os.environ['PYLAST_API_KEY'].strip()
            doc["api_secret"] = os.environ['PYLAST_API_SECRET'].strip()
        except KeyError:
            pytest.skip("Missing environment variables: PYLAST_USERNAME etc.")
    return doc


def handle_lastfm_exceptions(f):
    """Skip exceptions caused by Last.fm's broken API"""
    def wrapper(*args, **kw):
        try:
            return f(*args, **kw)
        except pylast.WSError as e:
            if (str(e) == "Invalid Method - "
                          "No method with that name in this package"):
                msg = "Ignore broken Last.fm API: " + str(e)
                print(msg)
                pytest.skip(msg)
            else:
                raise(e)
    return wrapper


@flaky(max_runs=5, min_passes=1)
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

    def skip_if_lastfm_api_broken(self, value):
        """Skip things not yet restored in Last.fm's broken API"""
        if value is None or len(value) == 0:
            pytest.skip("Last.fm API is broken.")

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
    def test_get_venue(self):
        # Arrange
        venue_name = "Last.fm Office"
        country_name = "United Kingdom"

        # Act
        venue_search = self.network.search_for_venue(venue_name, country_name)
        venue = venue_search.get_next_page()[0]

        # Assert
        self.assertEqual(str(venue.id), "8778225")

    @handle_lastfm_exceptions
    def test_get_user_registration(self):
        # Arrange
        username = "RJ"
        user = self.network.get_user(username)

        # Act
        registered = user.get_registered()

        # Assert
        # Last.fm API broken? Should be yyyy-mm-dd not Unix timestamp
        if int(registered):
            pytest.skip("Last.fm API is broken.")

        # Just check date because of timezones
        self.assertIn(u"2002-11-20 ", registered)

    @handle_lastfm_exceptions
    def test_get_user_unixtime_registration(self):
        # Arrange
        username = "RJ"
        user = self.network.get_user(username)

        # Act
        unixtime_registered = user.get_unixtime_registered()

        # Assert
        # Just check date because of timezones
        self.assertEqual(unixtime_registered, u"1037793040")

    @handle_lastfm_exceptions
    def test_get_genderless_user(self):
        # Arrange
        # Currently test_user has no gender set:
        lastfm_user = self.network.get_user("test_user")

        # Act
        gender = lastfm_user.get_gender()

        # Assert
        self.assertIsNone(gender)

    @handle_lastfm_exceptions
    def test_get_countryless_user(self):
        # Arrange
        # Currently test_user has no country set:
        lastfm_user = self.network.get_user("test_user")

        # Act
        country = lastfm_user.get_country()

        # Assert
        self.assertIsNone(country)

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
    def test_unlove(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)
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

    @handle_lastfm_exceptions
    def test_get_100_albums(self):
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)

        # Act
        albums = library.get_albums(limit=100)

        # Assert
        self.assertGreaterEqual(len(albums), 0)

    @handle_lastfm_exceptions
    def test_get_limitless_albums(self):
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)

        # Act
        albums = library.get_albums(limit=None)

        # Assert
        self.assertGreaterEqual(len(albums), 0)

    @handle_lastfm_exceptions
    def test_user_equals_none(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        value = (lastfm_user is None)

        # Assert
        self.assertFalse(value)

    @handle_lastfm_exceptions
    def test_user_not_equal_to_none(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        value = (lastfm_user is not None)

        # Assert
        self.assertTrue(value)

    @handle_lastfm_exceptions
    def test_now_playing_user_with_no_scrobbles(self):
        # Arrange
        # Currently test-account has no scrobbles:
        user = self.network.get_user('test-account')

        # Act
        current_track = user.get_now_playing()

        # Assert
        self.assertIsNone(current_track)

    @handle_lastfm_exceptions
    def test_love_limits(self):
        # Arrange
        # Currently test-account has at least 23 loved tracks:
        user = self.network.get_user("test-user")

        # Act/Assert
        self.assertEqual(len(user.get_loved_tracks(limit=20)), 20)
        self.assertLessEqual(len(user.get_loved_tracks(limit=100)), 100)
        self.assertGreaterEqual(len(user.get_loved_tracks(limit=None)), 23)
        self.assertGreaterEqual(len(user.get_loved_tracks(limit=0)), 23)

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
    def test_album_tags_are_topitems(self):
        # Arrange
        albums = self.network.get_user('RJ').get_top_albums()

        # Act
        tags = albums[0].item.get_top_tags(limit=1)

        # Assert
        self.assertGreater(len(tags), 0)
        self.assertIsInstance(tags[0], pylast.TopItem)

    def helper_is_thing_hashable(self, thing):
        # Arrange
        things = set()

        # Act
        things.add(thing)

        # Assert
        self.assertIsNotNone(thing)
        self.assertEqual(len(things), 1)

    @handle_lastfm_exceptions
    def test_album_is_hashable(self):
        # Arrange
        album = self.network.get_album("Test Artist", "Test Album")

        # Act/Assert
        self.helper_is_thing_hashable(album)

    @handle_lastfm_exceptions
    def test_artist_is_hashable(self):
        # Arrange
        test_artist = self.network.get_artist("Test Artist")
        artist = test_artist.get_similar(limit=2)[0].item
        self.assertIsInstance(artist, pylast.Artist)

        # Act/Assert
        self.helper_is_thing_hashable(artist)

    @handle_lastfm_exceptions
    def test_country_is_hashable(self):
        # Arrange
        country = self.network.get_country("Italy")

        # Act/Assert
        self.helper_is_thing_hashable(country)

    @handle_lastfm_exceptions
    def test_metro_is_hashable(self):
        # Arrange
        metro = self.network.get_metro("Helsinki", "Finland")

        # Act/Assert
        self.helper_is_thing_hashable(metro)

    @handle_lastfm_exceptions
    def test_event_is_hashable(self):
        # Arrange
        user = self.network.get_user("RJ")
        event = user.get_past_events(limit=1)[0]

        # Act/Assert
        self.helper_is_thing_hashable(event)

    @handle_lastfm_exceptions
    def test_group_is_hashable(self):
        # Arrange
        group = self.network.get_group("Audioscrobbler Beta")

        # Act/Assert
        self.helper_is_thing_hashable(group)

    @handle_lastfm_exceptions
    def test_library_is_hashable(self):
        # Arrange
        library = pylast.Library(user=self.username, network=self.network)

        # Act/Assert
        self.helper_is_thing_hashable(library)

    @handle_lastfm_exceptions
    def test_playlist_is_hashable(self):
        # Arrange
        playlist = pylast.Playlist(
            user="RJ", playlist_id="1k1qp_doglist", network=self.network)

        # Act/Assert
        self.helper_is_thing_hashable(playlist)

    @handle_lastfm_exceptions
    def test_tag_is_hashable(self):
        # Arrange
        tag = self.network.get_top_tags(limit=1)[0]

        # Act/Assert
        self.helper_is_thing_hashable(tag)

    @handle_lastfm_exceptions
    def test_track_is_hashable(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")
        track = artist.get_top_tracks()[0].item
        self.assertIsInstance(track, pylast.Track)

        # Act/Assert
        self.helper_is_thing_hashable(track)

    @handle_lastfm_exceptions
    def test_user_is_hashable(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")
        user = artist.get_top_fans(limit=1)[0].item
        self.assertIsInstance(user, pylast.User)

        # Act/Assert
        self.helper_is_thing_hashable(user)

    @handle_lastfm_exceptions
    def test_venue_is_hashable(self):
        # Arrange
        venue_id = "8778225"  # Last.fm office
        venue = pylast.Venue(venue_id, self.network)

        # Act/Assert
        self.helper_is_thing_hashable(venue)

    @handle_lastfm_exceptions
    def test_xspf_is_hashable(self):
        # Arrange
        xspf = pylast.XSPF(
            uri="lastfm://playlist/1k1qp_doglist", network=self.network)

        # Act/Assert
        self.helper_is_thing_hashable(xspf)

    @handle_lastfm_exceptions
    def test_invalid_xml(self):
        # Arrange
        # Currently causes PCDATA invalid Char value 25
        artist = "Blind Willie Johnson"
        title = "It's nobody's fault but mine"

        # Act
        search = self.network.search_for_track(artist, title)
        total = search.get_total_result_count()

        # Assert
        self.skip_if_lastfm_api_broken(total)
        self.assertGreaterEqual(int(total), 0)

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
    def test_album_in_recent_tracks(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        # limit=2 to ignore now-playing:
        track = lastfm_user.get_recent_tracks(limit=2)[0]

        # Assert
        self.assertTrue(hasattr(track, 'album'))

    @handle_lastfm_exceptions
    def test_album_in_artist_tracks(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        track = lastfm_user.get_artist_tracks(artist="Test Artist")[0]

        # Assert
        self.assertTrue(hasattr(track, 'album'))

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
    def test_artist_upcoming_events_returns_valid_ids(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act/Assert
        self.helper_upcoming_events_have_valid_ids(artist)

    @handle_lastfm_exceptions
    def test_user_past_events_returns_valid_ids(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act/Assert
        self.helper_past_events_have_valid_ids(lastfm_user)

    @handle_lastfm_exceptions
    def test_user_recommended_events_returns_valid_ids(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        events = lastfm_user.get_upcoming_events()

        # Assert
        self.helper_assert_events_have_valid_ids(events)

    @handle_lastfm_exceptions
    def test_user_upcoming_events_returns_valid_ids(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act/Assert
        self.helper_upcoming_events_have_valid_ids(lastfm_user)

    @handle_lastfm_exceptions
    def test_venue_past_events_returns_valid_ids(self):
        # Arrange
        venue_id = "8778225"  # Last.fm office
        venue = pylast.Venue(venue_id, self.network)

        # Act/Assert
        self.helper_past_events_have_valid_ids(venue)

    @handle_lastfm_exceptions
    def test_venue_upcoming_events_returns_valid_ids(self):
        # Arrange
        venue_id = "8778225"  # Last.fm office
        venue = pylast.Venue(venue_id, self.network)

        # Act/Assert
        self.helper_upcoming_events_have_valid_ids(venue)

    @handle_lastfm_exceptions
    def test_pickle(self):
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
        self.assertEqual(lastfm_user, loaded_user)

    @handle_lastfm_exceptions
    def test_bio_published_date(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        bio = artist.get_bio_published_date()

        # Assert
        self.assertIsNotNone(bio)
        self.assertGreaterEqual(len(bio), 1)

    @handle_lastfm_exceptions
    def test_bio_content(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        bio = artist.get_bio_content(language="en")

        # Assert
        self.assertIsNotNone(bio)
        self.assertGreaterEqual(len(bio), 1)

    @handle_lastfm_exceptions
    def test_bio_summary(self):
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        bio = artist.get_bio_summary(language="en")

        # Assert
        self.assertIsNotNone(bio)
        self.assertGreaterEqual(len(bio), 1)

    @handle_lastfm_exceptions
    def test_album_wiki_content(self):
        # Arrange
        album = pylast.Album("Test Artist", "Test Album", self.network)

        # Act
        wiki = album.get_wiki_content()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    @handle_lastfm_exceptions
    def test_album_wiki_published_date(self):
        # Arrange
        album = pylast.Album("Test Artist", "Test Album", self.network)

        # Act
        wiki = album.get_wiki_published_date()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    @handle_lastfm_exceptions
    def test_album_wiki_summary(self):
        # Arrange
        album = pylast.Album("Test Artist", "Test Album", self.network)

        # Act
        wiki = album.get_wiki_summary()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    @handle_lastfm_exceptions
    def test_track_wiki_content(self):
        # Arrange
        track = pylast.Track("Test Artist", "Test Title", self.network)

        # Act
        wiki = track.get_wiki_content()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    @handle_lastfm_exceptions
    def test_track_wiki_summary(self):
        # Arrange
        track = pylast.Track("Test Artist", "Test Title", self.network)

        # Act
        wiki = track.get_wiki_summary()

        # Assert
        self.assertIsNotNone(wiki)
        self.assertGreaterEqual(len(wiki), 1)

    @handle_lastfm_exceptions
    def test_lastfm_network_name(self):
        # Act
        name = str(self.network)

        # Assert
        self.assertEqual(name, "Last.fm Network")

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

    @handle_lastfm_exceptions
    def test_cacheable_artist_get_shouts(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")

        # Act/Assert
        self.helper_validate_cacheable(artist, "get_shouts")

    @handle_lastfm_exceptions
    def test_cacheable_event_get_shouts(self):
        # Arrange
        user = self.network.get_user("RJ")
        event = user.get_past_events(limit=1)[0]

        # Act/Assert
        self.helper_validate_cacheable(event, "get_shouts")

    @handle_lastfm_exceptions
    def test_cacheable_track_get_shouts(self):
        # Arrange
        track = self.network.get_top_tracks()[0].item

        # Act/Assert
        self.helper_validate_cacheable(track, "get_shouts")

    @handle_lastfm_exceptions
    def test_cacheable_group_get_members(self):
        # Arrange
        group = self.network.get_group("Audioscrobbler Beta")

        # Act/Assert
        self.helper_validate_cacheable(group, "get_members")

    @handle_lastfm_exceptions
    def test_cacheable_library(self):
        # Arrange
        library = pylast.Library(self.username, self.network)

        # Act/Assert
        self.helper_validate_cacheable(library, "get_albums")
        self.helper_validate_cacheable(library, "get_artists")
        self.helper_validate_cacheable(library, "get_tracks")

    @handle_lastfm_exceptions
    def test_cacheable_user_artist_tracks(self):
        # Arrange
        lastfm_user = self.network.get_authenticated_user()

        # Act
        result1 = lastfm_user.get_artist_tracks("Test Artist", cacheable=False)
        result2 = lastfm_user.get_artist_tracks("Test Artist", cacheable=True)
        result3 = lastfm_user.get_artist_tracks("Test Artist")

        # Assert
        self.helper_validate_results(result1, result2, result3)

    @handle_lastfm_exceptions
    def test_cacheable_user(self):
        # Arrange
        lastfm_user = self.network.get_authenticated_user()

        # Act/Assert
        # Skip the first one because Last.fm API is broken
        # self.helper_validate_cacheable(lastfm_user, "get_friends")
        self.helper_validate_cacheable(lastfm_user, "get_loved_tracks")
        self.helper_validate_cacheable(lastfm_user, "get_neighbours")
        self.helper_validate_cacheable(lastfm_user, "get_past_events")
        self.helper_validate_cacheable(lastfm_user, "get_recent_tracks")
        self.helper_validate_cacheable(lastfm_user, "get_recommended_artists")
        self.helper_validate_cacheable(lastfm_user, "get_recommended_events")
        self.helper_validate_cacheable(lastfm_user, "get_shouts")

    @handle_lastfm_exceptions
    def test_geo_get_events_in_location(self):
        # Arrange
        # Act
        events = self.network.get_geo_events(
            location="London", tag="blues", limit=1)

        # Assert
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIsInstance(event, pylast.Event)
        self.assertIn(event.get_venue().location['city'],
                      ["London", "Camden"])

    @handle_lastfm_exceptions
    def test_geo_get_events_in_latlong(self):
        # Arrange
        # Act
        events = self.network.get_geo_events(
            latitude=53.466667, longitude=-2.233333, distance=5, limit=1)

        # Assert
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIsInstance(event, pylast.Event)
        self.assertEqual(event.get_venue().location['city'], "Manchester")

    @handle_lastfm_exceptions
    def test_geo_get_events_festival(self):
        # Arrange
        # Act
        events = self.network.get_geo_events(
            location="Reading", festivalsonly=True, limit=1)

        # Assert
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIsInstance(event, pylast.Event)
        self.assertEqual(event.get_venue().location['city'], "Reading")

    def helper_dates_valid(self, dates):
        # Assert
        self.assertGreaterEqual(len(dates), 1)
        self.assertIsInstance(dates[0], tuple)
        (start, end) = dates[0]
        self.assertLess(start, end)

    @handle_lastfm_exceptions
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
        self.assertIsInstance(chart[0], pylast.TopItem)
        self.assertIsInstance(chart[0].item, expected_type)

    @handle_lastfm_exceptions
    def test_get_metro_artist_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart("get_artist_chart")

    @handle_lastfm_exceptions
    def test_get_metro_hype_artist_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart("get_hype_artist_chart")

    @handle_lastfm_exceptions
    def test_get_metro_unique_artist_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart("get_unique_artist_chart")

    @handle_lastfm_exceptions
    def test_get_metro_track_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart("get_track_chart", expected_type=pylast.Track)

    @handle_lastfm_exceptions
    def test_get_metro_hype_track_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart(
            "get_hype_track_chart", expected_type=pylast.Track)

    @handle_lastfm_exceptions
    def test_get_metro_unique_track_chart(self):
        # Arrange/Act/Assert
        self.helper_geo_chart(
            "get_unique_track_chart", expected_type=pylast.Track)

    @handle_lastfm_exceptions
    def test_geo_get_metros(self):
        # Arrange
        # Act
        metros = self.network.get_metros(country="Poland")

        # Assert
        self.assertGreaterEqual(len(metros), 1)
        self.assertIsInstance(metros[0], pylast.Metro)
        self.assertEqual(metros[0].get_country(), "Poland")

    @handle_lastfm_exceptions
    def test_geo_get_top_artists(self):
        # Arrange
        # Act
        artists = self.network.get_geo_top_artists(
            country="United Kingdom", limit=1)

        # Assert
        self.assertEqual(len(artists), 1)
        self.assertIsInstance(artists[0], pylast.TopItem)
        self.assertIsInstance(artists[0].item, pylast.Artist)

    @handle_lastfm_exceptions
    def test_geo_get_top_tracks(self):
        # Arrange
        # Act
        tracks = self.network.get_geo_top_tracks(
            country="United Kingdom", location="Manchester", limit=1)

        # Assert
        self.assertEqual(len(tracks), 1)
        self.assertIsInstance(tracks[0], pylast.TopItem)
        self.assertIsInstance(tracks[0].item, pylast.Track)

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
    def test_get_album_play_links(self):
        # Arrange
        album1 = self.network.get_album("Portishead", "Dummy")
        album2 = self.network.get_album("Radiohead", "OK Computer")
        albums = [album1, album2]

        # Act
        links = self.network.get_album_play_links(albums)

        # Assert
        self.assertIsInstance(links, list)
        self.assertEqual(len(links), 2)
        self.assertIn("spotify:album:", links[0])
        self.assertIn("spotify:album:", links[1])

    @handle_lastfm_exceptions
    def test_get_artist_play_links(self):
        # Arrange
        artists = ["Portishead", "Radiohead"]
        # Act
        links = self.network.get_artist_play_links(artists)

        # Assert
        self.assertIsInstance(links, list)
        self.assertEqual(len(links), 2)
        self.assertIn("spotify:artist:", links[0])
        self.assertIn("spotify:artist:", links[1])

    @handle_lastfm_exceptions
    def test_get_track_play_links(self):
        # Arrange
        track1 = self.network.get_track(artist="Portishead", title="Mysterons")
        track2 = self.network.get_track(artist="Radiohead", title="Creep")
        tracks = [track1, track2]

        # Act
        links = self.network.get_track_play_links(tracks)

        # Assert
        self.assertIsInstance(links, list)
        self.assertEqual(len(links), 2)
        self.assertIn("spotify:track:", links[0])
        self.assertIn("spotify:track:", links[1])

    def helper_at_least_one_thing_in_top_list(self, things, expected_type):
        # Assert
        self.assertGreater(len(things), 1)
        self.assertIsInstance(things, list)
        self.assertIsInstance(things[0], pylast.TopItem)
        self.assertIsInstance(things[0].item, expected_type)

    def helper_only_one_thing_in_top_list(self, things, expected_type):
        # Assert
        self.assertEqual(len(things), 1)
        self.assertIsInstance(things, list)
        self.assertIsInstance(things[0], pylast.TopItem)
        self.assertIsInstance(things[0].item, expected_type)

    def helper_only_one_thing_in_list(self, things, expected_type):
        # Assert
        self.assertEqual(len(things), 1)
        self.assertIsInstance(things, list)
        self.assertIsInstance(things[0], expected_type)

    def helper_two_different_things_in_top_list(self, things, expected_type):
        # Assert
        self.assertEqual(len(things), 2)
        thing1 = things[0]
        thing2 = things[1]
        self.assertIsInstance(thing1, pylast.TopItem)
        self.assertIsInstance(thing2, pylast.TopItem)
        self.assertIsInstance(thing1.item, expected_type)
        self.assertIsInstance(thing2.item, expected_type)
        self.assertNotEqual(thing1, thing2)

    def helper_two_things_in_list(self, things, expected_type):
        # Assert
        self.assertEqual(len(things), 2)
        self.assertIsInstance(things, list)
        thing1 = things[0]
        thing2 = things[1]
        self.assertIsInstance(thing1, expected_type)
        self.assertIsInstance(thing2, expected_type)

    @handle_lastfm_exceptions
    def test_user_get_top_tags_with_limit(self):
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        tags = user.get_top_tags(limit=1)

        # Assert
        self.skip_if_lastfm_api_broken(tags)
        self.helper_only_one_thing_in_top_list(tags, pylast.Tag)

    @handle_lastfm_exceptions
    def test_network_get_top_artists_with_limit(self):
        # Arrange
        # Act
        artists = self.network.get_top_artists(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(artists, pylast.Artist)

    @handle_lastfm_exceptions
    def test_network_get_top_tags_with_limit(self):
        # Arrange
        # Act
        tags = self.network.get_top_tags(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(tags, pylast.Tag)

    @handle_lastfm_exceptions
    def test_network_get_top_tags_with_no_limit(self):
        # Arrange
        # Act
        tags = self.network.get_top_tags()

        # Assert
        self.helper_at_least_one_thing_in_top_list(tags, pylast.Tag)

    @handle_lastfm_exceptions
    def test_network_get_top_tracks_with_limit(self):
        # Arrange
        # Act
        tracks = self.network.get_top_tracks(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(tracks, pylast.Track)

    @handle_lastfm_exceptions
    def test_artist_top_tracks(self):
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    @handle_lastfm_exceptions
    def test_artist_top_albums(self):
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_albums(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Album)

    @handle_lastfm_exceptions
    def test_artist_top_fans(self):
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_fans(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.User)

    @handle_lastfm_exceptions
    def test_country_top_tracks(self):
        # Arrange
        country = self.network.get_country("Croatia")

        # Act
        things = country.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    @handle_lastfm_exceptions
    def test_country_network_top_tracks(self):
        # Arrange
        # Act
        things = self.network.get_geo_top_tracks("Croatia", limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    @handle_lastfm_exceptions
    def test_tag_top_tracks(self):
        # Arrange
        tag = self.network.get_tag("blues")

        # Act
        things = tag.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    @handle_lastfm_exceptions
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
        self.assertIsInstance(chart[0], pylast.TopItem)
        self.assertIsInstance(chart[0].item, expected_type)

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

    @handle_lastfm_exceptions
    def test_group_charts(self):
        # Arrange
        group = self.network.get_group("mnml")
        dates = group.get_weekly_chart_dates()
        self.helper_dates_valid(dates)

        # Act/Assert
        self.helper_get_assert_charts(group, dates[-2])

    @handle_lastfm_exceptions
    def test_tag_charts(self):
        # Arrange
        tag = self.network.get_tag("rock")
        dates = tag.get_weekly_chart_dates()
        self.helper_dates_valid(dates)

        # Act/Assert
        self.helper_get_assert_charts(tag, dates[-2])

    @handle_lastfm_exceptions
    def test_user_charts(self):
        # Arrange
        lastfm_user = self.network.get_user("RJ")
        dates = lastfm_user.get_weekly_chart_dates()
        self.helper_dates_valid(dates)

        # Act/Assert
        self.helper_get_assert_charts(lastfm_user, dates[0])

    @handle_lastfm_exceptions
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

        # album/artist/event/track/user

    @handle_lastfm_exceptions
    def test_album_shouts(self):
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item
        album = artist.get_top_albums(limit=1)[0].item

        # Act
        shouts = album.get_shouts(limit=2)

        # Assert
        self.helper_two_things_in_list(shouts, pylast.Shout)

    @handle_lastfm_exceptions
    def test_artist_shouts(self):
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        shouts = artist.get_shouts(limit=2)

        # Assert
        self.helper_two_things_in_list(shouts, pylast.Shout)

    @handle_lastfm_exceptions
    def test_event_shouts(self):
        # Arrange
        event_id = 3478520  # Glasto 2014
        event = pylast.Event(event_id, self.network)

        # Act
        shouts = event.get_shouts(limit=2)

        # Assert
        self.helper_two_things_in_list(shouts, pylast.Shout)

    @handle_lastfm_exceptions
    def test_track_shouts(self):
        # Arrange
        track = self.network.get_track("The Cinematic Orchestra", "Postlude")

        # Act
        shouts = track.get_shouts(limit=2)

        # Assert
        self.helper_two_things_in_list(shouts, pylast.Shout)

    @handle_lastfm_exceptions
    def test_user_shouts(self):
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        shouts = user.get_shouts(limit=2)

        # Assert
        self.helper_two_things_in_list(shouts, pylast.Shout)

    @handle_lastfm_exceptions
    def test_album_data(self):
        # Arrange
        thing = self.network.get_album("Test Artist", "Test Album")

        # Act
        stringed = str(thing)
        repr = thing.__repr__()
        title = thing.get_title()
        name = thing.get_name()
        playcount = thing.get_playcount()
        url = thing.get_url()

        # Assert
        self.assertEqual(stringed, "Test Artist - Test Album")
        self.assertIn("pylast.Album('Test Artist', 'Test Album',", repr)
        self.assertEqual(title, name)
        self.assertIsInstance(playcount, int)
        self.assertGreater(playcount, 1)
        self.assertEqual(
            "http://www.last.fm/music/test%2bartist/test%2balbum", url)

    @handle_lastfm_exceptions
    def test_track_data(self):
        # Arrange
        thing = self.network.get_track("Test Artist", "Test Title")

        # Act
        stringed = str(thing)
        repr = thing.__repr__()
        title = thing.get_title()
        name = thing.get_name()
        playcount = thing.get_playcount()
        url = thing.get_url(pylast.DOMAIN_FRENCH)

        # Assert
        self.assertEqual(stringed, "Test Artist - Test Title")
        self.assertIn("pylast.Track('Test Artist', 'Test Title',", repr)
        self.assertEqual(title, "Test Title")
        self.assertEqual(title, name)
        self.assertIsInstance(playcount, int)
        self.assertGreater(playcount, 1)
        self.assertEqual(
            "http://www.lastfm.fr/music/test%2bartist/_/test%2btitle", url)

    @handle_lastfm_exceptions
    def test_tag_top_artists(self):
        # Arrange
        tag = self.network.get_tag("blues")

        # Act
        artists = tag.get_top_artists(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(artists, pylast.Artist)

    @handle_lastfm_exceptions
    def test_country_top_artists(self):
        # Arrange
        country = self.network.get_country("Ukraine")

        # Act
        artists = country.get_top_artists(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(artists, pylast.Artist)

    @handle_lastfm_exceptions
    def test_user_top_artists(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        artists = lastfm_user.get_top_artists(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(artists, pylast.Artist)

    @handle_lastfm_exceptions
    def test_tag_top_albums(self):
        # Arrange
        tag = self.network.get_tag("blues")

        # Act
        albums = tag.get_top_albums(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(albums, pylast.Album)

    @handle_lastfm_exceptions
    def test_user_top_albums(self):
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        albums = user.get_top_albums(limit=1)

        # Assert
        self.helper_only_one_thing_in_top_list(albums, pylast.Album)

    @handle_lastfm_exceptions
    def test_user_tagged_artists(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)
        tags = ["artisttagola"]
        artist = self.network.get_artist("Test Artist")
        artist.add_tags(tags)

        # Act
        artists = lastfm_user.get_tagged_artists('artisttagola', limit=1)

        # Assert
        self.helper_only_one_thing_in_list(artists, pylast.Artist)

    @handle_lastfm_exceptions
    def test_user_tagged_albums(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)
        tags = ["albumtagola"]
        album = self.network.get_album("Test Artist", "Test Album")
        album.add_tags(tags)

        # Act
        albums = lastfm_user.get_tagged_albums('albumtagola', limit=1)

        # Assert
        self.helper_only_one_thing_in_list(albums, pylast.Album)

    @handle_lastfm_exceptions
    def test_user_tagged_tracks(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)
        tags = ["tracktagola"]
        track = self.network.get_track("Test Artist", "Test Title")
        track.add_tags(tags)
        # Act
        tracks = lastfm_user.get_tagged_tracks('tracktagola', limit=1)

        # Assert
        self.helper_only_one_thing_in_list(tracks, pylast.Track)

    @handle_lastfm_exceptions
    def test_caching(self):
        # Arrange
        user = self.network.get_user("RJ")

        # Act
        self.network.enable_caching()
        shouts1 = user.get_shouts(limit=1, cacheable=True)
        shouts2 = user.get_shouts(limit=1, cacheable=True)

        # Assert
        self.assertTrue(self.network.is_caching_enabled())
        self.assertEqual(shouts1, shouts2)
        self.network.disable_caching()
        self.assertFalse(self.network.is_caching_enabled())

    @handle_lastfm_exceptions
    def test_create_playlist(self):
        # Arrange
        title = "Test playlist"
        description = "Testing"
        lastfm_user = self.network.get_user(self.username)

        # Act
        playlist = self.network.create_new_playlist(title, description)

        # Assert
        self.assertIsInstance(playlist, pylast.Playlist)
        self.assertEqual(playlist.get_title(), "Test playlist")
        self.assertEqual(playlist.get_description(), "Testing")
        self.assertEqual(playlist.get_user(), lastfm_user)

    @handle_lastfm_exceptions
    def test_empty_playlist_unstreamable(self):
        # Arrange
        title = "Empty playlist"
        description = "Unstreamable"

        # Act
        playlist = self.network.create_new_playlist(title, description)

        # Assert
        self.assertEqual(playlist.get_size(), 0)
        self.assertEqual(playlist.get_duration(), 0)
        self.assertFalse(playlist.is_streamable())

    @handle_lastfm_exceptions
    def test_big_playlist_is_streamable(self):
        # Arrange
        # Find a big playlist on Last.fm, eg "top 100 classick rock songs"
        user = "kaxior"
        id = 10417943
        playlist = pylast.Playlist(user, id, self.network)
        self.assertEqual(
            playlist.get_url(),
            "http://www.last.fm/user/kaxior/library/"
            "playlists/67ajb_top_100_classick_rock_songs")

        # Act
        # Nothing

        # Assert
        self.assertIsInstance(playlist, pylast.Playlist)
        self.assertGreaterEqual(playlist.get_size(), 45)
        self.assertGreater(playlist.get_duration(), 0)
        self.assertTrue(playlist.is_streamable())

    @handle_lastfm_exceptions
    def test_add_track_to_playlist(self):
        # Arrange
        title = "One track playlist"
        description = "Testing"
        playlist = self.network.create_new_playlist(title, description)
        track = pylast.Track("Test Artist", "Test Title", self.network)

        # Act
        playlist.add_track(track)

        # Assert
        self.assertEqual(playlist.get_size(), 1)
        self.assertEqual(len(playlist.get_tracks()), 1)
        self.assertTrue(playlist.has_track(track))

    @handle_lastfm_exceptions
    def test_album_mbid(self):
        # Arrange
        mbid = "a6a265bf-9f81-4055-8224-f7ac0aa6b937"

        # Act
        album = self.network.get_album_by_mbid(mbid)
        album_mbid = album.get_mbid()

        # Assert
        self.assertIsInstance(album, pylast.Album)
        self.assertEqual(album.title.lower(), "test")
        self.assertEqual(album_mbid, mbid)

    @handle_lastfm_exceptions
    def test_artist_mbid(self):
        # Arrange
        mbid = "7e84f845-ac16-41fe-9ff8-df12eb32af55"

        # Act
        artist = self.network.get_artist_by_mbid(mbid)

        # Assert
        self.assertIsInstance(artist, pylast.Artist)
        self.assertEqual(artist.name, "MusicBrainz Test Artist")

    @handle_lastfm_exceptions
    def test_track_mbid(self):
        # Arrange
        mbid = "ebc037b1-cc9c-44f2-a21f-83c219f0e1e0"

        # Act
        track = self.network.get_track_by_mbid(mbid)
        track_mbid = track.get_mbid()

        # Assert
        self.assertIsInstance(track, pylast.Track)
        self.assertEqual(track.title, "first")
        self.assertEqual(track_mbid, mbid)

    @handle_lastfm_exceptions
    def test_artist_listener_count(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")

        # Act
        count = artist.get_listener_count()

        # Assert
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    @handle_lastfm_exceptions
    def test_event_attendees(self):
        # Arrange
        user = self.network.get_user("RJ")
        event = user.get_past_events(limit=1)[0]

        # Act
        users = event.get_attendees()

        # Assert
        self.assertIsInstance(users, list)
        self.assertIsInstance(users[0], pylast.User)

    @handle_lastfm_exceptions
    def test_tag_artist(self):
        # Arrange
        artist = self.network.get_artist("Test Artist")
#         artist.clear_tags()

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

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
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

    @handle_lastfm_exceptions
    def test_set_tags(self):
        # Arrange
        tags = ["sometag1", "sometag2"]
        artist = self.network.get_artist("Test Artist")
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

    @handle_lastfm_exceptions
    def test_tracks_notequal(self):
        # Arrange
        track1 = pylast.Track("Test Artist", "Test Title", self.network)
        track2 = pylast.Track("Test Artist", "Test Track", self.network)

        # Act
        # Assert
        self.assertNotEqual(track1, track2)

    @handle_lastfm_exceptions
    def test_track_id(self):
        # Arrange
        track = pylast.Track("Test Artist", "Test Title", self.network)

        # Act
        id = track.get_id()

        # Assert
        self.skip_if_lastfm_api_broken(id)
        self.assertEqual(id, "14053327")

    @handle_lastfm_exceptions
    def test_track_title_prop_caps(self):
        # Arrange
        track = pylast.Track("test artist", "test title", self.network)

        # Act
        title = track.get_title(properly_capitalized=True)

        # Assert
        self.assertEqual(title, "Test Title")

    @handle_lastfm_exceptions
    def test_track_listener_count(self):
        # Arrange
        track = pylast.Track("test artist", "test title", self.network)

        # Act
        count = track.get_listener_count()

        # Assert
        self.assertGreater(count, 21)

    @handle_lastfm_exceptions
    def test_album_rel_date(self):
        # Arrange
        album = pylast.Album("Test Artist", "Test Release", self.network)

        # Act
        date = album.get_release_date()

        # Assert
        self.skip_if_lastfm_api_broken(date)
        self.assertIn("2011", date)

    @handle_lastfm_exceptions
    def test_album_tracks(self):
        # Arrange
        album = pylast.Album("Test Artist", "Test Release", self.network)

        # Act
        tracks = album.get_tracks()

        # Assert
        self.assertIsInstance(tracks, list)
        self.assertIsInstance(tracks[0], pylast.Track)
        self.assertEqual(len(tracks), 4)

    @handle_lastfm_exceptions
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
        self.assertTrue(tag1 == tag1)
        self.assertTrue(tag1 != tag2)
        self.assertEqual(url, "http://www.last.fm/tag/blues")

    @handle_lastfm_exceptions
    def test_tags_similar(self):
        # Arrange
        tag = self.network.get_tag("blues")

        # Act
        similar = tag.get_similar()

        # Assert
        self.skip_if_lastfm_api_broken(similar)
        found = False
        for tag in similar:
            if tag.name == "delta blues":
                found = True
                break
        self.assertTrue(found)

    @handle_lastfm_exceptions
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
        self.assertIn("http", image)
        self.assertGreater(playcount, 1)
        self.assertTrue(artist1 != artist2)
        self.assertEqual(name.lower(), name_cap.lower())
        self.assertEqual(url, "http://www.last.fm/music/radiohead")
        self.assertEqual(mbid, "a74b1b7f-71a5-4011-9441-d0b5e4122711")
        self.assertIsInstance(streamable, bool)

    @handle_lastfm_exceptions
    def test_events(self):
        # Arrange
        event_id_1 = 3162700  # Glasto 2013
        event_id_2 = 3478520  # Glasto 2014
        event1 = pylast.Event(event_id_1, self.network)
        event2 = pylast.Event(event_id_2, self.network)

        # Act
        text = str(event1)
        rep = repr(event1)
        title = event1.get_title()
        artists = event1.get_artists()
        start = event1.get_start_date()
        description = event1.get_description()
        review_count = event1.get_review_count()
        attendance_count = event1.get_attendance_count()

        # Assert
        self.assertIn("3162700", rep)
        self.assertIn("pylast.Event", rep)
        self.assertEqual(text, "Event #3162700")
        self.assertTrue(event1 != event2)
        self.assertIn("Glastonbury", title)
        found = False
        for artist in artists:
            if artist.name == "The Rolling Stones":
                found = True
                break
        self.assertTrue(found)
        self.assertIn("Wed, 26 Jun 2013", start)
        self.assertIn("astonishing bundle", description)
        self.assertGreater(review_count, 0)
        self.assertGreater(attendance_count, 100)

    @handle_lastfm_exceptions
    def test_countries(self):
        # Arrange
        country1 = pylast.Country("Italy", self.network)
        country2 = pylast.Country("Finland", self.network)

        # Act
        text = str(country1)
        rep = repr(country1)
        url = country1.get_url()

        # Assert
        self.assertIn("Italy", rep)
        self.assertIn("pylast.Country", rep)
        self.assertEqual(text, "Italy")
        self.assertTrue(country1 == country1)
        self.assertTrue(country1 != country2)
        self.assertEqual(url, "http://www.last.fm/place/italy")

    @handle_lastfm_exceptions
    def test_track_eq_none_is_false(self):
        # Arrange
        track1 = None
        track2 = pylast.Track("Test Artist", "Test Title", self.network)

        # Act / Assert
        self.assertFalse(track1 == track2)

    @handle_lastfm_exceptions
    def test_track_ne_none_is_true(self):
        # Arrange
        track1 = None
        track2 = pylast.Track("Test Artist", "Test Title", self.network)

        # Act / Assert
        self.assertTrue(track1 != track2)

    @handle_lastfm_exceptions
    def test_artist_eq_none_is_false(self):
        # Arrange
        artist1 = None
        artist2 = pylast.Artist("Test Artist", self.network)

        # Act / Assert
        self.assertFalse(artist1 == artist2)

    @handle_lastfm_exceptions
    def test_artist_ne_none_is_true(self):
        # Arrange
        artist1 = None
        artist2 = pylast.Artist("Test Artist", self.network)

        # Act / Assert
        self.assertTrue(artist1 != artist2)

    @handle_lastfm_exceptions
    def test_album_eq_none_is_false(self):
        # Arrange
        album1 = None
        album2 = pylast.Album("Test Artist", "Test Album", self.network)

        # Act / Assert
        self.assertFalse(album1 == album2)

    @handle_lastfm_exceptions
    def test_album_ne_none_is_true(self):
        # Arrange
        album1 = None
        album2 = pylast.Album("Test Artist", "Test Album", self.network)

        # Act / Assert
        self.assertTrue(album1 != album2)

    @handle_lastfm_exceptions
    def test_event_eq_none_is_false(self):
        # Arrange
        event1 = None
        event_id = 3478520  # Glasto 2014
        event2 = pylast.Event(event_id, self.network)

        # Act / Assert
        self.assertFalse(event1 == event2)

    @handle_lastfm_exceptions
    def test_event_ne_none_is_true(self):
        # Arrange
        event1 = None
        event_id = 3478520  # Glasto 2014
        event2 = pylast.Event(event_id, self.network)

        # Act / Assert
        self.assertTrue(event1 != event2)

    @handle_lastfm_exceptions
    def test_band_members(self):
        # Arrange
        artist = pylast.Artist("The Beatles", self.network)

        # Act
        band_members = artist.get_band_members()

        # Assert
        self.skip_if_lastfm_api_broken(band_members)
        self.assertGreaterEqual(len(band_members), 4)

    @handle_lastfm_exceptions
    def test_no_band_members(self):
        # Arrange
        artist = pylast.Artist("John Lennon", self.network)

        # Act
        band_members = artist.get_band_members()

        # Assert
        self.assertIsNone(band_members)

    @handle_lastfm_exceptions
    def test_get_recent_tracks_from_to(self):
        # Arrange
        lastfm_user = self.network.get_user("RJ")

        from datetime import datetime
        start = datetime(2011, 7, 21, 15, 10)
        end = datetime(2011, 7, 21, 15, 15)
        import calendar
        utc_start = calendar.timegm(start.utctimetuple())
        utc_end = calendar.timegm(end.utctimetuple())

        # Act
        tracks = lastfm_user.get_recent_tracks(time_from=utc_start,
                                               time_to=utc_end)

        # Assert
        self.assertEqual(len(tracks), 1)
        self.assertEqual(str(tracks[0].track.artist), "Johnny Cash")
        self.assertEqual(str(tracks[0].track.title), "Ring of Fire")

    @handle_lastfm_exceptions
    def test_artist_get_correction(self):
        # Arrange
        artist = pylast.Artist("guns and roses", self.network)

        # Act
        corrected_artist_name = artist.get_correction()

        # Assert
        self.assertEqual(corrected_artist_name, "Guns N' Roses")

    @handle_lastfm_exceptions
    def test_track_get_correction(self):
        # Arrange
        track = pylast.Track("Guns N' Roses", "mrbrownstone", self.network)

        # Act
        corrected_track_name = track.get_correction()

        # Assert
        self.assertEqual(corrected_track_name, "Mr. Brownstone")

    @handle_lastfm_exceptions
    def test_track_with_no_mbid(self):
        # Arrange
        track = pylast.Track("Static-X", "Set It Off", self.network)

        # Act
        mbid = track.get_mbid()

        # Assert
        self.assertEqual(mbid, None)


@flaky(max_runs=5, min_passes=1)
class TestPyLastWithLibreFm(unittest.TestCase):
    """Own class for Libre.fm because we don't need the Last.fm setUp"""

    def test_libre_fm(self):
        # Arrange
        secrets = load_secrets()
        username = secrets["username"]
        password_hash = secrets["password_hash"]

        # Act
        network = pylast.LibreFMNetwork(
            password_hash=password_hash, username=username)
        artist = network.get_artist("Radiohead")
        name = artist.get_name()

        # Assert
        self.assertEqual(name, "Radiohead")


if __name__ == '__main__':
    unittest.main(failfast=True)
