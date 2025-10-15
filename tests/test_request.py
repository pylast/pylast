from __future__ import annotations

import pytest

import pylast


@pytest.mark.parametrize(
    ("given, expected"),
    [(True, "1"), (False, "0"), (1, "1"), (0, "0"), ("foo", "foo"), ("1", "1")],
)
def test_param_conversion(given: bool | int | str, expected: str) -> None:
    assert pylast._Request._convert_param(given) == expected
