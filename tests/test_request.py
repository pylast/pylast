from __future__ import annotations

from unittest.mock import patch

import pytest

import pylast


@pytest.mark.parametrize(
    ("given, expected"),
    [(True, "1"), (False, "0"), (1, "1"), (0, "0"), ("foo", "foo"), ("1", "1")],
)
def test_param_conversion(given: bool | int | str, expected: str) -> None:
    assert pylast._Request._convert_param(given) == expected


def _fake_post_factory(call_counter: list[int]) -> object:
    body = (
        b'<?xml version="1.0"?>'
        b'<lfm status="ok"><album><userplaycount>1</userplaycount></album></lfm>'
    )

    def fake_post(*args, **kwargs):
        call_counter.append(1)

        class _Response:
            status_code = 200

            def read(self) -> bytes:
                return body

        return _Response()

    return fake_post


def test_download_response_does_not_mutate_params() -> None:
    network = pylast.LastFMNetwork(api_key="k", api_secret="s")
    request = pylast._Request(
        network, "album.getInfo", {"artist": "A", "album": "B", "username": "alice"}
    )
    original = dict(request.params)

    calls: list[int] = []
    with patch("httpx.Client.post", side_effect=_fake_post_factory(calls)):
        request._download_response()

    assert request.params == original
    assert "username" in request.params


def test_cacheable_request_with_username_param_hits_cache_on_second_call() -> None:
    network = pylast.LastFMNetwork(api_key="k", api_secret="s")
    network.enable_caching()
    album = pylast.Album("Beatles", "Abbey Road", network, username="alice")

    calls: list[int] = []
    with patch("httpx.Client.post", side_effect=_fake_post_factory(calls)):
        album.get_userplaycount()
        album.get_userplaycount()
        album.get_userplaycount()

    assert len(calls) == 1
