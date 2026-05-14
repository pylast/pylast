from __future__ import annotations

from unittest.mock import patch
from xml.dom import minidom
from xml.sax.saxutils import escape

import pylast


def _album_info_doc(tracks: list[tuple[str, str]]) -> minidom.Document:
    track_xml = "".join(
        f"<track><name>{escape(title)}</name>"
        f"<artist><name>{escape(artist)}</name></artist></track>"
        for title, artist in tracks
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<lfm status="ok"><album>'
        "<name>Some Album</name>"
        f"<tracks>{track_xml}</tracks>"
        "</album></lfm>"
    )
    return minidom.parseString(xml)


def _make_album(
    artist: str = "Yui Hirasawa", title: str = "Ho-kago Tea Time"
) -> pylast.Album:
    network = pylast.LastFMNetwork(api_key="key", api_secret="secret")
    return pylast.Album(artist, title, network)


def test_returns_single_artist_when_all_tracks_agree() -> None:
    album = _make_album()
    doc = _album_info_doc(
        [
            ("Cagayake! GIRLS", "Houkago Tea Time"),
            ("Fuwa Fuwa Time", "Houkago Tea Time"),
            ("Don't say 'lazy'", "Houkago Tea Time"),
        ]
    )
    with patch.object(pylast._Request, "execute", return_value=doc):
        assert album.get_album_artist_from_tracks() == "Houkago Tea Time"


def test_returns_various_artists_for_multi_artist_compilation() -> None:
    album = _make_album(title="K-ON! Character Song Collection")
    doc = _album_info_doc(
        [
            ("Pure Pure Heart", "Aki Toyosaki"),
            ("Heart Goes Boom!!", "Yoko Hikasa"),
            ("Diary wa Fortissimo", "Satomi Sato"),
            ("Honey Sweet Tea Time", "Minako Kotobuki"),
            ("Singing!", "Ayana Taketatsu"),
        ]
    )
    with patch.object(pylast._Request, "execute", return_value=doc):
        assert album.get_album_artist_from_tracks() == "Various Artists"


def test_returns_none_for_stub_entry_with_no_tracks() -> None:
    album = _make_album()
    doc = _album_info_doc([])
    with patch.object(pylast._Request, "execute", return_value=doc):
        assert album.get_album_artist_from_tracks() is None


def test_find_compilation_variant_returns_album_when_variant_has_tracks() -> None:
    album = _make_album(title="K-ON! Character Song Collection")
    doc = _album_info_doc(
        [
            ("Pure Pure Heart", "Aki Toyosaki"),
            ("Heart Goes Boom!!", "Yoko Hikasa"),
        ]
    )
    with patch.object(pylast._Request, "execute", return_value=doc):
        variant = album.find_compilation_variant()
    assert variant is not None
    assert variant.get_artist().get_name() == "Various Artists"


def test_find_compilation_variant_returns_none_for_stub_variant() -> None:
    album = _make_album()
    doc = _album_info_doc([])
    with patch.object(pylast._Request, "execute", return_value=doc):
        assert album.find_compilation_variant() is None
