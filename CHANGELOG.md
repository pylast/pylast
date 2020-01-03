# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2020-01-03
### Added

* Support for Python 3.8
* Store album art URLs when you call `GetTopAlbums` ([#307])
* Retry paging through results on exception ([#297])
* More error status codes from https://last.fm/api/errorcodes ([#297])

### Changed

* Respect `get_recent_tracks`' limit when there's a now playing track ([#310])
* Move installable code to `src/` ([#301])
* Update `get_weekly_artist_charts` docstring: only for `User` ([#311])
* Remove Python 2 warnings, `python_requires` should be enough ([#312])
* Use setuptools_scm to simplify versioning during release ([#316])
* Various lint and test updates

### Deprecated

* Last.fm's `user.getArtistTracks` has now been deprecated by Last.fm and is no longer
  available. Last.fm returns a "Deprecated - This type of request is no longer
  supported" error when calling it. A future version of pylast will remove its
  `User.get_artist_tracks` altogether. ([#305])

* `STATUS_TOKEN_ERROR` is deprecated and will be removed in a future version.
  Use `STATUS_OPERATION_FAILED` instead.

## [3.1.0] - 2019-03-07
### Added

* Extract username from session via new
  `SessionKeyGenerator.get_web_auth_session_key_username` ([#290])
* `User.get_track_scrobbles` ([#298])

### Deprecated

*  `User.get_artist_tracks`. Use `User.get_track_scrobbles` as a partial replacement.
   ([#298])

## [3.0.0] - 2019-01-01
### Added
* This changelog file ([#273])

### Removed

* Support for Python 2.7 ([#265])

* Constants `COVER_SMALL`, `COVER_MEDIUM`, `COVER_LARGE`, `COVER_EXTRA_LARGE`
  and `COVER_MEGA`. Use `SIZE_SMALL` etc. instead. ([#282])

## [2.4.0] - 2018-08-08
### Deprecated

* Support for Python 2.7 ([#265])

[Unreleased]: https://github.com/pylast/pylast/compare/v3.2.0...HEAD
[3.2.0]: https://github.com/pylast/pylast/compare/v3.1.0...3.2.0
[3.1.0]: https://github.com/pylast/pylast/compare/v3.0.0...3.1.0
[3.0.0]: https://github.com/pylast/pylast/compare/2.4.0...3.0.0
[2.4.0]: https://github.com/pylast/pylast/compare/2.3.0...2.4.0
[#265]: https://github.com/pylast/pylast/issues/265
[#273]: https://github.com/pylast/pylast/issues/273
[#282]: https://github.com/pylast/pylast/pull/282
[#290]: https://github.com/pylast/pylast/pull/290
[#297]: https://github.com/pylast/pylast/issues/297
[#298]: https://github.com/pylast/pylast/issues/298
[#301]: https://github.com/pylast/pylast/issues/301
[#305]: https://github.com/pylast/pylast/issues/305
[#307]: https://github.com/pylast/pylast/issues/307
[#310]: https://github.com/pylast/pylast/issues/310
[#311]: https://github.com/pylast/pylast/issues/311
[#312]: https://github.com/pylast/pylast/issues/312
[#316]: https://github.com/pylast/pylast/issues/316
