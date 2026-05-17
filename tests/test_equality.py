from __future__ import annotations

import pylast


def _network() -> pylast.LastFMNetwork:
    return pylast.LastFMNetwork(api_key="key", api_secret="secret")


def test_country_equality_with_none_returns_false() -> None:
    country = pylast.Country("Italy", _network())
    assert (country == None) is False  # noqa: E711
    assert (country != None) is True  # noqa: E711


def test_country_equality_with_string_returns_false() -> None:
    country = pylast.Country("Italy", _network())
    assert (country == "Italy") is False
    assert (country != "Italy") is True


def test_country_in_list_with_strings_does_not_raise() -> None:
    network = _network()
    countries = [pylast.Country("Italy", network), pylast.Country("Finland", network)]
    assert "Italy" not in countries


def test_country_equality_is_case_insensitive() -> None:
    network = _network()
    assert pylast.Country("Italy", network) == pylast.Country("italy", network)
    assert pylast.Country("Italy", network) != pylast.Country("Finland", network)


def test_tag_equality_with_none_returns_false() -> None:
    tag = pylast.Tag("rock", _network())
    assert (tag == None) is False  # noqa: E711
    assert (tag != None) is True  # noqa: E711


def test_tag_equality_with_string_returns_false() -> None:
    tag = pylast.Tag("rock", _network())
    assert (tag == "rock") is False
    assert (tag != "rock") is True


def test_tag_in_list_with_strings_does_not_raise() -> None:
    network = _network()
    tags = [pylast.Tag("rock", network), pylast.Tag("jazz", network)]
    assert "blues" not in tags


def test_tag_equality_is_case_insensitive() -> None:
    network = _network()
    assert pylast.Tag("Rock", network) == pylast.Tag("rock", network)
    assert pylast.Tag("rock", network) != pylast.Tag("jazz", network)
