#
# pylast -
#     A Python interface to Last.fm and Libre.fm
#
# Copyright 2008-2010 Amr Hassan
# Copyright 2013-2021 hugovk
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
from __future__ import annotations

import collections
import hashlib
import html.entities
import importlib.metadata
import logging
import os
import re
import shelve
import ssl
import tempfile
import time
import xml.dom
from urllib.parse import quote_plus
from xml.dom import Node, minidom

import httpx

__author__ = "Amr Hassan, hugovk, Mice Pápai"
__copyright__ = "Copyright (C) 2008-2010 Amr Hassan, 2013-2021 hugovk, 2017 Mice Pápai"
__license__ = "apache2"
__email__ = "amr.hassan@gmail.com"
__version__ = importlib.metadata.version(__name__)


# 1 : This error does not exist
STATUS_INVALID_SERVICE = 2
STATUS_INVALID_METHOD = 3
STATUS_AUTH_FAILED = 4
STATUS_INVALID_FORMAT = 5
STATUS_INVALID_PARAMS = 6
STATUS_INVALID_RESOURCE = 7
STATUS_OPERATION_FAILED = 8
STATUS_INVALID_SK = 9
STATUS_INVALID_API_KEY = 10
STATUS_OFFLINE = 11
STATUS_SUBSCRIBERS_ONLY = 12
STATUS_INVALID_SIGNATURE = 13
STATUS_TOKEN_UNAUTHORIZED = 14
STATUS_TOKEN_EXPIRED = 15
STATUS_TEMPORARILY_UNAVAILABLE = 16
STATUS_LOGIN_REQUIRED = 17
STATUS_TRIAL_EXPIRED = 18
# 19 : This error does not exist
STATUS_NOT_ENOUGH_CONTENT = 20
STATUS_NOT_ENOUGH_MEMBERS = 21
STATUS_NOT_ENOUGH_FANS = 22
STATUS_NOT_ENOUGH_NEIGHBOURS = 23
STATUS_NO_PEAK_RADIO = 24
STATUS_RADIO_NOT_FOUND = 25
STATUS_API_KEY_SUSPENDED = 26
STATUS_DEPRECATED = 27
# 28 : This error is not documented
STATUS_RATE_LIMIT_EXCEEDED = 29

PERIOD_OVERALL = "overall"
PERIOD_7DAYS = "7day"
PERIOD_1MONTH = "1month"
PERIOD_3MONTHS = "3month"
PERIOD_6MONTHS = "6month"
PERIOD_12MONTHS = "12month"

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

SIZE_SMALL = 0
SIZE_MEDIUM = 1
SIZE_LARGE = 2
SIZE_EXTRA_LARGE = 3
SIZE_MEGA = 4

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

# Delay time in seconds from section 4.4 of https://www.last.fm/api/tos
DELAY_TIME = 0.2

# Python >3.4 has sane defaults
SSL_CONTEXT = ssl.create_default_context()

HEADERS = {
    "Content-type": "application/x-www-form-urlencoded",
    "Accept-Charset": "utf-8",
    "User-Agent": f"pylast/{__version__}",
}

logger = logging.getLogger(__name__)
logging.getLogger(__name__).addHandler(logging.NullHandler())


class _Network:
    """
    A music social network website such as Last.fm or
    one with a Last.fm-compatible API.
    """

    def __init__(
        self,
        name,
        homepage,
        ws_server,
        api_key,
        api_secret,
        session_key,
        username,
        password_hash,
        domain_names,
        urls,
        token=None,
    ) -> None:
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
        self.proxy = None
        self.last_call_time: float = 0.0
        self.limit_rate = False

        # Load session_key and username from authentication token if provided
        if token and not self.session_key:
            sk_gen = SessionKeyGenerator(self)
            self.session_key, self.username = sk_gen.get_web_auth_session_key_username(
                url=None, token=token
            )

        # Generate a session_key if necessary
        if (
            (self.api_key and self.api_secret)
            and not self.session_key
            and (self.username and self.password_hash)
        ):
            sk_gen = SessionKeyGenerator(self)
            self.session_key = sk_gen.get_session_key(self.username, self.password_hash)

    def __str__(self) -> str:
        return f"{self.name} Network"

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

    def _get_url(self, domain, url_type) -> str:
        return f"https://{self._get_language_domain(domain)}/{self.urls[url_type]}"

    def _get_ws_auth(self):
        """
        Returns an (API_KEY, API_SECRET, SESSION_KEY) tuple.
        """
        return self.api_key, self.api_secret, self.session_key

    def _delay_call(self) -> None:
        """
        Makes sure that web service calls are at least 0.2 seconds apart.
        """
        now = time.time()

        time_since_last = now - self.last_call_time

        if time_since_last < DELAY_TIME:
            time.sleep(DELAY_TIME - time_since_last)

        self.last_call_time = now

    def get_top_artists(self, limit=None, cacheable: bool = True):
        """Returns the most played artists as a sequence of TopItem objects."""

        params = {}
        if limit:
            params["limit"] = limit

        doc = _Request(self, "chart.getTopArtists", params).execute(cacheable)

        return _extract_top_artists(doc, self)

    def get_top_tracks(self, limit=None, cacheable: bool = True):
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

    def get_top_tags(self, limit=None, cacheable: bool = True):
        """Returns the most used tags as a sequence of TopItem objects."""

        # Last.fm has no "limit" parameter for tag.getTopTags
        # so we need to get all (250) and then limit locally
        doc = _Request(self, "tag.getTopTags").execute(cacheable)

        seq: list[TopItem] = []
        for node in doc.getElementsByTagName("tag"):
            if limit and len(seq) >= limit:
                break
            tag = Tag(_extract(node, "name"), self)
            weight = _number(_extract(node, "count"))
            seq.append(TopItem(tag, weight))

        return seq

    def get_geo_top_artists(self, country, limit=None, cacheable: bool = True):
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
        self, country, location=None, limit=None, cacheable: bool = True
    ):
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

    def enable_proxy(self, proxy: str | dict) -> None:
        """Enable default web proxy.
        Multiple proxies can be passed as a `dict`, see
        https://www.python-httpx.org/advanced/#http-proxying
        """
        self.proxy = proxy

    def disable_proxy(self) -> None:
        """Disable using the web proxy"""
        self.proxy = None

    def is_proxy_enabled(self) -> bool:
        """Returns True if web proxy is enabled."""
        return self.proxy is not None

    def enable_rate_limit(self) -> None:
        """Enables rate limiting for this network"""
        self.limit_rate = True

    def disable_rate_limit(self) -> None:
        """Disables rate limiting for this network"""
        self.limit_rate = False

    def is_rate_limited(self) -> bool:
        """Return True if web service calls are rate limited"""
        return self.limit_rate

    def enable_caching(self, file_path=None) -> None:
        """Enables caching request-wide for all cacheable calls.

        * file_path: A file path for the backend storage file. If
        None set, a temp file would probably be created, according the backend.
        """
        if not file_path:
            self.cache_backend = _ShelfCacheBackend.create_shelf()
            return

        self.cache_backend = _ShelfCacheBackend(file_path)

    def disable_caching(self) -> None:
        """Disables all caching features."""
        self.cache_backend = None

    def is_caching_enabled(self) -> bool:
        """Returns True if caching is enabled."""
        return self.cache_backend is not None

    def search_for_album(self, album_name):
        """Searches for an album by its name. Returns an AlbumSearch object.
        Use get_next_page() to retrieve sequences of results."""

        return AlbumSearch(album_name, self)

    def search_for_artist(self, artist_name):
        """Searches for an artist by its name. Returns an ArtistSearch object.
        Use get_next_page() to retrieve sequences of results."""

        return ArtistSearch(artist_name, self)

    def search_for_track(self, artist_name, track_name):
        """Searches for a track by its name and its artist. Set artist to an
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
        self,
        artist,
        title,
        album=None,
        album_artist=None,
        duration=None,
        track_number=None,
        mbid=None,
        context=None,
    ) -> None:
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
        self,
        artist,
        title,
        timestamp,
        album=None,
        album_artist=None,
        track_number=None,
        duration=None,
        stream_id=None,
        context=None,
        mbid=None,
    ):
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

        return self.scrobble_many(
            (
                {
                    "artist": artist,
                    "title": title,
                    "timestamp": timestamp,
                    "album": album,
                    "album_artist": album_artist,
                    "track_number": track_number,
                    "duration": duration,
                    "stream_id": stream_id,
                    "context": context,
                    "mbid": mbid,
                },
            )
        )

    def scrobble_many(self, tracks) -> None:
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
            params[f"artist[{i}]"] = tracks_to_scrobble[i]["artist"]
            params[f"track[{i}]"] = tracks_to_scrobble[i]["title"]

            additional_args = (
                "timestamp",
                "album",
                "album_artist",
                "context",
                "stream_id",
                "track_number",
                "mbid",
                "duration",
            )
            args_map_to = {  # so friggin lazy
                "album_artist": "albumArtist",
                "track_number": "trackNumber",
                "stream_id": "streamID",
            }

            for arg in additional_args:
                if arg in tracks_to_scrobble[i] and tracks_to_scrobble[i][arg]:
                    if arg in args_map_to:
                        maps_to = args_map_to[arg]
                    else:
                        maps_to = arg

                    params[f"{maps_to}[{i}]"] = tracks_to_scrobble[i][arg]

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
        self,
        api_key: str = "",
        api_secret: str = "",
        session_key: str = "",
        username: str = "",
        password_hash: str = "",
        token: str = "",
    ) -> None:
        super().__init__(
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
                DOMAIN_ENGLISH: "www.last.fm",
                DOMAIN_GERMAN: "www.last.fm/de",
                DOMAIN_SPANISH: "www.last.fm/es",
                DOMAIN_FRENCH: "www.last.fm/fr",
                DOMAIN_ITALIAN: "www.last.fm/it",
                DOMAIN_POLISH: "www.last.fm/pl",
                DOMAIN_PORTUGUESE: "www.last.fm/pt",
                DOMAIN_SWEDISH: "www.last.fm/sv",
                DOMAIN_TURKISH: "www.last.fm/tr",
                DOMAIN_RUSSIAN: "www.last.fm/ru",
                DOMAIN_JAPANESE: "www.last.fm/ja",
                DOMAIN_CHINESE: "www.last.fm/zh",
            },
            urls={
                "album": "music/%(artist)s/%(album)s",
                "artist": "music/%(artist)s",
                "country": "place/%(country_name)s",
                "tag": "tag/%(name)s",
                "track": "music/%(artist)s/_/%(title)s",
                "user": "user/%(name)s",
            },
        )

    def __repr__(self) -> str:
        return (
            "pylast.LastFMNetwork("
            f"'{self.api_key}', "
            f"'{self.api_secret}', "
            f"'{self.session_key}', "
            f"'{self.username}', "
            f"'{self.password_hash}'"
            ")"
        )


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
        self,
        api_key: str = "",
        api_secret: str = "",
        session_key: str = "",
        username: str = "",
        password_hash: str = "",
    ) -> None:
        super().__init__(
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
            },
        )

    def __repr__(self) -> str:
        return (
            "pylast.LibreFMNetwork("
            f"'{self.api_key}', "
            f"'{self.api_secret}', "
            f"'{self.session_key}', "
            f"'{self.username}', "
            f"'{self.password_hash}'"
            ")"
        )


class _ShelfCacheBackend:
    """Used as a backend for caching cacheable requests."""

    def __init__(self, file_path=None, flag=None) -> None:
        if flag is not None:
            self.shelf = shelve.open(file_path, flag=flag)
        else:
            self.shelf = shelve.open(file_path)
        self.cache_keys = set(self.shelf.keys())

    def __contains__(self, key) -> bool:
        return key in self.cache_keys

    def __iter__(self):
        return iter(self.shelf.keys())

    def get_xml(self, key):
        return self.shelf[key]

    def set_xml(self, key, xml_string) -> None:
        self.cache_keys.add(key)
        self.shelf[key] = xml_string

    @classmethod
    def create_shelf(cls):
        file_descriptor, file_path = tempfile.mkstemp(prefix="pylast_tmp_")
        os.close(file_descriptor)
        return cls(file_path=file_path, flag="n")


class _Request:
    """Representing an abstract web service operation."""

    def __init__(self, network, method_name, params=None) -> None:
        logger.info(method_name)

        if params is None:
            params = {}

        self.network = network
        self.params = {}

        for key in params:
            self.params[key] = _unicode(params[key])

        (self.api_key, self.api_secret, self.session_key) = network._get_ws_auth()

        self.params["api_key"] = self.api_key
        self.params["method"] = method_name

        if network.is_caching_enabled():
            self.cache = network.cache_backend

        if self.session_key:
            self.params["sk"] = self.session_key
            self.sign_it()

    def sign_it(self) -> None:
        """Sign this request."""

        if "api_sig" not in self.params.keys():
            self.params["api_sig"] = self._get_signature()

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

        cache_key = ""

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

        username = self.params.pop("username", None)
        username = "" if username is None else f"?username={username}"

        (host_name, host_subdir) = self.network.ws_server

        if self.network.is_proxy_enabled():
            client = httpx.Client(
                verify=SSL_CONTEXT,
                base_url=f"https://{host_name}",
                headers=HEADERS,
                proxies=self.network.proxy,
            )
        else:
            client = httpx.Client(
                verify=SSL_CONTEXT,
                base_url=f"https://{host_name}",
                headers=HEADERS,
            )

        try:
            response = client.post(f"{host_subdir}{username}", data=self.params)
        except Exception as e:
            raise NetworkError(self.network, e) from e

        if response.status_code in (500, 502, 503, 504):
            raise WSError(
                self.network,
                response.status_code,
                f"Connection to the API failed with HTTP code {response.status_code}",
            )
        response_text = _unicode(response.read())

        try:
            self._check_response_for_errors(response_text)
        finally:
            client.close()
        return response_text

    def execute(self, cacheable: bool = False) -> xml.dom.minidom.Document:
        """Returns the XML DOM response of the POST Request from the server"""

        if self.network.is_caching_enabled() and cacheable:
            response = self._get_cached_response()
        else:
            response = self._download_response()

        return _parse_response(response)

    def _check_response_for_errors(self, response):
        """Checks the response for errors and raises one if any exists."""
        try:
            doc = _parse_response(response)
        except Exception as e:
            raise MalformedResponseError(self.network, e) from e

        element = doc.getElementsByTagName("lfm")[0]
        logger.debug(doc.toprettyxml())

        if element.getAttribute("status") != "ok":
            element = doc.getElementsByTagName("error")[0]
            status = element.getAttribute("code")
            details = element.firstChild.data.strip()
            raise WSError(self.network, status, details)


class SessionKeyGenerator:
    """Methods of generating a session key:
    1) Web Authentication:
        a. network = get_*_network(API_KEY, API_SECRET)
        b. sg = SessionKeyGenerator(network)
        c. url = sg.get_web_auth_url()
        d. Ask the user to open the URL and authorize you, and wait for it.
        e. session_key = sg.get_web_auth_session_key(url)
    2) Username and Password Authentication:
        a. network = get_*_network(API_KEY, API_SECRET)
        b. username = raw_input("Please enter your username: ")
        c. password_hash = pylast.md5(raw_input("Please enter your password: ")
        d. session_key = SessionKeyGenerator(network).get_session_key(username,
            password_hash)

    A session key's lifetime is infinite, unless the user revokes the rights
    of the given API Key.

    If you create a Network object with just an API_KEY and API_SECRET and a
    username and a password_hash, a SESSION_KEY will be automatically generated
    for that network and stored in it so you don't have to do this manually,
    unless you want to.
    """

    def __init__(self, network) -> None:
        self.network = network
        self.web_auth_tokens = {}

    def _get_web_auth_token(self):
        """
        Retrieves a token from the network for web authentication.
        The token then has to be authorized from getAuthURL before creating
        session.
        """

        request = _Request(self.network, "auth.getToken")

        # default action is that a request is signed only when
        # a session key is provided.
        request.sign_it()

        doc = request.execute()

        e = doc.getElementsByTagName("token")[0]
        return e.firstChild.data

    def get_web_auth_url(self):
        """
        The user must open this page, and you first, then
        call get_web_auth_session_key(url) after that.
        """

        token = self._get_web_auth_token()

        url = (
            f"{self.network.homepage}/api/auth/"
            f"?api_key={self.network.api_key}"
            f"&token={token}"
        )

        self.web_auth_tokens[url] = token

        return url

    def get_web_auth_session_key_username(self, url, token: str = ""):
        """
        Retrieves the session key/username of a web authorization process by its URL.
        """

        if url in self.web_auth_tokens.keys():
            token = self.web_auth_tokens[url]

        request = _Request(self.network, "auth.getSession", {"token": token})

        # default action is that a request is signed only when
        # a session key is provided.
        request.sign_it()

        doc = request.execute()

        session_key = doc.getElementsByTagName("key")[0].firstChild.data
        username = doc.getElementsByTagName("name")[0].firstChild.data
        return session_key, username

    def get_web_auth_session_key(self, url, token: str = ""):
        """
        Retrieves the session key of a web authorization process by its URL.
        """
        session_key, _username = self.get_web_auth_session_key_username(url, token)
        return session_key

    def get_session_key(self, username, password_hash):
        """
        Retrieve a session key with a username and a md5 hash of the user's
        password.
        """

        params = {"username": username, "authToken": md5(username + password_hash)}
        request = _Request(self.network, "auth.getMobileSession", params)

        # default action is that a request is signed only when
        # a session key is provided.
        request.sign_it()

        doc = request.execute()

        return _extract(doc, "key")


TopItem = collections.namedtuple("TopItem", ["item", "weight"])
SimilarItem = collections.namedtuple("SimilarItem", ["item", "match"])
LibraryItem = collections.namedtuple("LibraryItem", ["item", "playcount", "tagcount"])
PlayedTrack = collections.namedtuple(
    "PlayedTrack", ["track", "album", "playback_date", "timestamp"]
)
LovedTrack = collections.namedtuple("LovedTrack", ["track", "date", "timestamp"])
ImageSizes = collections.namedtuple(
    "ImageSizes", ["original", "large", "largesquare", "medium", "small", "extralarge"]
)
Image = collections.namedtuple(
    "Image", ["title", "url", "dateadded", "format", "owner", "sizes", "votes"]
)


def _string_output(func):
    def r(*args):
        return str(func(*args))

    return r


class _BaseObject:
    """An abstract webservices object."""

    network = None

    def __init__(self, network, ws_prefix) -> None:
        self.network = network
        self.ws_prefix = ws_prefix

    def _request(self, method_name, cacheable: bool = False, params=None):
        if not params:
            params = self._get_params()

        return _Request(self.network, method_name, params).execute(cacheable)

    def _get_params(self):
        """Returns the most common set of parameters between all objects."""

        return {}

    def __hash__(self):
        # Convert any ints (or whatever) into strings
        values = map(str, self._get_params().values())

        return hash(self.network) + hash(
            str(type(self))
            + "".join(list(self._get_params().keys()) + list(values)).lower()
        )

    def _extract_cdata_from_request(self, method_name, tag_name, params):
        doc = self._request(method_name, True, params)

        first_child = doc.getElementsByTagName(tag_name)[0].firstChild

        if first_child is None:
            return None

        return first_child.wholeText.strip()

    def _get_things(
        self,
        method,
        thing_type,
        params=None,
        cacheable: bool = True,
        stream: bool = False,
    ):
        """Returns a list of the most played thing_types by this thing."""

        def _stream_get_things():
            limit = params.get("limit", 50)
            nodes = _collect_nodes(
                limit,
                self,
                self.ws_prefix + "." + method,
                cacheable,
                params,
                stream=stream,
            )
            for node in nodes:
                title = _extract(node, "name")
                artist = _extract(node, "name", 1)
                playcount = _number(_extract(node, "playcount"))

                yield TopItem(thing_type(artist, title, self.network), playcount)

        return _stream_get_things() if stream else list(_stream_get_things())

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


class _Chartable(_BaseObject):
    """Common functions for classes with charts."""

    def __init__(self, network, ws_prefix) -> None:
        super().__init__(network=network, ws_prefix=ws_prefix)

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
        Only for User.
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

        doc = self._request(self.ws_prefix + method, True, params)

        seq = []
        for node in doc.getElementsByTagName(chart_kind.lower()):
            if chart_kind == "artist":
                item = chart_type(_extract(node, "name"), self.network)
            else:
                item = chart_type(
                    _extract(node, "artist"), _extract(node, "name"), self.network
                )
            weight = _number(_extract(node, "playcount"))
            seq.append(TopItem(item, weight))

        return seq


class _Taggable(_BaseObject):
    """Common functions for classes with tags."""

    def __init__(self, network, ws_prefix) -> None:
        super().__init__(network=network, ws_prefix=ws_prefix)

    def add_tags(self, tags) -> None:
        """Adds one or several tags.
        * tags: A sequence of tag names or Tag objects.
        """

        for tag in tags:
            self.add_tag(tag)

    def add_tag(self, tag) -> None:
        """Adds one tag.
        * tag: a tag name or a Tag object.
        """

        if isinstance(tag, Tag):
            tag = tag.get_name()

        params = self._get_params()
        params["tags"] = tag

        self._request(self.ws_prefix + ".addTags", False, params)

    def remove_tag(self, tag) -> None:
        """Remove a user's tag from this object."""

        if isinstance(tag, Tag):
            tag = tag.get_name()

        params = self._get_params()
        params["tag"] = tag

        self._request(self.ws_prefix + ".removeTag", False, params)

    def get_tags(self):
        """Returns a list of the tags set by the user to this object."""

        # Uncacheable because it can be dynamically changed by the user.
        params = self._get_params()

        doc = self._request(self.ws_prefix + ".getTags", False, params)
        tag_names = _extract_all(doc, "name")
        tags = []
        for tag in tag_names:
            tags.append(Tag(tag, self.network))

        return tags

    def remove_tags(self, tags) -> None:
        """Removes one or several tags from this object.
        * tags: a sequence of tag names or Tag objects.
        """

        for tag in tags:
            self.remove_tag(tag)

    def clear_tags(self) -> None:
        """Clears all the user-set tags."""

        self.remove_tags(*(self.get_tags()))

    def set_tags(self, tags) -> None:
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

        doc = self._request(self.ws_prefix + ".getTopTags", True)

        elements = doc.getElementsByTagName("tag")
        seq = []

        for element in elements:
            tag_name = _extract(element, "name")
            tag_count = _extract(element, "count")

            seq.append(TopItem(Tag(tag_name, self.network), tag_count))

        if limit:
            seq = seq[:limit]

        return seq


class PyLastError(Exception):
    """Generic exception raised by PyLast"""

    pass


class WSError(PyLastError):
    """Exception related to the Network web service"""

    def __init__(self, network, status, details) -> None:
        self.status = status
        self.details = details
        self.network = network

    @_string_output
    def __str__(self) -> str:
        return self.details

    def get_id(self):
        """Returns the exception ID, from one of the following:
        STATUS_INVALID_SERVICE = 2
        STATUS_INVALID_METHOD = 3
        STATUS_AUTH_FAILED = 4
        STATUS_INVALID_FORMAT = 5
        STATUS_INVALID_PARAMS = 6
        STATUS_INVALID_RESOURCE = 7
        STATUS_OPERATION_FAILED = 8
        STATUS_INVALID_SK = 9
        STATUS_INVALID_API_KEY = 10
        STATUS_OFFLINE = 11
        STATUS_SUBSCRIBERS_ONLY = 12
        STATUS_TOKEN_UNAUTHORIZED = 14
        STATUS_TOKEN_EXPIRED = 15
        STATUS_TEMPORARILY_UNAVAILABLE = 16
        STATUS_LOGIN_REQUIRED = 17
        STATUS_TRIAL_EXPIRED = 18
        STATUS_NOT_ENOUGH_CONTENT = 20
        STATUS_NOT_ENOUGH_MEMBERS  = 21
        STATUS_NOT_ENOUGH_FANS = 22
        STATUS_NOT_ENOUGH_NEIGHBOURS = 23
        STATUS_NO_PEAK_RADIO = 24
        STATUS_RADIO_NOT_FOUND = 25
        STATUS_API_KEY_SUSPENDED = 26
        STATUS_DEPRECATED = 27
        STATUS_RATE_LIMIT_EXCEEDED = 29
        """

        return self.status


class MalformedResponseError(PyLastError):
    """Exception conveying a malformed response from the music network."""

    def __init__(self, network, underlying_error) -> None:
        self.network = network
        self.underlying_error = underlying_error

    def __str__(self) -> str:
        return (
            f"Malformed response from {self.network.name}. "
            f"Underlying error: {self.underlying_error}"
        )


class NetworkError(PyLastError):
    """Exception conveying a problem in sending a request to Last.fm"""

    def __init__(self, network, underlying_error) -> None:
        self.network = network
        self.underlying_error = underlying_error

    def __str__(self) -> str:
        return f"NetworkError: {self.underlying_error}"


class _Opus(_Taggable):
    """An album or track."""

    artist = None
    title = None
    username = None

    __hash__ = _BaseObject.__hash__

    def __init__(
        self, artist, title, network, ws_prefix, username=None, info=None
    ) -> None:
        """
        Create an opus instance.
        # Parameters:
            * artist: An artist name or an Artist object.
            * title: The album or track title.
            * ws_prefix: 'album' or 'track'
        """

        if info is None:
            info = {}

        super().__init__(network=network, ws_prefix=ws_prefix)

        if isinstance(artist, Artist):
            self.artist = artist
        else:
            self.artist = Artist(artist, self.network)

        self.title = title
        self.username = (
            username if username else network.username
        )  # Default to current user
        self.info = info

    def __repr__(self) -> str:
        return (
            f"pylast.{self.ws_prefix.title()}"
            f"({repr(self.artist.name)}, {repr(self.title)}, {repr(self.network)})"
        )

    @_string_output
    def __str__(self) -> str:
        return f"{self.get_artist().get_name()} - {self.get_title()}"

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        a = self.get_title().lower()
        b = other.get_title().lower()
        c = self.get_artist().get_name().lower()
        d = other.get_artist().get_name().lower()
        return (a == b) and (c == d)

    def __ne__(self, other):
        return not self == other

    def _get_params(self):
        return {
            "artist": self.get_artist().get_name(),
            self.ws_prefix: self.get_title(),
        }

    def get_artist(self):
        """Returns the associated Artist object."""

        return self.artist

    def get_cover_image(self, size=SIZE_EXTRA_LARGE):
        """
        Returns a URI to the cover image
        size can be one of:
            SIZE_EXTRA_LARGE
            SIZE_LARGE
            SIZE_MEDIUM
            SIZE_SMALL
        """
        if "image" not in self.info:
            self.info["image"] = _extract_all(
                self._request(self.ws_prefix + ".getInfo", cacheable=True), "image"
            )
        return self.info["image"][size]

    def get_title(self, properly_capitalized: bool = False):
        """Returns the artist or track title."""
        if properly_capitalized:
            self.title = _extract(
                self._request(self.ws_prefix + ".getInfo", True), "name"
            )

        return self.title

    def get_name(self, properly_capitalized: bool = False):
        """Returns the album or track title (alias to get_title())."""

        return self.get_title(properly_capitalized)

    def get_playcount(self):
        """Returns the number of plays on the network"""

        return _number(
            _extract(
                self._request(self.ws_prefix + ".getInfo", cacheable=True), "playcount"
            )
        )

    def get_userplaycount(self):
        """Returns the number of plays by a given username"""

        if not self.username:
            return

        params = self._get_params()
        params["username"] = self.username

        doc = self._request(self.ws_prefix + ".getInfo", True, params)
        return _number(_extract(doc, "userplaycount"))

    def get_listener_count(self):
        """Returns the number of listeners on the network"""

        return _number(
            _extract(
                self._request(self.ws_prefix + ".getInfo", cacheable=True), "listeners"
            )
        )

    def get_mbid(self) -> str | None:
        """Returns the MusicBrainz ID of the album or track."""

        doc = self._request(self.ws_prefix + ".getInfo", cacheable=True)

        try:
            lfm = doc.getElementsByTagName("lfm")[0]
            opus = next(self._get_children_by_tag_name(lfm, self.ws_prefix))
            mbid = next(self._get_children_by_tag_name(opus, "mbid"))
            return mbid.firstChild.nodeValue if mbid.firstChild else None
        except StopIteration:
            return None

    def _get_children_by_tag_name(self, node, tag_name):
        for child in node.childNodes:
            if child.nodeType == child.ELEMENT_NODE and (
                tag_name == "*" or child.tagName == tag_name
            ):
                yield child


class Album(_Opus):
    """An album."""

    __hash__ = _Opus.__hash__

    def __init__(self, artist, title, network, username=None, info=None) -> None:
        super().__init__(artist, title, network, "album", username, info)

    def get_tracks(self):
        """Returns the list of Tracks on this album."""

        return _extract_tracks(
            self._request(self.ws_prefix + ".getInfo", cacheable=True), self.network
        )

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

        return self.network._get_url(domain_name, self.ws_prefix) % {
            "artist": artist,
            "album": title,
        }


class Artist(_Taggable):
    """An artist."""

    name = None
    username = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, name, network, username=None, info=None) -> None:
        """Create an artist object.
        # Parameters:
            * name str: The artist's name.
        """

        if info is None:
            info = {}

        super().__init__(network=network, ws_prefix="artist")

        self.name = name
        self.username = username
        self.info = info

    def __repr__(self) -> str:
        return f"pylast.Artist({repr(self.get_name())}, {repr(self.network)})"

    def __unicode__(self):
        return str(self.get_name())

    @_string_output
    def __str__(self) -> str:
        return self.__unicode__()

    def __eq__(self, other):
        if type(self) is type(other):
            return self.get_name().lower() == other.get_name().lower()
        else:
            return False

    def __ne__(self, other):
        return not self == other

    def _get_params(self):
        return {self.ws_prefix: self.get_name()}

    def get_name(self, properly_capitalized: bool = False):
        """Returns the name of the artist.
        If properly_capitalized was asserted then the name would be downloaded
        overwriting the given one."""

        if properly_capitalized:
            self.name = _extract(
                self._request(self.ws_prefix + ".getInfo", True), "name"
            )

        return self.name

    def get_correction(self):
        """Returns the corrected artist name."""

        return _extract(self._request(self.ws_prefix + ".getCorrection"), "name")

    def get_playcount(self):
        """Returns the number of plays on the network."""

        return _number(
            _extract(self._request(self.ws_prefix + ".getInfo", True), "playcount")
        )

    def get_userplaycount(self):
        """Returns the number of plays by a given username"""

        if not self.username:
            return

        params = self._get_params()
        params["username"] = self.username

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
            self.listener_count = _number(
                _extract(self._request(self.ws_prefix + ".getInfo", True), "listeners")
            )
            return self.listener_count

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

        try:
            bio = self._extract_cdata_from_request(
                self.ws_prefix + ".getInfo", section, params
            )
        except IndexError:
            bio = None

        return bio

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
            params["limit"] = limit

        doc = self._request(self.ws_prefix + ".getSimilar", True, params)

        names = _extract_all(doc, "name")
        matches = _extract_all(doc, "match")

        artists = []
        for i in range(0, len(names)):
            artists.append(
                SimilarItem(Artist(names[i], self.network), _number(matches[i]))
            )

        return artists

    def get_top_albums(self, limit=None, cacheable: bool = True, stream: bool = False):
        """Returns a list of the top albums."""
        params = self._get_params()
        if limit:
            params["limit"] = limit

        return self._get_things("getTopAlbums", Album, params, cacheable, stream=stream)

    def get_top_tracks(self, limit=None, cacheable: bool = True, stream: bool = False):
        """Returns a list of the most played Tracks by this artist."""
        params = self._get_params()
        if limit:
            params["limit"] = limit

        return self._get_things("getTopTracks", Track, params, cacheable, stream=stream)

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the URL of the artist page on the network.
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

        return self.network._get_url(domain_name, "artist") % {"artist": artist}


class Country(_BaseObject):
    """A country at Last.fm."""

    name = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, name, network) -> None:
        super().__init__(network=network, ws_prefix="geo")

        self.name = name

    def __repr__(self) -> str:
        return f"pylast.Country({repr(self.name)}, {repr(self.network)})"

    @_string_output
    def __str__(self) -> str:
        return self.get_name()

    def __eq__(self, other):
        return self.get_name().lower() == other.get_name().lower()

    def __ne__(self, other):
        return not self == other

    def _get_params(self):  # TODO can move to _BaseObject
        return {"country": self.get_name()}

    def get_name(self):
        """Returns the country name."""

        return self.name

    def get_top_artists(self, limit=None, cacheable: bool = True):
        """Returns a sequence of the most played artists."""
        params = self._get_params()
        if limit:
            params["limit"] = limit

        doc = self._request("geo.getTopArtists", cacheable, params)

        return _extract_top_artists(doc, self)

    def get_top_tracks(self, limit=None, cacheable: bool = True, stream: bool = False):
        """Returns a sequence of the most played tracks"""
        params = self._get_params()
        if limit:
            params["limit"] = limit

        return self._get_things("getTopTracks", Track, params, cacheable, stream=stream)

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the URL of the country page on the network.
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

        return self.network._get_url(domain_name, "country") % {
            "country_name": country_name
        }


class Library(_BaseObject):
    """A user's Last.fm library."""

    user = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, user, network) -> None:
        super().__init__(network=network, ws_prefix="library")

        if isinstance(user, User):
            self.user = user
        else:
            self.user = User(user, self.network)

    def __repr__(self) -> str:
        return f"pylast.Library({repr(self.user)}, {repr(self.network)})"

    @_string_output
    def __str__(self) -> str:
        return repr(self.get_user()) + "'s Library"

    def _get_params(self):
        return {"user": self.user.get_name()}

    def get_user(self):
        """Returns the user who owns this library."""
        return self.user

    def get_artists(
        self, limit: int = 50, cacheable: bool = True, stream: bool = False
    ):
        """
        Returns a sequence of Album objects
        if limit==None it will return all (may take a while)
        """

        def _get_artists():
            for node in _collect_nodes(
                limit, self, self.ws_prefix + ".getArtists", cacheable, stream=stream
            ):
                name = _extract(node, "name")

                playcount = _number(_extract(node, "playcount"))
                tagcount = _number(_extract(node, "tagcount"))

                yield LibraryItem(Artist(name, self.network), playcount, tagcount)

        return _get_artists() if stream else list(_get_artists())


class Tag(_Chartable):
    """A Last.fm object tag."""

    name = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, name, network) -> None:
        super().__init__(network=network, ws_prefix="tag")

        self.name = name

    def __repr__(self) -> str:
        return f"pylast.Tag({repr(self.name)}, {repr(self.network)})"

    @_string_output
    def __str__(self) -> str:
        return self.get_name()

    def __eq__(self, other):
        return self.get_name().lower() == other.get_name().lower()

    def __ne__(self, other):
        return not self == other

    def _get_params(self):
        return {self.ws_prefix: self.get_name()}

    def get_name(self, properly_capitalized: bool = False):
        """Returns the name of the tag."""

        if properly_capitalized:
            self.name = _extract(
                self._request(self.ws_prefix + ".getInfo", True), "name"
            )

        return self.name

    def get_top_albums(self, limit=None, cacheable: bool = True):
        """Returns a list of the top albums."""
        params = self._get_params()
        if limit:
            params["limit"] = limit

        doc = self._request(self.ws_prefix + ".getTopAlbums", cacheable, params)

        return _extract_top_albums(doc, self.network)

    def get_top_tracks(self, limit=None, cacheable: bool = True, stream: bool = False):
        """Returns a list of the most played Tracks for this tag."""
        params = self._get_params()
        if limit:
            params["limit"] = limit

        return self._get_things("getTopTracks", Track, params, cacheable, stream=stream)

    def get_top_artists(self, limit=None, cacheable: bool = True):
        """Returns a sequence of the most played artists."""

        params = self._get_params()
        if limit:
            params["limit"] = limit

        doc = self._request(self.ws_prefix + ".getTopArtists", cacheable, params)

        return _extract_top_artists(doc, self.network)

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the URL of the tag page on the network.
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

        return self.network._get_url(domain_name, "tag") % {"name": name}


class Track(_Opus):
    """A Last.fm track."""

    __hash__ = _Opus.__hash__

    def __init__(self, artist, title, network, username=None, info=None) -> None:
        super().__init__(artist, title, network, "track", username, info)

    def get_correction(self):
        """Returns the corrected track name."""

        return _extract(self._request(self.ws_prefix + ".getCorrection"), "name")

    def get_duration(self):
        """Returns the track duration."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _number(_extract(doc, "duration"))

    def get_userloved(self):
        """Whether the user loved this track"""

        if not self.username:
            return

        params = self._get_params()
        params["username"] = self.username

        doc = self._request(self.ws_prefix + ".getInfo", True, params)
        loved = _number(_extract(doc, "userloved"))
        return bool(loved)

    def get_album(self):
        """Returns the album object of this track."""
        if "album" in self.info and self.info["album"] is not None:
            return Album(self.artist, self.info["album"], self.network)

        doc = self._request(self.ws_prefix + ".getInfo", True)

        albums = doc.getElementsByTagName("album")

        if len(albums) == 0:
            return

        node = doc.getElementsByTagName("album")[0]
        return Album(_extract(node, "artist"), _extract(node, "title"), self.network)

    def love(self) -> None:
        """Adds the track to the user's loved tracks."""

        self._request(self.ws_prefix + ".love")

    def unlove(self) -> None:
        """Remove the track to the user's loved tracks."""

        self._request(self.ws_prefix + ".unlove")

    def get_similar(self, limit=None):
        """
        Returns similar tracks for this track on the network,
        based on listening data.
        """

        params = self._get_params()
        if limit:
            params["limit"] = limit

        doc = self._request(self.ws_prefix + ".getSimilar", True, params)

        seq = []
        for node in doc.getElementsByTagName(self.ws_prefix):
            title = _extract(node, "name")
            artist = _extract(node, "name", 1)
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

        return self.network._get_url(domain_name, self.ws_prefix) % {
            "artist": artist,
            "title": title,
        }


class User(_Chartable):
    """A Last.fm user."""

    name = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, user_name, network) -> None:
        super().__init__(network=network, ws_prefix="user")

        self.name = user_name

    def __repr__(self) -> str:
        return f"pylast.User({repr(self.name)}, {repr(self.network)})"

    @_string_output
    def __str__(self) -> str:
        return self.get_name()

    def __eq__(self, other):
        if isinstance(other, User):
            return self.get_name() == other.get_name()
        else:
            return False

    def __ne__(self, other):
        return not self == other

    def _get_params(self):
        return {self.ws_prefix: self.get_name()}

    def _extract_played_track(self, track_node):
        title = _extract(track_node, "name")
        track_artist = _extract(track_node, "artist")
        date = _extract(track_node, "date")
        album = _extract(track_node, "album")
        timestamp = track_node.getElementsByTagName("date")[0].getAttribute("uts")
        return PlayedTrack(
            Track(track_artist, title, self.network), album, date, timestamp
        )

    def get_name(self, properly_capitalized: bool = False):
        """Returns the user name."""

        if properly_capitalized:
            self.name = _extract(
                self._request(self.ws_prefix + ".getInfo", True), "name"
            )

        return self.name

    def get_friends(
        self, limit: int = 50, cacheable: bool = False, stream: bool = False
    ):
        """Returns a list of the user's friends."""

        def _get_friends():
            for node in _collect_nodes(
                limit, self, self.ws_prefix + ".getFriends", cacheable, stream=stream
            ):
                yield User(_extract(node, "name"), self.network)

        return _get_friends() if stream else list(_get_friends())

    def get_loved_tracks(
        self, limit: int = 50, cacheable: bool = True, stream: bool = False
    ):
        """
        Returns this user's loved track as a sequence of LovedTrack objects in
        reverse order of their timestamp, all the way back to the first track.

        If limit==None, it will try to pull all the available data.
        If stream=True, it will yield tracks as soon as a page has been retrieved.

        This method uses caching. Enable caching only if you're pulling a
        large amount of data.
        """

        def _get_loved_tracks():
            params = self._get_params()
            if limit:
                params["limit"] = limit

            for track in _collect_nodes(
                limit,
                self,
                self.ws_prefix + ".getLovedTracks",
                cacheable,
                params,
                stream=stream,
            ):
                try:
                    artist = _extract(track, "name", 1)
                except IndexError:  # pragma: no cover
                    continue
                title = _extract(track, "name")
                date = _extract(track, "date")
                timestamp = track.getElementsByTagName("date")[0].getAttribute("uts")

                yield LovedTrack(Track(artist, title, self.network), date, timestamp)

        return _get_loved_tracks() if stream else list(_get_loved_tracks())

    def get_now_playing(self):
        """
        Returns the currently playing track, or None if nothing is playing.
        """

        params = self._get_params()
        params["limit"] = "1"

        doc = self._request(self.ws_prefix + ".getRecentTracks", False, params)

        tracks = doc.getElementsByTagName("track")

        if len(tracks) == 0:
            return None

        e = tracks[0]

        if not e.hasAttribute("nowplaying"):
            return None

        artist = _extract(e, "artist")
        title = _extract(e, "name")
        info = {"album": _extract(e, "album"), "image": _extract_all(e, "image")}

        return Track(artist, title, self.network, self.name, info=info)

    def get_recent_tracks(
        self,
        limit: int = 10,
        cacheable: bool = True,
        time_from=None,
        time_to=None,
        stream: bool = False,
        now_playing: bool = False,
    ):
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
        stream: If True, it will yield tracks as soon as a page has been retrieved.

        This method uses caching. Enable caching only if you're pulling a
        large amount of data.
        """

        def _get_recent_tracks():
            params = self._get_params()
            if limit:
                params["limit"] = limit + 1  # in case we remove the now playing track
            if time_from:
                params["from"] = time_from
            if time_to:
                params["to"] = time_to

            track_count = 0
            for track_node in _collect_nodes(
                limit + 1 if limit else None,
                self,
                self.ws_prefix + ".getRecentTracks",
                cacheable,
                params,
                stream=stream,
            ):
                if track_node.hasAttribute("nowplaying") and not now_playing:
                    continue  # to prevent the now playing track from sneaking in

                if limit and track_count >= limit:
                    break
                yield self._extract_played_track(track_node=track_node)
                track_count += 1

        return _get_recent_tracks() if stream else list(_get_recent_tracks())

    def get_country(self):
        """Returns the name of the country of the user."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        country = _extract(doc, "country")

        if country is None or country == "None":
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

        return int(doc.getElementsByTagName("registered")[0].getAttribute("unixtime"))

    def get_tagged_albums(self, tag, limit=None, cacheable: bool = True):
        """Returns the albums tagged by a user."""

        params = self._get_params()
        params["tag"] = tag
        params["taggingtype"] = "album"
        if limit:
            params["limit"] = limit
        doc = self._request(self.ws_prefix + ".getpersonaltags", cacheable, params)
        return _extract_albums(doc, self.network)

    def get_tagged_artists(self, tag, limit=None):
        """Returns the artists tagged by a user."""

        params = self._get_params()
        params["tag"] = tag
        params["taggingtype"] = "artist"
        if limit:
            params["limit"] = limit
        doc = self._request(self.ws_prefix + ".getpersonaltags", True, params)
        return _extract_artists(doc, self.network)

    def get_tagged_tracks(self, tag, limit=None, cacheable: bool = True):
        """Returns the tracks tagged by a user."""

        params = self._get_params()
        params["tag"] = tag
        params["taggingtype"] = "track"
        if limit:
            params["limit"] = limit
        doc = self._request(self.ws_prefix + ".getpersonaltags", cacheable, params)
        return _extract_tracks(doc, self.network)

    def get_top_albums(self, period=PERIOD_OVERALL, limit=None, cacheable: bool = True):
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
        params["period"] = period
        if limit:
            params["limit"] = limit

        doc = self._request(self.ws_prefix + ".getTopAlbums", cacheable, params)

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
        params["period"] = period
        if limit:
            params["limit"] = limit

        doc = self._request(self.ws_prefix + ".getTopArtists", True, params)

        return _extract_top_artists(doc, self.network)

    def get_top_tags(self, limit=None, cacheable: bool = True):
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
            seq.append(
                TopItem(
                    Tag(_extract(node, "name"), self.network), _extract(node, "count")
                )
            )

        return seq

    def get_top_tracks(
        self,
        period=PERIOD_OVERALL,
        limit=None,
        cacheable: bool = True,
        stream: bool = False,
    ):
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
        params["period"] = period
        params["limit"] = limit

        return self._get_things("getTopTracks", Track, params, cacheable, stream=stream)

    def get_track_scrobbles(
        self, artist, track, cacheable: bool = False, stream: bool = False
    ):
        """
        Get a list of this user's scrobbles of this artist's track,
        including scrobble time.
        """
        params = self._get_params()
        params["artist"] = artist
        params["track"] = track

        def _get_track_scrobbles():
            for track_node in _collect_nodes(
                None,
                self,
                self.ws_prefix + ".getTrackScrobbles",
                cacheable,
                params,
                stream=stream,
            ):
                yield self._extract_played_track(track_node)

        return _get_track_scrobbles() if stream else list(_get_track_scrobbles())

    def get_image(self, size=SIZE_EXTRA_LARGE):
        """
        Returns the user's avatar
        size can be one of:
            SIZE_EXTRA_LARGE
            SIZE_LARGE
            SIZE_MEDIUM
            SIZE_SMALL
        """

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _extract_all(doc, "image")[size]

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the URL of the user page on the network.
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

        return self.network._get_url(domain_name, "user") % {"name": name}

    def get_library(self):
        """Returns the associated Library object."""

        return Library(self, self.network)


class AuthenticatedUser(User):
    def __init__(self, network) -> None:
        super().__init__(user_name=network.username, network=network)

    def _get_params(self):
        return {"user": self.get_name()}

    def get_name(self, properly_capitalized: bool = False):
        """Returns the name of the authenticated user."""
        return super().get_name(properly_capitalized=properly_capitalized)


class _Search(_BaseObject):
    """An abstract class. Use one of its derivatives."""

    def __init__(self, ws_prefix, search_terms, network) -> None:
        super().__init__(network, ws_prefix)

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

    def __init__(self, album_name, network) -> None:
        super().__init__(
            ws_prefix="album", search_terms={"album": album_name}, network=network
        )

    def get_next_page(self):
        """Returns the next page of results as a sequence of Album objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("album"):
            seq.append(
                Album(
                    _extract(node, "artist"),
                    _extract(node, "name"),
                    self.network,
                    info={"image": _extract_all(node, "image")},
                )
            )

        return seq


class ArtistSearch(_Search):
    """Search for an artist by artist name."""

    def __init__(self, artist_name, network) -> None:
        super().__init__(
            ws_prefix="artist", search_terms={"artist": artist_name}, network=network
        )

    def get_next_page(self):
        """Returns the next page of results as a sequence of Artist objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("artist"):
            artist = Artist(
                _extract(node, "name"),
                self.network,
                info={"image": _extract_all(node, "image")},
            )
            artist.listener_count = _number(_extract(node, "listeners"))
            seq.append(artist)

        return seq


class TrackSearch(_Search):
    """
    Search for a track by track title. If you don't want to narrow the results
    down by specifying the artist name, set it to empty string.
    """

    def __init__(self, artist_name, track_title, network) -> None:
        super().__init__(
            ws_prefix="track",
            search_terms={"track": track_title, "artist": artist_name},
            network=network,
        )

    def get_next_page(self):
        """Returns the next page of results as a sequence of Track objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("track"):
            track = Track(
                _extract(node, "artist"),
                _extract(node, "name"),
                self.network,
                info={"image": _extract_all(node, "image")},
            )
            track.listener_count = _number(_extract(node, "listeners"))
            seq.append(track)

        return seq


def md5(text):
    """Returns the md5 hash of a string."""

    h = hashlib.md5()
    h.update(_unicode(text).encode("utf-8"))

    return h.hexdigest()


def _unicode(text):
    if isinstance(text, bytes):
        return str(text, "utf-8")
    else:
        return str(text)


def cleanup_nodes(doc):
    """
    Remove text nodes containing only whitespace
    """
    for node in doc.documentElement.childNodes:
        if node.nodeType == Node.TEXT_NODE and node.nodeValue.isspace():
            doc.documentElement.removeChild(node)
    return doc


def _collect_nodes(
    limit, sender, method_name, cacheable, params=None, stream: bool = False
):
    """
    Returns a sequence of dom.Node objects about as close to limit as possible
    """
    if not params:
        params = sender._get_params()

    def _stream_collect_nodes():
        node_count = 0
        page = 1
        end_of_pages = False

        while not end_of_pages and (not limit or (limit and node_count < limit)):
            params["page"] = str(page)

            tries = 1
            while True:
                try:
                    doc = sender._request(method_name, cacheable, params)
                    break  # success
                except Exception as e:
                    if tries >= 3:
                        raise PyLastError() from e
                    # Wait and try again
                    time.sleep(1)
                    tries += 1

            doc = cleanup_nodes(doc)

            # break if there are no child nodes
            if not doc.documentElement.childNodes:
                break
            main = doc.documentElement.childNodes[0]

            if main.hasAttribute("totalPages") or main.hasAttribute("totalpages"):
                total_pages = _number(
                    main.getAttribute("totalPages") or main.getAttribute("totalpages")
                )
            else:
                raise PyLastError("No total pages attribute")

            for node in main.childNodes:
                if not node.nodeType == xml.dom.Node.TEXT_NODE and (
                    not limit or (node_count < limit)
                ):
                    node_count += 1
                    yield node

            end_of_pages = page >= total_pages

            page += 1

    return _stream_collect_nodes() if stream else list(_stream_collect_nodes())


def _extract(node, name, index: int = 0):
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
        info = {"image": _extract_all(node, "image")}

        seq.append(TopItem(Album(artist, name, network, info=info), playcount))

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
    """Does all kinds of tricks on a text to make it safe to use in a URL."""

    return quote_plus(quote_plus(str(text))).lower()


def _number(string):
    """
    Extracts an int from a string.
    Returns a 0 if None or an empty string was passed.
    """

    if not string:
        return 0
    else:
        try:
            return int(string)
        except ValueError:
            return float(string)


def _unescape_htmlentity(string):
    mapping = html.entities.name2codepoint
    for key in mapping:
        string = string.replace(f"&{key};", chr(mapping[key]))

    return string


def _parse_response(response: str) -> xml.dom.minidom.Document:
    response = str(response).replace("opensearch:", "")
    try:
        doc = minidom.parseString(response)
    except xml.parsers.expat.ExpatError:
        # Try again. For performance, we only remove when needed in rare cases.
        doc = minidom.parseString(_remove_invalid_xml_chars(response))
    return doc


def _remove_invalid_xml_chars(string: str) -> str:
    return re.sub(
        r"[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u10000-\u10FFF]+", "", string
    )


# End of file
