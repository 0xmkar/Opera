import json
import os
import sys

import pytest

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from byreal_cli import ByrealCliError, loads_cli_json, redact_command, unwrap_cli_json


def test_loads_cli_json_with_prefix_lines():
    sample = """[DRY RUN] No transaction will be executed

{"success": true, "data": {"uiInAmount": "0.01"}}"""
    parsed = loads_cli_json(sample)
    assert parsed["success"] is True
    assert unwrap_cli_json(parsed)["uiInAmount"] == "0.01"


def test_redact_command_masks_secret_values():
    cmd = ["byreal-cli", "wallet", "set", "--private-key", "supersecret"]
    assert redact_command(cmd)[-1] == "<redacted>"


def test_unwrap_cli_json_raises_on_failure():
    with pytest.raises(ByrealCliError):
        unwrap_cli_json({"success": False, "error": {"message": "boom"}})
