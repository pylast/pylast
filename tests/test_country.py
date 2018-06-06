#!/usr/bin/env python
"""
Integration (not unit) tests for pylast.py
"""
import unittest

import pylast

from .test_pylast import TestPyLastWithLastFm


class TestPyLastCountry(TestPyLastWithLastFm):
    def test_country_is_hashable(self):
        # Arrange
        country = self.network.get_country("Italy")

        # Act/Assert
        self.helper_is_thing_hashable(country)

    def test_countries(self):
        # Arrange
        country1 = pylast.Country("Italy", self.network)
        country2 = pylast.Country("Finland", self.network)

        # Act
        text = str(country1)
        rep = repr(country1)
        url = country1.get_url()

        # Assert
        self.assertIn("Italy", rep)
        self.assertIn("pylast.Country", rep)
        self.assertEqual(text, "Italy")
        self.assertEqual(country1, country1)
        self.assertNotEqual(country1, country2)
        self.assertEqual(url, "https://www.last.fm/place/italy")


if __name__ == "__main__":
    unittest.main(failfast=True)
