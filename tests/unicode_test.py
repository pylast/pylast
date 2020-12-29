from unittest import mock

import pytest

import pylast


def mock_network():
    return mock.Mock(_get_ws_auth=mock.Mock(return_value=("", "", "")))


@pytest.mark.parametrize(
    "artist",
    [
        "\xe9lafdasfdsafdsa",
        "ééééééé",
        pylast.Artist("B\xe9l", mock_network()),
        "fdasfdsafsaf not unicode",
    ],
)
def test_get_cache_key(artist):
    request = pylast._Request(mock_network(), "some_method", params={"artist": artist})
    request._get_cache_key()


@pytest.mark.parametrize("obj", [pylast.Artist("B\xe9l", mock_network())])
def test_cast_and_hash(obj):
    assert type(str(obj)) is str
    assert isinstance(hash(obj), int)
