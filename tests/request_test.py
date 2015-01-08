# -*- coding: utf-8 -*-
import mock
import pytest

import pylast


def mock_network():
    return mock.Mock(
        _get_ws_auth=mock.Mock(return_value=("", "", ""))
    )


@pytest.mark.parametrize('unicode_artist', [u'\xe9lafdasfdsafdsa', u'ééééééé'])
def test_get_cache_key(unicode_artist):
    request = pylast._Request(mock_network(), 'some_method',
                              params={'artist': unicode_artist})
    request._get_cache_key()
