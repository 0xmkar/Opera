import os
import sys
from unittest.mock import patch

import pytest

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from price_fetcher import _get_byreal_price


@patch("price_fetcher.requests.post")
def test_get_byreal_price_parses_router_response(mock_post):
    mock_post.return_value.ok = True
    mock_post.return_value.json.return_value = {
        "success": True,
        "data": {"outAmount": "1500000"},
    }
    price = _get_byreal_price("SOL")
    assert price == 1.5


def test_get_byreal_price_usdc_is_one():
    assert _get_byreal_price("USDC") == 1.0
