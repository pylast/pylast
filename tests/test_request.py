from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

import pylast


@pytest.mark.parametrize(
    ("given, expected"),
    [(True, "1"), (False, "0"), (1, "1"), (0, "0"), ("foo", "foo"), ("1", "1")],
)
def test_param_conversion(given: bool | int | str, expected: str) -> None:
    assert pylast._Request._convert_param(given) == expected


FAKE_BODY = (
    b'<?xml version="1.0"?>'
    b'<lfm status="ok"><album><userplaycount>1</userplaycount></album></lfm>'
)


def _fake_response() -> Mock:
    return Mock(status_code=200, read=Mock(return_value=FAKE_BODY))


def test_download_response_does_not_mutate_params() -> None:
    network = pylast.LastFMNetwork(api_key="k", api_secret="s")
    request = pylast._Request(
        network, "album.getInfo", {"artist": "A", "album": "B", "username": "alice"}
    )
    original = dict(request.params)

    with patch("httpx2.Client.post", return_value=_fake_response()):
        request._download_response()

    assert request.params == original
    assert "username" in request.params


RECENT_TRACKS_BODY = (
    b'<?xml version="1.0"?>'
    b'<lfm status="ok">'
    b'<recenttracks user="alice" page="1" perPage="2" totalPages="1" total="1">'
    b'<track><artist mbid="">Artist</artist><name>Song</name>'
    b'<album mbid="">Album</album><date uts="1700000000">16 Nov 2023</date>'
    b"</track></recenttracks></lfm>"
)

LOGIN_REQUIRED_BODY = (
    b'<?xml version="1.0"?>'
    b'<lfm status="failed">'
    b'<error code="17">Login: User required to be logged in</error></lfm>'
)


def test_collect_nodes_raises_wserror_without_retrying() -> None:
    # Arrange
    network = pylast.LastFMNetwork(api_key="k", api_secret="s")
    user = network.get_user("alice")
    response = Mock(status_code=200, read=Mock(return_value=LOGIN_REQUIRED_BODY))

    # Act
    with (
        patch("httpx2.Client.post", return_value=response) as post,
        patch("pylast.time.sleep") as sleep,
        pytest.raises(pylast.WSError) as excinfo,
    ):
        user.get_recent_tracks(limit=1)

    # Assert
    assert excinfo.value.get_id() == "17"
    assert post.call_count == 1
    assert sleep.call_count == 0


def test_collect_nodes_retries_transient_errors() -> None:
    # Arrange
    network = pylast.LastFMNetwork(api_key="k", api_secret="s")
    user = network.get_user("alice")
    unavailable = Mock(status_code=503)
    ok = Mock(status_code=200, read=Mock(return_value=RECENT_TRACKS_BODY))

    # Act
    with (
        patch("httpx2.Client.post", side_effect=[unavailable, unavailable, ok]) as post,
        patch("pylast.time.sleep") as sleep,
    ):
        tracks = user.get_recent_tracks(limit=1)

    # Assert
    assert len(tracks) == 1
    assert tracks[0].track.title == "Song"
    assert post.call_count == 3
    assert sleep.call_count == 2


def test_collect_nodes_preserves_error_type_when_retries_exhausted() -> None:
    # Arrange
    network = pylast.LastFMNetwork(api_key="k", api_secret="s")
    user = network.get_user("alice")
    unavailable = Mock(status_code=503)

    # Act
    with (
        patch("httpx2.Client.post", return_value=unavailable) as post,
        patch("pylast.time.sleep"),
        pytest.raises(pylast.WSError) as excinfo,
    ):
        user.get_recent_tracks(limit=1)

    # Assert
    assert excinfo.value.get_id() == 503
    assert post.call_count == 3


def test_cacheable_request_with_username_param_hits_cache_on_second_call() -> None:
    network = pylast.LastFMNetwork(api_key="k", api_secret="s")
    network.enable_caching()
    album = pylast.Album("Beatles", "Abbey Road", network, username="alice")

    with patch("httpx2.Client.post", return_value=_fake_response()) as post:
        album.get_userplaycount()
        album.get_userplaycount()
        album.get_userplaycount()

    assert post.call_count == 1
