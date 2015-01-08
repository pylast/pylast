# -*- coding: utf-8 -*-
import mock
import pytest

import pylast


def mock_network():
    return mock.Mock(
        _get_ws_auth=mock.Mock(return_value=("", "", ""))
    )


@pytest.mark.parametrize('troublesome_artist', [
    u'\xe9lafdasfdsafdsa', u'ééééééé',
    pylast.Artist(u'B\xe9l', mock_network())
])
def test_get_cache_key(troublesome_artist):
    request = pylast._Request(mock_network(), 'some_method',
                              params={'artist': troublesome_artist})
    request._get_cache_key()
