from __future__ import annotations

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
def test_get_cache_key(artist) -> None:
    request = pylast._Request(mock_network(), "some_method", params={"artist": artist})
    request._get_cache_key()


@pytest.mark.parametrize("obj", [pylast.Artist("B\xe9l", mock_network())])
def test_cast_and_hash(obj) -> None:
    assert isinstance(str(obj), str)
    assert isinstance(hash(obj), int)


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (
            # Plain text
            '<album mbid="">test album name</album>',
            '<album mbid="">test album name</album>',
        ),
        (
            # Contains Unicode ENQ Enquiry control character
            '<album mbid="">test album \u0005name</album>',
            '<album mbid="">test album name</album>',
        ),
    ],
)
def test__remove_invalid_xml_chars(test_input: str, expected: str) -> None:
    assert pylast._remove_invalid_xml_chars(test_input) == expected


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (
            # Plain text
            '<album mbid="">test album name</album>',
            '<?xml version="1.0" ?><album mbid="">test album name</album>',
        ),
        (
            # Contains Unicode ENQ Enquiry control character
            '<album mbid="">test album \u0005name</album>',
            '<?xml version="1.0" ?><album mbid="">test album name</album>',
        ),
    ],
)
def test__parse_response(test_input: str, expected: str) -> None:
    doc = pylast._parse_response(test_input)
    assert doc.toxml() == expected
