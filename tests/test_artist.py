#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
from __future__ import annotations

import pytest

import pylast

from .test_pylast import WRITE_TEST, TestPyLastWithLastFm


class TestPyLastArtist(TestPyLastWithLastFm):
    def test_repr(self) -> None:
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        representation = repr(artist)

        # Assert
        assert representation.startswith("pylast.Artist('Test Artist',")

    def test_artist_is_hashable(self) -> None:
        # Arrange
        test_artist = self.network.get_artist("Radiohead")
        artist = test_artist.get_similar(limit=2)[0].item
        assert isinstance(artist, pylast.Artist)

        # Act/Assert
        self.helper_is_thing_hashable(artist)

    def test_bio_published_date(self) -> None:
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        bio = artist.get_bio_published_date()

        # Assert
        assert bio is not None
        assert len(bio) >= 1

    def test_bio_content(self) -> None:
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        bio = artist.get_bio_content(language="en")

        # Assert
        assert bio is not None
        assert len(bio) >= 1

    def test_bio_content_none(self) -> None:
        # Arrange
        # An artist with no biography, with "<content/>" in the API XML
        artist = pylast.Artist("Mr Sizef + Unquote", self.network)

        # Act
        bio = artist.get_bio_content()

        # Assert
        assert bio is None

    def test_bio_summary(self) -> None:
        # Arrange
        artist = pylast.Artist("Test Artist", self.network)

        # Act
        bio = artist.get_bio_summary(language="en")

        # Assert
        assert bio is not None
        assert len(bio) >= 1

    def test_artist_top_tracks(self) -> None:
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_tracks(limit=2)

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Track)

    def test_artist_top_albums(self) -> None:
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = list(artist.get_top_albums(limit=2))

        # Assert
        self.helper_two_different_things_in_top_list(things, pylast.Album)

    @pytest.mark.parametrize("test_limit", [1, 50, 100])
    def test_artist_top_albums_limit(self, test_limit: int) -> None:
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_albums(limit=test_limit)

        # Assert
        assert len(things) == test_limit

    def test_artist_top_albums_limit_default(self) -> None:
        # Arrange
        # Pick an artist with plenty of plays
        artist = self.network.get_top_artists(limit=1)[0].item

        # Act
        things = artist.get_top_albums()

        # Assert
        assert len(things) == 50

    def test_artist_listener_count(self) -> None:
        # Arrange
        artist = self.network.get_artist("Test Artist")

        # Act
        count = artist.get_listener_count()

        # Assert
        assert isinstance(count, int)
        assert count > 0

    @pytest.mark.skipif(not WRITE_TEST, reason="Only test once to avoid collisions")
    def test_tag_artist(self) -> None:
        # Arrange
        artist = self.network.get_artist("Test Artist")
        # artist.clear_tags()

        # Act
        artist.add_tag("testing")

        # Assert
        tags = artist.get_tags()
        assert len(tags) > 0
        found = any(tag.name == "testing" for tag in tags)
        assert found

    @pytest.mark.skipif(not WRITE_TEST, reason="Only test once to avoid collisions")
    def test_remove_tag_of_type_text(self) -> None:
        # Arrange
        tag = "testing"  # text
        artist = self.network.get_artist("Test Artist")
        artist.add_tag(tag)

        # Act
        artist.remove_tag(tag)

        # Assert
        tags = artist.get_tags()
        found = any(tag.name == "testing" for tag in tags)
        assert not found

    @pytest.mark.skipif(not WRITE_TEST, reason="Only test once to avoid collisions")
    def test_remove_tag_of_type_tag(self) -> None:
        # Arrange
        tag = pylast.Tag("testing", self.network)  # Tag
        artist = self.network.get_artist("Test Artist")
        artist.add_tag(tag)

        # Act
        artist.remove_tag(tag)

        # Assert
        tags = artist.get_tags()
        found = any(tag.name == "testing" for tag in tags)
        assert not found

    @pytest.mark.skipif(not WRITE_TEST, reason="Only test once to avoid collisions")
    def test_remove_tags(self) -> None:
        # Arrange
        tags = ["removetag1", "removetag2"]
        artist = self.network.get_artist("Test Artist")
        artist.add_tags(tags)
        artist.add_tags("1more")
        tags_before = artist.get_tags()

        # Act
        artist.remove_tags(tags)

        # Assert
        tags_after = artist.get_tags()
        assert len(tags_after) == len(tags_before) - 2
        found1 = any(tag.name == "removetag1" for tag in tags_after)
        found2 = any(tag.name == "removetag2" for tag in tags_after)
        assert not found1
        assert not found2

    @pytest.mark.skipif(not WRITE_TEST, reason="Only test once to avoid collisions")
    def test_set_tags(self) -> None:
        # Arrange
        tags = ["sometag1", "sometag2"]
        artist = self.network.get_artist("Test Artist 2")
        artist.add_tags(tags)
        tags_before = artist.get_tags()
        new_tags = ["settag1", "settag2"]

        # Act
        artist.set_tags(new_tags)

        # Assert
        tags_after = artist.get_tags()
        assert tags_before != tags_after
        assert len(tags_after) == 2
        found1, found2 = False, False
        for tag in tags_after:
            if tag.name == "settag1":
                found1 = True
            elif tag.name == "settag2":
                found2 = True
        assert found1
        assert found2

    def test_artists(self) -> None:
        # Arrange
        artist1 = self.network.get_artist("Radiohead")
        artist2 = self.network.get_artist("Portishead")

        # Act
        url = artist1.get_url()
        mbid = artist1.get_mbid()

        playcount = artist1.get_playcount()
        name = artist1.get_name(properly_capitalized=False)
        name_cap = artist1.get_name(properly_capitalized=True)

        # Assert
        assert playcount > 1
        assert artist1 != artist2
        assert name.lower() == name_cap.lower()
        assert url == "https://www.last.fm/music/radiohead"
        assert mbid == "a74b1b7f-71a5-4011-9441-d0b5e4122711"

    def test_artist_eq_none_is_false(self) -> None:
        # Arrange
        artist1 = None
        artist2 = pylast.Artist("Test Artist", self.network)

        # Act / Assert
        assert artist1 != artist2

    def test_artist_ne_none_is_true(self) -> None:
        # Arrange
        artist1 = None
        artist2 = pylast.Artist("Test Artist", self.network)

        # Act / Assert
        assert artist1 != artist2

    def test_artist_get_correction(self) -> None:
        # Arrange
        artist = pylast.Artist("guns and roses", self.network)

        # Act
        corrected_artist_name = artist.get_correction()

        # Assert
        assert corrected_artist_name == "Guns N' Roses"

    def test_get_userplaycount(self) -> None:
        # Arrange
        artist = pylast.Artist("John Lennon", self.network, username="RJ")

        # Act
        playcount = artist.get_userplaycount()

        # Assert
        assert playcount >= 10
