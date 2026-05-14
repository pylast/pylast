from __future__ import annotations

from unittest.mock import patch
from xml.dom import minidom

import pylast


def _fake_user_getinfo_doc(name: str) -> minidom.Document:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<lfm status="ok"><user><name>{name}</name></user></lfm>'
    )
    return minidom.parseString(xml)


def test_authenticated_user_get_name_resolves_via_api_when_username_missing() -> None:
    # Regression test for #300: with a session-key-only network (the typical
    # web-auth flow), AuthenticatedUser used to return an empty name because
    # network.username was never populated.
    network = pylast.LastFMNetwork(
        api_key="key", api_secret="secret", session_key="session"
    )

    user = network.get_authenticated_user()
    assert user.name == ""

    with patch.object(
        pylast._Request, "execute", return_value=_fake_user_getinfo_doc("Alice")
    ) as execute:
        assert user.get_name() == "Alice"
        assert execute.call_count == 1

    assert user.name == "Alice"
    assert user.get_name() == "Alice"


def test_authenticated_user_get_name_uses_existing_name_when_set() -> None:
    network = pylast.LastFMNetwork(
        api_key="key",
        api_secret="secret",
        session_key="session",
        username="Bob",
    )

    user = network.get_authenticated_user()

    with patch.object(pylast._Request, "execute") as execute:
        assert user.get_name() == "Bob"
        execute.assert_not_called()
