# -*- coding: utf-8 -*-
#
# pylast - A Python interface to the Last.fm API.
# Copyright (C) 2008-2009  Amr Hassan
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#
# http://code.google.com/p/pylast/

__name__ = 'pylast'
__version__ = '0.3.0a'
__doc__ = 'A Python interface to the Last.fm API.'
__author__ = 'Amr Hassan'
__email__ = 'amr.hassan@gmail.com'


__proxy = None
__proxy_enabled = False
__cache_dir = None
__cache_enabled = False
__last_call_time = 0

import hashlib
import httplib
import urllib
import threading
from xml.dom import minidom
import os
import time

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
PERIOD_3MONTHS = '3month'
PERIOD_6MONTHS = '6month'
PERIOD_12MONTHS = '12month'

IMAGE_SMALL = 0
IMAGE_MEDIUM = 1
IMAGE_LARGE = 2
IMAGE_EXTRA_LARGE = 3

DOMAIN_ENGLISH = 'www.last.fm'
DOMAIN_GERMAN = 'www.lastfm.de'
DOMAIN_SPANISH = 'www.lastfm.es'
DOMAIN_FRENCH = 'www.lastfm.fr'
DOMAIN_ITALIAN = 'www.lastfm.it'
DOMAIN_POLISH = 'www.lastfm.pl'
DOMAIN_PORTUGUESE = 'www.lastfm.com.br'
DOMAIN_SWEDISH = 'www.lastfm.se'
DOMAIN_TURKISH = 'www.lastfm.com.tr'
DOMAIN_RUSSIAN = 'www.lastfm.ru'
DOMAIN_JAPANESE = 'www.lastfm.jp'
DOMAIN_CHINESE = 'cn.last.fm'

USER_MALE = 'Male'
USER_FEMALE = 'Female'

class _ThreadedCall(threading.Thread):
	"""Facilitates calling a function on another thread."""
	
	def __init__(self, sender, funct, funct_args, callback, callback_args):
		
		threading.Thread.__init__(self)
		
		self.funct = funct
		self.funct_args = funct_args
		self.callback = callback
		self.callback_args = callback_args
		
		self.sender = sender
	
	def run(self):
		
		output = []
		
		if self.funct:
			if self.funct_args:
				output = self.funct(*self.funct_args)
			else:
				output = self.funct()
				
		if self.callback:
			if self.callback_args:
				self.callback(self.sender, output, *self.callback_args)
			else:
				self.callback(self.sender, output)
	
class _Request(object):
	"""Representing an abstract web service operation."""
	
	HOST_NAME = 'ws.audioscrobbler.com'
	HOST_SUBDIR = '/2.0/'
	
	def __init__(self, method_name, params, api_key, api_secret = None, session_key = None):

		self.params = params
		self.api_secret = api_secret
		
		self.params["api_key"] = api_key
		self.params["method"] = method_name
		self.params["sk"] = session_key
		
		if session_key:
			self.sign_it()
	
	def sign_it(self):
		"""Sign this request."""
		
		if not "api_sig" in self.params.keys():
			self.params['api_sig'] = self._get_signature()
	
	def _get_signature(self):
		"""Returns a 32-character hexadecimal md5 hash of the signature string."""
		
		keys = self.params.keys()[:]
		
		keys.sort()
		
		string = unicode()
		
		for name in keys:
			string += name
			string += self.params[name]
		
		string += self.api_secret
		
		return md5(string.encode('utf-8'))
	
	def _get_cache_key(self):
		"""The cache key is a string of concatenated sorted names and values."""
		
		keys = self.params.keys()
		keys.sort()
		
		cache_key = str()
		
		for key in keys:
			if key != "api_sig" and key != "api_key" and key != "sk":
				cache_key += urllib.quote_plus(key) + urllib.quote_plus(urllib.quote_plus(self.params[key]))
		
		return cache_key
	
	def _is_cached(self):
		"""Returns True if the request is available in the cache."""
		
		return os.path.exists(os.path.join(_get_cache_dir(), self._get_cache_key()))
	
	def _get_cached_response(self):
		"""Returns a file object of the cached response."""
		
		if not self._is_cached():
			response = self._download_response()
			
			response_file = open(os.path.join(_get_cache_dir(), self._get_cache_key()), "w")
			response_file.write(response)
			response_file.close()
		
		return open(os.path.join(_get_cache_dir(), self._get_cache_key()), "r").read()
	
	def _download_response(self):
		"""Returns a response body string from the server."""
		
		# Delay the call if necessary
		_delay_call()
		
		data = []
		for name in self.params.keys():
			data.append('='.join((name, urllib.quote_plus(self.params[name].encode('utf-8')))))
		data = '&'.join(data)
		
		headers = {
			"Content-type": "application/x-www-form-urlencoded",
			'Accept-Charset': 'utf-8',
			'User-Agent': __name__ + '/' + __version__
			}		
		
		if is_proxy_enabled():
			conn = httplib.HTTPConnection(host = _get_proxy()[0], port = _get_proxy()[1])
			conn.request(method='POST', url="http://" + HOST_NAME + HOST_SUBDIR, 
				body=data, headers=headers)
		else:
			conn = httplib.HTTPConnection(host=self.HOST_NAME)
			conn.request(method='POST', url=self.HOST_SUBDIR, body=data, headers=headers)
		
		response = conn.getresponse().read()
		self._check_response_for_errors(response)
		return response
		
	def execute(self, cacheable = False):
		"""Returns the XML DOM response of the POST Request from the server"""
		
		if is_caching_enabled() and cacheable:
			response = self._get_cached_response()
		else:
			response = self._download_response()
		
		return minidom.parseString(response)
	
	def _check_response_for_errors(self, response):
		"""Checks the response for errors and raises one if any exists."""
		
		doc = minidom.parseString(response)
		e = doc.getElementsByTagName('lfm')[0]
		
		if e.getAttribute('status') != "ok":
			e = doc.getElementsByTagName('error')[0]
			status = e.getAttribute('code')
			details = e.firstChild.data.strip()
			raise ServiceException(status, details)

class SessionKeyGenerator(object):
	"""Methods of generating a session key:
	1) Web Authentication:
		a. sg = SessionKeyGenerator(API_KEY, API_SECRET)
		b. url = sg.get_web_auth_url()
		c. Ask the user to open the url and authorize you, and wait for it.
		d. session_key = sg.get_web_auth_session_key(url)
	2) Username and Password Authentication:
		a. username = raw_input("Please enter your username: ")
		b. md5_password = pylast.md5(raw_input("Please enter your password: ")
		c. session_key = SessionKeyGenerator(API_KEY, API_SECRET).get_session_key(username, md5_password)
	
	A session key's lifetime is infinie, unless the user provokes the rights of the given API Key.
	"""
	
	def __init__(self, api_key, api_secret):		
		self.api_key = api_key
		self.api_secret = api_secret
		self.web_auth_tokens = {}
	
	def _get_web_auth_token(self):
		"""Retrieves a token from Last.fm for web authentication.
		The token then has to be authorized from getAuthURL before creating session.
		"""
		
		request = _Request('auth.getToken', dict(), self.api_key, self.api_secret)
		request.sign_it()
		
		doc = request.execute()
		
		e = doc.getElementsByTagName('token')[0]
		return e.firstChild.data
	
	def get_web_auth_url(self):
		"""The user must open this page, and you first, then call get_web_auth_session_key(url) after that."""
		
		token = self._get_web_auth_token()
		
		url = 'http://www.last.fm/api/auth/?api_key=%(api)s&token=%(token)s' % \
			{'api': self.api_key, 'token': token}
		
		self.web_auth_tokens[url] = token
		
		return url

	def get_web_auth_session_key(self, url):
		"""Retrieves the session key of a web authorization process by its url."""
		
		if url in self.web_auth_tokens.keys():
			token = self.web_auth_tokens[url]
		else:
			token = ""	#that's gonna raise a ServiceException of an unauthorized token when the request is executed.
		
		request = _Request('auth.getSession', {'token': token}, self.api_key, self.api_secret)
		request.sign_it()
		
		doc = request.execute()
		
		return doc.getElementsByTagName('key')[0].firstChild.data
	
	def get_session_key(self, username, md5_password):
		"""Retrieve a session key with a username and a md5 hash of the user's password."""
		
		params = {"username": username, "authToken": md5(username + md5_password)}
		request = _Request("auth.getMobileSession", params, self.api_key, self.api_secret)
		request.sign_it()
		
		doc = request.execute()
		
		return doc.getElementsByTagName('key')[0].firstChild.data

class _BaseObject(object):
	"""An abstract webservices object."""
		
	def __init__(self, api_key, api_secret, session_key):
				
		self.api_key = api_key
		self.api_secret = api_secret
		self.session_key = session_key
		
		self.auth_data = (self.api_key, self.api_secret, self.session_key)
	
	def _request(self, method_name, cacheable = False, params = None):
		if not params:
			params = self._get_params()
			
		return _Request(method_name, params, *self.auth_data).execute(cacheable)
	
	def _get_params():
		"""Returns the most common set of parameters between all objects."""
		
		return dict()

class _Taggable(object):
	"""Common functions for classes with tags."""
	
	def __init__(self, ws_prefix):
		self.ws_prefix = ws_prefix
	
	def add_tags(self, *tags):
		"""Adds one or several tags.
		* *tags: Any number of tag names or Tag objects. 
		"""
		
		for tag in tags:
			self._add_tag(tag)	
	
	def _add_tag(self, tag):
		"""Adds one or several tags.
		* tag: one tag name or a Tag object.
		"""
		
		if isinstance(tag, Tag):
			tag = tag.get_name()
		
		params = self._get_params()
		params['tags'] = unicode(tag)
		
		self._request(self.ws_prefix + '.addTags', False, params)
	
	def _remove_tag(self, single_tag):
		"""Remove a user's tag from this object."""
		
		if isinstance(single_tag, Tag):
			single_tag = single_tag.get_name()
		
		params = self._get_params()
		params['tag'] = unicode(single_tag)
		
		self._request(self.ws_prefix + '.removeTag', False, params)

	def get_tags(self):
		"""Returns a list of the tags set by the user to this object."""
		
		# Uncacheable because it can be dynamically changed by the user.
		params = self._get_params()
		doc = _Request(self.ws_prefix + '.getTags', params, *self.auth_data).execute(cacheable = False)
		
		tag_names = _extract_all(doc, 'name')
		tags = []
		for tag in tag_names:
			tags.append(Tag(tag, *self.auth_data))
		
		return tags
	
	def remove_tags(self, *tags):
		"""Removes one or several tags from this object.
		* *tags: Any number of tag names or Tag objects. 
		"""
		
		for tag in tags:
			self._remove_tag(tag)
	
	def clear_tags(self):
		"""Clears all the user-set tags. """
		
		self.remove_tags(*(self.get_tags()))
	
	def set_tags(self, *tags):
		"""Sets this object's tags to only those tags.
		* *tags: any number of tag names.
		"""
		
		c_old_tags = []
		old_tags = []
		c_new_tags = []
		new_tags = []
		
		to_remove = []
		to_add = []
		
		tags_on_server = self.get_tags()
		if tags_on_server == None:
			return
		
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
		
		self.remove_tags(*to_remove)
		self.add_tags(*to_add)
		
	def get_top_tags(self, limit = None):
		"""Returns a list of the most frequently used Tags on this object."""
		
		doc = self._request(self.ws_prefix + '.getTopTags', True)
		
		elements = doc.getElementsByTagName('tag')
		list = []
		
		for element in elements:
			if limit and len(list) >= limit:
				break
			tag_name = _extract(element, 'name')
			tagcount = _extract(element, 'count')
			
			list.append(TopItem(Tag(tag_name, *self.auth_data), tagcount))
		
		return list
		
class ServiceException(Exception):
	"""Exception related to the Last.fm web service"""
	
	def __init__(self, lastfm_status, details):
		self._lastfm_status = lastfm_status
		self._details = details
	
	def __str__(self):
		return self._details
	
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
		
		return self._lastfm_status

class TopItem (object):
	"""A top item in a list that has a weight. Returned from functions like get_top_tracks() and get_top_artists()."""
	
	def __init__(self, item, weight):
		object.__init__(self)
		
		self.item = item
		self.weight = _number(weight)
	
	def __repr__(self):
		return "Item: " + self.get_item().__repr__() + ", Weight: " + str(self.get_weight())
	
	def get_item(self):
		"""Returns the item."""
		
		return self.item
	
	def get_weight(self):
		"""Returns the weight of the itme in the list."""
		
		return self.weight


class LibraryItem (object):
	"""An item in a User's Library. It could be an artist, an album or a track."""
	
	def __init__(self, item, playcount, tagcount):
		object.__init__(self)
		
		self.item = item
		self.playcount = _number(playcount)
		self.tagcount = _number(tagcount)
	
	def __repr__(self):
		return "Item: " + self.get_item().__repr__() + ", Playcount: " + str(self.get_playcount()) + ", Tagcount: " + str(self.get_tagcount())
	
	def get_item(self):
		"""Returns the itme."""
		
		return self.item
	
	def get_playcount(self):
		"""Returns the item's playcount in the Library."""
		
		return self.playcount
		
	def get_tagcount(self):
		"""Returns the item's tagcount in the Library."""
		
		return self.tagcount

class Album(_BaseObject, _Taggable):
	"""A Last.fm album."""
	
	def __init__(self, artist, title, api_key, api_secret, session_key):
		"""
		Create an album instance.
		# Parameters:
			* artist str|Artist: An artist name or an Artist object.
			* title str: The album title.
		"""
		
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		_Taggable.__init__(self, 'album')
		
		if isinstance(artist, Artist):
			self.artist = artist
		else:
			self.artist = Artist(artist, *self.auth_data)
		
		self.title = title

	def __repr__(self):
		return self.get_artist().get_name().encode('utf-8') + ' - ' + self.get_title().encode('utf-8')
	
	def __eq__(self, other):
		return (self.get_title().lower() == other.get_title().lower()) and (self.get_artist().get_name().lower() == other.get_artist().get_name().lower())
	
	def __ne__(self, other):
		return (self.get_title().lower() != other.get_title().lower()) or (self.get_artist().get_name().lower() != other.get_artist().get_name().lower())
	
	def _get_params(self):
		return {'artist': self.get_artist().get_name(), 'album': self.get_title(), }
	
	def get_artist(self):
		"""Returns the associated Artist object."""
		
		return self.artist
	
	def get_title(self):
		"""Returns the album title."""
		
		return self.title
	
	def get_name(self):
		"""Returns the album title (alias to Album.get_title)."""
		
		return self.get_title()
	
	def get_release_date(self):
		"""Retruns the release date of the album."""
		
		return _extract(self._request("album.getInfo", cacheable = True), "releasedate")
	
	def get_image_url(self, size = IMAGE_EXTRA_LARGE):
		"""Returns the associated image URL.
		# Parameters:
		* size int: The image size. Possible values:
			o IMAGE_EXTRA_LARGE
			o IMAGE_LARGE
		 	o IMAGE_MEDIUM
			o IMAGE_SMALL
		"""
		
		return _extract_all(self._request("album.getInfo", cacheable = True), 'image')[size]
	
	def get_id(self):
		"""Returns the Last.fm ID."""
		
		return _extract(self._request("album.getInfo", cacheable = True), "id")
	
	def get_playcount(self):
		"""Returns the number of plays on Last.fm."""
		
		return _number(_extract(self._request("album.getInfo", cacheable = True), "playcount"))
	
	def get_listener_count(self):
		"""Returns the number of liteners on Last.fm."""
		
		return _number(_extract(self._request("album.getInfo", cacheable = True), "listeners"))
	
	def get_top_tags(self, limit = None):
		"""Returns a list of the most-applied tags to this album."""
		
		# BROKEN: Web service is currently broken.
		
		return None

	def get_tracks(self):
		"""Returns the list of Tracks on this album."""
		
		uri = 'lastfm://playlist/album/%s' %self.get_id()
		
		return XSPF(uri, *self.auth_data).get_tracks()
	
	def get_mbid(self):
		"""Returns the MusicBrainz id of the album."""
		
		return _extract(self._request("album.getInfo", cacheable = True), "mbid")
		
	def get_url(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the album page on Last.fm. 
		# Parameters:
		* domain_name str: Last.fm's language domain. Possible values:
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
		
		url = 'http://%(domain)s/music/%(artist)s/%(album)s'
		
		artist = _get_url_safe(self.get_artist().get_name())
		album = _get_url_safe(self.get_title())
		
		return url %{'domain': domain_name, 'artist': artist, 'album': album}

class Artist(_BaseObject, _Taggable):
	"""A Last.fm artist."""
	
	def __init__(self, name, api_key, api_secret, session_key):
		"""Create an artist object.
		# Parameters:
			* name str: The artist's name.
		"""
		
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		_Taggable.__init__(self, 'artist')
		
		self.name = name

	def __repr__(self):
		return self.get_name().encode('utf-8')
	
	def __eq__(self, other):
		return self.get_name().lower() == other.get_name().lower()
	
	def __ne__(self, other):
		return self.get_name().lower() != other.get_name().lower()
	
	def _get_params(self):
		return {'artist': self.get_name()}
	
	def get_name(self):
		"""Returns the name of the artist."""
		
		return self.name
	
	def get_image_url(self, size = IMAGE_LARGE):
		"""Returns the associated image URL. 
		# Parameters:
			* size int: The image size. Possible values:
			  o IMAGE_LARGE
			  o IMAGE_MEDIUM
			  o IMAGE_SMALL
		"""
		
		return _extract_all(self._request("artist.getInfo", True), "image")[size]
	
	def get_playcount(self):
		"""Returns the number of plays on Last.fm."""
		
		return _number(_extract(self._request("artist.getInfo", True), "playcount"))
	
	def get_listener_count(self):
		"""Returns the number of liteners on Last.fm."""
		
		return _number(_extract(self._request("artist.getInfo", True), "listeners"))
	
	def is_streamable(self):
		"""Returns True if the artist is streamable."""
		
		return bool(_number(_extract(self._request("artist.getInfo", True), "streamable")))
	
	def get_bio_published_date(self):
		"""Returns the date on which the artist's biography was published."""
		
		return _extract(self._request("artist.getInfo", True), "published")
	
	def get_bio_summary(self):
		"""Returns the summary of the artist's biography."""
		
		return _extract(self._request("artist.getInfo", True), "summary")
	
	def get_bio_content(self):
		"""Returns the content of the artist's biography."""
		
		return _extract(self._request("artist.getInfo", True), "content")
	
	def get_upcoming_events(self):
		"""Returns a list of the upcoming Events for this artist."""
		
		doc = self._request('artist.getEvents', True)
		
		ids = _extract_all(doc, 'id')
		
		events = []
		for id in ids:
			events.append(Event(id, *self.auth_data))
		
		return events
	
	def get_similar(self, limit = None):
		"""Returns the similar artists on Last.fm."""
		
		params = self._get_params()
		if limit:
			params['limit'] = unicode(limit)
		
		doc = self._request('artist.getSimilar', True, params)
		
		names = _extract_all(doc, 'name')
		
		artists = []
		for name in names:
			artists.append(Artist(name, *self.auth_data))
		
		return artists

	def get_top_albums(self):
		"""Retuns a list of the top albums."""
		
		doc = self._request('artist.getTopAlbums', True)
		
		list = []
		
		for node in doc.getElementsByTagName("album"):
			name = _extract(node, "name")
			artist = _extract(node, "name", 1)
			playcount = _extract(node, "playcount")
			
			list.append(TopItem(Album(artist, name, *self.auth_data), playcount))
		
		return list
		
	def get_top_tracks(self):
		"""Returns a list of the most played Tracks by this artist."""
		
		doc = self._request("artist.getTopTracks", True)
		
		list = []
		for track in doc.getElementsByTagName('track'):
			
			title = _extract(track, "name")
			artist = _extract(track, "name", 1)
			playcount = _number(_extract(track, "playcount"))
			
			list.append( TopItem(Track(artist, title, *self.auth_data), playcount) )
		
		return list
	
	def get_top_fans(self, limit = None):
		"""Returns a list of the Users who played this artist the most.
		# Parameters:
			* limit int: Max elements.
		"""
		
		params = self._get_params()
		doc = self._request('artist.getTopFans', True)
		
		list = []
		
		elements = doc.getElementsByTagName('user')
		
		for element in elements:
			if limit and len(list) >= limit:
				break
				
			name = _extract(element, 'name')
			weight = _number(_extract(element, 'weight'))
			
			list.append(TopItem(User(name, *self.auth_data), weight))
		
		return list

	def share(self, users, message = None):
		"""Shares this artist (sends out recommendations). 
		# Parameters:
			* users [User|str,]: A list that can contain usernames, emails, User objects, or all of them.
			* message str: A message to include in the recommendation message. 
		"""
		
		#last.fm currently accepts a max of 10 recipient at a time
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
		if message: params['message'] = unicode(message)
		
		self._request('artist.share', False, params)
	
	def get_url(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the artist page on Last.fm. 
		# Parameters:
		* domain_name: Last.fm's language domain. Possible values:
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
		
		url = 'http://%(domain)s/music/%(artist)s'
		
		artist = _get_url_safe(self.get_name())
		
		return url %{'domain': domain_name, 'artist': artist}


class Event(_BaseObject):
	"""A Last.fm event."""
	
	def __init__(self, event_id, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self.id = unicode(event_id)
	
	def __repr__(self):
		return "Event #" + self.get_id()
	
	def __eq__(self, other):
		return self.get_id() == other.get_id()
	
	def __ne__(self, other):
		return self.get_id() != other.get_id()
	
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
		params['status'] = unicode(attending_status)
		
		doc = self._request('event.attend', False, params)
	
	def get_id(self):
		"""Returns the id of the event on Last.fm. """
		return self.id
	
	def get_title(self):
		"""Returns the title of the event. """
		
		doc = self._request("event.getInfo", True)
		
		return _extract(doc, "title")
	
	def get_headliner(self):
		"""Returns the headliner of the event. """
		
		doc = self._request("event.getInfo", True)
		
		return Artist(_extract(doc, "headliner"), *self.auth_data)
	
	def get_artists(self):
		"""Returns a list of the participating Artists. """
		
		doc = self._request("event.getInfo", True)
		names = _extract_all(doc, "artist")
		
		artists = []
		for name in names:
			artists.append(Artist(name, *self.auth_data))
		
		return artists
	
	def get_venue(self):
		"""Returns the venue where the event is held."""
		
		doc = self._request("event.getInfo", True)
		
		venue_url = _extract(doc, "url")
		venue_id = _number(venue_url[venue_url.rfind("/") + 1:])
		
		return Venue(venue_id, *self.auth_data)
	
	def get_start_date(self):
		"""Returns the date when the event starts."""
		
		doc = self._request("event.getInfo", True)
		
		return _extract(doc, "startDate")
		
	def get_description(self):
		"""Returns the description of the event. """
		
		doc = self._request("event.getInfo", True)
		
		return _extract(doc, "description")
	
	def get_image_url(self, size = IMAGE_LARGE):
		"""Returns the associated image URL. 
		* size: The image size. Possible values:
		  o IMAGE_LARGE
		  o IMAGE_MEDIUM
		  o IMAGE_SMALL 
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
	
	def get_url(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the event page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
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
		
		url = 'http://%(domain)s/event/%(id)s'
		
		return url %{'domain': domain_name, 'id': self.get_id()}

	def share(self, users, message = None):
		"""Shares this event (sends out recommendations). 
  		* users: A list that can contain usernames, emails, User objects, or all of them.
  		* message: A message to include in the recommendation message. 
		"""
		
		#last.fm currently accepts a max of 10 recipient at a time
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
		if message: params['message'] = unicode(message)
		
		self._request('event.share', False, params)


class Country(_BaseObject):
	"""A country at Last.fm."""
	
	def __init__(self, name, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self.name = name
	
	def __repr__(self):
		return self.get_name().encode('utf-8')
	
	def __eq__(self, other):
		self.get_name().lower() == other.get_name().lower()
	
	def __ne__(self, other):
		self.get_name() != other.get_name()
	
	def _get_params(self):
		return {'country': self.get_name()}
	
	def _get_name_from_code(self, alpha2code):
		# TODO: Have this function lookup the alpha-2 code and return the country name.
		
		return alpha2code
	
	def get_name(self):
		"""Returns the country name. """
		
		return self.name
	
	def get_top_artists(self):
		"""Returns a sequence of the most played artists."""
		
		doc = self._request('geo.getTopArtists', True)
		
		list = []
		for node in doc.getElementsByTagName("artist"):
			name = _extract(node, 'name')
			playcount = _extract(node, "playcount")
		
			list.append(TopItem(Artist(name, *self.auth_data), playcount))
		
		return list
	
	def get_top_tracks(self):
		"""Returns a sequence of the most played tracks"""
		
		doc = self._request("geo.getTopTracks", True)
		
		list = []
		
		for n in doc.getElementsByTagName('track'):
			
			title = _extract(n, 'name')
			artist = _extract(n, 'name', 1)
			playcount = _number(_extract(n, "playcount"))
			
			list.append( TopItem(Track(artist, title, *self.auth_data), playcount))
		
		return list
	
	def get_url(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the event page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
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
		
		url = 'http://%(domain)s/place/%(country_name)s'
		
		country_name = _get_url_safe(self.get_name())
		
		return url %{'domain': domain_name, 'country_name': country_name}


class Library(_BaseObject):
	"""A user's Last.fm library."""
	
	def __init__(self, user, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		if isinstance(user, User):
			self.user = user
		else:
			self.user = User(user, *self.auth_data)
		
		self._albums_index = 0
		self._artists_index = 0
		self._tracks_index = 0
	
	def __repr__(self):
		return self.get_user().__repr__() + "'s Library"
	
	def _get_params(self):
		return {'user': self.user.get_name()}
	
	def get_user(self):
		"""Returns the user who owns this library."""
		
		return self.user
	
	def add_album(self, album):
		"""Add an album to this library."""
		
		params = self._get_params()
		params["artist"] = album.get_artist.get_name()
		params["album"] = album.get_name()
		
		self._request("library.addAlbum", False, params)
	
	def add_artist(self, artist):
		"""Add an artist to this library."""
		
		params = self._get_params()
		params["artist"] = artist.get_name()
		
		self._request("library.addArtist", False, params)
	
	def add_track(self, track):
		"""Add a track to this library."""
		
		params = self._get_prams()
		params["track"] = track.get_title()
		
		self._request("library.addTrack", False, params)
	
	def _get_albums_pagecount(self):
		"""Returns the number of album pages in this library."""
		
		doc = self._request("library.get_albums", True)
		
		return _number(doc.getElementsByTagName("albums")[0].getAttribute("totalPages"))
	
	def is_end_of_albums(self):
		"""Returns True when the last page of albums has ben retrieved."""

		if self._albums_index >= self._get_albums_pagecount():
			return True
		else:
			return False
	
	def _get_artists_pagecount(self):
		"""Returns the number of artist pages in this library."""
		
		doc = self._request("library.getArtists", True)
		
		return _number(doc.getElementsByTagName("artists")[0].getAttribute("totalPages"))
	
	def is_end_of_artists(self):
		"""Returns True when the last page of artists has ben retrieved."""
		
		if self._artists_index >= self._get_artists_pagecount():
			return True
		else:
			return False

	def _get_tracks_pagecount(self):
		"""Returns the number of track pages in this library."""
		
		doc = self._request("library.getTracks", True)
		
		return _number(doc.getElementsByTagName("tracks")[0].getAttribute("totalPages"))
	
	def is_end_of_tracks(self):
		"""Returns True when the last page of tracks has ben retrieved."""
		
		if self._tracks_index >= self._get_tracks_pagecount():
			return True
		else:
			return False
	
	def get_albums_page(self):
		"""Retreives the next page of albums in the Library. Returns a sequence of TopItem objects.
		Use the function extract_items like extract_items(Library.get_albums_page()) to return only a sequence of
		Album objects with no extra data.
		
		Example:
		-------
		library = Library("rj", API_KEY, API_SECRET, SESSION_KEY)
		
		while not library.is_end_of_albums():
			print library.get_albums_page()
		"""
		
		self._albums_index += 1
		
		params = self._get_params()
		params["page"] = str(self._albums_index)
		
		list = []
		doc = self._request("library.get_albums", True, params)
		for node in doc.getElementsByTagName("album"):
			name = _extract(node, "name")
			artist = _extract(node, "name", 1)
			playcount = _number(_extract(node, "playcount"))
			tagcount = _number(_extract(node, "tagcount"))
			
			list.append(LibraryItem(Album(artist, name, *self.auth_data), playcount, tagcount))
		
		return list
	
	def get_artists_page(self):
		"""Retreives the next page of artists in the Library. Returns a sequence of TopItem objects.
		Use the function extract_items like extract_items(Library.get_artists_page()) to return only a sequence of
		Artist objects with no extra data.
		
		Example:
		-------
		library = Library("rj", API_KEY, API_SECRET, SESSION_KEY)
		
		while not library.is_end_of_artists():
			print library.get_artists_page()
		"""

		self._artists_index += 1
		
		params = self._get_params()
		params["page"] = str(self._artists_index)
		
		list = []
		doc = self._request("library.getArtists", True, params)
		for node in doc.getElementsByTagName("artist"):
			name = _extract(node, "name")
			
			playcount = _number(_extract(node, "playcount"))
			tagcount = _number(_extract(node, "tagcount"))
			
			list.append(LibraryItem(Artist(name, *self.auth_data), playcount, tagcount))
		
		return list

	def get_tracks_page(self):
		"""Retreives the next page of tracks in the Library. Returns a sequence of TopItem objects.
		Use the function extract_items like extract_items(Library.get_tracks_page()) to return only a sequence of
		Track objects with no extra data.
		
		Example:
		-------
		library = Library("rj", API_KEY, API_SECRET, SESSION_KEY)
		
		while not library.is_end_of_tracks():
			print library.get_tracks_page()
		"""
		
		self._tracks_index += 1
		
		params = self._get_params()
		params["page"] = str(self._tracks_index)
		
		list = []
		doc = self._request("library.getTracks", True, params)
		for node in doc.getElementsByTagName("track"):
			name = _extract(node, "name")
			artist = _extract(node, "name", 1)
			playcount = _number(_extract(node, "playcount"))
			tagcount = _number(_extract(node, "tagcount"))
			
			list.append(LibraryItem(Track(artist, name, *self.auth_data), playcount, tagcount))
		
		return list
			

class Playlist(_BaseObject):
	"""A Last.fm user playlist."""
	
	def __init__(self, user, id, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		if isinstance(user, User):
			self.user = user
		else:
			self.user = User(user, *self.auth_data)
		
		self.id = unicode(id)

	def _get_info_node(self):
		"""Returns the node from user.getPlaylists where this playlist's info is."""
		
		doc = self._request("user.getPlaylists", True)
		
		for node in doc.getElementsByTagName("playlist"):
			if _extract(node, "id") == str(self.get_id()):
				return node
	
	def _get_params(self):
		return {'user': self.user.get_name(), 'playlistID': self.get_id()}
	
	def get_id(self):
		"""Returns the playlist id."""
		
		return self.id
	
	def get_user(self):
		"""Returns the owner user of this playlist."""
		
		return self.user
	
	def get_tracks(self):
		"""Returns a list of the tracks on this user playlist."""
		
		uri = u'lastfm://playlist/%s' %self.get_id()
		
		return XSPF(uri, *self.auth_data).get_tracks()
	
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
		"""Returns True if the playlist is streamable.
		For a playlist to be streamable, it needs at least 45 tracks by 15 different artists."""
		
		if _extract(self._get_info_node(), "streamable") == '1':
			return True
		else:
			return False
	
	def has_track(self, track):
		"""Checks to see if track is already in the playlist.
		* track: Any Track object.
		"""
		
		return track in self.get_tracks()

	def get_image_url(self, size = IMAGE_LARGE):
		"""Returns the associated image URL.
		* size: The image size. Possible values:
		  o IMAGE_LARGE
		  o IMAGE_MEDIUM
		  o IMAGE_SMALL
		"""
		
		return _extract(self._get_info_node(), "image")[size]
	
	def get_url(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the playlist on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
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
		url = "http://%(domain)s/user/%(user)s/library/playlists/%(appendix)s"
		
		english_url = _extract(self._get_info_node(), "url")
		appendix = english_url[english_url.rfind("/") + 1:]
		
		return url %{'domain': domain_name, 'appendix': appendix, "user": self.get_user().get_name()}
		

class Tag(_BaseObject):
	"""A Last.fm object tag."""
	
	# TODO: getWeeklyArtistChart (too lazy, i'll wait for when someone requests it)
	
	def __init__(self, name, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self.name = name
	
	def _get_params(self):
		return {'tag': self.get_name()}
	
	def __repr__(self):
		return self.get_name().encode('utf-8')
	
	def __eq__(self):
		return self.get_name().lower() == other.get_name().lower()
	
	def __ne__(self):
		return self.get_name().lower() != other.get_name().lower()
	
	def get_name(self):
		"""Returns the name of the tag. """
		
		return self.name

	def get_similar(self):
		"""Returns the tags similar to this one, ordered by similarity. """
		
		doc = self._request('tag.getSimilar', True)
		
		list = []
		names = _extract_all(doc, 'name')
		for name in names:
			list.append(Tag(name, *self.auth_data))
		
		return list
	
	def get_top_albums(self):
		"""Retuns a list of the top albums."""
		
		doc = self._request('tag.getTopAlbums', True)
		
		list = []
		
		for node in doc.getElementsByTagName("album"):
			name = _extract(node, "name")
			artist = _extract(node, "name", 1)
			playcount = _extract(node, "playcount")
			
			list.append(TopItem(Album(artist, name, *self.auth_data), playcount))
		
		return list
		
	def get_top_tracks(self):
		"""Returns a list of the most played Tracks by this artist."""
		
		doc = self._request("tag.getTopTracks", True)
		
		list = []
		for track in doc.getElementsByTagName('track'):
			
			title = _extract(track, "name")
			artist = _extract(track, "name", 1)
			playcount = _number(_extract(track, "playcount"))
			
			list.append( TopItem(Track(artist, title, *self.auth_data), playcount) )
		
		return list
	
	def get_top_artists(self):
		"""Returns a sequence of the most played artists."""
		
		doc = self._request('tag.getTopArtists', True)
		
		list = []
		for node in doc.getElementsByTagName("artist"):
			name = _extract(node, 'name')
			playcount = _extract(node, "playcount")
		
			list.append(TopItem(Artist(name, *self.auth_data), playcount))
		
		return list
	
	def get_weekly_chart_dates(self):
		"""Returns a list of From and To tuples for the available charts."""
		
		doc = self._request("tag.getWeeklyChartList", True)
		
		list = []
		for node in doc.getElementsByTagName("chart"):
			list.append( (node.getAttribute("from"), node.getAttribute("to")) )
		
		return list
	
	def get_weekly_artist_charts(self, from_date = None, to_date = None):
		"""Returns the weekly artist charts for the week starting from the from_date value to the to_date value."""
		
		params = self._get_params()
		if from_date and to_date:
			params["from"] = from_date
			params["to"] = to_date
		
		doc = self._request("tag.getWeeklyArtistChart", True, params)
		
		list = []
		for node in doc.getElementsByTagName("artist"):
			item = Artist(_extract(node, "name"), *self.auth_data)
			weight = _extract(node, "weight")
			list.append(TopItem(item, weight))
		
		return list
	
	def get_url(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the tag page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
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
		
		url = 'http://%(domain)s/tag/%(name)s'
		
		name = _get_url_safe(self.get_name())
		
		return url %{'domain': domain_name, 'name': name}

class Track(_BaseObject, _Taggable):
	"""A Last.fm track."""
	
	def __init__(self, artist, title, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		_Taggable.__init__(self, 'track')
		
		if isinstance(artist, Artist):
			self.artist = artist
		else:
			self.artist = Artist(artist, *self.auth_data)
		
		self.title = title

	def __repr__(self):
		return self.get_artist().get_name().encode('utf-8') + ' - ' + self.get_title().encode('utf-8')

	def __eq__(self, other):
		return (self.get_title().lower() == other.get_title().lower()) and (self.get_artist().get_name().lower() == other.get_artist().get_name().lower())
	
	def __ne__(self, other):
		return (self.get_title().lower() != other.get_title().lower()) or (self.get_artist().get_name().lower() != other.get_artist().get_name().lower())
	
	def _get_params(self):
		return {'artist': self.get_artist().get_name(), 'track': self.get_title()}
			
	def get_artist(self):
		"""Returns the associated Artist object."""
		
		return self.artist
	
	def get_title(self):
		"""Returns the track title."""
		
		return self.title
	
	def get_name(self):
		"""Returns the track title (alias to Track.get_title)."""
		
		return self.get_title()
	
	def get_id(self):
		"""Returns the track id on Last.fm."""
		
		doc = self._request("track.getInfo", True)
		
		return _extract(doc, "id")
	
	def get_duration(self):
		"""Returns the track duration."""
		
		doc = self._request("track.getInfo", True)
		
		return _number(_extract(doc, "duration"))
	
	def get_mbid(self):
		"""Returns the MusicBrainz ID of this track."""
		
		doc = self._request("track.getInfo", True)
		
		return _extract(doc, "mbid")
		
	def get_listener_count(self):
		"""Returns the listener count."""
		
		doc = self._request("track.getInfo", True)
		
		return _number(_extract(doc, "listeners"))
	
	def get_playcount(self):
		"""Returns the play count."""
		
		doc = self._request("track.getInfo", True)
		return _number(_extract(node, "playcount"))
	
	def is_streamable(self):
		"""Returns True if the track is available at Last.fm."""
		
		doc = self._request("track.getInfo", True)
		return _extract(node, "streamable") == "1"
	
	def is_fulltrack_available(self):
		"""Returns True if the fulltrack is available for streaming."""
		
		doc = self._request("track.getInfo", True)
		return doc.getElementsByTagName("streamable")[0].getAttribute("fulltrack") == "1"
		
	def get_album(self):
		"""Returns the album object of this track."""
		
		doc = self._request("track.getInfo", True)
		
		albums = doc.getElementsByTagName("album")
		
		if len(albums) == 0:
			return
		
		node = doc.getElementsByTagName("album")[0]
		return Album(_extract(node, "artist"), _extract(node, "title"))
	
	def get_wiki_published_date(self):
		"""Returns the date of publishing this version of the wiki."""
		
		doc = self._request("track.getInfo", True)
		
		if len(doc.getElementsByTagName("wiki")) == 0:
			return
		
		node = doc.getElementsByTagName("wiki")[0]
		
		return _extract(node, "published")
	
	def get_wiki_summary(self):
		"""Returns the summary of the wiki."""
		
		doc = self._request("track.getInfo", True)
		
		if len(doc.getElementsByTagName("wiki")) == 0:
			return
		
		node = doc.getElementsByTagName("wiki")[0]
		
		return _extract(node, "summary")
		
	def get_wiki_content(self):
		"""Returns the content of the wiki."""
		
		doc = self._request("track.getInfo", True)
		
		if len(doc.getElementsByTagName("wiki")) == 0:
			return
		
		node = doc.getElementsByTagName("wiki")[0]
		
		return _extract(node, "content")
	
	def love(self):
		"""Adds the track to the user's loved tracks. """
		
		self._request('track.love')
	
	def ban(self):
		"""Ban this track from ever playing on the radio. """
		
		self._request('track.ban')
	
	def get_similar(self):
		"""Returns similar tracks for this track on Last.fm, based on listening data. """
		
		doc = self._request('track.getSimilar', True)
		
		list = []
		for node in doc.getElementsByTagName("track"):
			title = _extract(node, 'name')
			artist = _extract(node, 'name', 1)
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list

	def get_top_fans(self, limit = None):
		"""Returns a list of the Users who played this track."""
		
		doc = self._request('track.getTopFans', True)
		
		list = []
		
		elements = doc.getElementsByTagName('user')
		
		for element in elements:
			if limit and len(list) >= limit:
				break
				
			name = _extract(element, 'name')
			weight = _number(_extract(element, 'weight'))
			
			list.append(TopItem(User(name, *self.auth_data), weight))
		
		return list
	
	def share(self, users, message = None):
		"""Shares this track (sends out recommendations). 
  		* users: A list that can contain usernames, emails, User objects, or all of them.
  		* message: A message to include in the recommendation message. 
		"""
		
		#last.fm currently accepts a max of 10 recipient at a time
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
		if message: params['message'] = unicode(message)
		
		self._request('track.share', False, params)
	
	def get_url(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the track page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
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
		url = 'http://%(domain)s/music/%(artist)s/_/%(title)s'
		
		artist = _get_url_safe(self.get_artist().get_name())
		title = _get_url_safe(self.get_title())
		
		return url %{'domain': domain_name, 'artist': artist, 'title': title}
	
class Group(_BaseObject):
	"""A Last.fm group."""
	
	def __init__(self, group_name, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self.name = group_name
	
	def __repr__(self):
		return self.get_name().encode('utf-8')
	
	def __eq__(self, other):
		return self.get_name().lower() == other.get_name().lower()
	
	def __ne__(self, other):
		return self.get_name() != other.get_name()
	
	def _get_params(self):
		return {'group': self.get_name()}
	
	def get_name(self):
		"""Returns the group name. """
		return self.name
	
	def get_weekly_chart_dates(self):
		"""Returns a list of From and To tuples for the available charts."""
		
		doc = self._request("group.getWeeklyChartList", True)
		
		list = []
		for node in doc.getElementsByTagName("chart"):
			list.append( (node.getAttribute("from"), node.getAttribute("to")) )
		
		return list
	
	def get_weekly_artist_charts(self, from_date = None, to_date = None):
		"""Returns the weekly artist charts for the week starting from the from_date value to the to_date value."""
		
		params = self._get_params()
		if from_date and to_date:
			params["from"] = from_date
			params["to"] = to_date
		
		doc = self._request("group.getWeeklyArtistChart", True, params)
		
		list = []
		for node in doc.getElementsByTagName("artist"):
			item = Artist(_extract(node, "name"), *self.auth_data)
			weight = _extract(node, "playcount")
			list.append(TopItem(item, weight))
		
		return list

	def get_weekly_album_charts(self, from_date = None, to_date = None):
		"""Returns the weekly album charts for the week starting from the from_date value to the to_date value."""
		
		params = self._get_params()
		if from_date and to_date:
			params["from"] = from_date
			params["to"] = to_date
		
		doc = self._request("group.getWeeklyAlbumChart", True, params)
		
		list = []
		for node in doc.getElementsByTagName("album"):
			item = Album(_extract(node, "artist"), _extract(node, "name"), *self.auth_data)
			weight = _extract(node, "playcount")
			list.append(TopItem(item, weight))
		
		return list

	def get_weekly_track_charts(self, from_date = None, to_date = None):
		"""Returns the weekly track charts for the week starting from the from_date value to the to_date value."""
		
		params = self._get_params()
		if from_date and to_date:
			params["from"] = from_date
			params["to"] = to_date
		
		doc = self._request("group.getWeeklyTrackChart", True, params)
		
		list = []
		for node in doc.getElementsByTagName("track"):
			item = Track(_extract(node, "artist"), _extract(node, "name"), *self.auth_data)
			weight = _extract(node, "playcount")
			list.append(TopItem(item, weight))
		
		return list
		
	def get_url(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the group page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
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
		
		url = 'http://%(domain)s/group/%(name)s'
		
		name = _get_url_safe(self.get_name())
		
		return url %{'domain': domain_name, 'name': name}

class XSPF(_BaseObject):
	"A Last.fm XSPF playlist."""
	
	def __init__(self, uri, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self.uri = uri
	
	def _get_params(self):
		return {'playlistURL': self.get_uri()}
	
	def __repr__(self):
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
		
		list = []
		for n in doc.getElementsByTagName('track'):
			title = _extract(n, 'title')
			artist = _extract(n, 'creator')
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list

class User(_BaseObject):
	"""A Last.fm user."""
	
	def __init__(self, user_name, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self.name = user_name
		
		self._past_events_index = 0
		self._recommended_events_index = 0
		self._recommended_artists_index = 0
	
	def __repr__(self):
		return self.get_name().encode('utf-8')
	
	def __eq__(self, another):
		return self.get_name() == another.get_name()
	
	def __ne__(self, another):
		return self.get_name() != another.get_name()
	
	def _get_params(self):
		return {"user": self.get_name()}
		
	def get_name(self):
		"""Returns the nuser name."""
		
		return self.name
	
	def get_upcoming_events(self):
		"""Returns all the upcoming events for this user. """
		
		doc = self._request('user.getEvents', True)
		
		ids = _extract_all(doc, 'id')
		events = []
		
		for id in ids:
			events.append(Event(id, *self.auth_data))
		
		return events
	
	def get_friends(self, limit = None):
		"""Returns a list of the user's friends. """
		
		params = self._get_params()
		if limit:
			params['limit'] = unicode(limit)
		
		doc = self._request('user.getFriends', True, params)
		
		names = _extract_all(doc, 'name')
		
		list = []
		for name in names:
			list.append(User(name, *self.auth_data))
		
		return list
	
	def get_loved_tracks(self):
		"""Returns the last 50 tracks loved by this user. """
		
		doc = self._request('user.getLovedTracks', True)
		
		list = []
		for track in doc.getElementsByTagName('track'):
			title = _extract(track, 'name', 0)
			artist = _extract(track, 'name', 1)
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list
	
	def get_neighbours(self, limit = None):
		"""Returns a list of the user's friends."""
		
		params = self._get_params()
		if limit:
			params['limit'] = unicode(limit)
		
		doc = self._request('user.getNeighbours', True, params)
		
		list = []
		names = _extract_all(doc, 'name')
		
		for name in names:
			list.append(User(name, *self.auth_data))
		
		return list
	
	def _get_past_events_pagecount(self):
		"""Returns the number of pages in the past events."""
		
		params = self._get_params()
		params["page"] = str(self._past_events_index)
		doc = self._request("user.getPastEvents", True, params)
		
		return _number(doc.getElementsByTagName("events")[0].getAttribute("totalPages"))
	
	def is_end_of_past_events(self):
		"""Returns True if the end of Past Events was reached."""
		
		return self._past_events_index >= self._get_past_events_pagecount()
		
	def get_past_events_page(self, ):
		"""Retruns a paginated list of all events a user has attended in the past.
		
		Example:
		--------
		
		while not user.is_end_of_past_events():
			print user.get_past_events_page()
		
		"""
		
		self._past_events_index += 1
		params = self._get_params()
		params["page"] = str(self._past_events_index)
		
		doc = self._request('user.getPastEvents', True, params)
		
		list = []
		for id in _extract_all(doc, 'id'):
			list.append(Event(id, *self.auth_data))
		
		return list
				
	def get_playlists(self):
		"""Returns a list of Playlists that this user owns."""
		
		doc = self._request("user.getPlaylists", True)
		
		playlists = []
		for id in _extract_all(doc, "id"):
			playlists.append(Playlist(self.get_name(), id, *self.auth_data))
		
		return playlists
	
	def get_now_playing(self):
		"""Returns the currently playing track, or None if nothing is playing. """
		
		params = self._get_params()
		params['limit'] = '1'
		
		list = []
		
		doc = self._request('user.getRecentTracks', False, params)
		
		e = doc.getElementsByTagName('track')[0]
		
		if not e.hasAttribute('nowplaying'):
			return None
		
		artist = _extract(e, 'artist')
		title = _extract(e, 'name')
		
		return Track(artist, title, *self.auth_data)


	def get_recent_tracks(self, limit = None):
		"""Returns this user's recent listened-to tracks. """
		
		params = self._get_params()
		if limit:
			params['limit'] = unicode(limit)
		
		doc = self._request('user.getRecentTracks', False, params)
		
		list = []
		for track in doc.getElementsByTagName('track'):
			title = _extract(track, 'name')
			artist = _extract(track, 'artist')
			
			if track.hasAttribute('nowplaying'):
				continue	#to prevent the now playing track from sneaking in here
				
			list.append(Track(artist, title, *self.auth_data))
		
		return list
	
	def get_top_albums(self, period = PERIOD_OVERALL):
		"""Returns the top albums played by a user. 
		* period: The period of time. Possible values:
		  o PERIOD_OVERALL
		  o PERIOD_3MONTHS
		  o PERIOD_6MONTHS
		  o PERIOD_12MONTHS 
		"""
		
		params = self._get_params()
		params['period'] = period
		
		doc = self._request('user.getTopAlbums', True, params)
		
		list = []
		for album in doc.getElementsByTagName('album'):
			name = _extract(album, 'name')
			artist = _extract(album, 'name', 1)
			playcount = _extract(album, "playcount")
			
			list.append(TopItem(Album(artist, name, *self.auth_data), playcount))
		
		return list
	
	def get_top_artists(self, period = PERIOD_OVERALL):
		"""Returns the top artists played by a user. 
		* period: The period of time. Possible values:
		  o PERIOD_OVERALL
		  o PERIOD_3MONTHS
		  o PERIOD_6MONTHS
		  o PERIOD_12MONTHS 
		"""
		
		params = self._get_params()
		params['period'] = period
		
		doc = self._request('user.getTopArtists', True, params)
		
		list = []
		for node in doc.getElementsByTagName('artist'):
			name = _extract(node, 'name')
			playcount = _extract(node, "playcount")
			
			list.append(TopItem(Artist(name, *self.auth_data), playcount))
		
		return list
	
	def get_top_tags(self, limit = None):
		"""Returns a sequence of the top tags used by this user with their counts as (Tag, tagcount). 
		* limit: The limit of how many tags to return. 
		"""
		
		doc = self._request("user.getTopTags", True)
		
		list = []
		for node in doc.getElementsByTagName("tag"):
			list.append(TopItem(Tag(_extract(node, "name"), *self.auth_data), _extract(node, "count")))
		
		return list
	
	def get_top_tracks(self, period = PERIOD_OVERALL):
		"""Returns the top tracks played by a user. 
		* period: The period of time. Possible values:
		  o PERIOD_OVERALL
		  o PERIOD_3MONTHS
		  o PERIOD_6MONTHS
		  o PERIOD_12MONTHS 
		"""
		
		params = self._get_params()
		params['period'] = period
		
		doc = self._request('user.getTopTracks', True, params)
		
		list = []
		for track in doc.getElementsByTagName('track'):
			name = _extract(track, 'name')
			artist = _extract(track, 'name', 1)
			playcount = _extract(track, "playcount")
			
			list.append(TopItem(Track(artist, name, *self.auth_data), playcount))
		
		return list
	
	def get_weekly_chart_dates(self):
		"""Returns a list of From and To tuples for the available charts."""
		
		doc = self._request("user.getWeeklyChartList", True)
		
		list = []
		for node in doc.getElementsByTagName("chart"):
			list.append( (node.getAttribute("from"), node.getAttribute("to")) )
		
		return list
	
	def get_weekly_artist_charts(self, from_date = None, to_date = None):
		"""Returns the weekly artist charts for the week starting from the from_date value to the to_date value."""
		
		params = self._get_params()
		if from_date and to_date:
			params["from"] = from_date
			params["to"] = to_date
		
		doc = self._request("user.getWeeklyArtistChart", True, params)
		
		list = []
		for node in doc.getElementsByTagName("artist"):
			item = Artist(_extract(node, "name"), *self.auth_data)
			weight = _extract(node, "playcount")
			list.append(TopItem(item, weight))
		
		return list

	def get_weekly_album_charts(self, from_date = None, to_date = None):
		"""Returns the weekly album charts for the week starting from the from_date value to the to_date value."""
		
		params = self._get_params()
		if from_date and to_date:
			params["from"] = from_date
			params["to"] = to_date
		
		doc = self._request("user.getWeeklyAlbumChart", True, params)
		
		list = []
		for node in doc.getElementsByTagName("album"):
			item = Album(_extract(node, "artist"), _extract(node, "name"), *self.auth_data)
			weight = _extract(node, "playcount")
			list.append(TopItem(item, weight))
		
		return list

	def get_weekly_track_charts(self, from_date = None, to_date = None):
		"""Returns the weekly track charts for the week starting from the from_date value to the to_date value."""
		
		params = self._get_params()
		if from_date and to_date:
			params["from"] = from_date
			params["to"] = to_date
		
		doc = self._request("user.getWeeklyTrackChart", True, params)
		
		list = []
		for node in doc.getElementsByTagName("track"):
			item = Track(_extract(node, "artist"), _extract(node, "name"), *self.auth_data)
			weight = _extract(node, "playcount")
			list.append(TopItem(item, weight))
		
		return list
	
	def compare_with_user(self, user, shared_artists_limit = None):
		"""Compare this user with another Last.fm user.
		Returns a sequence (tasteometer_score, (shared_artist1, shared_artist2, ...))
		user: A User object or a username string/unicode object.
		"""
		
		if isinstance(user, User):
			user = user.get_name()
		
		params = self._get_params()
		if shared_artists_limit:
			params['limit'] = unicode(shared_artists_limit)
		params['type1'] = 'user'
		params['type2'] = 'user'
		params['value1'] = self.get_name()
		params['value2'] = user
		
		doc = _Request('tasteometer.compare', params, *self.auth_data).execute()
		
		score = _extract(doc, 'score')
		
		artists = doc.getElementsByTagName('artists')[0]
		shared_artists_names = _extract_all(artists, 'name')
		
		shared_artists_list = []
		
		for name in shared_artists_names:
			shared_artists_list.append(Artist(name, *self.auth_data))
		
		return (score, shared_artists_list)
	
	def getRecommendedEvents(self, page = None, limit = None):
		"""Returns a paginated list of all events recommended to a user by Last.fm, based on their listening profile.
		* page: The page number of results to return.
		* limit: The limit of events to return.
		"""
		
		params = self._get_params()
		if page:
			params['page'] = unicode(page)
		if limit:
			params['limit'] = unicode(limit)
		
		doc = _Request('user.getRecommendedEvents', params, *self.auth_data).execute()
		
		ids = _extract_all(doc, 'id')
		list = []
		for id in ids:
			list.append(Event(id, *self.auth_data))
		
		return list
	
	def get_url(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the user page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
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
		url = 'http://%(domain)s/user/%(name)s'
		
		name = _get_url_safe(self.get_name())
		
		return url %{'domain': domain_name, 'name': name}

	def get_library(self):
		"""Returns the associated Library object. """
		
		return Library(self, *self.auth_data)

class AuthenticatedUser(User):
	def __init__(self, api_key, api_secret, session_key):
		User.__init__(self, "", api_key, api_secret, session_key);
	
	def _get_params(self):
		return {}
		
	def get_name(self):
		"""Returns the name of the authenticated user."""
		
		doc = self._request("user.getInfo", True)
		
		self.name = _extract(doc, "name")
		return self.name
	
	def get_id(self):
		"""Returns the user id."""
		
		doc = self._request("user.getInfo", True)
		
		return _extract(doc, "id")
	
	def get_image_url(self):
		"""Returns the user's avatar."""
			
		doc = self._request("user.getInfo", True)
		
		return _extract(doc, "image")
	
	def get_language(self):
		"""Returns the language code of the language used by the user."""
		
		doc = self._request("user.getInfo", True)
		
		return _extract(doc, "lang")
	
	def get_country(self):
		"""Returns the name of the country of the user."""
		
		doc = self._request("user.getInfo", True)
		
		return Country(_extract(doc, "country"), *self.auth_data)
	
	def get_age(self):
		"""Returns the user's age."""
		
		doc = self._request("user.getInfo", True)
		
		return _number(_extract(doc, "age"))
	
	def get_gender(self):
		"""Returns the user's gender. Either USER_MALE or USER_FEMALE."""
		
		doc = self._request("user.getInfo", True)
		
		return _extract(doc, "gender")
		
		if value == 'm':
			return USER_MALE
		elif value == 'f':
			return USER_FEMALE
		
		return None
	
	def is_subscriber(self):
		"""Returns whether the user is a subscriber or not. True or False."""
		
		doc = self._request("user.getInfo", True)
		
		return _extract(doc, "subscriber") == "1"
	
	def get_playcount(self):
		"""Returns the user's playcount so far."""
		
		doc = self._request("user.getInfo", True)
		
		return _number(_extract(doc, "playcount"))

	def _get_recommended_events_pagecount(self):
		"""Returns the number of pages in the past events."""
		
		params = self._get_params()
		params["page"] = str(self._recommended_events_index)
		doc = self._request("user.getRecommendedEvents", True, params)
		
		return _number(doc.getElementsByTagName("events")[0].getAttribute("totalPages"))
	
	def is_end_of_recommended_events(self):
		"""Returns True if the end of Past Events was reached."""
		
		return self._recommended_events_index >= self._get_recommended_events_pagecount()
		
	def get_recommended_events_page(self, ):
		"""Retruns a paginated list of all events a user has attended in the past.
		
		Example:
		--------
		
		while not user.is_end_of_recommended_events():
			print user.get_recommended_events_page()
		
		"""
		
		self._recommended_events_index += 1
		params = self._get_params()
		params["page"] = str(self._recommended_events_index)
		
		doc = self._request('user.getRecommendedEvents', True, params)
		
		list = []
		for id in _extract_all(doc, 'id'):
			list.append(Event(id, *self.auth_data))
		
		return list

	def _get_recommended_artists_pagecount(self):
		"""Returns the number of pages in the past artists."""
		
		params = self._get_params()
		params["page"] = str(self._recommended_artists_index)
		doc = self._request("user.getRecommendedArtists", True, params)
		
		return _number(doc.getElementsByTagName("recommendations")[0].getAttribute("totalPages"))
	
	def is_end_of_recommended_artists(self):
		"""Returns True if the end of Past Artists was reached."""
		
		return self._recommended_artists_index >= self._get_recommended_artists_pagecount()
		
	def get_recommended_artists_page(self, ):
		"""Retruns a paginated list of all artists a user has attended in the past.
		
		Example:
		--------
		
		while not user.is_end_of_recommended_artists():
			print user.get_recommended_artists_page()
		
		"""
		
		self._recommended_artists_index += 1
		params = self._get_params()
		params["page"] = str(self._recommended_artists_index)
		
		doc = self._request('user.getRecommendedArtists', True, params)
		
		list = []
		for name in _extract_all(doc, 'name'):
			list.append(Artist(name, *self.auth_data))
		
		return list
	
class _Search(_BaseObject):
	"""An abstract class. Use one of its derivatives."""
	
	def __init__(self, ws_prefix, search_terms, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
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
	
	def _retreive_page(self, page_index):
		"""Returns the node of matches to be processed"""
		
		params = self._get_params()
		params["page"] = str(page_index)
		doc = self._request(self._ws_prefix + ".search", True, params)
		
		return doc.getElementsByTagName(self._ws_prefix + "matches")[0]
	
	def _retrieve_next_page(self):
		self._last_page_index += 1
		return self._retreive_page(self._last_page_index)

class AlbumSearch(_Search):
	"""Search for an album by name."""
	
	def __init__(self, album_name, api_key, api_secret, session_key):
		
		_Search.__init__(self, "album", {"album": album_name}, api_key, api_secret, session_key)
	
	def get_next_page(self):
		"""Returns the next page of results as a sequence of Album objects."""
		
		master_node = self._retrieve_next_page()
		
		list = []
		for node in master_node.getElementsByTagName("album"):
			list.append(Album(_extract(node, "artist"), _extract(node, "name"), *self.auth_data))
		
		return list

class ArtistSearch(_Search):
	"""Search for an artist by artist name."""
	
	def __init__(self, artist_name, api_key, api_secret, session_key):
		_Search.__init__(self, "artist", {"artist": artist_name}, api_key, api_secret, session_key)

	def get_next_page(self):
		"""Returns the next page of results as a sequence of Artist objects."""
		
		master_node = self._retrieve_next_page()
		
		list = []
		for node in master_node.getElementsByTagName("artist"):
			list.append(Artist(_extract(node, "name"), *self.auth_data))
		
		return list

class TagSearch(_Search):
	"""Search for a tag by tag name."""
	
	def __init__(self, tag_name, api_key, api_secret, session_key):
		
		_Search.__init__(self, "tag", {"tag": tag_name}, api_key, api_secret, session_key)
		
	def get_next_page(self):
		"""Returns the next page of results as a sequence of Tag objects."""
		
		master_node = self._retrieve_next_page()
		
		list = []
		for node in master_node.getElementsByTagName("tag"):
			list.append(Tag(_extract(node, "name"), *self.auth_data))
		
		return list

class TrackSearch(_Search):
	"""Search for a track by track title. If you don't wanna narrow the results down
	by specifying the artist name, set it to empty string."""
	
	def __init__(self, artist_name, track_title, api_key, api_secret, session_key):
		
		_Search.__init__(self, "track", {"track": track_title, "artist": artist_name}, api_key, api_secret, session_key)

	def get_next_page(self):
		"""Returns the next page of results as a sequence of Track objects."""
		
		master_node = self._retrieve_next_page()
		
		list = []
		for node in master_node.getElementsByTagName("track"):
			list.append(Track(_extract(node, "artist"), _extract(node, "name"), *self.auth_data))
		
		return list

class VenueSearch(_Search):
	"""Search for a venue by its name. If you don't wanna narrow the results down
	by specifying a country, set it to empty string."""
	
	def __init__(self, venue_name, country_name, api_key, api_secret, session_key):
		
		_Search.__init__(self, "venue", {"venue": venue_name, "country": country_name}, api_key, api_secret, session_key)

	def get_next_page(self):
		"""Returns the next page of results as a sequence of Track objects."""
		
		master_node = self._retrieve_next_page()
		
		list = []
		for node in master_node.getElementsByTagName("venue"):
			list.append(Venue(_extract(node, "id"), *self.auth_data))
		
		return list

class Venue(_BaseObject):
	"""A venue where events are held."""
	
	# TODO: waiting for a venue.getInfo web service to use.
	
	def __init__(self, id, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self.id = _number(id)
	
	def __repr__(self):
		return "Venue #" + str(self.id)
	
	def __eq__(self, other):
		return self.get_id() == other.get_id()
	
	def _get_params(self):
		return {"venue": self.get_id()}
		
	def get_id(self):
		"""Returns the id of the venue."""
		
		return self.id
	
	def get_upcoming_events(self):
		"""Returns the upcoming events in this venue."""
		
		doc = self._request("venue.getEvents", True)
		
		list = []
		for node in doc.getElementsByTagName("event"):
			list.append(Event(_extract(node, "id"), *self.auth_data))
		
		return list
	
	def get_past_events(self):
		"""Returns the past events held in this venue."""
		
		doc = self._request("venue.getEvents", True)
		
		list = []
		for node in doc.getElementsByTagName("event"):
			list.append(Event(_extract(node, "id"), *self.auth_data))
		
		return list
		
def create_new_playlist(title, description, api_key, api_secret, session_key):
	"""Creates a playlist for the authenticated user and returns it.
	* title: The title of the new playlist.
	* description: The description of the new playlist.
	"""
	
	params = dict()
	params['title'] = unicode(title)
	params['description'] = unicode(description)
	
	doc = _Request('playlist.create', params, api_key, api_secret, session_key).execute()
	
	id = doc.getElementsByTagName("id")[0].firstChild.data
	user = doc.getElementsByTagName('playlists')[0].getAttribute('user')
	
	return Playlist(user, id, api_key, api_secret, session_key)

def get_authenticated_user(api_key, api_secret, session_key):
	"""Returns the authenticated user."""
	
	return AuthenticatedUser(api_key, api_secret, session_key)

def md5(text):
	"""Returns the md5 hash of a string."""
	
	hash = hashlib.md5()
	hash.update(text.encode('utf-8'))
	
	return hash.hexdigest()

def enable_proxy(host, port):
	"""Enable a default web proxy."""
	
	global __proxy
	global __proxy_enabled
	
	__proxy = [host, _number(port)]
	__proxy_enabled = True

def disable_proxy():
	"""Disable using the web proxy."""
	
	global __proxy_enabled
	
	__proxy_enabled = False

def is_proxy_enabled():
	"""Returns True if a web proxy is enabled."""
	
	global __proxy_enabled
	
	return __proxy_enabled

def _get_proxy():
	"""Returns proxy details."""
	
	global __proxy
	
	return __proxy

def async_call(sender, call, callback = None, call_args = None, callback_args = None):
	"""This is the function for setting up an asynchronous operation.
	* call: The function to call asynchronously.
	* callback: The function to call after the operation is complete, Its prototype has to be like:
		callback(sender, output[, param1, param3, ... ])
	* call_args: A sequence of args to be passed to call.
	* callback_args: A sequence of args to be passed to callback.
	"""
	
	thread = _ThreadedCall(sender, call, call_args, callback, callback_args)
	thread.start()

def enable_caching(cache_dir = None):
	"""Enables caching request-wide for all cachable calls.
	* cache_dir: A directory path to use to store the caching data. Set to None to use a temporary directory.
	"""
	
	global __cache_dir
	global __cache_enabled
	
	if cache_dir == None:
		import tempfile
		__cache_dir = tempfile.mkdtemp()
	else:
		if not os.path.exists(cache_dir):
			os.mkdir(cache_dir)
		__cache_dir = cache_dir
	
	__cache_enabled = True
		
def disable_caching():
	"""Disables all caching features."""

	global __cache_enabled
		
	__cache_enabled = False
	
	print "cache is disabled"

def is_caching_enabled():
	"""Returns True if caching is enabled."""
	
	global __cache_enabled
	
	return __cache_enabled

def _get_cache_dir():
	"""Returns the directory in which cache files are saved."""
	
	global __cache_dir
	global __cache_enabled
	
	return __cache_dir

def _extract(node, name, index = 0):
	"""Extracts a value from the xml string"""
	
	nodes = node.getElementsByTagName(name)
	
	if len(nodes):
		if nodes[index].firstChild:
			return nodes[index].firstChild.data.strip()
	else:
		return None

def _extract_all(node, name, limit_count = None):
	"""Extracts all the values from the xml string. returning a list."""
	
	list = []
	
	for i in range(0, len(node.getElementsByTagName(name))):
		if len(list) == limit_count:
			break
		
		list.append(_extract(node, name, i))
	
	return list

def _get_url_safe(text):
	"""Does all kinds of tricks on a text to make it safe to use in a url."""
	
	if type(text) == type(unicode()):
		text = text.encode('utf-8')
	
	return urllib.quote_plus(urllib.quote_plus(text)).lower()

def _number(string):
	"""Extracts an int from a string. Returns a 0 if None or an empty string was passed."""
	
	if not string:
		return 0
	elif string == "":
		return 0
	else:
		return int(string)

def search_for_album(album_name, api_key, api_secret, session_key):
	"""Searches for an album by its name. Returns a AlbumSearch object.
	Use get_next_page() to retreive sequences of results."""
	
	return AlbumSearch(album_name, api_key, api_secret, session_key)

def search_for_artist(artist_name, api_key, api_secret, session_key):
	"""Searches of an artist by its name. Returns a ArtistSearch object.
	Use get_next_page() to retreive sequences of results."""
	
	return ArtistSearch(artist_name, api_key, api_secret, session_key)

def search_for_tag(tag_name, api_key, api_secret, session_key):
	"""Searches of a tag by its name. Returns a TagSearch object.
	Use get_next_page() to retreive sequences of results."""
	
	return TagSearch(tag_name, api_key, api_secret, session_key)

def search_for_track(artist_name, track_name, api_key, api_secret, session_key):
	"""Searches of a track by its name and its artist. Set artist to an empty string if not available.
	Returns a TrackSearch object.
	Use get_next_page() to retreive sequences of results."""
	
	return TrackSearch(artist_name, track_name, api_key, api_secret, session_key)

def search_for_venue(venue_name, country_name, api_key, api_secret, session_key):
	"""Searches of a venue by its name and its country. Set country_name to an empty string if not available.
	Returns a VenueSearch object.
	Use get_next_page() to retreive sequences of results."""

	return VenueSearch(venue_name, country_name, api_key, api_secret, session_key)

def extract_items(topitems_or_libraryitems):
	"""Extracts a sequence of items from a sequence of TopItem or LibraryItem objects."""
	
	list = []
	for i in topitems_or_libraryitems:
		list.append(i.get_item())
	
	return list

def get_top_tags(api_key, api_secret, session_key):
	"""Returns a sequence of the most used Last.fm tags as a sequence of TopItem objects."""
	
	doc = _Request("tag.getTopTags", dict(), api_key, api_secret, session_key).execute(True)
	list = []
	for node in doc.getElementsByTagName("tag"):
		tag = Tag(_extract(node, "name"), api_key, api_secret, session_key)
		weight = _extract(node, "count")
		
		list.append(TopItem(tag, weight))
	
	return list

def get_track_by_mbid(mbid, api_key, api_secret, session_key):
	"""Looks up a track by its MusicBrainz ID."""
	
	params = {"mbid": unicode(mbid)}
	
	doc = _Request("track.getInfo", params, api_key, api_secret, session_key).execute(True)
	
	return Track(_extract(doc, "name", 1), _extract(doc, "name"), api_key, api_secret, session_key)

def get_artist_by_mbid(mbid, api_key, api_secret, session_key):
	"""Loooks up an artist by its MusicBrainz ID."""
	
	params = {"mbid": unicode(mbid)}
	
	doc = _Request("artist.getInfo", params, api_key, api_secret, session_key).execute(True)
	
	return Artist(_extract(doc, "name"), api_key, api_secret, session_key)

def get_album_by_mbid(mbid, api_key, api_secret, session_key):
	"""Looks up an album by its MusicBrainz ID."""
	
	params = {"mbid": unicode(mbid)}
	
	doc = _Request("album.getInfo", params, api_key, api_secret, session_key).execute(True)
	
	return Album(_extract(doc, "artist"), _extract(doc, "name"), api_key, api_secret, session_key)

def _delay_call():
	"""Makes sure that web service calls are at least a second apart."""
	
	global __last_call_time
	
	# delay time in seconds
	DELAY_TIME = 1.0
	now = time.time()
	
	print "Last call:", __last_call_time
	print "Now:", int(time.time())
	
	if (now - __last_call_time) < DELAY_TIME:
		time.sleep(1)
	
	__last_call_time = now
