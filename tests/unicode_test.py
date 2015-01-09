# -*- coding: utf-8 -*-
import mock
import pytest
import six

import pylast


def mock_network():
    return mock.Mock(
        _get_ws_auth=mock.Mock(return_value=("", "", ""))
    )


@pytest.mark.parametrize('artist', [
    u'\xe9lafdasfdsafdsa', u'ééééééé',
    pylast.Artist(u'B\xe9l', mock_network()),
    'fdasfdsafsaf not unicode',
])
def test_get_cache_key(artist):
    request = pylast._Request(mock_network(), 'some_method',
                              params={'artist': artist})
    request._get_cache_key()


@pytest.mark.parametrize('obj', [pylast.Artist(u'B\xe9l', mock_network())])
def test_cast_and_hash(obj):
    assert type(six.text_type(obj)) is six.text_type
    assert isinstance(hash(obj), int)
