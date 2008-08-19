# -*- coding: utf-8 -*-
#
# pylast - Python bindings for the Last.fm webservices.
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
# For help regarding using this library, please visit the official
# documentation at http://code.google.com/p/pylast/wiki/Documentation

LIB_NAME = 'pyLast'
LIB_VERSION = '0.2b'

API_SERVER = 'ws.audioscrobbler.com'
API_SUBDIR = '/2.0/'

import md5
import httplib
import urllib
import threading
from xml.dom import minidom

STATUS_OK = 'ok'
STATUS_FAILED = 'failed'
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

def _status2str(lastfm_status):
	
	statuses = {
		STATUS_OK: 'OK',
		STATUS_FAILED: 'Failed',
		STATUS_INVALID_METHOD: 'Invalid Method - No method with that name in this package',
		STATUS_TOKEN_ERROR: 'There was an error granting the request token.',
		STATUS_INVALID_SERVICE: 'Invalid service - This service does not exist',
		STATUS_AUTH_FAILED: 'Authentication Failed - You do not have permissions to access the service',
		STATUS_INVALID_FORMAT: "Invalid format - This service doesn't exist in that format",
		STATUS_INVALID_PARAMS: 'Invalid parameters - Your request is missing a required parameter',
		STATUS_INVALID_RESOURCE: 'Invalid resource specified',
		STATUS_INVALID_SK: 'Invalid session key - Please re-authenticate',
		STATUS_INVALID_API_KEY: 'Invalid API key - You must be granted a valid key by last.fm',
		STATUS_OFFLINE: 'Service Offline - This service is temporarily offline. Try again later.',
		STATUS_SUBSCRIBERS_ONLY: 'Subscribers Only - This service is only available to paid last.fm subscribers',
		STATUS_TOKEN_UNAUTHORIZED: 'This token has not been authorized',
		STATUS_TOKEN_EXPIRED: 'This token has expired'
	}
	
	return statuses[int(lastfm_status)]

class ServiceException(Exception):
	"""Exception related to the Last.fm web service"""
	
	def __init__(self, lastfm_status, details):
		self._lastfm_status = lastfm_status
		self._details = details
	
	def __str__(self):
		return "%s: %s." %(_status2str(self._lastfm_status), self._details)

class Asynchronizer(threading.Thread):
	"""Hopingly, this class would help perform asynchronous operations less painfully.
	For inherited use only. And you must call Asynchronizer.__init__(descendant) before usage.
	"""
	
	def __init__(self):
		threading.Thread.__init__(self)
		
		self._calls = {}		#calls is structured like this: {call_pointer: (arg1, arg2, ...)}
		self._callbacks = {} 	#callbacks is structred like this: {call_pointer: callback_pointer}
	
	def run(self):
		"""Avoid running this function. Use start() to begin the thread's work."""
		for call in self._calls.keys():
			output = call(*(self._calls[call]))
			callback = self._callbacks[call]
			callback(self, output)
			
			del self._calls[call]
			del self._callbacks[call]
	
	def async_call(self, callback, call, *call_args):
		"""This is the function for setting up an asynchronous operation.
		callback: the function to callback afterwards, accepting two argument, one being the sender and the other is the return of the target call.
		call: the target call.
		*call_args: any number of arguments to pass to the target call function.
		"""
		
		self._calls[call] = call_args
		self._callbacks[call] = callback

class Exceptionable(object):
	"""An abstract class that adds support for error reporting."""
	
	def __init__(self, parent = None, raising_exceptions = False):
		self.__errors = []
		self.__raising_exceptions = raising_exceptions
		
		#An Exceptionable parent to mirror all the errors to automatically.
		self._parent = parent
	
	def last_error(self):
		"""Returns the last error, or None."""
		
		if len(self.__errors):
			return self.__errors[len(self.__errors) -1]
		else:
			return None
	
	def _report_error(self, exception):
		
		if self.get_raising_exceptions():
			raise exception
		
		self.__errors.append(exception)
		
		if self._parent:
			self._parent._mirror_errors(self)
	
	def _mirror_errors(self, exceptional):
		"""Mirrors the errors from another Exceptional object"""
		
		for e in exceptional.get_all_errors():
			self._report_error(e)
	
	def clear_erros(self):
		"""Clear the error log for this object."""
		self.__errors = []
	
	def get_all_errors(self):
		"""Return a list of exceptions raised about this object."""
		
		return self.__errors
	
	def enable_raising_exceptions(self):
		"""Enable raising the exceptions about this object."""
		self.__raising_exceptions = True
	
	def disable_raising_exceptions(self):
		"""Disable raising the exceptions about this object, but still report them to the log."""
		self.__raising_exceptions = False
	
	def get_raising_exceptions(self):
		"""Get the status on raising exceptions."""
		return self.__raising_exceptions
	
class Request(Exceptionable):
	"""Representing an abstract web service operation."""
	
	def __init__(self, parent, method_name, api_key, params, sign_it = False, secret = None):
		Exceptionable.__init__(self, parent)
		
		self.method_name = method_name
		self.api_key = api_key
		self.params = params
		self.sign_it = sign_it
		self.secret = secret
	
	def _getSignature(self):
		"""Returns a 32-character hexadecimal md5 hash of the signature string."""
		
		keys = self.params.keys()[:]
		
		keys.sort()
		
		string = unicode()
		
		for name in keys:
			string += name
			string += self.params[name]
		
		string += self.secret
		
		hash = md5.new()
		hash.update(string)
		
		return hash.hexdigest()
	
	def execute(self):
		"""Returns the XML DOM response of the POST request from the server"""
		
		self.params['api_key'] = self.api_key
		self.params['method'] = self.method_name
		if self.sign_it:
			self.params['api_sig'] = self._getSignature()
		
		data = []
		for name in self.params.keys():
			data.append('='.join((name, self.params[name])))
		
		try:
			conn = httplib.HTTPConnection(API_SERVER)
			headers = {
				"Content-type": "application/x-www-form-urlencoded",
				'Accept-Charset': 'utf-8',
				'User-Agent': LIB_NAME + '/' + LIB_VERSION
				}
			conn.request('POST', API_SUBDIR, '&'.join(data), headers)
			response = conn.getresponse()
		except Exception, e:
			self._report_error(e)
			return None
		
		doc = minidom.parse(response)
		
		if self.__checkResponseStatus(doc) == STATUS_OK:
			return doc
		
		return None
		
	def __checkResponseStatus(self, xml_dom):
		"""Checks the response for errors and raises one if any exists."""
		
		doc = xml_dom
		e = doc.getElementsByTagName('lfm')[0]
		
		if e.getAttribute('status') == STATUS_OK:
			return STATUS_OK
		else:
			e = doc.getElementsByTagName('error')[0]
			status = e.getAttribute('code')
			details = e.firstChild.data.strip()
			self._report_error(ServiceException(status, details))

class SessionGenerator(Asynchronizer, Exceptionable):
	"""Steps of authorization:
	1. Retrieve token: token = getToken()
	2. Authorize this token by openning the web page at the URL returned by getAuthURL(token)
	3. Call getSessionData(token) to collect the session parameters.
	
	A session key's lifetime is infinie, unless the user provokes the rights of the given API Key.
	"""
	
	def __init__(self, api_key, secret):
		Asynchronizer.__init__(self)
		Exceptionable.__init__(self)
		
		self.api_key = api_key
		self.secret = secret
	
	
	def getToken(self):
		"""Retrieves a token from Last.fm.
		The token then has to be authorized from getAuthURL before creating session.
		"""
		
		
		doc = Request(self, 'auth.getToken', self.api_key, dict(), True, self.secret).execute()
		
		if not doc:
			return None
		
		e = doc.getElementsByTagName('token')[0]
		return e.firstChild.data
		
	
	def getAuthURL(self, token):
		"""The user must open this page, and authorize the given token."""
		
		url = 'http://www.last.fm/api/auth/?api_key=%(api)s&token=%(token)s' % \
			{'api': self.api_key, 'token': token}
		return url
	
	def getSessionData(self, token):
		"""Retrieves session data for the authorized token.
		getSessionData(token) --> {'name': str, 'key': str, 'subscriber': bool}
		"""
		
		params = {'token': token}
		doc = Request(self, 'auth.getSession', self.api_key, params, True, self.secret).execute()
		
		if not doc:
			return None
		
		name_e = doc.getElementsByTagName('name')[0]
		key_e = doc.getElementsByTagName('key')[0]
		subscriber_e = doc.getElementsByTagName('subscriber')[0]
		
		data = {}
		data['name'] = name_e.firstChild.data
		data['key'] = key_e.firstChild.data
		data['subscriber'] = bool(subscriber_e.firstChild.data)
		
		return data

class BaseObject(Asynchronizer, Exceptionable):
	"""An abstract webservices object."""
		
	def __init__(self, api_key, secret, session_key):
		Asynchronizer.__init__(self)
		Exceptionable.__init__(self)
		
		self.api_key = api_key
		self.secret = secret
		self.session_key = session_key
		
		self.auth_data = (self.api_key, self.secret, self.session_key)
	
	def _extract(self, node, name, index = 0):
		"""Extracts a value from the xml string"""
		
		nodes = node.getElementsByTagName(name)
		
		if len(nodes):
			if nodes[index].firstChild:
				return nodes[index].firstChild.data.strip()
		else:
			return None
	
	def _extract_all(self, node, name, limit_count = None):
		"""Extracts all the values from the xml string. returning a list."""
		
		list = []
		
		for i in range(0, len(node.getElementsByTagName(name))):
			if len(list) == limit_count:
				break
			
			list.append(self._extract(node, name, i))
		
		return list
	
	def _get_url_safe(self, text):
		
		if type(text) == type(unicode()):
			text = text.encode('utf-8')
		
		return urllib.quote_plus(text)

	def toStr():
		return ""
	
	def _hash(self):
		return self.toStr().lower()
	
	def __str__(self):
		return self.toStr()

class Cacheable(object):
	"""Common functions for objects that can have cached metadata"""
	
	def __init__(self, user_set_data = False):
		
		# user_set_data identifies objects like Track that doesn't have
		# a getInfo function, so the user sets the extra data from other feeds
		
		self._cached_info = None
		self._user_set_data = user_set_data
	
	def _getInfo(self):
		"""Abstract function, should be inherited"""
	
	def _getCachedInfo(self):
		"""Returns the cached collection of info regarding this object
		If not available in cache, it will be downloaded first
		"""
		
		if self._user_set_data:
			return None
		
		if not self._cached_info:
			self._cached_info = self._getInfo()
		
		return self._cached_info
	
	def _setCachedInfo(self, info):
		"""Set the info for objects that does not have a getInfo function"""
		
		self._cached_info = info


class Album(BaseObject, Cacheable):
	
	def __init__(self, artist_name, album_title, api_key, secret, session_key):
		BaseObject.__init__(self, api_key, secret, session_key)
		Cacheable.__init__(self)
		
		self._artist_name = artist_name
		self._album_title = album_title
		
		self._cached_info = None
	
	def _getParams(self):
		return {'artist': self._artist_name, 'album': self._album_title, 'sk': self.session_key}

	def _getInfo(self):
		"""Get the metadata for an album"""	
		
		params = self._getParams()
		
		doc = Request(self, 'album.getInfo', self.api_key, params).execute()
		
		if not doc:
			return None
		
		data = {}
		
		data['name'] = self._extract(doc, 'name')
		data['artist'] = self._extract(doc, 'artist')
		data['id'] = self._extract(doc, 'id')
		data['release_date'] = self._extract(doc, 'releasedate')
		data['images'] = self._extract_all(doc, 'image')
		data['listeners'] = self._extract(doc, 'listeners')
		data['play_count'] = self._extract(doc, 'playcount')
		
		tags_element = doc.getElementsByTagName('toptags')[0]
		data['top_tags'] = self._extract_all(tags_element, 'name')
		
		return data
	
	def getArtist(self):
		"""Returns the associated Artist object. """
		
		return Artist(self._artist_name, *self.auth_data)
	
	def getTitle(self):
		"""Returns the album title."""
		
		return self._album_title
	
	def getReleaseDate(self):
		"""Retruns the release date of the album."""
		
		return self._getCachedInfo()['release_date']
	
	def getImage(self, size = IMAGE_LARGE):
		"""Returns the associated image URL.
    	  * size: The image size. Possible values:
            o IMAGE_LARGE
            o IMAGE_MEDIUM
            o IMAGE_SMALL 
		"""
		
		return self._getCachedInfo()['images'][size]
	
	def getID(self):
		"""Returns the Last.fm ID. """
		
		return self._getCachedInfo()['id']
	
	def getPlayCount(self):
		"""Returns the number of plays on Last.fm."""
		
		return self._getCachedInfo()['play_count']
	
	def getListenerCount(self):
		"""Returns the number of liteners on Last.fm."""
		
		return self._getCachedInfo()['listeners']
	
	def getTopTags(self):
		"""Returns a list of the most-applied tags to this album. """
		
		l = []
		for tag in self._getCachedInfo()['top_tags']:
			l.append(Tag(tag, *self.auth_data))
		
		return l
	
	def addTags(self, *tags):
		"""Adds one or several tags.
		* *tags: Any number of tag names or Tag objects. 
		"""
		
		#last.fm currently accepts a max of 10 tags at a time
		while(len(tags) > 10):
			section = tags[0:9]
			tags = tags[9:]
			self.addTags(section)
		
		if len(tags) == 0:
			return None
		
		ntags = []
		for tag in tags:
			if isinstance(tag, Tag):
				ntags.append(tag.getName())
			else:
				ntags.append(tag)
		
		tagstr = ','.join(ntags)
		
		params = self._getParams()
		params['tags'] = tagstr
		
		Request(self, 'album.addTags', self.api_key, params, True, self.secret).execute()
	
	def getTags(self):
		"""Returns a list of the user-set tags to this album."""
		
		params = self._getParams()
		doc = Request(self, 'album.getTags', self.api_key, params, True, self.secret).execute()
		
		if not doc:
			return None
		
		tag_names = self._extract_all(doc, 'name')
		tags = []
		for tag in tag_names:
			tags.append(Tag(tag, *self.auth_data))
		
		return tags
	
	def _removeTag(self, single_tag):
		"""Remove a user's tag from an album"""
		
		if isinstance(single_tag, Tag):
			single_tag = single_tag.getName()
		
		params = self._getParams()
		params['tag'] = single_tag
		
		Request(self, 'album.removeTag', self.api_key, params, True, self.secret).execute()
	
	def removeTags(self, *tags):
		"""Removes one or several tags from this album.
		    * *tags: Any number of tag names or Tag objects. 
		"""
		
		for tag in tags:
			self._removeTag(tag)
	
	def clearTags(self):
		"""Clears all the user-set tags. """
		
		self.removeTags(*(self.getTags()))
	
	def fetchPlaylist(self):
		"""Returns the list of Tracks on this album. """
		
		uri = 'lastfm://playlist/album/%s' %self._getCachedInfo()['id']
		
		return Playlist(uri, *self.auth_data).fetch()
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the album page on Last.fm. 
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
		
		url = 'http://%(domain)s/music/%(artist)s/%(album)s'
		
		artist = self._get_url_safe(self.getArtist().getName())
		album = self._get_url_safe(self.getTitle())
		
		return url %{'domain': domain_name, 'artist': artist, 'album': album}

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getArtist().getName() + u' - ' + self.getTitle()

class Track(BaseObject, Cacheable):
	def __init__(self, artist_name, title, api_key, secret, session_key, extra_info = None):
		BaseObject.__init__(self, api_key, secret, session_key)
		Cacheable.__init__(self, True)
		
		self._artist_name = artist_name
		self._title = title
		
		self._setCachedInfo(extra_info)
	
	def _getParams(self):
		return {'sk': self.session_key, 'artist': self._artist_name, 'track': self._title}
	
	def getArtist(self):
		"""Returns the associated Artist object. """
		
		return Artist(self._artist_name, *self.auth_data)
	
	def getTitle(self):
		"""Returns the track title. """
		
		return self._title
	
	def addTags(self, *tags):
		"""Adds one or several tags. 
		  * *tags: Any number of tag names or Tag objects. 
		"""
		
		#last.fm currently accepts a max of 10 tags at a time
		while(len(tags) > 10):
			section = tags[0:9]
			tags = tags[9:]
			self.addTags(section)
		
		if len(tags) == 0:
			return None
		
		tagstr = ','.join(tags)
		
		params = self._getParams()
		params['tags'] = tagstr
		
		Request(self, 'track.addTags', self.api_key, params, True, self.secret).execute()
	
	def addToPlaylist(self, playlist_id):
		"""Adds this track to a user playlist. 
		  * playlist_id: The unique playlist ID. 
		"""
		
		params = self._getParams()
		params['playlistID'] = unicode(playlist_id)
		
		Request(self, 'playlist.addTrack', self.api_key, params, True, self.secret).execute()
	
	def love(self):
		"""Adds the track to the user's loved tracks. """
		
		params = self._getParams()
		Request(self, 'track.love', self.api_key, params, True, self.secret).execute()
	
	def ban(self):
		"""Ban this track from ever playing on the radio. """
		
		params = self._getParams()
		Request(self, 'track.ban', self.api_key, params, True, self.secret).execute()
	
	def getSimilar(self):
		"""Returns similar tracks for this track on Last.fm, based on listening data. """
		
		params = self._getParams()
		doc = Request(self, 'track.getSimilar', self.api_key, params).execute()
		
		if not doc:
			return None
		
		tracks = doc.getElementsByTagName('track')
		
		data = []
		for track in tracks:
			extra_info = {}
			
			title = self._extract(track, 'name', 0)
			artist = self._extract(track, 'name', 1)
			extra_info['images'] = self._extract_all(track, 'image')
			
			data.append(Track(artist, title, self.api_key, self.secret, self.session_key, extra_info))
		
		return data
	
	def getTags(self):
		"""Returns tags applied by the user to this track. """
		
		params = self._getParams()
		doc = Request(self, 'track.getTags', self.api_key, params, True, self.secret).execute()
		
		if not doc:
			return None
		
		names = self._extract_all(doc, 'name')
		list = []
		for name in names:
			list.append(Tag(name, *self.auth_data))
		
		return list
	
	def getTopFans(self):
		"""Returns the top fans for this track on Last.fm. """
		
		params = self._getParams()
		doc = Request(self, 'track.getTopFans', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		names = self._extract_all(doc, 'name')
		for name in names:
			list.append(User(name, *self.auth_data))
		
		return list
	
	def getTopTags(self):
		"""Returns the top tags for this track on Last.fm, ordered by tag count. """
		
		params = self._getParams()
		doc = Request(self, 'track.getTopTags', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		names = self._extract_all(doc, 'name')

		for name in names:
			list.append(Tag(name, *self.auth_data))
		
		return list
	
	def _removeTag(self, single_tag):
		"""Remove a user's tag from a track"""
		
		if isinstance(single_tag, Tag):
			single_tag = single_tag.getName()
		
		params = self._getParams()
		params['tag'] = single_tag
		
		Request(self, 'track.removeTag', self.api_key, params, True, self.secret).execute()

	def removeTags(self, *tags):
		"""Removes one or several tags from this track. 
		  * *tags: Any number of tag names or Tag objects. 
		"""
		
		for tag in tags:
			self._removeTag(tag)
	
	def clearTags(self):
		"""Clears all the user-set tags. """
		
		self.removeTags(*(self.getTags()))
	
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
				nusers.append(user.getName())
			else:
				nusers.append(user)
		
		params = self._getParams()
		recipients = ','.join(nusers)
		params['recipient'] = recipients
		if message: params['message'] = message
		
		Request(self, 'track.share', self.api_key, params, True, self.secret).execute()
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
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
		
		artist = self._get_url_safe(self.getArtist().getName())
		title = self._get_url_safe(self.getTitle())
		
		return url %{'domain': domain_name, 'artist': artist, 'title': title}

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getArtist().getName() + u' - ' + self.getTitle()
		
class Artist(BaseObject, Cacheable):
	
	def __init__(self, artist_name, api_key, secret, session_key):
		BaseObject.__init__(self, api_key, secret, session_key)
		Cacheable.__init__(self)
		
		self._artist_name = artist_name
	
	def _getParams(self):
		return {'sk': self.session_key, 'artist': self._artist_name}

	def _getInfo(self):
		"""Get the metadata for an artist on Last.fm, Includes biography"""
		
		params = self._getParams()
		doc = Request(self, 'artist.getInfo', self.api_key, params).execute()
		
		if not doc:
			return None
		
		data = {}
		
		data['name'] = self._extract(doc, 'name')
		data['images'] = self._extract_all(doc, 'image', 3)
		data['streamable'] = self._extract(doc, 'streamable')
		data['listeners'] = self._extract(doc, 'listeners')
		data['play_count'] = self._extract(doc, 'playcount')
		bio = {}
		bio['published'] = self._extract(doc, 'published')
		bio['summary'] = self._extract(doc, 'summary')
		bio['content'] = self._extract(doc, 'content')
		data['bio'] = bio
		
		return data
	
	def getName(self):
		"""Returns the name of the artist. """
		
		return self._artist_name
	
	def getImage(self, size = IMAGE_LARGE):
		"""Returns the associated image URL. 
    	  * size: The image size. Possible values:
            o IMAGE_LARGE
            o IMAGE_MEDIUM
            o IMAGE_SMALL 
		"""
		
		return self._getCachedInfo()['images'][size]
	
	def getPlayCount(self):
		"""Returns the number of plays on Last.fm. """
		
		return self._getCachedInfo()['play_count']
	
	def getListenerCount(self):
		"""Returns the number of liteners on Last.fm. """
		
		return self._getCachedInfo()['listeners']
	
	def getBioPublishedDate(self):
		"""Returns the date on which the artist's biography was published. """
		
		return self._getCachedInfo()['bio']['published']
	
	def getBioSummary(self):
		"""Returns the summary of the artist's biography. """
		
		return self._getCachedInfo()['bio']['summary']
	
	def getBioContent(self):
		"""Returns the content of the artist's biography. """
		
		return self._getCachedInfo()['bio']['content']
	
	def addTags(self, *tags):
		"""Adds one or several tags. 
		  * *tags: Any number of tag names or Tag objects. 
		"""
		
		#last.fm currently accepts a max of 10 tags at a time
		while(len(tags) > 10):
			section = tags[0:9]
			tags = tags[9:]
			self.addTags(section)
		
		if len(tags) == 0:
			return None
		
		ntags = []
		for tag in tags:
			if isinstance(tag, Tag):
				ntags.append(tag.getName())
			else:
				ntags.append(tag)
		
		tagstr = ','.join(ntags)
		
		params = self._getParams()
		params['tags'] = tagstr
		
		Request(self, 'artist.addTags', self.api_key, params, True, self.secret).execute()
	
	def getEvents(self):
		"""Returns a list of the upcoming Events for this artist. """
		
		params = self._getParams()
		doc = Request(self, 'artist.getEvents', self.api_key, params).execute()
		
		ids = self._extract_all(doc, 'id')
		
		events = []
		for id in ids:
			events.append(Event(id, *self.auth_data))
		
		return events
	
	def getSimilar(self, limit = None):
		"""Returns the similar artists on Last.fm. 
		  * limit: The limit of similar artists to retrieve. 
		"""
		
		params = self._getParams()
		if limit:
			params['limit'] = unicode(limit)
		
		doc = Request(self, 'artist.getSimilar', self.api_key, params).execute()
		
		if not doc:
			return None
		
		names = self._extract_all(doc, 'name')
		
		artists = []
		for name in names:
			artists.append(Artist(name, *self.auth_data))
		
		return artists
	
	def getTags(self):
		"""Returns a list of the user-set tags to this artist. """
		
		params = self._getParams()
		doc = Request(self, 'artist.getTags', self.api_key, params, True, self.secret).execute()
		
		if not doc:
			return None
		
		tag_names = self._extract_all(doc, 'name')
		tags = []
		for tag in tag_names:
			tags.append(Tag(tag, *self.auth_data))
		
		return tags
	
	def getTopAlbums(self):
		"""Returns a list of the top Albums by this artist on Last.fm. """
		
		params = self._getParams()
		doc = Request(self, 'artist.getTopAlbums', self.api_key, params).execute()
		
		if not doc:
			return None
		
		names = self._extract_all(doc, 'name')
		
		albums = []
		for name in names:
			albums.append(Album(self.getName(), name, *self.auth_data))
		
		return albums
	
	def getTopFans(self):
		"""Returns a list of the Users who listened to this artist the most. """
		
		params = self._getParams()
		doc = Request(self, 'artist.getTopFans', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		
		names = self._extract_all(doc, 'name')
		for name in names:
			list.append(User(name, *self.auth_data))
		
		return list
	
	def getTopTags(self):
		"""Returns a list of the most frequently used Tags on this artist. """
		
		params = self._getParams()
		doc = Request(self, 'artist.getTopTags', self.api_key, params).execute()
		
		if not doc:
			return None
		
		names = self._extract_all(doc, 'name')
		tags = []
		for name in names:
			tags.append(Tag(name, *self.auth_data))
		
		return tags
	
	def getTopTracks(self):
		"""Returns a list of the most listened to Tracks by this artist. """
		
		params = self._getParams()
		doc = Request(self, 'artist.getTopTracks', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		
		for track in doc.getElementsByTagName('track'):
			t = {}
			title = self._extract(track, 'name')
			artist = self.getName()
			
			data = {}
			data['play_count'] = self._extract(track, 'playcount')
			data['images'] = self._extract_all(track, 'image')
			
			list.append(Track(artist, title, self.api_key, self.secret, self.session_key, data))
		
		return list
	
	def _removeTag(self, single_tag):
		"""Remove a user's tag from an artist"""
		
		if isinstance(single_tag, Tag):
			single_tag = single_tag.getName()
		
		params = self._getParams()
		params['tag'] = single_tag
		
		Request(self, 'artist.removeTag', self.api_key, params, True, self.secret).execute()

	def removeTags(self, *tags):
		"""Removes one or several tags from this artist. 
		  * *tags: Any number of tag names or Tag objects. 
		"""
		
		for tag in tags:
			self._removeTag(tag)

	def clearTags(self):
		"""Clears all the user-set tags. """
		
		self.removeTags(*(self.getTags()))

	def share(self, users, message = None):
		"""Shares this artist (sends out recommendations). 
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
				nusers.append(user.getName())
			else:
				nusers.append(user)
		
		params = self._getParams()
		recipients = ','.join(nusers)
		params['recipient'] = recipients
		if message: params['message'] = message
		
		Request(self, 'artist.share', self.api_key, params, True, self.secret).execute()
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the artist page on Last.fm. 
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
		
		artist = self._get_url_safe(self.getName())
		
		return url %{'domain': domain_name, 'artist': artist}
	
	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getName()

class Event(BaseObject, Cacheable):
	"""Represents an event"""
	
	def __init__(self, event_id, api_key, secret, session_key):
		BaseObject.__init__(self, api_key, secret, session_key)
		Cacheable.__init__(self)
		
		self._event_id = unicode(event_id)
	
	def _getParams(self):
		return {'sk': self.session_key, 'event': self.getID()}
	
	def attend(self, attending_status):
		"""Sets the attending status.
		  * attending_status: The attending status. Possible values:
            o EVENT_ATTENDING
            o EVENT_MAYBE_ATTENDING
            o EVENT_NOT_ATTENDING 
		"""
		
		params = self._getParams()
		params['status'] = attending_status
		
		doc = Request(self, 'event.attend', self.api_key, params, True, self.secret).execute()
	
	def _getInfo(self):
		"""Get the metadata for an event on Last.fm
		Includes attendance and lineup information"""
		
		params = self._getParams()
		
		doc = Request(self, 'event.getInfo', self.api_key, params).execute()
		
		if not doc:
			return None
		
		data = {}
		data['title'] = self._extract(doc, 'title')
		artists = []
		for i in range(0, len(doc.getElementsByTagName('artist'))):
			artists.append(self._extract(doc, 'artist', i))
		data['artists'] = artists
		data['headliner'] = self._extract(doc, 'headliner')
		
		venue = {}
		venue['name'] = self._extract(doc, 'name')
		venue['city'] = self._extract(doc, 'city')
		venue['country'] = self._extract(doc, 'country')
		venue['street'] = self._extract(doc, 'street')
		venue['postal_code'] = self._extract(doc, 'postalcode')
		
		geo = {}
		geo['lat'] = self._extract(doc, 'geo:lat')
		geo['long'] = self._extract(doc, 'geo:long')
		
		venue['geo'] = geo
		venue['time_zone'] = self._extract(doc, 'timezone')
		
		data['venue'] = venue
		data['description'] = self._extract(doc, 'description')
		data['images'] = self._extract_all(doc, 'image')
		data['attendance'] = self._extract(doc, 'attendance')
		data['reviews'] = self._extract(doc, 'reviews')
		
		
		return data
	
	def getID(self):
		"""Returns the id of the event on Last.fm. """
		return self._event_id
	
	def getTitle(self):
		"""Returns the title of the event. """
		
		return self._getCachedInfo()['title']
	
	def getHeadliner(self):
		"""Returns the headliner of the event. """
		
		return self._getCachedInfo()['headliner']
	
	def getArtists(self):
		"""Returns a list of the participating Artists. """
		
		names = self._getCachedInfo()['artists']
		
		artists = []
		for name in names:
			artists.append(Artist(name, *self.auth_data))
		
		return artists
	
	def getVenueName(self):
		"""Returns the name of the venue where the event is held. """
		
		return self._getCachedInfo()['venue']['name']
	
	def getCityName(self):
		"""Returns the name of the city where the event is held. """
		
		return self._getCachedInfo()['venue']['city']
	
	def getCountryName(self):
		"""Returns the name of the country where the event is held. """
		
		return self._getCachedInfo()['venue']['country']

	def getPostalCode(self):
		"""Returns the postal code of where the event is held. """
		
		return self._getCachedInfo()['venue']['postal_code']

	def getStreetName(self):
		"""Returns the name of the street where the event is held. """
		
		return self._getCachedInfo()['venue']['street']
	
	def getGeoPoint(self):
		"""Returns a tuple of latitude and longitude values of where the event is held. """
		
		i = self._getCachedInfo()
		return (i['venue']['geo']['lat'], i['venue']['geo']['long'])
	
	def getTimeZone(self):
		"""Returns the timezone of where the event is held. """
		
		return self._getCachedInfo()['venue']['time_zone']
	
	def getDescription(self):
		"""Returns the description of the event. """
		
		return self._getCachedInfo()['description']
	
	def getImage(self, size = IMAGE_LARGE):
		"""Returns the associated image URL. 
    	  * size: The image size. Possible values:
            o IMAGE_LARGE
            o IMAGE_MEDIUM
            o IMAGE_SMALL 
		"""
		
		return self._getCachedInfo()['images'][size]
	
	def getAttendanceCount(self):
		"""Returns the number of attending people. """
		
		return self._getCachedInfo()['attendance']
	
	def getReviewCount(self):
		"""Returns the number of available reviews for this event. """
		
		return self._getCachedInfo()['reviews']
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
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
		
		return url %{'domain': domain_name, 'id': self.getID()}

	def toStr(self):
		"""Returns a string representation of the object."""
		
		sa = ""
		artists = self.getArtists()
		for i in range(0, len(artists)):
			if i == 0:
				sa = artists[i].getName()
				continue
			elif i< len(artists)-1:
				sa += ', '
				sa += artists[i].getName()
				continue
			elif i == len(artists) - 1:
				sa += ' and '
				sa += artists[i].getName()
		
		return "%(title)s: %(artists)s at %(place)s" %{'title': self.getTitle(), 'artists': sa, 'place': self.getVenueName()}

class Country(BaseObject):
	
	def __init__(self, country_name, api_key, secret, session_key):
		BaseObject.__init__(self, api_key, secret, session_key)
		
		self._country_name = country_name
	
	def _getParams(self):
		return {'country': self._country_name}
	
	def getName(self):
		"""Returns the country name. """
		
		return self._country_name
	
	def getTopArtists(self):
		"""Returns a tuple of the most popular Artists in the country, ordered by popularity. """
		
		params = self._getParams()
		doc = Request(self, 'geo.getTopArtists', self.api_key, params).execute()
		
		if not doc:
			return None
		
		names = self._extract_all(doc, 'name')
		
		artists = []
		for name in names:
			artists.append(Artist(name, *self.auth_data))
		
		return artists
	
	def getTopTracks(self, location = None):
		"""Returns a tuple of the most popular Tracks in the country, ordered by popularity. 
		  * location: A metro name, to fetch the charts for (must be within the country specified).
		"""
		
		params = self._getParams()
		if location:
			params['location'] = location
			
		doc = Request(self, 'geo.getTopTracks', self.api_key, params).execute()
		
		list = []
		
		for n in doc.getElementsByTagName('track'):
			
			title = self._extract(n, 'name')
			artist = self._extract(n, 'name', 1)
			
			info = {}
			info['play_count'] = self._extract(n, 'playcount')
			info['images'] = self._extract_all(n, 'image')
			
			list.append(Track(artist, title, self.api_key, self.secret, self.session_key, info))
		
		return list
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
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
		
		country_name = self._get_url_safe(self.getName())
		
		return url %{'domain': domain_name, 'country_name': country_name}

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getName()
	
class Group(BaseObject):
	
	def __init__(self, group_name, api_key, secret, session_key):
		BaseObject.__init__(self, api_key, secret, session_key)
		
		self._group_name = group_name
	
	def _getParams(self):
		return {'group': self._group_name}
	
	def getName(self):
		"""Returns the group name. """
		return self._group_name
	
	def getTopWeeklyAlbums(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Albums in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList. 
  		  * from_value: The value marking the beginning of a week.
  		  * to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = unicode(from_value)
			params['to'] = unicode(to_value)
		
		doc = Request(self, 'group.getWeeklyAlbumChart', self.api_key, params).execute()
		
		list = []
		
		for n in doc.getElementsByTagName('album'):
			artist = self._extract(n, 'artist')
			name = self._extract(n, 'name')
			
			list.append(Album(artist, name, *self.auth_data))
		
		return list
	
	def getTopWeeklyArtists(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Artists in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList. 
  		  * from_value: The value marking the beginning of a week.
  		  * to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = unicode(from_value)
			params['to'] = unicode(to_value)
		
		doc = Request(self, 'group.getWeeklyArtistChart', self.api_key, params).execute()
		
		list = []
		
		names = self._extract_all(doc, 'name')
		for name in names:
			list.append(Artist(name, *self.auth_data))
		
		return list

	def getTopWeeklyTracks(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Tracks in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList. 
    	  * from_value: The value marking the beginning of a week.
    	  * to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = from_value
			params['to'] = to_value
		
		doc = Request(self, 'group.getWeeklyTrackChart', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		for track in doc.getElementsByTagName('track'):
			artist = self._extract(track, 'artist')
			title = self._extract(track, 'name')
			
			info = {}
			info['play_count'] = self._extract(track, 'playcount')
			
			list.append(Track(artist, title, self.api_key, self.secret, self.session_key, info))
		
		return list

	def getWeeklyChartList(self):
		"""Returns a list of range pairs to use with the chart methods. """
		
		params = self._getParams()
		doc = Request(self, 'group.getWeeklyChartList', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		for chart in doc.getElementsByTagName('chart'):
			c = {}
			c['from'] = chart.getAttribute('from')
			c['to'] = chart.getAttribute('to')
			
			list.append(c)
		
		return list

	def getURL(self, domain_name = DOMAIN_ENGLISH):
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
		
		name = self._get_url_safe(self.getName())
		
		return url %{'domain': domain_name, 'name': name}

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getName()

class Library(BaseObject):
	"""Represents a user's library."""
	
	def __init__(self, username, api_key, secret, session_key):
		BaseObject.__init__(self, api_key, secret, session_key)
		
		self._username = username
		
		self._albums_playcounts = {}
		self._albums_tagcounts = {}
		self._artists_playcounts = {}
		self._artists_tagcounts = {}
		self._tracks_playcounts = {}
		self._tracks_tagcounts = {}
		
		self._album_pages = None
		self._album_perpage = None
		self._artist_pages = None
		self._artist_perpage = None
		self._track_pages = None
		self._track_perpage = None

	def _getParams(self):
		return {'sk': self.session_key, 'user': self._username}
	
	def getUser(self):
		"""Returns the user who owns this library."""
		
		return User(self._username, *self.auth_data)
	
	def _get_albums_info(self):
		
		params = self._getParams()
		doc = Request(self, 'library.getAlbums', self.api_key, params).execute()
		
		if not doc:
			return None
		
		self._album_pages = int(doc.getElementsByTagName('albums')[0].getAttribute('totalPages'))
		self._album_perpage = int(doc.getElementsByTagName('albums')[0].getAttribute('perPage'))

	def _get_artists_info(self):
		
		params = self._getParams()
		doc = Request(self, 'library.getArtists', self.api_key, params).execute()
		
		if not doc:
			return None
		
		self._artist_pages = int(doc.getElementsByTagName('artists')[0].getAttribute('totalPages'))
		self._artist_perpage = int(doc.getElementsByTagName('artists')[0].getAttribute('perPage'))

	def _get_tracks_info(self):
		
		params = self._getParams()
		doc = Request(self, 'library.getTracks', self.api_key, params).execute()
		
		if not doc:
			return None
		
		self._track_pages = int(doc.getElementsByTagName('tracks')[0].getAttribute('totalPages'))
		self._track_perpage = int(doc.getElementsByTagName('tracks')[0].getAttribute('perPage'))

	def getAlbumsPageCount(self):
		"""Returns the number of pages you'd get when calling getAlbums. """
		
		if self._album_pages:
			return self._album_pages
		
		self._get_albums_info()
		
		return self._album_pages
	
	def getAlbumsPerPage(self):
		"""Returns the number of albums per page you'd get wen calling getAlbums. """
		
		if self._album_perpage:
			return self._album_perpage
		
		self._get_albums_info()
		
		return self._album_perpage

	def getArtistsPageCount(self):
		"""Returns the number of pages you'd get when calling getArtists(). """
		
		if self._artist_pages:
			return self._artist_pages
		
		self._get_artists_info()
		
		return self._artist_pages
	
	def getArtistsPerPage(self):
		"""Returns the number of artists per page you'd get wen calling getArtists(). """
		
		if self._artist_perpage:
			return self._artist_perpage
		
		self._get_artists_info()
		
		return self._artist_perpage

	def getTracksPageCount(self):
		"""Returns the number of pages you'd get when calling getTracks(). """
		
		if self._track_pages:
			return self._track_pages
		
		self._get_tracks_info()
		
		return self._track_pages
	
	def getTracksPerPage(self):
		"""Returns the number of tracks per page you'd get wen calling getTracks. """
		
		if self._track_perpage:
			return self._track_perpage
		
		self._get_tracks_info()
		
		return self._track_perpage
	
	def getAlbums(self, limit = None, page = None):
		"""Returns a paginated list of all the albums in a user's library. 
		    * limit: The number of albums to retrieve.
    		* page: The page to retrieve (default is the first one). 
		"""
		
		params = self._getParams()
		if limit: params['limit'] = str(limit)
		if page: params['page'] = str(page)
		
		doc = Request(self, 'library.getAlbums', self.api_key, params).execute()
		
		if not doc:
			return None
		
		albums = doc.getElementsByTagName('album')
		list = []
		
		for album in albums:
			artist = self._extract(album, 'name', 1)
			name = self._extract(album, 'name')
			
			playcount = self._extract(album, 'playcount')
			tagcount = self._extract(album, 'tagcount')
			
			a = Album(artist, name, *self.auth_data)
			list.append(a)
			
			self._albums_playcounts[a._hash()] = playcount
			self._albums_tagcounts[a._hash()] = tagcount
		
		return list

	def getArtists(self, limit = None, page = None):
		"""Returns a paginated list of all the artists in a user's library. 
		    * limit: The number of artists to retrieve.
    		* page: The page to retrieve (default is the first one). 
		"""
		
		params = self._getParams()
		if limit: params['limit'] = str(limit)
		if page: params['page'] = str(page)
		
		doc = Request(self, 'library.getArtists', self.api_key, params).execute()
		
		if not doc:
			return None
		
		artists = doc.getElementsByTagName('artist')
		list = []
		
		for artist in artists:
			name = self._extract(artist, 'name')
			
			playcount = self._extract(artist, 'playcount')
			tagcount = self._extract(artist, 'tagcount')
			
			a = Artist(name, *self.auth_data)
			list.append(a)
			
			self._artists_playcounts[a._hash()] = playcount
			self._artists_tagcounts[a._hash()] = tagcount
		
		return list

	def getTracks(self, limit = None, page = None):
		"""Returns a paginated list of all the tracks in a user's library. """
		
		params = self._getParams()
		if limit: params['limit'] = str(limit)
		if page: params['page'] = str(page)
		
		doc = Request(self, 'library.getTracks', self.api_key, params).execute()
		
		if not doc:
			return None
		
		tracks = doc.getElementsByTagName('track')
		list = []
		
		for track in tracks:
			
			title = self._extract(track, 'name')
			artist = self._extract(track, 'name', 1)
			
			playcount = self._extract(track, 'playcount')
			tagcount = self._extract(track, 'tagcount')
			
			t = Track(artist, title, *self.auth_data)
			list.append(t)
			
			self._tracks_playcounts[t._hash()] = playcount
			self._tracks_tagcounts[t._hash()] = tagcount
		
		return list
	
	def getAlbumPlaycount(self, album_object):
		"""Goes through the library until it finds the playcount of this album and returns it (could take a relatively long time). 
		  * album_object : The Album to find. 
		"""
		
		key = album_object._hash()
		if key in self._albums_playcounts.keys():
			return self._albums_playcounts[key]
		
		for i in range(1, self.getAlbumsPageCount() +1):
			stack = self.getAlbums(page = i)
			
			for album in stack:
				if album._hash() == album_object._hash():
					return self._albums_playcounts[album._hash()]

	def getAlbumTagcount(self, album_object):
		"""Goes through the library until it finds the tagcount of this album and returns it (could take a relatively long time). 
		  * album_object : The Album to find. 
		"""
		
		key = album_object._hash()
		if key in self._albums_tagcounts.keys():
			return self._albums_tagcounts[key]
		
		for i in range(1, self.getAlbumsPageCount() +1):
			stack = self.getAlbums(page = i)
			
			for album in stack:
				if album._hash() == album_object._hash():
					return self._albums_tagcounts[album._hash()]

	def getArtistPlaycount(self, artist_object):
		"""Goes through the library until it finds the playcount of this artist and returns it (could take a relatively long time). 
		  * artist_object : The Artist to find. 
		"""
		
		key = artist_object._hash()
		if key in self._artists_playcounts.keys():
			return self._artists_playcounts[key]
		
		for i in range(1, self.getArtistsPageCount() +1):
			stack = self.getArtists(page = i)
			
			for artist in stack:
				if artist._hash() == artist_object._hash():
					return self._artists_playcounts[artist._hash()]

	def getArtistTagcount(self, artist_object):
		"""Goes through the library until it finds the tagcount of this artist and returns it (could take a relatively long time). 
		  * artist_object : The Artist to find. 
		"""
		
		key = artist_object._hash()
		if key in self._artists_tagcounts.keys():
			return self._artists_tagcounts[key]
		
		for i in range(1, self.getArtistsPageCount() +1):
			stack = self.getArtist(page = i)
			
			for artist in stack:
				if artist._hash() == artist_object._hash():
					return self._artists_tagcounts[artist._hash()]

	def getTrackPlaycount(self, track_object):
		"""Goes through the library until it finds the playcount of this track and returns it (could take a relatively long time). 
		  * track_object : The Track to find. 
		"""
		
		key = track_object._hash()
		if key in self._tracks_playcounts.keys():
			return self._tracks_playcounts[key]
		
		for i in range(1, self.getTracksPageCount() +1):
			stack = self.getTracks(page = i)
			
			for track in stack:
				if track._hash() == track_object._hash():
					return self._tracks_playcounts[track._hash()]

	def getTrackTagcount(self, track_object):
		"""Goes through the library until it finds the tagcount of this track and returns it (could take a relatively long time). 
		  * track_object : The Track to find. 
		"""
		
		key = track_object._hash()
		if key in self._tracks_tagcounts.keys():
			return self._tracks_tagcounts[key]
		
		for i in range(1, self.getTracksPageCount() +1):
			stack = self.getTracks(page = i)
			
			for track in stack:
				if track._hash() == track_object._hash():
					return self._tracks_tagcounts[track._hash()]

class Playlist(BaseObject):
	
	def __init__(self, playlist_uri, api_key, secret, session_key):
		BaseObject.__init__(self, api_key, secret, session_key)
		
		self._playlist_uri = playlist_uri
	
	def _getParams(self):
		return {'playlistURL': self._playlist_uri}
	
	def getPlaylistURI(self):
		return self._playlist_uri
	
	def fetch(self):
		"""Returns the Last.fm playlist URI. """
		
		params = self._getParams()
		
		doc = Request(self, 'playlist.fetch', self.api_key, params).execute()
		
		if not doc:
			return None
		
		data = {}
		
		data['title'] = self._extract(doc, 'title')
		list = []
		
		for n in doc.getElementsByTagName('track'):
			title = self._extract(n, 'title')
			artist = self._extract(n, 'creator')
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getPlaylistURI()

class Tag(BaseObject):
	
	def __init__(self, tag_name, api_key, secret, session_key):
		BaseObject.__init__(self, api_key, secret, session_key)
		
		self._tag_name = tag_name
	
	def _getParams(self):
		return {'tag': self._tag_name}
	
	def getName(self):
		"""Returns the name of the tag. """
		
		return self._tag_name

	def getSimilar(self):
		"""Returns the tags similar to this one, ordered by similarity. """
		
		params = self._getParams()
		doc = Request(self, 'tag.getSimilar', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		names = self._extract_all(doc, 'name')
		for name in names:
			list.append(Tag(name, *self.auth_data))
		
		return list
	
	def getTopAlbums(self):
		"""Returns a list of the top Albums tagged by this tag, ordered by tag count. """
		
		params = self._getParams()
		doc = Request(self, 'tag.getTopAlbums', self.api_key, params).execute()
		
		list = []
		
		for n in doc.getElementsByTagName('album'):
			name = self._extract(n, 'name')
			artist = self._extract(n, 'name', 1)
			
			list.append(Album(artist, name, *self.auth_data))
		
		return list
	
	def getTopArtists(self):
		"""Returns a list of the top Artists tagged by this tag, ordered by tag count. """
		
		params = self._getParams()
		doc = Request(self, 'tag.getTopArtists', self.api_key, params).execute()
		
		list = []
		
		names = self._extract_all(doc, 'name')
		
		for name in names:
			list.append(Artist(name, *self.auth_data))
		
		return list
	
	def getTopTracks(self):
		"""Returns a list of the top Tracks tagged by this tag, ordered by tag count. """
		
		params = self._getParams()
		doc = Request(self, 'tag.getTopTracks', self.api_key, params).execute()
		
		list = []
		
		for n in doc.getElementsByTagName('track'):
			title = self._extract(n, 'name')
			artist = self._extract(n, 'name', 1)
			
			info = {}
			info['images'] = self._extract_all(n, 'image')
			
			list.append(Track(artist, title, self.api_key, self.secret, self.session_key, info))
		
		return list
	
	def fetchPlaylist(self, free_tracks_only = False):
		"""Returns lit of the tracks tagged by this tag. 
		  * free_tracks_only: Set to True to include only free tracks. 
		"""
		
		uri = 'lastfm://playlist/tag/%s' %self.getName()
		if free_tracks_only:
			uri += '/freetracks'
		
		return Playlist(uri, *self.auth_data).fetch()

	def getURL(self, domain_name = DOMAIN_ENGLISH):
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
		
		name = self._get_url_safe(self.getName())
		
		return url %{'domain': domain_name, 'name': name}

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getName()

class User(BaseObject):
	
	def __init__(self, user_name, api_key, api_secret, session_key):
		BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self._user_name = user_name
	
	def _getParams(self):
		return {'sk': self.session_key, 'user': self._user_name}
	
	def getName(self):
		"""Returns the user name. """
		
		return self._user_name
	
	def getEvents(self):
		"""Returns all the upcoming events for this user. """
		
		params = self._getParams()
		doc = Request(self, 'user.getEvents', self.api_key, params).execute()
		
		if not doc:
			return None
		
		ids = self._extract_all(doc, 'id')
		events = []
		
		for id in ids:
			events.append(Event(id, *self.auth_data))
		
		return events
	
	def getFriends(self, limit = None):
		"""Returns a list of the user's friends. """
		
		params = self._getParams()
		if limit:
			params['limit'] = limit
		
		doc = Request(self, 'user.getFriends', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		users = doc.getElementsByTagName('user')
		
		names = self._extract_all(doc, 'name')
		
		for name in names:
			list.append(User(name, *self.auth_data))
		
		return list
	
	def getLovedTracks(self):
		"""Returns the last 50 tracks loved by this user. """
		
		params = self._getParams()
		doc = Request(self, 'user.getLovedTracks', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		
		for track in doc.getElementsByTagName('track'):
			title = self._extract(track, 'name', 0)
			artist = self._extract(track, 'name', 1)
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list
	
	def getNeighbours(self, limit = None):
		"""Returns a list of the user's friends. 
		  * limit: A limit for how many neighbours to show. 
		"""
		
		params = self._getParams()
		if limit:
			params['limit'] = limit
		
		doc = Request(self, 'user.getNeighbours', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		names = self._extract_all(doc, 'name')
		
		for name in names:
			list.append(User(name, *self.auth_data))
		
		return list
	
	def getPastEvents(self, limit = None):
		"""Retruns the past events of this user. """
		
		params = self._getParams()
		if limit:
			params['limit'] = limit
		
		doc = Request(self, 'user.getPastEvents', self.api_key, params).execute()
		
		if not doc:
			return None
		
		ids = self._extract_all(doc, 'id')
		list = []
		for id in ids:
			list.append(User(id, *self.auth_data))
		
		return list
	
	def getPlaylistIDs(self):
		"""Returns a list the playlists IDs this user has created. """
		
		params = self._getParams()
		doc = Request(self, 'user.getPlaylists', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []		
		for playlist in doc.getElementsByTagName('playlist'):
			p = {}
			p['id'] = self._extract(playlist, 'id')
			p['title'] = self._extract(playlist, 'title')
			p['date'] = self._extract(playlist, 'date')
			p['size'] = self._extract(playlist, 'size')
			
			list.append(p)
		
		return list
	
	def fetchPlaylist(self, playlist_id):
		"""Returns a list of the tracks on a playlist. 
		  * playlist_id: A unique last.fm playlist ID, can be retrieved from getPlaylistIDs(). 
		"""
		
		uri = u'lastfm://playlist/%s' %unicode(playlist_id)
		
		return Playlist(uri, self.api_key).fetch()
	
	def getNowPlaying(self):
		"""Returns the currently playing track, or None if nothing is playing. """
		
		params = self._getParams()
		params['limit'] = '1'
		
		list = []
		
		doc = Request(self, 'user.getRecentTracks', self.api_key, params).execute()
		
		if not doc:
			return None
		
		e = doc.getElementsByTagName('track')[0]
		
		if not e.hasAttribute('nowplaying'):
			return None
		
		artist = self._extract(e, 'artist')
		title = self._extract(e, 'name')
		
		return Track(artist, title, *self.auth_data)


	def getRecentTracks(self, limit = None):
		"""Returns this user's recent listened-to tracks. """
		
		params = self._getParams()
		if limit:
			params['limit'] = unicode(limit)
		
		list = []
		
		doc = Request(self, 'user.getRecentTracks', self.api_key, params).execute()
		
		if not doc:
			return None
		
		for track in doc.getElementsByTagName('track'):
			title = self._extract(track, 'name')
			artist = self._extract(track, 'artist')
			
			if track.hasAttribute('nowplaying'):
				continue	#to prevent the now playing track from sneaking in here
				
			list.append(Track(artist, title, *self.auth_data))
		
		return list
	
	def getTopAlbums(self, period = PERIOD_OVERALL):
		"""Returns the top albums listened to by a user. 
		  * period: The period of time. Possible values:
            o PERIOD_OVERALL
            o PERIOD_3MONTHS
            o PERIOD_6MONTHS
            o PERIOD_12MONTHS 
		"""
		
		params = self._getParams()
		params['period'] = period
		
		doc = Request(self, 'user.getTopAlbums', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		for album in doc.getElementsByTagName('album'):
			name = self._extract(album, 'name')
			artist = self._extract(album, 'name', 1)
			
			list.append(Album(artist, name, *self.auth_data))
		
		return list
	
	def getTopArtists(self, period = PERIOD_OVERALL):
		"""Returns the top artists listened to by a user. 
		  * period: The period of time. Possible values:
            o PERIOD_OVERALL
            o PERIOD_3MONTHS
            o PERIOD_6MONTHS
            o PERIOD_12MONTHS 
		"""
		
		params = self._getParams()
		params['period'] = period
		
		doc = Request(self, 'user.getTopArtists', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		
		names = self._extract_all(doc, 'name')
		for name in names:
			list.append(Artist(name, *self.auth_data))
		
		return list
		
	def getTopTags(self, limit = None):
		"""Returns the top tags used by this user. 
		  * limit: The limit of how many tags to return. 
		"""
		
		params = self._getParams()
		if limit:
			params['limit'] = limit
		
		doc = Request(self, 'user.getTopTags', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		names = self._extract_all(doc, 'name')
		
		for name in names:
			list.append(Tag(name, *self.auth_data))
		
		return list
	
	def getTopTracks(self, period = PERIOD_OVERALL):
		"""Returns the top tracks listened to by a user. 
            o PERIOD_OVERALL
            o PERIOD_3MONTHS
            o PERIOD_6MONTHS
            o PERIOD_12MONTHS 
		"""
		
		params = self._getParams()
		params['period'] = period
		
		doc = Request(self, 'user.getTopTracks', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		for track in doc.getElementsByTagName('track'):
			title = self._extract(track, 'name')
			artist = self._extract(track, 'name', 1)
			
			info = {}
			info['play_count'] = self._extract(track, 'playcount')
			info['images'] = self._extract_all(track, 'image')
		
			list.append(Track(artist, title, self.api_key, self.secret, self.session_key, info))
		
		return list
	
	def getTopWeeklyAlbums(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Albums in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList(). 
		  * from_value: The value marking the beginning of a week.
    	  * to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = from_value
			params['to'] = to_value
		
		doc = Request(self, 'user.getWeeklyAlbumChart', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		
		for n in doc.getElementsByTagName('album'):
			artist = self._extract(n, 'artist')
			name = self._extract(n, 'name')
			
			list.append(Album(artist, name, *self.auth_data))
		
		return list
	
	def getTopWeeklyArtists(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Artists in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList(). 
		  * from_value: The value marking the beginning of a week.
    	  * to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = from_value
			params['to'] = to_value
		
		doc = Request(self, 'user.getWeeklyArtistChart', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		
		names = self._extract_all(doc, 'name')
		for name in names:
			list.append(Artist(name, *self.auth_data))
		
		return list
	
	def getTopWeeklyTracks(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Tracks in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList(). 
		  * from_value: The value marking the beginning of a week.
    	  * to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = from_value
			params['to'] = to_value
		
		doc = Request(self, 'user.getWeeklyTrackChart', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		for track in doc.getElementsByTagName('track'):
			artist = self._extract(track, 'artist')
			title = self._extract(track, 'name')
			
			info = {}
			info['play_count'] = self._extract(track, 'playcount')
			
			list.append(Track(artist, title, self.api_key, self.secret, self.session_key, info))
		
		return list
	
	def getWeeklyChartList(self):
		"""Returns a list of range pairs to use with the chart methods."""
		
		params = self._getParams()
		doc = Request(self, 'user.getWeeklyChartList', self.api_key, params).execute()
		
		if not doc:
			return None
		
		list = []
		for chart in doc.getElementsByTagName('chart'):
			c = {}
			c['from'] = chart.getAttribute('from')
			c['to'] = chart.getAttribute('to')
			
			list.append(c)
		
		return list

	def getURL(self, domain_name = DOMAIN_ENGLISH):
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
		
		name = self._get_url_safe(self.getName())
		
		return url %{'domain': domain_name, 'name': name}

	def getLibrary(self):
		"""Returns the associated Library object. """
		
		return Library(self.getName(), *self.auth_data)

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getName()

class Search(BaseObject):
	"""An abstract search class. Use one of its derivatives."""
	
	def __init__(self, api_key, api_secret, session_key):
		BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self._limit = None
		self._page = None
		self._total_result_count = None

	def getLimit(self):
		"""Returns the limit of the search."""
		
		return self._limit
	
	def getPage(self):
		"""Returns the last page retrieved."""
		
		return self._page
	
	def getTotalResultCount(self):
		"""Returns the total count of all the results."""
		
		return self._total_result_count
	
	def getResults(self, limit = 30, page = 1):
		pass
	
	def getFirstMatch(self):
		"""Returns the first match."""
		
		matches = self.getResults(1)
		if matches:
			return matches[0]

class ArtistSearch(Search):
	"""Search for an artist by artist name."""
	
	def __init__(self, artist_name, api_key, api_secret, session_key):
		Search.__init__(self, api_key, api_secret, session_key)
		
		self._artist_name = artist_name

	def _getParams(self):
		return {'sk': self.session_key, 'artist': self.getArtistName()}
		
	def getArtistName(self):
		"""Returns the artist name."""
		
		return self._artist_name

	def getResults(self, limit = 30, page = 1):
		"""Returns the matches sorted by relevance.
		  * limit: Limit the number of artists returned at one time. Default (maximum) is 30.
		  * page: Scan into the results by specifying a page number. Defaults to first page.
		"""
		
		params = self._getParams()
		params['limit'] = unicode(limit)
		params['page'] = unicode(page)
		
		doc = Request(self, 'artist.search', self.api_key, params).execute()
		
		if not doc:
			return None
		
		self._total_result_count = self._extract(doc, 'opensearch:totalResults')
		self._page = page
		self._limit = limit
		
		e = doc.getElementsByTagName('artistmatches')[0]
		
		names = self._extract_all(e, 'name')
		
		list = []
		for name in names:
			list.append(Artist(name, *self.auth_data))
		
		return list

class TagSearch(Search):
	"""Search for a tag by tag name."""
	
	def __init__(self, tag_name, api_key, api_secret, session_key):
		Search.__init__(self, api_key, api_secret, session_key)
		
		self._tag_name = tag_name

	def _getParams(self):
		return {'sk': self.session_key, 'tag': self.getTagName()}
		
	def getTagName(self):
		"""Returns the tag name."""
		
		return self._tag_name

	def getResults(self, limit = 30, page = 1):
		"""Returns the matches sorted by relevance.
		  * limit: Limit the number of artists returned at one time. Default (maximum) is 30.
		  * page: Scan into the results by specifying a page number. Defaults to first page.
		"""
		
		params = self._getParams()
		params['limit'] = unicode(limit)
		params['page'] = unicode(page)
		
		doc = Request(self, 'tag.search', self.api_key, params).execute()
		
		if not doc:
			return None
		
		self._total_result_count = self._extract(doc, 'opensearch:totalResults')
		self._page = page
		self._limit = limit
		
		e = doc.getElementsByTagName('tagmatches')[0]
		
		names = self._extract_all(e, 'name')
		
		list = []
		for name in names:
			list.append(Tag(name, *self.auth_data))
		
		return list

class TrackSearch(Search):
	"""Search for a track by track title. If you don't wanna narrow the results down
	by specifying the artist name, set it to None"""
	
	def __init__(self, track_title, artist_name, api_key, api_secret, session_key):
		Search.__init__(self, api_key, api_secret, session_key)
		
		self._track_title = track_title
		self._artist_name = artist_name

	def _getParams(self):
		params = {'sk': self.session_key, 'track': self.getTrackTitle()}
		if self.getTrackArtistName():
			params['artist'] = self.getTrackArtistName()
		
		return params
		
	def getTrackTitle(self):
		"""Returns the track title."""
		
		return self._track_title
	
	def getTrackArtistName(self):
		"""Returns the artist name."""
		
		return self._artist_name

	def getResults(self, limit = 30, page = 1):
		"""Returns the matches sorted by relevance.
		  * limit: Limit the number of artists returned at one time. Default (maximum) is 30.
		  * page: Scan into the results by specifying a page number. Defaults to first page.
		"""
		
		params = self._getParams()
		params['limit'] = unicode(limit)
		params['page'] = unicode(page)
		
		doc = Request(self, 'track.search', self.api_key, params).execute()
		
		if not doc:
			return None
		
		self._total_result_count = self._extract(doc, 'opensearch:totalResults')
		self._page = page
		self._limit = limit
		
		e = doc.getElementsByTagName('trackmatches')[0]
		
		titles = self._extract_all(e, 'name')
		artists = self._extract_all(e, 'artist')
		
		list = []
		for i in range(0, len(titles)):
			list.append(Track(artists[i], titles[i], *self.auth_data))
		
		return list
