from __future__ import annotations

import pytest

import pylast


def _network() -> pylast.LastFMNetwork:
    return pylast.LastFMNetwork(api_key="key", api_secret="secret")


THINGS = [
    pytest.param(pylast.Country, "Italy", "Finland", id="country"),
    pytest.param(pylast.Tag, "rock", "jazz", id="tag"),
]


@pytest.mark.parametrize("cls, name, other_name", THINGS)
@pytest.mark.parametrize("other", [None, "Italy"])
def test_equality_with_non_matching_type_returns_false(
    cls, name, other_name, other
) -> None:
    obj = cls(name, _network())
    assert (obj == other) is False
    assert (obj != other) is True


@pytest.mark.parametrize("cls, name, other_name", THINGS)
def test_in_list_does_not_raise_on_string_comparison(cls, name, other_name) -> None:
    network = _network()
    things = [cls(name, network), cls(other_name, network)]
    assert "blues" not in things


@pytest.mark.parametrize("cls, name, other_name", THINGS)
def test_equality_is_case_insensitive(cls, name, other_name) -> None:
    network = _network()
    assert cls(name, network) == cls(name.lower(), network)
    assert cls(name, network) != cls(other_name, network)
