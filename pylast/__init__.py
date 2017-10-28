# -*- coding: utf-8 -*-
#
# pylast -
#     A Python interface to Last.fm and Libre.fm
#
# Copyright 2008-2010 Amr Hassan
# Copyright 2013-2017 hugovk
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# https://github.com/pylast/pylast

from xml.dom import minidom, Node
import collections
import hashlib
import shelve
import six
import ssl
import sys
import tempfile
import time
import xml.dom

__version__ = '2.0.0'
__author__ = 'Amr Hassan, hugovk, Mice Pápai'
__copyright__ = ('Copyright (C) 2008-2010 Amr Hassan, 2013-2017 hugovk, '
                 '2017 Mice Pápai')
__license__ = "apache2"
__email__ = 'amr.hassan@gmail.com'


if sys.version_info[0] == 3:
    import html.entities as htmlentitydefs
    from http.client import HTTPSConnection
    from urllib.parse import quote_plus as url_quote_plus

    unichr = chr

elif sys.version_info[0] == 2:
    import htmlentitydefs
    from httplib import HTTPSConnection
    from urllib import quote_plus as url_quote_plus

STATUS_INVALID_SERVICE = 2
STATUS_INVALID_METHOD = 3
STATUS_AUTH_FAILED = 4
STATUS_INVALID_FORMAT = 5
STATUS_INVALID_PARAMS = 6
STATUS_INVALID_RESOURCE = 7
STATUS_TOKEN_ERROR = 8
STATUS_INVALID_SK = 9
STATUS_INVALID_API_KEY = 10
STATUS_OFFLINE = 11
STATUS_SUBSCRIBERS_ONLY = 12
STATUS_INVALID_SIGNATURE = 13
STATUS_TOKEN_UNAUTHORIZED = 14
STATUS_TOKEN_EXPIRED = 15

PERIOD_OVERALL = 'overall'
PERIOD_7DAYS = '7day'
PERIOD_1MONTH = '1month'
PERIOD_3MONTHS = '3month'
PERIOD_6MONTHS = '6month'
PERIOD_12MONTHS = '12month'

DOMAIN_ENGLISH = 0
DOMAIN_GERMAN = 1
DOMAIN_SPANISH = 2
DOMAIN_FRENCH = 3
DOMAIN_ITALIAN = 4
DOMAIN_POLISH = 5
DOMAIN_PORTUGUESE = 6
DOMAIN_SWEDISH = 7
DOMAIN_TURKISH = 8
DOMAIN_RUSSIAN = 9
DOMAIN_JAPANESE = 10
DOMAIN_CHINESE = 11

COVER_SMALL = 0
COVER_MEDIUM = 1
COVER_LARGE = 2
COVER_EXTRA_LARGE = 3
COVER_MEGA = 4

IMAGES_ORDER_POPULARITY = "popularity"
IMAGES_ORDER_DATE = "dateadded"


SCROBBLE_SOURCE_USER = "P"
SCROBBLE_SOURCE_NON_PERSONALIZED_BROADCAST = "R"
SCROBBLE_SOURCE_PERSONALIZED_BROADCAST = "E"
SCROBBLE_SOURCE_LASTFM = "L"
SCROBBLE_SOURCE_UNKNOWN = "U"

SCROBBLE_MODE_PLAYED = ""
SCROBBLE_MODE_LOVED = "L"
SCROBBLE_MODE_BANNED = "B"
SCROBBLE_MODE_SKIPPED = "S"

# Python >3.4 and >2.7.9 has sane defaults
SSL_CONTEXT = ssl.create_default_context()


class _Network(object):
    """
    A music social network website such as Last.fm or
    one with a Last.fm-compatible API.
    """

    def __init__(
            self, name, homepage, ws_server, api_key, api_secret, session_key,
            username, password_hash, domain_names, urls, token=None):
        """
            name: the name of the network
            homepage: the homepage URL
            ws_server: the URL of the webservices server
            api_key: a provided API_KEY
            api_secret: a provided API_SECRET
            session_key: a generated session_key or None
            username: a username of a valid user
            password_hash: the output of pylast.md5(password) where password is
                the user's password
            domain_names: a dict mapping each DOMAIN_* value to a string domain
                name
            urls: a dict mapping types to URLs
            token: an authentication token to retrieve a session

            if username and password_hash were provided and not session_key,
            session_key will be generated automatically when needed.

            Either a valid session_key or a combination of username and
            password_hash must be present for scrobbling.

            You should use a preconfigured network object through a
            get_*_network(...) method instead of creating an object
            of this class, unless you know what you're doing.
        """

        self.name = name
        self.homepage = homepage
        self.ws_server = ws_server
        self.api_key = api_key
        self.api_secret = api_secret
        self.session_key = session_key
        self.username = username
        self.password_hash = password_hash
        self.domain_names = domain_names
        self.urls = urls

        self.cache_backend = None
        self.proxy_enabled = False
        self.proxy = None
        self.last_call_time = 0
        self.limit_rate = False

        # Load session_key from authentication token if provided
        if token and not self.session_key:
            sk_gen = SessionKeyGenerator(self)
            self.session_key = sk_gen.get_web_auth_session_key(
                url=None, token=token)

        # Generate a session_key if necessary
        if ((self.api_key and self.api_secret) and not self.session_key and
           (self.username and self.password_hash)):
            sk_gen = SessionKeyGenerator(self)
            self.session_key = sk_gen.get_session_key(
                self.username, self.password_hash)

    def __str__(self):
        return "%s Network" % self.name

    def get_artist(self, artist_name):
        """
            Return an Artist object
        """

        return Artist(artist_name, self)

    def get_track(self, artist, title):
        """
            Return a Track object
        """

        return Track(artist, title, self)

    def get_album(self, artist, title):
        """
            Return an Album object
        """

        return Album(artist, title, self)

    def get_authenticated_user(self):
        """
            Returns the authenticated user
        """

        return AuthenticatedUser(self)

    def get_country(self, country_name):
        """
            Returns a country object
        """

        return Country(country_name, self)

    def get_user(self, username):
        """
            Returns a user object
        """

        return User(username, self)

    def get_tag(self, name):
        """
            Returns a tag object
        """

        return Tag(name, self)

    def _get_language_domain(self, domain_language):
        """
            Returns the mapped domain name of the network to a DOMAIN_* value
        """

        if domain_language in self.domain_names:
            return self.domain_names[domain_language]

    def _get_url(self, domain, url_type):
        return "https://%s/%s" % (
            self._get_language_domain(domain), self.urls[url_type])

    def _get_ws_auth(self):
        """
            Returns an (API_KEY, API_SECRET, SESSION_KEY) tuple.
        """
        return self.api_key, self.api_secret, self.session_key

    def _delay_call(self):
        """
            Makes sure that web service calls are at least 0.2 seconds apart.
        """

        # Delay time in seconds from section 4.4 of https://www.last.fm/api/tos
        DELAY_TIME = 0.2
        now = time.time()

        time_since_last = now - self.last_call_time

        if time_since_last < DELAY_TIME:
            time.sleep(DELAY_TIME - time_since_last)

        self.last_call_time = now

    def get_top_artists(self, limit=None, cacheable=True):
        """Returns the most played artists as a sequence of TopItem objects."""

        params = {}
        if limit:
            params["limit"] = limit

        doc = _Request(self, "chart.getTopArtists", params).execute(cacheable)

        return _extract_top_artists(doc, self)

    def get_top_tracks(self, limit=None, cacheable=True):
        """Returns the most played tracks as a sequence of TopItem objects."""

        params = {}
        if limit:
            params["limit"] = limit

        doc = _Request(self, "chart.getTopTracks", params).execute(cacheable)

        seq = []
        for node in doc.getElementsByTagName("track"):
            title = _extract(node, "name")
            artist = _extract(node, "name", 1)
            track = Track(artist, title, self)
            weight = _number(_extract(node, "playcount"))
            seq.append(TopItem(track, weight))

        return seq

    def get_top_tags(self, limit=None, cacheable=True):
        """Returns the most used tags as a sequence of TopItem objects."""

        # Last.fm has no "limit" parameter for tag.getTopTags
        # so we need to get all (250) and then limit locally
        doc = _Request(self, "tag.getTopTags").execute(cacheable)

        seq = []
        for node in doc.getElementsByTagName("tag"):
            if limit and len(seq) >= limit:
                break
            tag = Tag(_extract(node, "name"), self)
            weight = _number(_extract(node, "count"))
            seq.append(TopItem(tag, weight))

        return seq

    def get_geo_top_artists(self, country, limit=None, cacheable=True):
        """Get the most popular artists on Last.fm by country.
        Parameters:
        country (Required) : A country name, as defined by the ISO 3166-1
            country names standard.
        limit (Optional) : The number of results to fetch per page.
            Defaults to 50.
        """
        params = {"country": country}

        if limit:
            params["limit"] = limit

        doc = _Request(self, "geo.getTopArtists", params).execute(cacheable)

        return _extract_top_artists(doc, self)

    def get_geo_top_tracks(
            self, country, location=None, limit=None, cacheable=True):
        """Get the most popular tracks on Last.fm last week by country.
        Parameters:
        country (Required) : A country name, as defined by the ISO 3166-1
            country names standard
        location (Optional) : A metro name, to fetch the charts for
            (must be within the country specified)
        limit (Optional) : The number of results to fetch per page.
            Defaults to 50.
        """
        params = {"country": country}

        if location:
            params["location"] = location
        if limit:
            params["limit"] = limit

        doc = _Request(self, "geo.getTopTracks", params).execute(cacheable)

        tracks = doc.getElementsByTagName("track")
        seq = []

        for track in tracks:
            title = _extract(track, "name")
            artist = _extract(track, "name", 1)
            listeners = _extract(track, "listeners")

            seq.append(TopItem(Track(artist, title, self), listeners))

        return seq

    def enable_proxy(self, host, port):
        """Enable a default web proxy"""

        self.proxy = [host, _number(port)]
        self.proxy_enabled = True

    def disable_proxy(self):
        """Disable using the web proxy"""

        self.proxy_enabled = False

    def is_proxy_enabled(self):
        """Returns True if a web proxy is enabled."""

        return self.proxy_enabled

    def _get_proxy(self):
        """Returns proxy details."""

        return self.proxy

    def enable_rate_limit(self):
        """Enables rate limiting for this network"""
        self.limit_rate = True

    def disable_rate_limit(self):
        """Disables rate limiting for this network"""
        self.limit_rate = False

    def is_rate_limited(self):
        """Return True if web service calls are rate limited"""
        return self.limit_rate

    def enable_caching(self, file_path=None):
        """Enables caching request-wide for all cacheable calls.

        * file_path: A file path for the backend storage file. If
        None set, a temp file would probably be created, according the backend.
        """

        if not file_path:
            file_path = tempfile.mktemp(prefix="pylast_tmp_")

        self.cache_backend = _ShelfCacheBackend(file_path)

    def disable_caching(self):
        """Disables all caching features."""

        self.cache_backend = None

    def is_caching_enabled(self):
        """Returns True if caching is enabled."""

        return not (self.cache_backend is None)

    def _get_cache_backend(self):

        return self.cache_backend

    def search_for_album(self, album_name):
        """Searches for an album by its name. Returns a AlbumSearch object.
        Use get_next_page() to retrieve sequences of results."""

        return AlbumSearch(album_name, self)

    def search_for_artist(self, artist_name):
        """Searches of an artist by its name. Returns a ArtistSearch object.
        Use get_next_page() to retrieve sequences of results."""

        return ArtistSearch(artist_name, self)

    def search_for_track(self, artist_name, track_name):
        """Searches of a track by its name and its artist. Set artist to an
        empty string if not available.
        Returns a TrackSearch object.
        Use get_next_page() to retrieve sequences of results."""

        return TrackSearch(artist_name, track_name, self)

    def get_track_by_mbid(self, mbid):
        """Looks up a track by its MusicBrainz ID"""

        params = {"mbid": mbid}

        doc = _Request(self, "track.getInfo", params).execute(True)

        return Track(_extract(doc, "name", 1), _extract(doc, "name"), self)

    def get_artist_by_mbid(self, mbid):
        """Looks up an artist by its MusicBrainz ID"""

        params = {"mbid": mbid}

        doc = _Request(self, "artist.getInfo", params).execute(True)

        return Artist(_extract(doc, "name"), self)

    def get_album_by_mbid(self, mbid):
        """Looks up an album by its MusicBrainz ID"""

        params = {"mbid": mbid}

        doc = _Request(self, "album.getInfo", params).execute(True)

        return Album(_extract(doc, "artist"), _extract(doc, "name"), self)

    def update_now_playing(
            self, artist, title, album=None, album_artist=None,
            duration=None, track_number=None, mbid=None, context=None):
        """
        Used to notify Last.fm that a user has started listening to a track.

            Parameters:
                artist (Required) : The artist name
                title (Required) : The track title
                album (Optional) : The album name.
                album_artist (Optional) : The album artist - if this differs
                    from the track artist.
                duration (Optional) : The length of the track in seconds.
                track_number (Optional) : The track number of the track on the
                    album.
                mbid (Optional) : The MusicBrainz Track ID.
                context (Optional) : Sub-client version
                    (not public, only enabled for certain API keys)
        """

        params = {"track": title, "artist": artist}

        if album:
            params["album"] = album
        if album_artist:
            params["albumArtist"] = album_artist
        if context:
            params["context"] = context
        if track_number:
            params["trackNumber"] = track_number
        if mbid:
            params["mbid"] = mbid
        if duration:
            params["duration"] = duration

        _Request(self, "track.updateNowPlaying", params).execute()

    def scrobble(
            self, artist, title, timestamp, album=None, album_artist=None,
            track_number=None, duration=None, stream_id=None, context=None,
            mbid=None):

        """Used to add a track-play to a user's profile.

        Parameters:
            artist (Required) : The artist name.
            title (Required) : The track name.
            timestamp (Required) : The time the track started playing, in UNIX
                timestamp format (integer number of seconds since 00:00:00,
                January 1st 1970 UTC). This must be in the UTC time zone.
            album (Optional) : The album name.
            album_artist (Optional) : The album artist - if this differs from
                the track artist.
            context (Optional) : Sub-client version (not public, only enabled
                for certain API keys)
            stream_id (Optional) : The stream id for this track received from
                the radio.getPlaylist service.
            track_number (Optional) : The track number of the track on the
                album.
            mbid (Optional) : The MusicBrainz Track ID.
            duration (Optional) : The length of the track in seconds.
        """

        return self.scrobble_many(({
            "artist": artist, "title": title, "timestamp": timestamp,
            "album": album, "album_artist": album_artist,
            "track_number": track_number, "duration": duration,
            "stream_id": stream_id, "context": context, "mbid": mbid},))

    def scrobble_many(self, tracks):
        """
        Used to scrobble a batch of tracks at once. The parameter tracks is a
        sequence of dicts per track containing the keyword arguments as if
        passed to the scrobble() method.
        """

        tracks_to_scrobble = tracks[:50]
        if len(tracks) > 50:
            remaining_tracks = tracks[50:]
        else:
            remaining_tracks = None

        params = {}
        for i in range(len(tracks_to_scrobble)):

            params["artist[%d]" % i] = tracks_to_scrobble[i]["artist"]
            params["track[%d]" % i] = tracks_to_scrobble[i]["title"]

            additional_args = (
                "timestamp", "album", "album_artist", "context",
                "stream_id", "track_number", "mbid", "duration")
            args_map_to = {  # so friggin lazy
                "album_artist": "albumArtist",
                "track_number": "trackNumber",
                "stream_id": "streamID"}

            for arg in additional_args:

                if arg in tracks_to_scrobble[i] and tracks_to_scrobble[i][arg]:
                    if arg in args_map_to:
                        maps_to = args_map_to[arg]
                    else:
                        maps_to = arg

                    params[
                        "%s[%d]" % (maps_to, i)] = tracks_to_scrobble[i][arg]

        _Request(self, "track.scrobble", params).execute()

        if remaining_tracks:
            self.scrobble_many(remaining_tracks)


class LastFMNetwork(_Network):

    """A Last.fm network object

    api_key: a provided API_KEY
    api_secret: a provided API_SECRET
    session_key: a generated session_key or None
    username: a username of a valid user
    password_hash: the output of pylast.md5(password) where password is the
        user's password

    if username and password_hash were provided and not session_key,
    session_key will be generated automatically when needed.

    Either a valid session_key or a combination of username and password_hash
    must be present for scrobbling.

    Most read-only webservices only require an api_key and an api_secret, see
    about obtaining them from:
    https://www.last.fm/api/account
    """

    def __init__(
            self, api_key="", api_secret="", session_key="", username="",
            password_hash="", token=""):
        _Network.__init__(
            self,
            name="Last.fm",
            homepage="https://www.last.fm",
            ws_server=("ws.audioscrobbler.com", "/2.0/"),
            api_key=api_key,
            api_secret=api_secret,
            session_key=session_key,
            username=username,
            password_hash=password_hash,
            token=token,
            domain_names={
                DOMAIN_ENGLISH: 'www.last.fm',
                DOMAIN_GERMAN: 'www.last.fm/de',
                DOMAIN_SPANISH: 'www.last.fm/es',
                DOMAIN_FRENCH: 'www.last.fm/fr',
                DOMAIN_ITALIAN: 'www.last.fm/it',
                DOMAIN_POLISH: 'www.last.fm/pl',
                DOMAIN_PORTUGUESE: 'www.last.fm/pt',
                DOMAIN_SWEDISH: 'www.last.fm/sv',
                DOMAIN_TURKISH: 'www.last.fm/tr',
                DOMAIN_RUSSIAN: 'www.last.fm/ru',
                DOMAIN_JAPANESE: 'www.last.fm/ja',
                DOMAIN_CHINESE: 'www.last.fm/zh',
            },
            urls={
                "album": "music/%(artist)s/%(album)s",
                "artist": "music/%(artist)s",
                "country": "place/%(country_name)s",
                "tag": "tag/%(name)s",
                "track": "music/%(artist)s/_/%(title)s",
                "user": "user/%(name)s",
            }
        )

    def __repr__(self):
        return "pylast.LastFMNetwork(%s)" % (", ".join(
            ("'%s'" % self.api_key,
             "'%s'" % self.api_secret,
             "'%s'" % self.session_key,
             "'%s'" % self.username,
             "'%s'" % self.password_hash)))


class LibreFMNetwork(_Network):
    """
    A preconfigured _Network object for Libre.fm

    api_key: a provided API_KEY
    api_secret: a provided API_SECRET
    session_key: a generated session_key or None
    username: a username of a valid user
    password_hash: the output of pylast.md5(password) where password is the
        user's password

    if username and password_hash were provided and not session_key,
    session_key will be generated automatically when needed.
    """

    def __init__(
            self, api_key="", api_secret="", session_key="", username="",
            password_hash=""):

        _Network.__init__(
            self,
            name="Libre.fm",
            homepage="https://libre.fm",
            ws_server=("libre.fm", "/2.0/"),
            api_key=api_key,
            api_secret=api_secret,
            session_key=session_key,
            username=username,
            password_hash=password_hash,
            domain_names={
                DOMAIN_ENGLISH: "libre.fm",
                DOMAIN_GERMAN: "libre.fm",
                DOMAIN_SPANISH: "libre.fm",
                DOMAIN_FRENCH: "libre.fm",
                DOMAIN_ITALIAN: "libre.fm",
                DOMAIN_POLISH: "libre.fm",
                DOMAIN_PORTUGUESE: "libre.fm",
                DOMAIN_SWEDISH: "libre.fm",
                DOMAIN_TURKISH: "libre.fm",
                DOMAIN_RUSSIAN: "libre.fm",
                DOMAIN_JAPANESE: "libre.fm",
                DOMAIN_CHINESE: "libre.fm",
            },
            urls={
                "album": "artist/%(artist)s/album/%(album)s",
                "artist": "artist/%(artist)s",
                "country": "place/%(country_name)s",
                "tag": "tag/%(name)s",
                "track": "music/%(artist)s/_/%(title)s",
                "user": "user/%(name)s",
            }
        )

    def __repr__(self):
        return "pylast.LibreFMNetwork(%s)" % (", ".join(
            ("'%s'" % self.api_key,
             "'%s'" % self.api_secret,
             "'%s'" % self.session_key,
             "'%s'" % self.username,
             "'%s'" % self.password_hash)))


class _ShelfCacheBackend(object):
    """Used as a backend for caching cacheable requests."""
    def __init__(self, file_path=None):
        self.shelf = shelve.open(file_path)

    def __iter__(self):
        return iter(self.shelf.keys())

    def get_xml(self, key):
        return self.shelf[key]

    def set_xml(self, key, xml_string):
        self.shelf[key] = xml_string


class _Request(object):
    """Representing an abstract web service operation."""

    def __init__(self, network, method_name, params={}):

        self.network = network
        self.params = {}

        for key in params:
            self.params[key] = _unicode(params[key])

        (self.api_key, self.api_secret, self.session_key) = \
            network._get_ws_auth()

        self.params["api_key"] = self.api_key
        self.params["method"] = method_name

        if network.is_caching_enabled():
            self.cache = network._get_cache_backend()

        if self.session_key:
            self.params["sk"] = self.session_key
            self.sign_it()

    def sign_it(self):
        """Sign this request."""

        if "api_sig" not in self.params.keys():
            self.params['api_sig'] = self._get_signature()

    def _get_signature(self):
        """
        Returns a 32-character hexadecimal md5 hash of the signature string.
        """

        keys = list(self.params.keys())

        keys.sort()

        string = ""

        for name in keys:
            string += name
            string += self.params[name]

        string += self.api_secret

        return md5(string)

    def _get_cache_key(self):
        """
        The cache key is a string of concatenated sorted names and values.
        """

        keys = list(self.params.keys())
        keys.sort()

        cache_key = str()

        for key in keys:
            if key != "api_sig" and key != "api_key" and key != "sk":
                cache_key += key + self.params[key]

        return hashlib.sha1(cache_key.encode("utf-8")).hexdigest()

    def _get_cached_response(self):
        """Returns a file object of the cached response."""

        if not self._is_cached():
            response = self._download_response()
            self.cache.set_xml(self._get_cache_key(), response)

        return self.cache.get_xml(self._get_cache_key())

    def _is_cached(self):
        """Returns True if the request is already in cache."""

        return self._get_cache_key() in self.cache

    def _download_response(self):
        """Returns a response body string from the server."""

        if self.network.limit_rate:
            self.network._delay_call()

        data = []
        for name in self.params.keys():
            data.append('='.join((
                name, url_quote_plus(_string(self.params[name])))))
        data = '&'.join(data)

        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            'Accept-Charset': 'utf-8',
            'User-Agent': "pylast" + '/' + __version__
        }

        (HOST_NAME, HOST_SUBDIR) = self.network.ws_server

        if self.network.is_proxy_enabled():
            conn = HTTPSConnection(
                context=SSL_CONTEXT,
                host=self.network._get_proxy()[0],
                port=self.network._get_proxy()[1])

            try:
                conn.request(
                    method='POST', url="https://" + HOST_NAME + HOST_SUBDIR,
                    body=data, headers=headers)
            except Exception as e:
                raise NetworkError(self.network, e)

        else:
            conn = HTTPSConnection(context=SSL_CONTEXT, host=HOST_NAME)

            try:
                conn.request(
                    method='POST', url=HOST_SUBDIR, body=data, headers=headers)
            except Exception as e:
                raise NetworkError(self.network, e)

        try:
            response_text = _unicode(conn.getresponse().read())
        except Exception as e:
            raise MalformedResponseError(self.network, e)

        self._check_response_for_errors(response_text)
        conn.close()
        return response_text

    def execute(self, cacheable=False):
        """Returns the XML DOM response of the POST Request from the server"""

        if self.network.is_caching_enabled() and cacheable:
            response = self._get_cached_response()
        else:
            response = self._download_response()

        return minidom.parseString(_string(response).replace(
            "opensearch:", ""))

    def _check_response_for_errors(self, response):
        """Checks the response for errors and raises one if any exists."""

        try:
            doc = minidom.parseString(_string(response).replace(
                "opensearch:", ""))
        except Exception as e:
            raise MalformedResponseError(self.network, e)

        e = doc.getElementsByTagName('lfm')[0]

        if e.getAttribute('status') != "ok":
            e = doc.getElementsByTagName('error')[0]
            status = e.getAttribute('code')
            details = e.firstChild.data.strip()
            raise WSError(self.network, status, details)


class SessionKeyGenerator(object):
    """Methods of generating a session key:
    1) Web Authentication:
        a. network = get_*_network(API_KEY, API_SECRET)
        b. sg = SessionKeyGenerator(network)
        c. url = sg.get_web_auth_url()
        d. Ask the user to open the url and authorize you, and wait for it.
        e. session_key = sg.get_web_auth_session_key(url)
    2) Username and Password Authentication:
        a. network = get_*_network(API_KEY, API_SECRET)
        b. username = raw_input("Please enter your username: ")
        c. password_hash = pylast.md5(raw_input("Please enter your password: ")
        d. session_key = SessionKeyGenerator(network).get_session_key(username,
            password_hash)

    A session key's lifetime is infinite, unless the user revokes the rights
    of the given API Key.

    If you create a Network object with just a API_KEY and API_SECRET and a
    username and a password_hash, a SESSION_KEY will be automatically generated
    for that network and stored in it so you don't have to do this manually,
    unless you want to.
    """

    def __init__(self, network):
        self.network = network
        self.web_auth_tokens = {}

    def _get_web_auth_token(self):
        """
        Retrieves a token from the network for web authentication.
        The token then has to be authorized from getAuthURL before creating
        session.
        """

        request = _Request(self.network, 'auth.getToken')

        # default action is that a request is signed only when
        # a session key is provided.
        request.sign_it()

        doc = request.execute()

        e = doc.getElementsByTagName('token')[0]
        return e.firstChild.data

    def get_web_auth_url(self):
        """
        The user must open this page, and you first, then
        call get_web_auth_session_key(url) after that.
        """

        token = self._get_web_auth_token()

        url = '%(homepage)s/api/auth/?api_key=%(api)s&token=%(token)s' % \
            {"homepage": self.network.homepage,
             "api": self.network.api_key, "token": token}

        self.web_auth_tokens[url] = token

        return url

    def get_web_auth_session_key(self, url, token=""):
        """
        Retrieves the session key of a web authorization process by its url.
        """

        if url in self.web_auth_tokens.keys():
            token = self.web_auth_tokens[url]
        else:
            # This will raise a WSError if token is blank or unauthorized
            token = token

        request = _Request(self.network, 'auth.getSession', {'token': token})

        # default action is that a request is signed only when
        # a session key is provided.
        request.sign_it()

        doc = request.execute()

        return doc.getElementsByTagName('key')[0].firstChild.data

    def get_session_key(self, username, password_hash):
        """
        Retrieve a session key with a username and a md5 hash of the user's
        password.
        """

        params = {
            "username": username, "authToken": md5(username + password_hash)}
        request = _Request(self.network, "auth.getMobileSession", params)

        # default action is that a request is signed only when
        # a session key is provided.
        request.sign_it()

        doc = request.execute()

        return _extract(doc, "key")


TopItem = collections.namedtuple("TopItem", ["item", "weight"])
SimilarItem = collections.namedtuple("SimilarItem", ["item", "match"])
LibraryItem = collections.namedtuple(
    "LibraryItem", ["item", "playcount", "tagcount"])
PlayedTrack = collections.namedtuple(
    "PlayedTrack", ["track", "album", "playback_date", "timestamp"])
LovedTrack = collections.namedtuple(
    "LovedTrack", ["track", "date", "timestamp"])
ImageSizes = collections.namedtuple(
    "ImageSizes", [
        "original", "large", "largesquare", "medium", "small", "extralarge"])
Image = collections.namedtuple(
    "Image", [
        "title", "url", "dateadded", "format", "owner", "sizes", "votes"])


def _string_output(func):
    def r(*args):
        return _string(func(*args))

    return r


class _BaseObject(object):
    """An abstract webservices object."""

    network = None

    def __init__(self, network, ws_prefix):
        self.network = network
        self.ws_prefix = ws_prefix

    def _request(self, method_name, cacheable=False, params=None):
        if not params:
            params = self._get_params()

        return _Request(self.network, method_name, params).execute(cacheable)

    def _get_params(self):
        """Returns the most common set of parameters between all objects."""

        return {}

    def __hash__(self):
        # Convert any ints (or whatever) into strings
        values = map(six.text_type, self._get_params().values())

        return hash(self.network) + hash(six.text_type(type(self)) + "".join(
            list(self._get_params().keys()) + list(values)
        ).lower())

    def _extract_cdata_from_request(self, method_name, tag_name, params):
        doc = self._request(method_name, True, params)

        return doc.getElementsByTagName(
            tag_name)[0].firstChild.wholeText.strip()

    def _get_things(
            self, method, thing, thing_type, params=None, cacheable=True):
        """Returns a list of the most played thing_types by this thing."""

        doc = self._request(
            self.ws_prefix + "." + method, cacheable, params)

        seq = []
        for node in doc.getElementsByTagName(thing):
            title = _extract(node, "name")
            artist = _extract(node, "name", 1)
            playcount = _number(_extract(node, "playcount"))

            seq.append(TopItem(
                thing_type(artist, title, self.network), playcount))

        return seq

    def get_wiki_published_date(self):
        """
        Returns the summary of the wiki.
        Only for Album/Track.
        """
        return self.get_wiki("published")

    def get_wiki_summary(self):
        """
        Returns the summary of the wiki.
        Only for Album/Track.
        """
        return self.get_wiki("summary")

    def get_wiki_content(self):
        """
        Returns the summary of the wiki.
        Only for Album/Track.
        """
        return self.get_wiki("content")

    def get_wiki(self, section):
        """
        Returns a section of the wiki.
        Only for Album/Track.
        section can be "content", "summary" or
            "published" (for published date)
        """

        doc = self._request(self.ws_prefix + ".getInfo", True)

        if len(doc.getElementsByTagName("wiki")) == 0:
            return

        node = doc.getElementsByTagName("wiki")[0]

        return _extract(node, section)


class _Chartable(object):
    """Common functions for classes with charts."""

    def __init__(self, ws_prefix):
        self.ws_prefix = ws_prefix  # TODO move to _BaseObject?

    def get_weekly_chart_dates(self):
        """Returns a list of From and To tuples for the available charts."""

        doc = self._request(self.ws_prefix + ".getWeeklyChartList", True)

        seq = []
        for node in doc.getElementsByTagName("chart"):
            seq.append((node.getAttribute("from"), node.getAttribute("to")))

        return seq

    def get_weekly_album_charts(self, from_date=None, to_date=None):
        """
        Returns the weekly album charts for the week starting from the
        from_date value to the to_date value.
        Only for User.
        """
        return self.get_weekly_charts("album", from_date, to_date)

    def get_weekly_artist_charts(self, from_date=None, to_date=None):
        """
        Returns the weekly artist charts for the week starting from the
        from_date value to the to_date value.
        Only for Tag or User.
        """
        return self.get_weekly_charts("artist", from_date, to_date)

    def get_weekly_track_charts(self, from_date=None, to_date=None):
        """
        Returns the weekly track charts for the week starting from the
        from_date value to the to_date value.
        Only for User.
        """
        return self.get_weekly_charts("track", from_date, to_date)

    def get_weekly_charts(self, chart_kind, from_date=None, to_date=None):
        """
        Returns the weekly charts for the week starting from the
        from_date value to the to_date value.
        chart_kind should be one of "album", "artist" or "track"
        """
        method = ".getWeekly" + chart_kind.title() + "Chart"
        chart_type = eval(chart_kind.title())  # string to type

        params = self._get_params()
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date

        doc = self._request(
            self.ws_prefix + method, True, params)

        seq = []
        for node in doc.getElementsByTagName(chart_kind.lower()):
            item = chart_type(
                _extract(node, "artist"), _extract(node, "name"), self.network)
            weight = _number(_extract(node, "playcount"))
            seq.append(TopItem(item, weight))

        return seq


class _Taggable(object):
    """Common functions for classes with tags."""

    def __init__(self, ws_prefix):
        self.ws_prefix = ws_prefix  # TODO move to _BaseObject

    def add_tags(self, tags):
        """Adds one or several tags.
        * tags: A sequence of tag names or Tag objects.
        """

        for tag in tags:
            self.add_tag(tag)

    def add_tag(self, tag):
        """Adds one tag.
        * tag: a tag name or a Tag object.
        """

        if isinstance(tag, Tag):
            tag = tag.get_name()

        params = self._get_params()
        params['tags'] = tag

        self._request(self.ws_prefix + '.addTags', False, params)

    def remove_tag(self, tag):
        """Remove a user's tag from this object."""

        if isinstance(tag, Tag):
            tag = tag.get_name()

        params = self._get_params()
        params['tag'] = tag

        self._request(self.ws_prefix + '.removeTag', False, params)

    def get_tags(self):
        """Returns a list of the tags set by the user to this object."""

        # Uncacheable because it can be dynamically changed by the user.
        params = self._get_params()

        doc = self._request(self.ws_prefix + '.getTags', False, params)
        tag_names = _extract_all(doc, 'name')
        tags = []
        for tag in tag_names:
            tags.append(Tag(tag, self.network))

        return tags

    def remove_tags(self, tags):
        """Removes one or several tags from this object.
        * tags: a sequence of tag names or Tag objects.
        """

        for tag in tags:
            self.remove_tag(tag)

    def clear_tags(self):
        """Clears all the user-set tags. """

        self.remove_tags(*(self.get_tags()))

    def set_tags(self, tags):
        """Sets this object's tags to only those tags.
        * tags: a sequence of tag names or Tag objects.
        """

        c_old_tags = []
        old_tags = []
        c_new_tags = []
        new_tags = []

        to_remove = []
        to_add = []

        tags_on_server = self.get_tags()

        for tag in tags_on_server:
            c_old_tags.append(tag.get_name().lower())
            old_tags.append(tag.get_name())

        for tag in tags:
            c_new_tags.append(tag.lower())
            new_tags.append(tag)

        for i in range(0, len(old_tags)):
            if not c_old_tags[i] in c_new_tags:
                to_remove.append(old_tags[i])

        for i in range(0, len(new_tags)):
            if not c_new_tags[i] in c_old_tags:
                to_add.append(new_tags[i])

        self.remove_tags(to_remove)
        self.add_tags(to_add)

    def get_top_tags(self, limit=None):
        """Returns a list of the most frequently used Tags on this object."""

        doc = self._request(self.ws_prefix + '.getTopTags', True)

        elements = doc.getElementsByTagName('tag')
        seq = []

        for element in elements:
            tag_name = _extract(element, 'name')
            tagcount = _extract(element, 'count')

            seq.append(TopItem(Tag(tag_name, self.network), tagcount))

        if limit:
            seq = seq[:limit]

        return seq


class WSError(Exception):
    """Exception related to the Network web service"""

    def __init__(self, network, status, details):
        self.status = status
        self.details = details
        self.network = network

    @_string_output
    def __str__(self):
        return self.details

    def get_id(self):
        """Returns the exception ID, from one of the following:
            STATUS_INVALID_SERVICE = 2
            STATUS_INVALID_METHOD = 3
            STATUS_AUTH_FAILED = 4
            STATUS_INVALID_FORMAT = 5
            STATUS_INVALID_PARAMS = 6
            STATUS_INVALID_RESOURCE = 7
            STATUS_TOKEN_ERROR = 8
            STATUS_INVALID_SK = 9
            STATUS_INVALID_API_KEY = 10
            STATUS_OFFLINE = 11
            STATUS_SUBSCRIBERS_ONLY = 12
            STATUS_TOKEN_UNAUTHORIZED = 14
            STATUS_TOKEN_EXPIRED = 15
        """

        return self.status


class MalformedResponseError(Exception):
    """Exception conveying a malformed response from the music network."""

    def __init__(self, network, underlying_error):
        self.network = network
        self.underlying_error = underlying_error

    def __str__(self):
        return "Malformed response from {}. Underlying error: {}".format(
            self.network.name, str(self.underlying_error))


class NetworkError(Exception):
    """Exception conveying a problem in sending a request to Last.fm"""

    def __init__(self, network, underlying_error):
        self.network = network
        self.underlying_error = underlying_error

    def __str__(self):
        return "NetworkError: %s" % str(self.underlying_error)


class _Opus(_BaseObject, _Taggable):
    """An album or track."""

    artist = None
    title = None
    username = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, artist, title, network, ws_prefix, username=None):
        """
        Create an opus instance.
        # Parameters:
            * artist: An artist name or an Artist object.
            * title: The album or track title.
            * ws_prefix: 'album' or 'track'
        """

        _BaseObject.__init__(self, network, ws_prefix)
        _Taggable.__init__(self, ws_prefix)

        if isinstance(artist, Artist):
            self.artist = artist
        else:
            self.artist = Artist(artist, self.network)

        self.title = title
        self.username = username

    def __repr__(self):
        return "pylast.%s(%s, %s, %s)" % (
            self.ws_prefix.title(), repr(self.artist.name),
            repr(self.title), repr(self.network))

    @_string_output
    def __str__(self):
        return _unicode("%s - %s") % (
            self.get_artist().get_name(), self.get_title())

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        a = self.get_title().lower()
        b = other.get_title().lower()
        c = self.get_artist().get_name().lower()
        d = other.get_artist().get_name().lower()
        return (a == b) and (c == d)

    def __ne__(self, other):
        return not self.__eq__(other)

    def _get_params(self):
        return {
            'artist': self.get_artist().get_name(),
            self.ws_prefix: self.get_title()}

    def get_artist(self):
        """Returns the associated Artist object."""

        return self.artist

    def get_title(self, properly_capitalized=False):
        """Returns the artist or track title."""
        if properly_capitalized:
            self.title = _extract(
                self._request(self.ws_prefix + ".getInfo", True), "name")

        return self.title

    def get_name(self, properly_capitalized=False):
        """Returns the album or track title (alias to get_title())."""

        return self.get_title(properly_capitalized)

    def get_playcount(self):
        """Returns the number of plays on the network"""

        return _number(_extract(
            self._request(
                self.ws_prefix + ".getInfo", cacheable=True), "playcount"))

    def get_userplaycount(self):
        """Returns the number of plays by a given username"""

        if not self.username:
            return

        params = self._get_params()
        params['username'] = self.username

        doc = self._request(self.ws_prefix + ".getInfo", True, params)
        return _number(_extract(doc, "userplaycount"))

    def get_listener_count(self):
        """Returns the number of listeners on the network"""

        return _number(_extract(
            self._request(
                self.ws_prefix + ".getInfo", cacheable=True), "listeners"))

    def get_mbid(self):
        """Returns the MusicBrainz ID of the album or track."""

        doc = self._request(self.ws_prefix + ".getInfo", cacheable=True)

        try:
            lfm = doc.getElementsByTagName('lfm')[0]
            opus = next(self._get_children_by_tag_name(lfm, self.ws_prefix))
            mbid = next(self._get_children_by_tag_name(opus, "mbid"))
            return mbid.firstChild.nodeValue
        except StopIteration:
            return None

    def _get_children_by_tag_name(self, node, tag_name):
        for child in node.childNodes:
            if (child.nodeType == child.ELEMENT_NODE and
               (tag_name == '*' or child.tagName == tag_name)):
                yield child


class Album(_Opus):
    """An album."""

    __hash__ = _Opus.__hash__

    def __init__(self, artist, title, network, username=None):
        super(Album, self).__init__(artist, title, network, "album", username)

    def get_cover_image(self, size=COVER_EXTRA_LARGE):
        """
        Returns a uri to the cover image
        size can be one of:
            COVER_EXTRA_LARGE
            COVER_LARGE
            COVER_MEDIUM
            COVER_SMALL
        """

        return _extract_all(
            self._request(
                self.ws_prefix + ".getInfo", cacheable=True), 'image')[size]

    def get_tracks(self):
        """Returns the list of Tracks on this album."""

        return _extract_tracks(
            self._request(
                self.ws_prefix + ".getInfo", cacheable=True), self.network)

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the URL of the album or track page on the network.
        # Parameters:
        * domain_name str: The network's language domain. Possible values:
            o DOMAIN_ENGLISH
            o DOMAIN_GERMAN
            o DOMAIN_SPANISH
            o DOMAIN_FRENCH
            o DOMAIN_ITALIAN
            o DOMAIN_POLISH
            o DOMAIN_PORTUGUESE
            o DOMAIN_SWEDISH
            o DOMAIN_TURKISH
            o DOMAIN_RUSSIAN
            o DOMAIN_JAPANESE
            o DOMAIN_CHINESE
        """

        artist = _url_safe(self.get_artist().get_name())
        title = _url_safe(self.get_title())

        return self.network._get_url(
            domain_name, self.ws_prefix) % {
            'artist': artist, 'album': title}


class Artist(_BaseObject, _Taggable):
    """An artist."""

    name = None
    username = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, name, network, username=None):
        """Create an artist object.
        # Parameters:
            * name str: The artist's name.
        """

        _BaseObject.__init__(self, network, 'artist')
        _Taggable.__init__(self, 'artist')

        self.name = name
        self.username = username

    def __repr__(self):
        return "pylast.Artist(%s, %s)" % (
            repr(self.get_name()), repr(self.network))

    def __unicode__(self):
        return six.text_type(self.get_name())

    @_string_output
    def __str__(self):
        return self.__unicode__()

    def __eq__(self, other):
        if type(self) is type(other):
            return self.get_name().lower() == other.get_name().lower()
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def _get_params(self):
        return {self.ws_prefix: self.get_name()}

    def get_name(self, properly_capitalized=False):
        """Returns the name of the artist.
        If properly_capitalized was asserted then the name would be downloaded
        overwriting the given one."""

        if properly_capitalized:
            self.name = _extract(
                self._request(self.ws_prefix + ".getInfo", True), "name")

        return self.name

    def get_correction(self):
        """Returns the corrected artist name."""

        return _extract(
            self._request(self.ws_prefix + ".getCorrection"), "name")

    def get_cover_image(self, size=COVER_MEGA):
        """
        Returns a uri to the cover image
        size can be one of:
            COVER_MEGA
            COVER_EXTRA_LARGE
            COVER_LARGE
            COVER_MEDIUM
            COVER_SMALL
        """

        return _extract_all(
            self._request(self.ws_prefix + ".getInfo", True), "image")[size]

    def get_playcount(self):
        """Returns the number of plays on the network."""

        return _number(_extract(
            self._request(self.ws_prefix + ".getInfo", True), "playcount"))

    def get_userplaycount(self):
        """Returns the number of plays by a given username"""

        if not self.username:
            return

        params = self._get_params()
        params['username'] = self.username

        doc = self._request(self.ws_prefix + ".getInfo", True, params)
        return _number(_extract(doc, "userplaycount"))

    def get_mbid(self):
        """Returns the MusicBrainz ID of this artist."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _extract(doc, "mbid")

    def get_listener_count(self):
        """Returns the number of listeners on the network."""

        if hasattr(self, "listener_count"):
            return self.listener_count
        else:
            self.listener_count = _number(_extract(
                self._request(self.ws_prefix + ".getInfo", True), "listeners"))
            return self.listener_count

    def is_streamable(self):
        """Returns True if the artist is streamable."""

        return bool(_number(_extract(
            self._request(self.ws_prefix + ".getInfo", True), "streamable")))

    def get_bio(self, section, language=None):
        """
        Returns a section of the bio.
        section can be "content", "summary" or
            "published" (for published date)
        """
        if language:
            params = self._get_params()
            params["lang"] = language
        else:
            params = None

        return self._extract_cdata_from_request(
            self.ws_prefix + ".getInfo", section, params)

    def get_bio_published_date(self):
        """Returns the date on which the artist's biography was published."""
        return self.get_bio("published")

    def get_bio_summary(self, language=None):
        """Returns the summary of the artist's biography."""
        return self.get_bio("summary", language)

    def get_bio_content(self, language=None):
        """Returns the content of the artist's biography."""
        return self.get_bio("content", language)

    def get_similar(self, limit=None):
        """Returns the similar artists on the network."""

        params = self._get_params()
        if limit:
            params['limit'] = limit

        doc = self._request(self.ws_prefix + '.getSimilar', True, params)

        names = _extract_all(doc, "name")
        matches = _extract_all(doc, "match")

        artists = []
        for i in range(0, len(names)):
            artists.append(SimilarItem(
                Artist(names[i], self.network), _number(matches[i])))

        return artists

    def get_top_albums(self, limit=None, cacheable=True):
        """Returns a list of the top albums."""
        params = self._get_params()
        if limit:
            params['limit'] = limit

        return self._get_things(
            "getTopAlbums", "album", Album, params, cacheable)

    def get_top_tracks(self, limit=None, cacheable=True):
        """Returns a list of the most played Tracks by this artist."""
        params = self._get_params()
        if limit:
            params['limit'] = limit

        return self._get_things(
            "getTopTracks", "track", Track, params, cacheable)

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the artist page on the network.
        # Parameters:
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        artist = _url_safe(self.get_name())

        return self.network._get_url(
            domain_name, "artist") % {'artist': artist}


class Country(_BaseObject):
    """A country at Last.fm."""

    name = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, name, network):
        _BaseObject.__init__(self, network, "geo")

        self.name = name

    def __repr__(self):
        return "pylast.Country(%s, %s)" % (repr(self.name), repr(self.network))

    @_string_output
    def __str__(self):
        return self.get_name()

    def __eq__(self, other):
        return self.get_name().lower() == other.get_name().lower()

    def __ne__(self, other):
        return self.get_name() != other.get_name()

    def _get_params(self):  # TODO can move to _BaseObject
        return {'country': self.get_name()}

    def get_name(self):
        """Returns the country name. """

        return self.name

    def get_top_artists(self, limit=None, cacheable=True):
        """Returns a sequence of the most played artists."""
        params = self._get_params()
        if limit:
            params['limit'] = limit

        doc = self._request('geo.getTopArtists', cacheable, params)

        return _extract_top_artists(doc, self)

    def get_top_tracks(self, limit=None, cacheable=True):
        """Returns a sequence of the most played tracks"""
        params = self._get_params()
        if limit:
            params['limit'] = limit

        return self._get_things(
            "getTopTracks", "track", Track, params, cacheable)

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the country page on the network.
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        country_name = _url_safe(self.get_name())

        return self.network._get_url(
            domain_name, "country") % {'country_name': country_name}


class Library(_BaseObject):
    """A user's Last.fm library."""

    user = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, user, network):
        _BaseObject.__init__(self, network, 'library')

        if isinstance(user, User):
            self.user = user
        else:
            self.user = User(user, self.network)

    def __repr__(self):
        return "pylast.Library(%s, %s)" % (repr(self.user), repr(self.network))

    @_string_output
    def __str__(self):
        return repr(self.get_user()) + "'s Library"

    def _get_params(self):
        return {'user': self.user.get_name()}

    def get_user(self):
        """Returns the user who owns this library."""
        return self.user

    def get_artists(self, limit=50, cacheable=True):
        """
        Returns a sequence of Album objects
        if limit==None it will return all (may take a while)
        """

        seq = []
        for node in _collect_nodes(
                limit,
                self,
                self.ws_prefix + ".getArtists",
                cacheable):
            name = _extract(node, "name")

            playcount = _number(_extract(node, "playcount"))
            tagcount = _number(_extract(node, "tagcount"))

            seq.append(LibraryItem(
                Artist(name, self.network), playcount, tagcount))

        return seq


class Tag(_BaseObject, _Chartable):
    """A Last.fm object tag."""

    name = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, name, network):
        _BaseObject.__init__(self, network, 'tag')
        _Chartable.__init__(self, 'tag')

        self.name = name

    def __repr__(self):
        return "pylast.Tag(%s, %s)" % (repr(self.name), repr(self.network))

    @_string_output
    def __str__(self):
        return self.get_name()

    def __eq__(self, other):
        return self.get_name().lower() == other.get_name().lower()

    def __ne__(self, other):
        return self.get_name().lower() != other.get_name().lower()

    def _get_params(self):
        return {self.ws_prefix: self.get_name()}

    def get_name(self, properly_capitalized=False):
        """Returns the name of the tag. """

        if properly_capitalized:
            self.name = _extract(
                self._request(self.ws_prefix + ".getInfo", True), "name")

        return self.name

    def get_top_albums(self, limit=None, cacheable=True):
        """Returns a list of the top albums."""
        params = self._get_params()
        if limit:
            params['limit'] = limit

        doc = self._request(
            self.ws_prefix + '.getTopAlbums', cacheable, params)

        return _extract_top_albums(doc, self.network)

    def get_top_tracks(self, limit=None, cacheable=True):
        """Returns a list of the most played Tracks for this tag."""
        params = self._get_params()
        if limit:
            params['limit'] = limit

        return self._get_things(
            "getTopTracks", "track", Track, params, cacheable)

    def get_top_artists(self, limit=None, cacheable=True):
        """Returns a sequence of the most played artists."""

        params = self._get_params()
        if limit:
            params['limit'] = limit

        doc = self._request(
            self.ws_prefix + '.getTopArtists', cacheable, params)

        return _extract_top_artists(doc, self.network)

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the tag page on the network.
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        name = _url_safe(self.get_name())

        return self.network._get_url(domain_name, "tag") % {'name': name}


class Track(_Opus):
    """A Last.fm track."""

    __hash__ = _Opus.__hash__

    def __init__(self, artist, title, network, username=None):
        super(Track, self).__init__(artist, title, network, "track", username)

    def get_correction(self):
        """Returns the corrected track name."""

        return _extract(
            self._request(self.ws_prefix + ".getCorrection"), "name")

    def get_duration(self):
        """Returns the track duration."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _number(_extract(doc, "duration"))

    def get_userloved(self):
        """Whether the user loved this track"""

        if not self.username:
            return

        params = self._get_params()
        params['username'] = self.username

        doc = self._request(self.ws_prefix + ".getInfo", True, params)
        loved = _number(_extract(doc, "userloved"))
        return bool(loved)

    def is_streamable(self):
        """Returns True if the track is available at Last.fm."""

        doc = self._request(self.ws_prefix + ".getInfo", True)
        return _extract(doc, "streamable") == "1"

    def is_fulltrack_available(self):
        """Returns True if the full track is available for streaming."""

        doc = self._request(self.ws_prefix + ".getInfo", True)
        return doc.getElementsByTagName(
            "streamable")[0].getAttribute("fulltrack") == "1"

    def get_album(self):
        """Returns the album object of this track."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        albums = doc.getElementsByTagName("album")

        if len(albums) == 0:
            return

        node = doc.getElementsByTagName("album")[0]
        return Album(
            _extract(node, "artist"), _extract(node, "title"), self.network)

    def love(self):
        """Adds the track to the user's loved tracks. """

        self._request(self.ws_prefix + '.love')

    def unlove(self):
        """Remove the track to the user's loved tracks. """

        self._request(self.ws_prefix + '.unlove')

    def get_similar(self):
        """
        Returns similar tracks for this track on the network,
        based on listening data.
        """

        doc = self._request(self.ws_prefix + '.getSimilar', True)

        seq = []
        for node in doc.getElementsByTagName(self.ws_prefix):
            title = _extract(node, 'name')
            artist = _extract(node, 'name', 1)
            match = _number(_extract(node, "match"))

            seq.append(SimilarItem(Track(artist, title, self.network), match))

        return seq

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the URL of the album or track page on the network.
        # Parameters:
        * domain_name str: The network's language domain. Possible values:
            o DOMAIN_ENGLISH
            o DOMAIN_GERMAN
            o DOMAIN_SPANISH
            o DOMAIN_FRENCH
            o DOMAIN_ITALIAN
            o DOMAIN_POLISH
            o DOMAIN_PORTUGUESE
            o DOMAIN_SWEDISH
            o DOMAIN_TURKISH
            o DOMAIN_RUSSIAN
            o DOMAIN_JAPANESE
            o DOMAIN_CHINESE
        """

        artist = _url_safe(self.get_artist().get_name())
        title = _url_safe(self.get_title())

        return self.network._get_url(
            domain_name, self.ws_prefix) % {
            'artist': artist, 'title': title}


class User(_BaseObject, _Chartable):
    """A Last.fm user."""

    name = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, user_name, network):
        _BaseObject.__init__(self, network, 'user')
        _Chartable.__init__(self, 'user')

        self.name = user_name

    def __repr__(self):
        return "pylast.User(%s, %s)" % (repr(self.name), repr(self.network))

    @_string_output
    def __str__(self):
        return self.get_name()

    def __eq__(self, another):
        if isinstance(another, User):
            return self.get_name() == another.get_name()
        else:
            return False

    def __ne__(self, another):
        if isinstance(another, User):
            return self.get_name() != another.get_name()
        else:
            return True

    def _get_params(self):
        return {self.ws_prefix: self.get_name()}

    def get_name(self, properly_capitalized=False):
        """Returns the user name."""

        if properly_capitalized:
            self.name = _extract(
                self._request(self.ws_prefix + ".getInfo", True), "name")

        return self.name

    def get_artist_tracks(self, artist, cacheable=False):
        """
        Get a list of tracks by a given artist scrobbled by this user,
        including scrobble time.
        """
        # Not implemented:
        # "Can be limited to specific timeranges, defaults to all time."

        params = self._get_params()
        params['artist'] = artist

        seq = []
        for track in _collect_nodes(
                None,
                self,
                self.ws_prefix + ".getArtistTracks",
                cacheable,
                params):
            title = _extract(track, "name")
            artist = _extract(track, "artist")
            date = _extract(track, "date")
            album = _extract(track, "album")
            timestamp = track.getElementsByTagName(
                "date")[0].getAttribute("uts")

            seq.append(PlayedTrack(
                Track(artist, title, self.network), album, date, timestamp))

        return seq

    def get_friends(self, limit=50, cacheable=False):
        """Returns a list of the user's friends. """

        seq = []
        for node in _collect_nodes(
                limit,
                self,
                self.ws_prefix + ".getFriends",
                cacheable):
            seq.append(User(_extract(node, "name"), self.network))

        return seq

    def get_loved_tracks(self, limit=50, cacheable=True):
        """
        Returns this user's loved track as a sequence of LovedTrack objects in
        reverse order of their timestamp, all the way back to the first track.

        If limit==None, it will try to pull all the available data.

        This method uses caching. Enable caching only if you're pulling a
        large amount of data.
        """

        params = self._get_params()
        if limit:
            params['limit'] = limit

        seq = []
        for track in _collect_nodes(
                limit,
                self,
                self.ws_prefix + ".getLovedTracks",
                cacheable,
                params):
            title = _extract(track, "name")
            artist = _extract(track, "name", 1)
            date = _extract(track, "date")
            timestamp = track.getElementsByTagName(
                "date")[0].getAttribute("uts")

            seq.append(LovedTrack(
                Track(artist, title, self.network), date, timestamp))

        return seq

    def get_now_playing(self):
        """
        Returns the currently playing track, or None if nothing is playing.
        """

        params = self._get_params()
        params['limit'] = '1'

        doc = self._request(self.ws_prefix + '.getRecentTracks', False, params)

        tracks = doc.getElementsByTagName('track')

        if len(tracks) == 0:
            return None

        e = tracks[0]

        if not e.hasAttribute('nowplaying'):
            return None

        artist = _extract(e, 'artist')
        title = _extract(e, 'name')

        return Track(artist, title, self.network, self.name)

    def get_recent_tracks(self, limit=10, cacheable=True,
                          time_from=None, time_to=None):
        """
        Returns this user's played track as a sequence of PlayedTrack objects
        in reverse order of playtime, all the way back to the first track.

        Parameters:
        limit : If None, it will try to pull all the available data.
        from (Optional) : Beginning timestamp of a range - only display
        scrobbles after this time, in UNIX timestamp format (integer
        number of seconds since 00:00:00, January 1st 1970 UTC). This
        must be in the UTC time zone.
        to (Optional) : End timestamp of a range - only display scrobbles
        before this time, in UNIX timestamp format (integer number of
        seconds since 00:00:00, January 1st 1970 UTC). This must be in
        the UTC time zone.

        This method uses caching. Enable caching only if you're pulling a
        large amount of data.
        """

        params = self._get_params()
        if limit:
            params['limit'] = limit
        if time_from:
            params['from'] = time_from
        if time_to:
            params['to'] = time_to

        seq = []
        for track in _collect_nodes(
                limit,
                self,
                self.ws_prefix + ".getRecentTracks",
                cacheable,
                params):

            if track.hasAttribute('nowplaying'):
                continue  # to prevent the now playing track from sneaking in

            title = _extract(track, "name")
            artist = _extract(track, "artist")
            date = _extract(track, "date")
            album = _extract(track, "album")
            timestamp = track.getElementsByTagName(
                "date")[0].getAttribute("uts")

            seq.append(PlayedTrack(
                Track(artist, title, self.network), album, date, timestamp))

        return seq

    def get_country(self):
        """Returns the name of the country of the user."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        country = _extract(doc, "country")

        if country is None:
            return None
        else:
            return Country(country, self.network)

    def is_subscriber(self):
        """Returns whether the user is a subscriber or not. True or False."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _extract(doc, "subscriber") == "1"

    def get_playcount(self):
        """Returns the user's playcount so far."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _number(_extract(doc, "playcount"))

    def get_registered(self):
        """Returns the user's registration date."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _extract(doc, "registered")

    def get_unixtime_registered(self):
        """Returns the user's registration date as a UNIX timestamp."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return doc.getElementsByTagName(
            "registered")[0].getAttribute("unixtime")

    def get_tagged_albums(self, tag, limit=None, cacheable=True):
        """Returns the albums tagged by a user."""

        params = self._get_params()
        params['tag'] = tag
        params['taggingtype'] = 'album'
        if limit:
            params['limit'] = limit
        doc = self._request(self.ws_prefix + '.getpersonaltags', cacheable,
                            params)
        return _extract_albums(doc, self.network)

    def get_tagged_artists(self, tag, limit=None):
        """Returns the artists tagged by a user."""

        params = self._get_params()
        params['tag'] = tag
        params['taggingtype'] = 'artist'
        if limit:
            params["limit"] = limit
        doc = self._request(self.ws_prefix + '.getpersonaltags', True, params)
        return _extract_artists(doc, self.network)

    def get_tagged_tracks(self, tag, limit=None, cacheable=True):
        """Returns the tracks tagged by a user."""

        params = self._get_params()
        params['tag'] = tag
        params['taggingtype'] = 'track'
        if limit:
            params['limit'] = limit
        doc = self._request(self.ws_prefix + '.getpersonaltags', cacheable,
                            params)
        return _extract_tracks(doc, self.network)

    def get_top_albums(
            self, period=PERIOD_OVERALL, limit=None, cacheable=True):
        """Returns the top albums played by a user.
        * period: The period of time. Possible values:
          o PERIOD_OVERALL
          o PERIOD_7DAYS
          o PERIOD_1MONTH
          o PERIOD_3MONTHS
          o PERIOD_6MONTHS
          o PERIOD_12MONTHS
        """

        params = self._get_params()
        params['period'] = period
        if limit:
            params['limit'] = limit

        doc = self._request(
            self.ws_prefix + '.getTopAlbums', cacheable, params)

        return _extract_top_albums(doc, self.network)

    def get_top_artists(self, period=PERIOD_OVERALL, limit=None):
        """Returns the top artists played by a user.
        * period: The period of time. Possible values:
          o PERIOD_OVERALL
          o PERIOD_7DAYS
          o PERIOD_1MONTH
          o PERIOD_3MONTHS
          o PERIOD_6MONTHS
          o PERIOD_12MONTHS
        """

        params = self._get_params()
        params['period'] = period
        if limit:
            params["limit"] = limit

        doc = self._request(self.ws_prefix + '.getTopArtists', True, params)

        return _extract_top_artists(doc, self.network)

    def get_top_tags(self, limit=None, cacheable=True):
        """
        Returns a sequence of the top tags used by this user with their counts
        as TopItem objects.
        * limit: The limit of how many tags to return.
        * cacheable: Whether to cache results.
        """

        params = self._get_params()
        if limit:
            params["limit"] = limit

        doc = self._request(self.ws_prefix + ".getTopTags", cacheable, params)

        seq = []
        for node in doc.getElementsByTagName("tag"):
            seq.append(TopItem(
                Tag(_extract(node, "name"), self.network),
                _extract(node, "count")))

        return seq

    def get_top_tracks(
            self, period=PERIOD_OVERALL, limit=None, cacheable=True):
        """Returns the top tracks played by a user.
        * period: The period of time. Possible values:
          o PERIOD_OVERALL
          o PERIOD_7DAYS
          o PERIOD_1MONTH
          o PERIOD_3MONTHS
          o PERIOD_6MONTHS
          o PERIOD_12MONTHS
        """

        params = self._get_params()
        params['period'] = period
        if limit:
            params['limit'] = limit

        return self._get_things(
            "getTopTracks", "track", Track, params, cacheable)

    def get_image(self):
        """Returns the user's avatar."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _extract(doc, "image")

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the user page on the network.
        * domain_name: The network's language domain. Possible values:
          o DOMAIN_ENGLISH
          o DOMAIN_GERMAN
          o DOMAIN_SPANISH
          o DOMAIN_FRENCH
          o DOMAIN_ITALIAN
          o DOMAIN_POLISH
          o DOMAIN_PORTUGUESE
          o DOMAIN_SWEDISH
          o DOMAIN_TURKISH
          o DOMAIN_RUSSIAN
          o DOMAIN_JAPANESE
          o DOMAIN_CHINESE
        """

        name = _url_safe(self.get_name())

        return self.network._get_url(domain_name, "user") % {'name': name}

    def get_library(self):
        """Returns the associated Library object. """

        return Library(self, self.network)


class AuthenticatedUser(User):
    def __init__(self, network):
        User.__init__(self, "", network)

    def _get_params(self):
        return {"user": self.get_name()}

    def get_name(self):
        """Returns the name of the authenticated user."""

        doc = self._request("user.getInfo", True, {"user": ""})    # hack

        self.name = _extract(doc, "name")
        return self.name


class _Search(_BaseObject):
    """An abstract class. Use one of its derivatives."""

    def __init__(self, ws_prefix, search_terms, network):
        _BaseObject.__init__(self, network, ws_prefix)

        self._ws_prefix = ws_prefix
        self.search_terms = search_terms

        self._last_page_index = 0

    def _get_params(self):
        params = {}

        for key in self.search_terms.keys():
            params[key] = self.search_terms[key]

        return params

    def get_total_result_count(self):
        """Returns the total count of all the results."""

        doc = self._request(self._ws_prefix + ".search", True)

        return _extract(doc, "totalResults")

    def _retrieve_page(self, page_index):
        """Returns the node of matches to be processed"""

        params = self._get_params()
        params["page"] = str(page_index)
        doc = self._request(self._ws_prefix + ".search", True, params)

        return doc.getElementsByTagName(self._ws_prefix + "matches")[0]

    def _retrieve_next_page(self):
        self._last_page_index += 1
        return self._retrieve_page(self._last_page_index)


class AlbumSearch(_Search):
    """Search for an album by name."""

    def __init__(self, album_name, network):

        _Search.__init__(self, "album", {"album": album_name}, network)

    def get_next_page(self):
        """Returns the next page of results as a sequence of Album objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("album"):
            seq.append(Album(
                _extract(node, "artist"),
                _extract(node, "name"),
                self.network))

        return seq


class ArtistSearch(_Search):
    """Search for an artist by artist name."""

    def __init__(self, artist_name, network):
        _Search.__init__(self, "artist", {"artist": artist_name}, network)

    def get_next_page(self):
        """Returns the next page of results as a sequence of Artist objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("artist"):
            artist = Artist(_extract(node, "name"), self.network)
            artist.listener_count = _number(_extract(node, "listeners"))
            seq.append(artist)

        return seq


class TrackSearch(_Search):
    """
    Search for a track by track title. If you don't want to narrow the results
    down by specifying the artist name, set it to empty string.
    """

    def __init__(self, artist_name, track_title, network):

        _Search.__init__(
            self,
            "track",
            {"track": track_title, "artist": artist_name},
            network)

    def get_next_page(self):
        """Returns the next page of results as a sequence of Track objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("track"):
            track = Track(
                _extract(node, "artist"),
                _extract(node, "name"),
                self.network)
            track.listener_count = _number(_extract(node, "listeners"))
            seq.append(track)

        return seq


def md5(text):
    """Returns the md5 hash of a string."""

    h = hashlib.md5()
    h.update(_unicode(text).encode("utf-8"))

    return h.hexdigest()


def _unicode(text):
    if isinstance(text, six.binary_type):
        return six.text_type(text, "utf-8")
    elif isinstance(text, six.text_type):
        return text
    else:
        return six.text_type(text)


def _string(string):
    """For Python2 routines that can only process str type."""
    if isinstance(string, str):
        return string
    casted = six.text_type(string)
    if sys.version_info[0] == 2:
        casted = casted.encode("utf-8")
    return casted


def cleanup_nodes(doc):
    """
    Remove text nodes containing only whitespace
    """
    for node in doc.documentElement.childNodes:
        if node.nodeType == Node.TEXT_NODE and node.nodeValue.isspace():
            doc.documentElement.removeChild(node)
    return doc


def _collect_nodes(limit, sender, method_name, cacheable, params=None):
    """
    Returns a sequence of dom.Node objects about as close to limit as possible
    """

    if not params:
        params = sender._get_params()

    nodes = []
    page = 1
    end_of_pages = False

    while not end_of_pages and (not limit or (limit and len(nodes) < limit)):
        params["page"] = str(page)
        doc = sender._request(method_name, cacheable, params)
        doc = cleanup_nodes(doc)

        # break if there are no child nodes
        if not doc.documentElement.childNodes:
            break
        main = doc.documentElement.childNodes[0]

        if main.hasAttribute("totalPages"):
            total_pages = _number(main.getAttribute("totalPages"))
        elif main.hasAttribute("totalpages"):
            total_pages = _number(main.getAttribute("totalpages"))
        else:
            raise Exception("No total pages attribute")

        for node in main.childNodes:
            if not node.nodeType == xml.dom.Node.TEXT_NODE and (
                    not limit or (len(nodes) < limit)):
                nodes.append(node)

        if page >= total_pages:
            end_of_pages = True

        page += 1

    return nodes


def _extract(node, name, index=0):
    """Extracts a value from the xml string"""

    nodes = node.getElementsByTagName(name)

    if len(nodes):
        if nodes[index].firstChild:
            return _unescape_htmlentity(nodes[index].firstChild.data.strip())
    else:
        return None


def _extract_all(node, name, limit_count=None):
    """Extracts all the values from the xml string. returning a list."""

    seq = []

    for i in range(0, len(node.getElementsByTagName(name))):
        if len(seq) == limit_count:
            break

        seq.append(_extract(node, name, i))

    return seq


def _extract_top_artists(doc, network):
    # TODO Maybe include the _request here too?
    seq = []
    for node in doc.getElementsByTagName("artist"):
        name = _extract(node, "name")
        playcount = _extract(node, "playcount")

        seq.append(TopItem(Artist(name, network), playcount))

    return seq


def _extract_top_albums(doc, network):
    # TODO Maybe include the _request here too?
    seq = []
    for node in doc.getElementsByTagName("album"):
        name = _extract(node, "name")
        artist = _extract(node, "name", 1)
        playcount = _extract(node, "playcount")

        seq.append(TopItem(Album(artist, name, network), playcount))

    return seq


def _extract_artists(doc, network):
    seq = []
    for node in doc.getElementsByTagName("artist"):
        seq.append(Artist(_extract(node, "name"), network))
    return seq


def _extract_albums(doc, network):
    seq = []
    for node in doc.getElementsByTagName("album"):
        name = _extract(node, "name")
        artist = _extract(node, "name", 1)
        seq.append(Album(artist, name, network))
    return seq


def _extract_tracks(doc, network):
    seq = []
    for node in doc.getElementsByTagName("track"):
        name = _extract(node, "name")
        artist = _extract(node, "name", 1)
        seq.append(Track(artist, name, network))
    return seq


def _url_safe(text):
    """Does all kinds of tricks on a text to make it safe to use in a url."""

    return url_quote_plus(url_quote_plus(_string(text))).lower()


def _number(string):
    """
        Extracts an int from a string.
        Returns a 0 if None or an empty string was passed.
    """

    if not string:
        return 0
    elif string == "":
        return 0
    else:
        try:
            return int(string)
        except ValueError:
            return float(string)


def _unescape_htmlentity(string):

    # string = _unicode(string)

    mapping = htmlentitydefs.name2codepoint
    for key in mapping:
        string = string.replace("&%s;" % key, unichr(mapping[key]))

    return string


# End of file
