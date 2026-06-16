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


def test_cacheable_request_with_username_param_hits_cache_on_second_call() -> None:
    network = pylast.LastFMNetwork(api_key="k", api_secret="s")
    network.enable_caching()
    album = pylast.Album("Beatles", "Abbey Road", network, username="alice")

    with patch("httpx2.Client.post", return_value=_fake_response()) as post:
        album.get_userplaycount()
        album.get_userplaycount()
        album.get_userplaycount()

    assert post.call_count == 1
