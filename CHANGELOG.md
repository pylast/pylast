# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### TODO

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

[Unreleased]: https://github.com/pylast/pylast/compare/v3.1.0...HEAD
[3.1.0]: https://github.com/pylast/pylast/compare/v3.0.0...3.1.0
[3.0.0]: https://github.com/pylast/pylast/compare/2.4.0...3.0.0
[2.4.0]: https://github.com/pylast/pylast/compare/2.3.0...2.4.0
[#298]: https://github.com/pylast/pylast/issues/298
[#290]: https://github.com/pylast/pylast/pull/290
[#265]: https://github.com/pylast/pylast/issues/265
[#273]: https://github.com/pylast/pylast/issues/273
[#282]: https://github.com/pylast/pylast/pull/282
