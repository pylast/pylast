#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
import os
from random import choice
import time
import unittest
import yaml # pip install pyyaml

import pylast

def load_secrets():
    secrets_file = "test_pylast.yaml"
    if os.path.isfile(secrets_file):
        with open(secrets_file, "r") as f: # see test_pylast_example.yaml
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

        API_KEY       = self.__class__.secrets["api_key"]
        API_SECRET    = self.__class__.secrets["api_secret"]

        self.network = pylast.LastFMNetwork(api_key = API_KEY, api_secret =
    API_SECRET, username = self.username, password_hash = password_hash)


    def test_scrobble(self):
        # Arrange
        artist = "Test Artist"
        title = "Test Title"
        timestamp = self.unix_timestamp()
        lastfm_user = self.network.get_user(self.username)

        # Act
        self.network.scrobble(artist = artist, title = title, timestamp = timestamp)

        # Assert
        last_scrobble = lastfm_user.get_recent_tracks(limit = 2)[0] # 2 to ignore now-playing
        self.assertEqual(str(last_scrobble.track.artist), str(artist))
        self.assertEqual(str(last_scrobble.track.title),  str(title))
        self.assertEqual(str(last_scrobble.timestamp),    str(timestamp))


    def test_unscrobble(self):
        # Arrange
        artist = "Test Artist 2"
        title = "Test Title 2"
        timestamp = self.unix_timestamp()
        library = pylast.Library(user = self.username, network = self.network)
        self.network.scrobble(artist = artist, title = title, timestamp = timestamp)
        lastfm_user = self.network.get_user(self.username)

        # Act
        library.remove_scrobble(artist = artist, title = title, timestamp = timestamp)

        # Assert
        last_scrobble = lastfm_user.get_recent_tracks(limit = 2)[0] # 2 to ignore now-playing
        self.assertNotEqual(str(last_scrobble.timestamp), str(timestamp))


    def test_add_album(self):
        # Arrange
        library = pylast.Library(user = self.username, network = self.network)
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
        library = pylast.Library(user = self.username, network = self.network)
        # Pick an artist with plenty of albums
        artist = self.network.get_top_artists()[0]
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
        library = pylast.Library(user = self.username, network = self.network)

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
        my_artist = choice(artists)
        library = pylast.Library(user = self.username, network = self.network)
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
        country_name = "United Kingom"

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
        lastfm_user = self.network.get_user("test_user") # currently no gender set

        # Act
        gender = lastfm_user.get_gender()

        # Assert
        self.assertIsNone(gender)


    def test_get_countryless_user(self):
        # Arrange
        lastfm_user = self.network.get_user("test_user") # currently no country set

        # Act
        country = lastfm_user.get_country()

        # Assert
        self.assertIsNone(country)


    def test_love(self):
        # Arrange
        artist = "Test Artist"
        title = "Test Title"
        track = pylast.Track(artist, title, self.network)
        lastfm_user = self.network.get_user(self.username)

        # Act
        track.love()

        # Assert
        loved = lastfm_user.get_loved_tracks(limit = 1)
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
        loved = lastfm_user.get_loved_tracks(limit = 1)
        if len(loved): # OK to be empty but if not:
            self.assertNotEqual(str(loved.track.artist), "Test Artist")
            self.assertNotEqual(str(loved.track.title), "Test Title")


    def test_get_100_albums(self):
        # Arrange
        library = pylast.Library(user = self.username, network = self.network)

        # Act
        albums = library.get_albums(limit = 100)

        # Assert
        self.assertGreaterEqual(len(albums), 0)


    def test_get_limitless_albums(self):
        # Arrange
        library = pylast.Library(user = self.username, network = self.network)

        # Act
        albums = library.get_albums(limit = None)

        # Assert
        self.assertGreaterEqual(len(albums), 0)


    def test_user_equals_none(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        value = (lastfm_user == None)

        # Assert
        self.assertFalse(value)


    def test_user_not_equal_to_none(self):
        # Arrange
        lastfm_user = self.network.get_user(self.username)

        # Act
        value = (lastfm_user != None)

        # Assert
        self.assertTrue(value)


    def test_now_playing_user_with_no_scrobbles(self):
        # Arrange
        user = self.network.get_user('test-account') # currently has no scrobbles

        # Act
        current_track = user.get_now_playing()

        # Assert
        self.assertIsNone(current_track)


    def test_love_limits(self):
        # Arrange
        user = self.network.get_user("test-user") # currently at least 23 loved tracks

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
        self.network.update_now_playing(artist = artist, title = title, album = album, track_number = track_number)

        # Assert
        current_track = lastfm_user.get_now_playing()
        self.assertIsNotNone(current_track)
        self.assertEqual(str(current_track.title), "Test Title")
        self.assertEqual(str(current_track.artist), "Test Artist")


    def test_libre_fm(self):
        # Arrange
        username      = self.__class__.secrets["username"]
        password_hash = self.__class__.secrets["password_hash"]

        # Act
        network = pylast.LibreFMNetwork(password_hash = password_hash, username = username)
        tags = network.get_top_tags(limit = 1)

        # Assert
        self.assertGreater(len(tags), 0)
        self.assertTrue(type(tags[0])  == pylast.TopItem)


    def test_album_tags_are_topitems(self):
        # Arrange
        albums = self.network.get_user('RJ').get_top_albums()

        # Act
        tags = albums[0].item.get_top_tags(limit = 1)

        # Assert
        self.assertGreater(len(tags), 0)
        self.assertTrue(type(tags[0])  == pylast.TopItem)


    def test_track_is_hashable(self):
        # TODO same for some other types
        # https://github.com/hugovk/pylast/issues/82
        # (passes in Python 2.7 but how about 3?)

        # Arrange
        lastfm_user = self.network.get_user(self.username)
        track = lastfm_user.get_recent_tracks(limit = 2)[0] # 2 to ignore now-playing
        tracks = set()

        # Act
        tracks.add(track)

        # Assert
        self.assertIsNotNone(track)
        self.assertEqual(len(tracks), 1)


if __name__ == '__main__':

    # For quick testing of a single-case (eg. test = "test_scrobble")
    test = ""

    if test is not None and len(test):
        suite = unittest.TestSuite()
        suite.addTest(TestPyLast(test))
        unittest.TextTestRunner().run(suite)
    else:
        unittest.main()

# End of file
