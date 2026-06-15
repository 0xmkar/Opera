import os
import sys
from unittest.mock import patch

import pytest

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from byreal_cli import ByrealCliError
from byreal_tools import execute_tool, get_openai_tools


def test_get_openai_tools_dex_product():
    names = {tool["function"]["name"] for tool in get_openai_tools("dex")}
    assert "pools_list" in names
    assert "swap_quote" in names
    assert "perps_markets" not in names


@patch("byreal_tools.run_dex_command")
def test_swap_quote_calls_dry_run(mock_run):
    mock_run.return_value = {"uiInAmount": "0.01", "uiOutAmount": "0.68", "mode": "dry-run"}
    result = execute_tool(
        "swap_quote",
        {"input_token": "SOL", "output_token": "USDC", "amount": 0.01},
        mode="paper",
    )
    assert result["uiOutAmount"] == "0.68"
    args = mock_run.call_args[0][0]
    assert "--dry-run" in args


@patch("byreal_tools.run_dex_command")
def test_swap_execute_real_requires_confirm(mock_run):
    mock_run.return_value = {"uiInAmount": "0.01", "uiOutAmount": "0.68"}
    with pytest.raises(ByrealCliError):
        execute_tool(
            "swap_execute",
            {"input_token": "SOL", "output_token": "USDC", "amount": 0.01, "confirm": True},
            mode="paper",
            wallet_configured=True,
        )
