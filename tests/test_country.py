#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
from __future__ import annotations

import pylast

from .test_pylast import TestPyLastWithLastFm


class TestPyLastCountry(TestPyLastWithLastFm):
    def test_country_is_hashable(self) -> None:
        # Arrange
        country = self.network.get_country("Italy")

        # Act/Assert
        self.helper_is_thing_hashable(country)

    def test_countries(self) -> None:
        # Arrange
        country1 = pylast.Country("Italy", self.network)
        country2 = pylast.Country("Finland", self.network)

        # Act
        text = str(country1)
        rep = repr(country1)
        url = country1.get_url()

        # Assert
        assert "Italy" in rep
        assert "pylast.Country" in rep
        assert text == "Italy"
        assert country1 == country1
        assert country1 != country2
        assert url == "https://www.last.fm/place/italy"

    def test_country_top_artists_have_correct_network(self) -> None:
        # Arrange
        country = self.network.get_country("Germany")

        # Act
        artists = country.get_top_artists(limit=1)

        # Assert
        assert len(artists) > 0
        artist = artists[0].item
        assert isinstance(artist.network, pylast.LastFMNetwork)
        assert hasattr(artist.network, "username")
