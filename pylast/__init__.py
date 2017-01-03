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
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# https://github.com/pylast/pylast

import hashlib
from xml.dom import minidom, Node
import xml.dom
import time
import shelve
import tempfile
import sys
import collections
import warnings
import re
import six

__version__ = '1.7.0'
__author__ = 'Amr Hassan, hugovk'
__copyright__ = "Copyright (C) 2008-2010 Amr Hassan, 2013-2017 hugovk"
__license__ = "apache2"
__email__ = 'amr.hassan@gmail.com'


def _deprecation_warning(message):
    warnings.warn(message, DeprecationWarning)


def _can_use_ssl_securely():
    # Python 3.3 doesn't support create_default_context() but can be made to
    # work sanely.
    # <2.7.9 and <3.2 never did any SSL verification so don't do SSL there.
    # >3.4 and >2.7.9 has sane defaults so use SSL there.
    v = sys.version_info
    return v > (3, 3) or ((2, 7, 9) < v < (3, 0))

if _can_use_ssl_securely():
    import ssl

if sys.version_info[0] == 3:
    if _can_use_ssl_securely():
        from http.client import HTTPSConnection
    else:
        from http.client import HTTPConnection
    import html.entities as htmlentitydefs
    from urllib.parse import splithost as url_split_host
    from urllib.parse import quote_plus as url_quote_plus

    unichr = chr

elif sys.version_info[0] == 2:
    if _can_use_ssl_securely():
        from httplib import HTTPSConnection
    else:
        from httplib import HTTPConnection
    import htmlentitydefs
    from urllib import splithost as url_split_host
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

EVENT_ATTENDING = '0'
EVENT_MAYBE_ATTENDING = '1'
EVENT_NOT_ATTENDING = '2'

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


USER_MALE = 'Male'
USER_FEMALE = 'Female'

SCROBBLE_SOURCE_USER = "P"
SCROBBLE_SOURCE_NON_PERSONALIZED_BROADCAST = "R"
SCROBBLE_SOURCE_PERSONALIZED_BROADCAST = "E"
SCROBBLE_SOURCE_LASTFM = "L"
SCROBBLE_SOURCE_UNKNOWN = "U"

SCROBBLE_MODE_PLAYED = ""
SCROBBLE_MODE_LOVED = "L"
SCROBBLE_MODE_BANNED = "B"
SCROBBLE_MODE_SKIPPED = "S"

# From http://boodebr.org/main/python/all-about-python-and-unicode#UNI_XML
RE_XML_ILLEGAL = (u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' +
                  u'|' +
                  u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])'
                  %
                  (unichr(0xd800), unichr(0xdbff), unichr(0xdc00),
                   unichr(0xdfff), unichr(0xd800), unichr(0xdbff),
                   unichr(0xdc00), unichr(0xdfff), unichr(0xd800),
                   unichr(0xdbff), unichr(0xdc00), unichr(0xdfff)))

XML_ILLEGAL = re.compile(RE_XML_ILLEGAL)

# Python <=3.3 doesn't support create_default_context()
# <2.7.9 and <3.2 never did any SSL verification
# FIXME This can be removed after 2017-09 when 3.3 is no longer supported and
# pypy3 uses 3.4 or later, see
# https://en.wikipedia.org/wiki/CPython#Version_history
if sys.version_info[0] == 3 and sys.version_info[1] == 3:
    import certifi
    SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    SSL_CONTEXT.verify_mode = ssl.CERT_REQUIRED
    SSL_CONTEXT.options |= ssl.OP_NO_COMPRESSION
    # Intermediate from https://wiki.mozilla.org/Security/Server_Side_TLS
    # Create the cipher string
    cipher_string = """
    ECDHE-ECDSA-CHACHA20-POLY1305
    ECDHE-RSA-CHACHA20-POLY1305
    ECDHE-ECDSA-AES128-GCM-SHA256
    ECDHE-RSA-AES128-GCM-SHA256
    ECDHE-ECDSA-AES256-GCM-SHA384
    ECDHE-RSA-AES256-GCM-SHA384
    DHE-RSA-AES128-GCM-SHA256
    DHE-RSA-AES256-GCM-SHA384
    ECDHE-ECDSA-AES128-SHA256
    ECDHE-RSA-AES128-SHA256
    ECDHE-ECDSA-AES128-SHA
    ECDHE-RSA-AES256-SHA384
    ECDHE-RSA-AES128-SHA
    ECDHE-ECDSA-AES256-SHA384
    ECDHE-ECDSA-AES256-SHA
    ECDHE-RSA-AES256-SHA
    DHE-RSA-AES128-SHA256
    DHE-RSA-AES128-SHA
    DHE-RSA-AES256-SHA256
    DHE-RSA-AES256-SHA
    ECDHE-ECDSA-DES-CBC3-SHA
    ECDHE-RSA-DES-CBC3-SHA
    EDH-RSA-DES-CBC3-SHA
    AES128-GCM-SHA256
    AES256-GCM-SHA384
    AES128-SHA256
    AES256-SHA256
    AES128-SHA
    AES256-SHA
    DES-CBC3-SHA
    !DSS
    """
    cipher_string = ' '.join(cipher_string.split())
    SSL_CONTEXT.set_ciphers(cipher_string)
    SSL_CONTEXT.load_verify_locations(certifi.where())

# Python >3.4 and >2.7.9 has sane defaults
elif sys.version_info > (3, 4) or ((2, 7, 9) < sys.version_info < (3, 0)):
    SSL_CONTEXT = ssl.create_default_context()


class _Network(object):
    """
    A music social network website such as Last.fm or
    one with a Last.fm-compatible API.
    """

    def __init__(
            self, name, homepage, ws_server, api_key, api_secret, session_key,
            submission_server, username, password_hash, domain_names, urls):
        """
            name: the name of the network
            homepage: the homepage URL
            ws_server: the URL of the webservices server
            api_key: a provided API_KEY
            api_secret: a provided API_SECRET
            session_key: a generated session_key or None
            submission_server: the URL of the server to which tracks are
                submitted (scrobbled)
            username: a username of a valid user
            password_hash: the output of pylast.md5(password) where password is
                the user's password
            domain_names: a dict mapping each DOMAIN_* value to a string domain
                name
            urls: a dict mapping types to URLs

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
        self.submission_server = submission_server
        self.username = username
        self.password_hash = password_hash
        self.domain_names = domain_names
        self.urls = urls

        self.cache_backend = None
        self.proxy_enabled = False
        self.proxy = None
        self.last_call_time = 0
        self.limit_rate = False

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

    def get_metro(self, metro_name, country_name):
        """
            Returns a metro object
        """

        return Metro(metro_name, country_name, self)

    def get_group(self, name):
        """
            Returns a Group object
        """

        return Group(name, self)

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

    def get_scrobbler(self, client_id, client_version):
        """
            Returns a Scrobbler object used for submitting tracks to the server

            Quote from http://www.last.fm/api/submissions:
            ========
            Client identifiers are used to provide a centrally managed database
            of the client versions, allowing clients to be banned if they are
            found to be behaving undesirably. The client ID is associated with
            a version number on the server, however these are only incremented
            if a client is banned and do not have to reflect the version of the
            actual client application.

            During development, clients which have not been allocated an
            identifier should use the identifier tst, with a version number of
            1.0. Do not distribute code or client implementations which use
            this test identifier. Do not use the identifiers used by other
            clients.
            =========

            To obtain a new client identifier please contact:
                * Last.fm: submissions@last.fm
                * # TODO: list others

            ...and provide us with the name of your client and its homepage
            address.
        """

        _deprecation_warning(
            "Use _Network.scrobble(...), _Network.scrobble_many(...),"
            " and Network.update_now_playing(...) instead")

        return Scrobbler(self, client_id, client_version)

    def _get_language_domain(self, domain_language):
        """
            Returns the mapped domain name of the network to a DOMAIN_* value
        """

        if domain_language in self.domain_names:
            return self.domain_names[domain_language]

    def _get_url(self, domain, url_type):
        return "http://%s/%s" % (
            self._get_language_domain(domain), self.urls[url_type])

    def _get_ws_auth(self):
        """
            Returns an (API_KEY, API_SECRET, SESSION_KEY) tuple.
        """
        return (self.api_key, self.api_secret, self.session_key)

    def _delay_call(self):
        """
            Makes sure that web service calls are at least 0.2 seconds apart.
        """

        # Delay time in seconds from section 4.4 of http://www.last.fm/api/tos
        DELAY_TIME = 0.2
        now = time.time()

        time_since_last = now - self.last_call_time

        if time_since_last < DELAY_TIME:
            time.sleep(DELAY_TIME - time_since_last)

        self.last_call_time = now

    def create_new_playlist(self, title, description):
        """
            Creates a playlist for the authenticated user and returns it
                title: The title of the new playlist.
                description: The description of the new playlist.
        """

        params = {}
        params['title'] = title
        params['description'] = description

        doc = _Request(self, 'playlist.create', params).execute(False)

        e_id = doc.getElementsByTagName("id")[0].firstChild.data
        user = doc.getElementsByTagName('playlists')[0].getAttribute('user')

        return Playlist(user, e_id, self)

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

    def get_geo_events(
            self, longitude=None, latitude=None, location=None, distance=None,
            tag=None, festivalsonly=None, limit=None, cacheable=True):
        """
        Returns all events in a specific location by country or city name.
        Parameters:
        longitude (Optional) : Specifies a longitude value to retrieve events
            for (service returns nearby events by default)
        latitude (Optional) : Specifies a latitude value to retrieve events for
            (service returns nearby events by default)
        location (Optional) : Specifies a location to retrieve events for
            (service returns nearby events by default)
        distance (Optional) : Find events within a specified radius
            (in kilometres)
        tag (Optional) : Specifies a tag to filter by.
        festivalsonly[0|1] (Optional) : Whether only festivals should be
            returned, or all events.
        limit (Optional) : The number of results to fetch per page.
            Defaults to 10.
        """

        params = {}

        if longitude:
            params["long"] = longitude
        if latitude:
            params["lat"] = latitude
        if location:
            params["location"] = location
        if limit:
            params["limit"] = limit
        if distance:
            params["distance"] = distance
        if tag:
            params["tag"] = tag
        if festivalsonly:
            params["festivalsonly"] = 1
        elif not festivalsonly:
            params["festivalsonly"] = 0

        doc = _Request(self, "geo.getEvents", params).execute(cacheable)

        return _extract_events_from_doc(doc, self)

    def get_metro_weekly_chart_dates(self, cacheable=True):
        """
        Returns a list of From and To tuples for the available metro charts.
        """

        doc = _Request(self, "geo.getMetroWeeklyChartlist").execute(cacheable)

        seq = []
        for node in doc.getElementsByTagName("chart"):
            seq.append((node.getAttribute("from"), node.getAttribute("to")))

        return seq

    def get_metros(self, country=None, cacheable=True):
        """
        Get a list of valid countries and metros for use in the other
        webservices.
        Parameters:
        country (Optional) : Optionally restrict the results to those Metros
            from a particular country, as defined by the ISO 3166-1 country
            names standard.
        """
        params = {}

        if country:
            params["country"] = country

        doc = _Request(self, "geo.getMetros", params).execute(cacheable)

        metros = doc.getElementsByTagName("metro")
        seq = []

        for metro in metros:
            name = _extract(metro, "name")
            country = _extract(metro, "country")

            seq.append(Metro(name, country, self))

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

    def search_for_tag(self, tag_name):
        """Searches of a tag by its name. Returns a TagSearch object.
        Use get_next_page() to retrieve sequences of results."""

        return TagSearch(tag_name, self)

    def search_for_track(self, artist_name, track_name):
        """Searches of a track by its name and its artist. Set artist to an
        empty string if not available.
        Returns a TrackSearch object.
        Use get_next_page() to retrieve sequences of results."""

        return TrackSearch(artist_name, track_name, self)

    def search_for_venue(self, venue_name, country_name):
        """Searches of a venue by its name and its country. Set country_name to
        an empty string if not available.
        Returns a VenueSearch object.
        Use get_next_page() to retrieve sequences of results."""

        return VenueSearch(venue_name, country_name, self)

    def get_track_by_mbid(self, mbid):
        """Looks up a track by its MusicBrainz ID"""

        params = {"mbid": mbid}

        doc = _Request(self, "track.getInfo", params).execute(True)

        return Track(_extract(doc, "name", 1), _extract(doc, "name"), self)

    def get_artist_by_mbid(self, mbid):
        """Loooks up an artist by its MusicBrainz ID"""

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

    def get_play_links(self, link_type, things, cacheable=True):
        method = link_type + ".getPlaylinks"
        params = {}

        for i, thing in enumerate(things):
            if link_type == "artist":
                params['artist[' + str(i) + ']'] = thing
            elif link_type == "album":
                params['artist[' + str(i) + ']'] = thing.artist
                params['album[' + str(i) + ']'] = thing.title
            elif link_type == "track":
                params['artist[' + str(i) + ']'] = thing.artist
                params['track[' + str(i) + ']'] = thing.title

        doc = _Request(self, method, params).execute(cacheable)

        seq = []

        for node in doc.getElementsByTagName("externalids"):
            spotify = _extract(node, "spotify")
            seq.append(spotify)

        return seq

    def get_artist_play_links(self, artists, cacheable=True):
        return self.get_play_links("artist", artists, cacheable)

    def get_album_play_links(self, albums, cacheable=True):
        return self.get_play_links("album", albums, cacheable)

    def get_track_play_links(self, tracks, cacheable=True):
        return self.get_play_links("track", tracks, cacheable)


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
    http://www.last.fm/api/account
    """

    def __init__(
            self, api_key="", api_secret="", session_key="", username="",
            password_hash=""):
        _Network.__init__(
            self,
            name="Last.fm",
            homepage="http://last.fm",
            ws_server=("ws.audioscrobbler.com", "/2.0/"),
            api_key=api_key,
            api_secret=api_secret,
            session_key=session_key,
            submission_server="http://post.audioscrobbler.com:80/",
            username=username,
            password_hash=password_hash,
            domain_names={
                DOMAIN_ENGLISH: 'www.last.fm',
                DOMAIN_GERMAN: 'www.lastfm.de',
                DOMAIN_SPANISH: 'www.lastfm.es',
                DOMAIN_FRENCH: 'www.lastfm.fr',
                DOMAIN_ITALIAN: 'www.lastfm.it',
                DOMAIN_POLISH: 'www.lastfm.pl',
                DOMAIN_PORTUGUESE: 'www.lastfm.com.br',
                DOMAIN_SWEDISH: 'www.lastfm.se',
                DOMAIN_TURKISH: 'www.lastfm.com.tr',
                DOMAIN_RUSSIAN: 'www.lastfm.ru',
                DOMAIN_JAPANESE: 'www.lastfm.jp',
                DOMAIN_CHINESE: 'cn.last.fm',
            },
            urls={
                "album": "music/%(artist)s/%(album)s",
                "artist": "music/%(artist)s",
                "event": "event/%(id)s",
                "country": "place/%(country_name)s",
                "playlist": "user/%(user)s/library/playlists/%(appendix)s",
                "tag": "tag/%(name)s",
                "track": "music/%(artist)s/_/%(title)s",
                "group": "group/%(name)s",
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


def get_lastfm_network(
        api_key="", api_secret="", session_key="", username="",
        password_hash=""):
    """
    Returns a preconfigured _Network object for Last.fm

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
    http://www.last.fm/api/account
    """

    _deprecation_warning("Create a LastFMNetwork object instead")

    return LastFMNetwork(
        api_key, api_secret, session_key, username, password_hash)


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
            homepage="http://libre.fm",
            ws_server=("libre.fm", "/2.0/"),
            api_key=api_key,
            api_secret=api_secret,
            session_key=session_key,
            submission_server="http://turtle.libre.fm:80/",
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
                "event": "event/%(id)s",
                "country": "place/%(country_name)s",
                "playlist": "user/%(user)s/library/playlists/%(appendix)s",
                "tag": "tag/%(name)s",
                "track": "music/%(artist)s/_/%(title)s",
                "group": "group/%(name)s",
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


def get_librefm_network(
        api_key="", api_secret="", session_key="", username="",
        password_hash=""):
    """
    Returns a preconfigured _Network object for Libre.fm

    api_key: a provided API_KEY
    api_secret: a provided API_SECRET
    session_key: a generated session_key or None
    username: a username of a valid user
    password_hash: the output of pylast.md5(password) where password is the
        user's password

    if username and password_hash were provided and not session_key,
    session_key will be generated automatically when needed.
    """

    _deprecation_warning(
        "DeprecationWarning: Create a LibreFMNetwork object instead")

    return LibreFMNetwork(
        api_key, api_secret, session_key, username, password_hash)


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
            if _can_use_ssl_securely():
                conn = HTTPSConnection(
                    context=SSL_CONTEXT,
                    host=self.network._get_proxy()[0],
                    port=self.network._get_proxy()[1])
            else:
                conn = HTTPConnection(
                    host=self.network._get_proxy()[0],
                    port=self.network._get_proxy()[1])

            try:
                conn.request(
                    method='POST', url="http://" + HOST_NAME + HOST_SUBDIR,
                    body=data, headers=headers)
            except Exception as e:
                raise NetworkError(self.network, e)

        else:
            if _can_use_ssl_securely():
                conn = HTTPSConnection(
                    context=SSL_CONTEXT,
                    host=HOST_NAME
                )
            else:
                conn = HTTPConnection(
                    host=HOST_NAME
                )

            try:
                conn.request(
                    method='POST', url=HOST_SUBDIR, body=data, headers=headers)
            except Exception as e:
                raise NetworkError(self.network, e)

        try:
            response_text = _unicode(conn.getresponse().read())
        except Exception as e:
            raise MalformedResponseError(self.network, e)

        response_text = XML_ILLEGAL.sub("?", response_text)

        self._check_response_for_errors(response_text)
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

    def get_web_auth_session_key(self, url):
        """
        Retrieves the session key of a web authorization process by its url.
        """

        if url in self.web_auth_tokens.keys():
            token = self.web_auth_tokens[url]
        else:
            # That's going to raise a WSError of an unauthorized token when the
            # request is executed.
            token = ""

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
Shout = collections.namedtuple(
    "Shout", ["body", "author", "date"])


def _string_output(funct):
    def r(*args):
        return _string(funct(*args))

    return r


def _pad_list(given_list, desired_length, padding=None):
    """
        Pads a list to be of the desired_length.
    """

    while len(given_list) < desired_length:
        given_list.append(padding)

    return given_list


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

    def get_top_fans(self, limit=None, cacheable=True):
        """Returns a list of the Users who played this the most.
        # Parameters:
            * limit int: Max elements.
        # For Artist/Track
        """

        doc = self._request(self.ws_prefix + '.getTopFans', cacheable)

        seq = []

        elements = doc.getElementsByTagName('user')

        for element in elements:
            if limit and len(seq) >= limit:
                break

            name = _extract(element, 'name')
            weight = _number(_extract(element, 'weight'))

            seq.append(TopItem(User(name, self.network), weight))

        return seq

    def share(self, users, message=None):
        """
        Shares this (sends out recommendations).
        Parameters:
            * users [User|str,]: A list that can contain usernames, emails,
            User objects, or all of them.
            * message str: A message to include in the recommendation message.
        Only for Artist/Event/Track.
        """

        # Last.fm currently accepts a max of 10 recipient at a time
        while(len(users) > 10):
            section = users[0:9]
            users = users[9:]
            self.share(section, message)

        nusers = []
        for user in users:
            if isinstance(user, User):
                nusers.append(user.get_name())
            else:
                nusers.append(user)

        params = self._get_params()
        recipients = ','.join(nusers)
        params['recipient'] = recipients
        if message:
            params['message'] = message

        self._request(self.ws_prefix + '.share', False, params)

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

    def get_shouts(self, limit=50, cacheable=False):
        """
            Returns a sequence of Shout objects
        """

        shouts = []
        for node in _collect_nodes(
                limit,
                self,
                self.ws_prefix + ".getShouts",
                cacheable):
            shouts.append(
                Shout(
                    _extract(node, "body"),
                    User(_extract(node, "author"), self.network),
                    _extract(node, "date")
                )
            )
        return shouts


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
        Only for Group or User.
        """
        return self.get_weekly_charts("album", from_date, to_date)

    def get_weekly_artist_charts(self, from_date=None, to_date=None):
        """
        Returns the weekly artist charts for the week starting from the
        from_date value to the to_date value.
        Only for Group, Tag or User.
        """
        return self.get_weekly_charts("artist", from_date, to_date)

    def get_weekly_track_charts(self, from_date=None, to_date=None):
        """
        Returns the weekly track charts for the week starting from the
        from_date value to the to_date value.
        Only for Group or User.
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

    def get_id(self):
        """Returns the ID on the network."""

        return _extract(
            self._request(self.ws_prefix + ".getInfo", cacheable=True), "id")

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

    def get_release_date(self):
        """Returns the release date of the album."""

        return _extract(self._request(
            self.ws_prefix + ".getInfo", cacheable=True), "releasedate")

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
                self.ws_prefix + ".getInfo", cacheable=True), "tracks")

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

    def get_upcoming_events(self):
        """Returns a list of the upcoming Events for this artist."""

        doc = self._request(self.ws_prefix + '.getEvents', True)

        return _extract_events_from_doc(doc, self.network)

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

    def shout(self, message):
        """
            Post a shout
        """

        params = self._get_params()
        params["message"] = message

        self._request("artist.Shout", False, params)

    def get_band_members(self):
        """Returns a list of band members or None if unknown."""

        names = None
        doc = self._request(self.ws_prefix + ".getInfo", True)

        for node in doc.getElementsByTagName("bandmembers"):
            names = _extract_all(node, "name")

        return names


class Event(_BaseObject):
    """An event."""

    id = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, event_id, network):
        _BaseObject.__init__(self, network, 'event')

        self.id = event_id

    def __repr__(self):
        return "pylast.Event(%s, %s)" % (repr(self.id), repr(self.network))

    @_string_output
    def __str__(self):
        return "Event #" + str(self.get_id())

    def __eq__(self, other):
        if type(self) is type(other):
            return self.get_id() == other.get_id()
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def _get_params(self):
        return {'event': self.get_id()}

    def attend(self, attending_status):
        """Sets the attending status.
        * attending_status: The attending status. Possible values:
          o EVENT_ATTENDING
          o EVENT_MAYBE_ATTENDING
          o EVENT_NOT_ATTENDING
        """

        params = self._get_params()
        params['status'] = attending_status

        self._request('event.attend', False, params)

    def get_attendees(self):
        """
            Get a list of attendees for an event
        """

        doc = self._request("event.getAttendees", False)

        users = []
        for name in _extract_all(doc, "name"):
            users.append(User(name, self.network))

        return users

    def get_id(self):
        """Returns the id of the event on the network. """

        return self.id

    def get_title(self):
        """Returns the title of the event. """

        doc = self._request("event.getInfo", True)

        return _extract(doc, "title")

    def get_headliner(self):
        """Returns the headliner of the event. """

        doc = self._request("event.getInfo", True)

        return Artist(_extract(doc, "headliner"), self.network)

    def get_artists(self):
        """Returns a list of the participating Artists. """

        doc = self._request("event.getInfo", True)
        names = _extract_all(doc, "artist")

        artists = []
        for name in names:
            artists.append(Artist(name, self.network))

        return artists

    def get_venue(self):
        """Returns the venue where the event is held."""

        doc = self._request("event.getInfo", True)

        v = doc.getElementsByTagName("venue")[0]
        venue_id = _number(_extract(v, "id"))

        return Venue(venue_id, self.network, venue_element=v)

    def get_start_date(self):
        """Returns the date when the event starts."""

        doc = self._request("event.getInfo", True)

        return _extract(doc, "startDate")

    def get_description(self):
        """Returns the description of the event. """

        doc = self._request("event.getInfo", True)

        return _extract(doc, "description")

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

        doc = self._request("event.getInfo", True)

        return _extract_all(doc, "image")[size]

    def get_attendance_count(self):
        """Returns the number of attending people. """

        doc = self._request("event.getInfo", True)

        return _number(_extract(doc, "attendance"))

    def get_review_count(self):
        """Returns the number of available reviews for this event. """

        doc = self._request("event.getInfo", True)

        return _number(_extract(doc, "reviews"))

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the event page on the network.
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

        return self.network._get_url(
            domain_name, "event") % {'id': self.get_id()}

    def shout(self, message):
        """
            Post a shout
        """

        params = self._get_params()
        params["message"] = message

        self._request("event.Shout", False, params)


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

    def _get_name_from_code(self, alpha2code):
        # TODO: Have this function lookup the alpha-2 code and return the
        # country name.

        return alpha2code

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
        """Returns the url of the event page on the network.
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


class Metro(_BaseObject):
    """A metro at Last.fm."""

    name = None
    country = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, name, country, network):
        _BaseObject.__init__(self, network, None)

        self.name = name
        self.country = country

    def __repr__(self):
        return "pylast.Metro(%s, %s, %s)" % (
            repr(self.name), repr(self.country), repr(self.network))

    @_string_output
    def __str__(self):
        return self.get_name() + ", " + self.get_country()

    def __eq__(self, other):
        return (self.get_name().lower() == other.get_name().lower() and
                self.get_country().lower() == other.get_country().lower())

    def __ne__(self, other):
        return (self.get_name() != other.get_name() or
                self.get_country().lower() != other.get_country().lower())

    def _get_params(self):
        return {'metro': self.get_name(), 'country': self.get_country()}

    def get_name(self):
        """Returns the metro name."""

        return self.name

    def get_country(self):
        """Returns the metro country."""

        return self.country

    def _get_chart(
            self, method, tag="artist", limit=None, from_date=None,
            to_date=None, cacheable=True):
        """Internal helper for getting geo charts."""
        params = self._get_params()
        if limit:
            params["limit"] = limit
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date

        doc = self._request(method, cacheable, params)

        seq = []
        for node in doc.getElementsByTagName(tag):
            if tag == "artist":
                item = Artist(_extract(node, "name"), self.network)
            elif tag == "track":
                title = _extract(node, "name")
                artist = _extract_element_tree(node).get('artist')['name']
                item = Track(artist, title, self.network)
            else:
                return None
            weight = _number(_extract(node, "listeners"))
            seq.append(TopItem(item, weight))

        return seq

    def get_artist_chart(
            self, tag="artist", limit=None, from_date=None, to_date=None,
            cacheable=True):
        """Get a chart of artists for a metro.
        Parameters:
        from_date (Optional) : Beginning timestamp of the weekly range
            requested
        to_date (Optional) : Ending timestamp of the weekly range requested
        limit (Optional) : The number of results to fetch per page.
            Defaults to 50.
        """
        return self._get_chart(
            "geo.getMetroArtistChart", tag=tag, limit=limit,
            from_date=from_date, to_date=to_date, cacheable=cacheable)

    def get_hype_artist_chart(
            self, tag="artist", limit=None, from_date=None, to_date=None,
            cacheable=True):
        """Get a chart of hyped (up and coming) artists for a metro.
        Parameters:
        from_date (Optional) : Beginning timestamp of the weekly range
            requested
        to_date (Optional) : Ending timestamp of the weekly range requested
        limit (Optional) : The number of results to fetch per page.
            Defaults to 50.
        """
        return self._get_chart(
            "geo.getMetroHypeArtistChart", tag=tag, limit=limit,
            from_date=from_date, to_date=to_date, cacheable=cacheable)

    def get_unique_artist_chart(
            self, tag="artist", limit=None, from_date=None, to_date=None,
            cacheable=True):
        """Get a chart of the artists which make that metro unique.
        Parameters:
        from_date (Optional) : Beginning timestamp of the weekly range
            requested
        to_date (Optional) : Ending timestamp of the weekly range requested
        limit (Optional) : The number of results to fetch per page.
            Defaults to 50.
        """
        return self._get_chart(
            "geo.getMetroUniqueArtistChart", tag=tag, limit=limit,
            from_date=from_date, to_date=to_date, cacheable=cacheable)

    def get_track_chart(
            self, tag="track", limit=None, from_date=None, to_date=None,
            cacheable=True):
        """Get a chart of tracks for a metro.
        Parameters:
        from_date (Optional) : Beginning timestamp of the weekly range
            requested
        to_date (Optional) : Ending timestamp of the weekly range requested
        limit (Optional) : The number of results to fetch per page.
            Defaults to 50.
        """
        return self._get_chart(
            "geo.getMetroTrackChart", tag=tag, limit=limit,
            from_date=from_date, to_date=to_date, cacheable=cacheable)

    def get_hype_track_chart(
            self, tag="track", limit=None, from_date=None, to_date=None,
            cacheable=True):
        """Get a chart of tracks for a metro.
        Parameters:
        from_date (Optional) : Beginning timestamp of the weekly range
            requested
        to_date (Optional) : Ending timestamp of the weekly range requested
        limit (Optional) : The number of results to fetch per page.
            Defaults to 50.
        """
        return self._get_chart(
            "geo.getMetroHypeTrackChart", tag=tag,
            limit=limit, from_date=from_date, to_date=to_date,
            cacheable=cacheable)

    def get_unique_track_chart(
            self, tag="track", limit=None, from_date=None, to_date=None,
            cacheable=True):
        """Get a chart of tracks for a metro.
        Parameters:
        from_date (Optional) : Beginning timestamp of the weekly range
            requested
        to_date (Optional) : Ending timestamp of the weekly range requested
        limit (Optional) : The number of results to fetch per page.
            Defaults to 50.
        """
        return self._get_chart(
            "geo.getMetroUniqueTrackChart", tag=tag, limit=limit,
            from_date=from_date, to_date=to_date, cacheable=cacheable)


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

        self._albums_index = 0
        self._artists_index = 0
        self._tracks_index = 0

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

    def add_album(self, album):
        """Add an album to this library."""

        params = self._get_params()
        params["artist"] = album.get_artist().get_name()
        params["album"] = album.get_name()

        self._request("library.addAlbum", False, params)

    def remove_album(self, album):
        """Remove an album from this library."""

        params = self._get_params()
        params["artist"] = album.get_artist().get_name()
        params["album"] = album.get_name()

        self._request(self.ws_prefix + ".removeAlbum", False, params)

    def add_artist(self, artist):
        """Add an artist to this library."""

        params = self._get_params()
        if type(artist) == str:
            params["artist"] = artist
        else:
            params["artist"] = artist.get_name()

        self._request(self.ws_prefix + ".addArtist", False, params)

    def remove_artist(self, artist):
        """Remove an artist from this library."""

        params = self._get_params()
        if type(artist) == str:
            params["artist"] = artist
        else:
            params["artist"] = artist.get_name()

        self._request(self.ws_prefix + ".removeArtist", False, params)

    def add_track(self, track):
        """Add a track to this library."""

        params = self._get_params()
        params["track"] = track.get_title()

        self._request(self.ws_prefix + ".addTrack", False, params)

    def get_albums(self, artist=None, limit=50, cacheable=True):
        """
        Returns a sequence of Album objects
        If no artist is specified, it will return all, sorted by decreasing
        play count.
        If limit==None it will return all (may take a while)
        """

        params = self._get_params()
        if artist:
            params["artist"] = artist

        seq = []
        for node in _collect_nodes(
                limit,
                self,
                self.ws_prefix + ".getAlbums",
                cacheable,
                params):
            name = _extract(node, "name")
            artist = _extract(node, "name", 1)
            playcount = _number(_extract(node, "playcount"))
            tagcount = _number(_extract(node, "tagcount"))

            seq.append(LibraryItem(
                Album(artist, name, self.network), playcount, tagcount))

        return seq

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

    def get_tracks(self, artist=None, album=None, limit=50, cacheable=True):
        """
        Returns a sequence of Album objects
        If limit==None it will return all (may take a while)
        """

        params = self._get_params()
        if artist:
            params["artist"] = artist
        if album:
            params["album"] = album

        seq = []
        for node in _collect_nodes(
                limit,
                self,
                self.ws_prefix + ".getTracks",
                cacheable,
                params):
            name = _extract(node, "name")
            artist = _extract(node, "name", 1)
            playcount = _number(_extract(node, "playcount"))
            tagcount = _number(_extract(node, "tagcount"))

            seq.append(LibraryItem(
                Track(artist, name, self.network), playcount, tagcount))

        return seq

    def remove_scrobble(self, artist, title, timestamp):
        """Remove a scrobble from a user's Last.fm library. Parameters:
            artist (Required) : The artist that composed the track
            title (Required) : The name of the track
            timestamp (Required) : The unix timestamp of the scrobble
                                   that you wish to remove
        """

        params = self._get_params()
        params["artist"] = artist
        params["track"] = title
        params["timestamp"] = timestamp

        self._request(self.ws_prefix + ".removeScrobble", False, params)


class Playlist(_BaseObject):
    """A Last.fm user playlist."""

    id = None
    user = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, user, playlist_id, network):
        _BaseObject.__init__(self, network, "playlist")

        if isinstance(user, User):
            self.user = user
        else:
            self.user = User(user, self.network)

        self.id = playlist_id

    @_string_output
    def __str__(self):
        return repr(self.user) + "'s playlist # " + repr(self.id)

    def _get_info_node(self):
        """
        Returns the node from user.getPlaylists where this playlist's info is.
        """

        doc = self._request("user.getPlaylists", True)

        for node in doc.getElementsByTagName("playlist"):
            if _extract(node, "id") == str(self.get_id()):
                return node

    def _get_params(self):
        return {'user': self.user.get_name(), 'playlistID': self.get_id()}

    def get_id(self):
        """Returns the playlist ID."""

        return self.id

    def get_user(self):
        """Returns the owner user of this playlist."""

        return self.user

    def get_tracks(self):
        """Returns a list of the tracks on this user playlist."""

        uri = _unicode('lastfm://playlist/%s') % self.get_id()

        return XSPF(uri, self.network).get_tracks()

    def add_track(self, track):
        """Adds a Track to this Playlist."""

        params = self._get_params()
        params['artist'] = track.get_artist().get_name()
        params['track'] = track.get_title()

        self._request('playlist.addTrack', False, params)

    def get_title(self):
        """Returns the title of this playlist."""

        return _extract(self._get_info_node(), "title")

    def get_creation_date(self):
        """Returns the creation date of this playlist."""

        return _extract(self._get_info_node(), "date")

    def get_size(self):
        """Returns the number of tracks in this playlist."""

        return _number(_extract(self._get_info_node(), "size"))

    def get_description(self):
        """Returns the description of this playlist."""

        return _extract(self._get_info_node(), "description")

    def get_duration(self):
        """Returns the duration of this playlist in milliseconds."""

        return _number(_extract(self._get_info_node(), "duration"))

    def is_streamable(self):
        """
        Returns True if the playlist is streamable.
        For a playlist to be streamable, it needs at least 45 tracks by 15
        different artists."""

        if _extract(self._get_info_node(), "streamable") == '1':
            return True
        else:
            return False

    def has_track(self, track):
        """Checks to see if track is already in the playlist.
        * track: Any Track object.
        """

        return track in self.get_tracks()

    def get_cover_image(self, size=COVER_EXTRA_LARGE):
        """
        Returns a uri to the cover image
        size can be one of:
            COVER_MEGA
            COVER_EXTRA_LARGE
            COVER_LARGE
            COVER_MEDIUM
            COVER_SMALL
        """

        return _extract(self._get_info_node(), "image")[size]

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the playlist on the network.
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

        english_url = _extract(self._get_info_node(), "url")
        appendix = english_url[english_url.rfind("/") + 1:]

        return self.network._get_url(domain_name, "playlist") % {
            'appendix': appendix, "user": self.get_user().get_name()}


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

    def get_similar(self):
        """Returns the tags similar to this one, ordered by similarity. """

        doc = self._request(self.ws_prefix + '.getSimilar', True)

        seq = []
        names = _extract_all(doc, 'name')
        for name in names:
            seq.append(Tag(name, self.network))

        return seq

    def get_top_albums(self, limit=None, cacheable=True):
        """Retuns a list of the top albums."""
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
        """Returns True if the fulltrack is available for streaming."""

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

    def ban(self):
        """Ban this track from ever playing on the radio. """

        self._request(self.ws_prefix + '.ban')

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


class Group(_BaseObject, _Chartable):
    """A Last.fm group."""

    name = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, name, network):
        _BaseObject.__init__(self, network, 'group')
        _Chartable.__init__(self, 'group')

        self.name = name

    def __repr__(self):
        return "pylast.Group(%s, %s)" % (repr(self.name), repr(self.network))

    @_string_output
    def __str__(self):
        return self.get_name()

    def __eq__(self, other):
        return self.get_name().lower() == other.get_name().lower()

    def __ne__(self, other):
        return self.get_name() != other.get_name()

    def _get_params(self):
        return {self.ws_prefix: self.get_name()}

    def get_name(self):
        """Returns the group name. """
        return self.name

    def get_url(self, domain_name=DOMAIN_ENGLISH):
        """Returns the url of the group page on the network.
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

        return self.network._get_url(domain_name, "group") % {'name': name}

    def get_members(self, limit=50, cacheable=False):
        """
            Returns a sequence of User objects
            if limit==None it will return all
        """

        nodes = _collect_nodes(
            limit, self, self.ws_prefix + ".getMembers", cacheable)

        users = []

        for node in nodes:
            users.append(User(_extract(node, "name"), self.network))

        return users


class XSPF(_BaseObject):
    "A Last.fm XSPF playlist."""

    uri = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, uri, network):
        _BaseObject.__init__(self, network, None)

        self.uri = uri

    def _get_params(self):
        return {'playlistURL': self.get_uri()}

    @_string_output
    def __str__(self):
        return self.get_uri()

    def __eq__(self, other):
        return self.get_uri() == other.get_uri()

    def __ne__(self, other):
        return self.get_uri() != other.get_uri()

    def get_uri(self):
        """Returns the Last.fm playlist URI. """

        return self.uri

    def get_tracks(self):
        """Returns the tracks on this playlist."""

        doc = self._request('playlist.fetch', True)

        seq = []
        for node in doc.getElementsByTagName('track'):
            title = _extract(node, 'title')
            artist = _extract(node, 'creator')

            seq.append(Track(artist, title, self.network))

        return seq


class User(_BaseObject, _Chartable):
    """A Last.fm user."""

    name = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, user_name, network):
        _BaseObject.__init__(self, network, 'user')
        _Chartable.__init__(self, 'user')

        self.name = user_name

        self._past_events_index = 0
        self._recommended_events_index = 0
        self._recommended_artists_index = 0

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

    def get_upcoming_events(self):
        """Returns all the upcoming events for this user."""

        doc = self._request(self.ws_prefix + '.getEvents', True)

        return _extract_events_from_doc(doc, self.network)

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

        Use extract_items() with the return of this function to
        get only a sequence of Track objects with no playback dates.
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

    def get_neighbours(self, limit=50, cacheable=True):
        """Returns a list of the user's friends."""

        params = self._get_params()
        if limit:
            params['limit'] = limit

        doc = self._request(
            self.ws_prefix + '.getNeighbours', cacheable, params)

        seq = []
        names = _extract_all(doc, 'name')

        for name in names:
            seq.append(User(name, self.network))

        return seq

    def get_past_events(self, limit=50, cacheable=False):
        """
        Returns a sequence of Event objects
        if limit==None it will return all
        """

        seq = []
        for node in _collect_nodes(
                limit,
                self,
                self.ws_prefix + ".getPastEvents",
                cacheable):
            seq.append(Event(_extract(node, "id"), self.network))

        return seq

    def get_playlists(self):
        """Returns a list of Playlists that this user owns."""

        doc = self._request(self.ws_prefix + ".getPlaylists", True)

        playlists = []
        for playlist_id in _extract_all(doc, "id"):
            playlists.append(
                Playlist(self.get_name(), playlist_id, self.network))

        return playlists

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

        Use extract_items() with the return of this function to
        get only a sequence of Track objects with no playback dates.
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

    def get_id(self):
        """Returns the user ID."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _extract(doc, "id")

    def get_language(self):
        """Returns the language code of the language used by the user."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _extract(doc, "lang")

    def get_country(self):
        """Returns the name of the country of the user."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        country = _extract(doc, "country")

        if country is None:
            return None
        else:
            return Country(country, self.network)

    def get_age(self):
        """Returns the user's age."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        return _number(_extract(doc, "age"))

    def get_gender(self):
        """Returns the user's gender. Either USER_MALE or USER_FEMALE."""

        doc = self._request(self.ws_prefix + ".getInfo", True)

        value = _extract(doc, "gender")

        if value == 'm':
            return USER_MALE
        elif value == 'f':
            return USER_FEMALE

        return None

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

    def compare_with_user(self, user, shared_artists_limit=None):
        """
        Compare this user with another Last.fm user.
        Returns a sequence:
            (tasteometer_score, (shared_artist1, shared_artist2, ...))
        user: A User object or a username string/unicode object.
        """

        if isinstance(user, User):
            user = user.get_name()

        params = self._get_params()
        if shared_artists_limit:
            params['limit'] = shared_artists_limit
        params['type1'] = 'user'
        params['type2'] = 'user'
        params['value1'] = self.get_name()
        params['value2'] = user

        doc = self._request('tasteometer.compare', False, params)

        score = _extract(doc, 'score')

        artists = doc.getElementsByTagName('artists')[0]
        shared_artists_names = _extract_all(artists, 'name')

        shared_artists_seq = []

        for name in shared_artists_names:
            shared_artists_seq.append(Artist(name, self.network))

        return (score, shared_artists_seq)

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

    def shout(self, message):
        """
            Post a shout
        """

        params = self._get_params()
        params["message"] = message

        self._request(self.ws_prefix + ".Shout", False, params)


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

    def get_recommended_events(self, limit=50, cacheable=False):
        """
        Returns a sequence of Event objects
        if limit==None it will return all
        """

        seq = []
        for node in _collect_nodes(
                limit, self, "user.getRecommendedEvents", cacheable):
            seq.append(Event(_extract(node, "id"), self.network))

        return seq

    def get_recommended_artists(self, limit=50, cacheable=False):
        """
        Returns a sequence of Artist objects
        if limit==None it will return all
        """

        seq = []
        for node in _collect_nodes(
                limit, self, "user.getRecommendedArtists", cacheable):
            seq.append(Artist(_extract(node, "name"), self.network))

        return seq


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

        return _extract(doc, "opensearch:totalResults")

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


class TagSearch(_Search):
    """Search for a tag by tag name."""

    def __init__(self, tag_name, network):

        _Search.__init__(self, "tag", {"tag": tag_name}, network)

    def get_next_page(self):
        """Returns the next page of results as a sequence of Tag objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("tag"):
            tag = Tag(_extract(node, "name"), self.network)
            tag.tag_count = _number(_extract(node, "count"))
            seq.append(tag)

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


class VenueSearch(_Search):
    """
    Search for a venue by its name. If you don't want to narrow the results
    down by specifying a country, set it to empty string.
    """

    def __init__(self, venue_name, country_name, network):

        _Search.__init__(
            self,
            "venue",
            {"venue": venue_name, "country": country_name},
            network)

    def get_next_page(self):
        """Returns the next page of results as a sequence of Track objects."""

        master_node = self._retrieve_next_page()

        seq = []
        for node in master_node.getElementsByTagName("venue"):
            seq.append(Venue(_extract(node, "id"), self.network))

        return seq


class Venue(_BaseObject):
    """A venue where events are held."""

    # TODO: waiting for a venue.getInfo web service to use.
    # TODO: As an intermediate use case, can pass the venue DOM element when
    # using Event.get_venue() to populate the venue info, if the venue.getInfo
    # API call becomes available this workaround should be removed

    id = None
    info = None
    name = None
    location = None
    url = None

    __hash__ = _BaseObject.__hash__

    def __init__(self, netword_id, network, venue_element=None):
        _BaseObject.__init__(self, network, "venue")

        self.id = _number(netword_id)
        if venue_element is not None:
            self.info = _extract_element_tree(venue_element)
            self.name = self.info.get('name')
            self.url = self.info.get('url')
            self.location = self.info.get('location')

    def __repr__(self):
        return "pylast.Venue(%s, %s)" % (repr(self.id), repr(self.network))

    @_string_output
    def __str__(self):
        return "Venue #" + str(self.id)

    def __eq__(self, other):
        return self.get_id() == other.get_id()

    def _get_params(self):
        return {self.ws_prefix: self.get_id()}

    def get_id(self):
        """Returns the id of the venue."""

        return self.id

    def get_name(self):
        """Returns the name of the venue."""

        return self.name

    def get_url(self):
        """Returns the URL of the venue page."""

        return self.url

    def get_location(self):
        """Returns the location of the venue (dictionary)."""

        return self.location

    def get_upcoming_events(self):
        """Returns the upcoming events in this venue."""

        doc = self._request(self.ws_prefix + ".getEvents", True)

        return _extract_events_from_doc(doc, self.network)

    def get_past_events(self):
        """Returns the past events held in this venue."""

        doc = self._request(self.ws_prefix + ".getEvents", True)

        return _extract_events_from_doc(doc, self.network)


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


def _extract_element_tree(node):
    """Extract an element tree into a multi-level dictionary

    NB: If any elements have text nodes as well as nested
    elements this will ignore the text nodes"""

    def _recurse_build_tree(rootNode, targetDict):
        """Recursively build a multi-level dict"""

        def _has_child_elements(rootNode):
            """Check if an element has any nested (child) elements"""

            for node in rootNode.childNodes:
                if node.nodeType == node.ELEMENT_NODE:
                    return True
            return False

        for node in rootNode.childNodes:
            if node.nodeType == node.ELEMENT_NODE:
                if _has_child_elements(node):
                    targetDict[node.tagName] = {}
                    _recurse_build_tree(node, targetDict[node.tagName])
                else:
                    val = None if node.firstChild is None else \
                        _unescape_htmlentity(node.firstChild.data.strip())
                    targetDict[node.tagName] = val
        return targetDict

    return _recurse_build_tree(node, {})


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


def _extract_events_from_doc(doc, network):
    events = []
    for node in doc.getElementsByTagName("event"):
        events.append(Event(_extract(node, "id"), network))
    return events


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


def extract_items(topitems_or_libraryitems):
    """
    Extracts a sequence of items from a sequence of TopItem or
    LibraryItem objects.
    """

    seq = []
    for i in topitems_or_libraryitems:
        seq.append(i.item)

    return seq


class ScrobblingError(Exception):
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message

    @_string_output
    def __str__(self):
        return self.message


class BannedClientError(ScrobblingError):
    def __init__(self):
        ScrobblingError.__init__(
            self, "This version of the client has been banned")


class BadAuthenticationError(ScrobblingError):
    def __init__(self):
        ScrobblingError.__init__(self, "Bad authentication token")


class BadTimeError(ScrobblingError):
    def __init__(self):
        ScrobblingError.__init__(
            self, "Time provided is not close enough to current time")


class BadSessionError(ScrobblingError):
    def __init__(self):
        ScrobblingError.__init__(
            self, "Bad session id, consider re-handshaking")


class _ScrobblerRequest(object):

    def __init__(self, url, params, network, request_type="POST"):

        for key in params:
            params[key] = str(params[key])

        self.params = params
        self.type = request_type
        (self.hostname, self.subdir) = url_split_host(url[len("http:"):])
        self.network = network

    def execute(self):
        """Returns a string response of this request."""

        if _can_use_ssl_securely():
            connection = HTTPSConnection(
                context=SSL_CONTEXT,
                host=self.hostname
            )
        else:
            connection = HTTPConnection(
                host=self.hostname
            )

        data = []
        for name in self.params.keys():
            value = url_quote_plus(self.params[name])
            data.append('='.join((name, value)))
        data = "&".join(data)

        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "Accept-Charset": "utf-8",
            "User-Agent": "pylast" + "/" + __version__,
            "HOST": self.hostname
        }

        if self.type == "GET":
            connection.request(
                "GET", self.subdir + "?" + data, headers=headers)
        else:
            connection.request("POST", self.subdir, data, headers)
        response = _unicode(connection.getresponse().read())

        self._check_response_for_errors(response)

        return response

    def _check_response_for_errors(self, response):
        """
        When passed a string response it checks for errors, raising any
        exceptions as necessary.
        """

        lines = response.split("\n")
        status_line = lines[0]

        if status_line == "OK":
            return
        elif status_line == "BANNED":
            raise BannedClientError()
        elif status_line == "BADAUTH":
            raise BadAuthenticationError()
        elif status_line == "BADTIME":
            raise BadTimeError()
        elif status_line == "BADSESSION":
            raise BadSessionError()
        elif status_line.startswith("FAILED "):
            reason = status_line[status_line.find("FAILED ") + len("FAILED "):]
            raise ScrobblingError(reason)


class Scrobbler(object):
    """A class for scrobbling tracks to Last.fm"""

    session_id = None
    nowplaying_url = None
    submissions_url = None

    def __init__(self, network, client_id, client_version):
        self.client_id = client_id
        self.client_version = client_version
        self.username = network.username
        self.password = network.password_hash
        self.network = network

    def _do_handshake(self):
        """Handshakes with the server"""

        timestamp = str(int(time.time()))

        if self.password and self.username:
            token = md5(self.password + timestamp)
        elif self.network.api_key and self.network.api_secret and \
                self.network.session_key:
            if not self.username:
                self.username = self.network.get_authenticated_user()\
                    .get_name()
            token = md5(self.network.api_secret + timestamp)

        params = {
            "hs": "true", "p": "1.2.1", "c": self.client_id,
            "v": self.client_version, "u": self.username, "t": timestamp,
            "a": token}

        if self.network.session_key and self.network.api_key:
            params["sk"] = self.network.session_key
            params["api_key"] = self.network.api_key

        server = self.network.submission_server
        response = _ScrobblerRequest(
            server, params, self.network, "GET").execute().split("\n")

        self.session_id = response[1]
        self.nowplaying_url = response[2]
        self.submissions_url = response[3]

    def _get_session_id(self, new=False):
        """
        Returns a handshake. If new is true, then it will be requested from
        the server even if one was cached.
        """

        if not self.session_id or new:
            self._do_handshake()

        return self.session_id

    def report_now_playing(
            self, artist, title, album="", duration="", track_number="",
            mbid=""):

        _deprecation_warning(
            "DeprecationWarning: Use Network.update_now_playing(...) instead")

        params = {
            "s": self._get_session_id(), "a": artist, "t": title,
            "b": album, "l": duration, "n": track_number, "m": mbid}

        try:
            _ScrobblerRequest(
                self.nowplaying_url, params, self.network
            ).execute()
        except BadSessionError:
            self._do_handshake()
            self.report_now_playing(
                artist, title, album, duration, track_number, mbid)

    def scrobble(
            self, artist, title, time_started, source, mode, duration,
            album="", track_number="", mbid=""):
        """Scrobble a track. parameters:
            artist: Artist name.
            title: Track title.
            time_started: UTC timestamp of when the track started playing.
            source: The source of the track
                SCROBBLE_SOURCE_USER: Chosen by the user
                    (the most common value, unless you have a reason for
                    choosing otherwise, use this).
                SCROBBLE_SOURCE_NON_PERSONALIZED_BROADCAST: Non-personalised
                    broadcast (e.g. Shoutcast, BBC Radio 1).
                SCROBBLE_SOURCE_PERSONALIZED_BROADCAST: Personalised
                    recommendation except Last.fm (e.g. Pandora, Launchcast).
                SCROBBLE_SOURCE_LASTFM: ast.fm (any mode). In this case, the
                    5-digit recommendation_key value must be set.
                SCROBBLE_SOURCE_UNKNOWN: Source unknown.
            mode: The submission mode
                SCROBBLE_MODE_PLAYED: The track was played.
                SCROBBLE_MODE_LOVED: The user manually loved the track
                    (implies a listen)
                SCROBBLE_MODE_SKIPPED: The track was skipped
                    (Only if source was Last.fm)
                SCROBBLE_MODE_BANNED: The track was banned
                    (Only if source was Last.fm)
            duration: Track duration in seconds.
            album: The album name.
            track_number: The track number on the album.
            mbid: MusicBrainz ID.
        """

        _deprecation_warning(
            "DeprecationWarning: Use Network.scrobble(...) instead")

        params = {
            "s": self._get_session_id(),
            "a[0]": _string(artist),
            "t[0]": _string(title),
            "i[0]": str(time_started),
            "o[0]": source,
            "r[0]": mode,
            "l[0]": str(duration),
            "b[0]": _string(album),
            "n[0]": track_number,
            "m[0]": mbid
        }

        _ScrobblerRequest(self.submissions_url, params, self.network).execute()

    def scrobble_many(self, tracks):
        """
            Scrobble several tracks at once.

            tracks: A sequence of a sequence of parameters for each track.
                The order of parameters is the same as if passed to the
                scrobble() method.
        """

        _deprecation_warning(
            "DeprecationWarning: Use Network.scrobble_many(...) instead")

        remainder = []

        if len(tracks) > 50:
            remainder = tracks[50:]
            tracks = tracks[:50]

        params = {"s": self._get_session_id()}

        i = 0
        for t in tracks:
            _pad_list(t, 9, "")
            params["a[%s]" % str(i)] = _string(t[0])
            params["t[%s]" % str(i)] = _string(t[1])
            params["i[%s]" % str(i)] = str(t[2])
            params["o[%s]" % str(i)] = t[3]
            params["r[%s]" % str(i)] = t[4]
            params["l[%s]" % str(i)] = str(t[5])
            params["b[%s]" % str(i)] = _string(t[6])
            params["n[%s]" % str(i)] = t[7]
            params["m[%s]" % str(i)] = t[8]

            i += 1

        _ScrobblerRequest(self.submissions_url, params, self.network).execute()

        if remainder:
            self.scrobble_many(remainder)

# End of file
