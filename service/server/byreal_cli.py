"""
Subprocess adapter for byreal-cli and byreal-perps-cli.

Parses JSON envelopes from CLI stdout (may include human-readable prefix lines).
Redacts secrets from logged commands.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from typing import Any, Optional

from config import (
    BYREAL_AGENT_RUN_TIMEOUT_SECONDS,
    BYREAL_CLI_PATH,
    BYREAL_PERPS_CLI_PATH,
)

logger = logging.getLogger(__name__)

SECRET_PATTERN = re.compile(
    r"(private[_-]?key|secret|api[_-]?key|passphrase|mnemonic)",
    re.IGNORECASE,
)

TOKEN_MINTS: dict[str, str] = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "MNT": "4SoQ8UkWfeDH47T56PA53CZCeW4KytYCiU65CwBWoJUt",
}

TOKEN_DECIMALS: dict[str, int] = {
    "SOL": 9,
    "USDC": 6,
    "USDT": 6,
    "MNT": 9,
}


class ByrealCliError(RuntimeError):
    def __init__(self, message: str, *, command: list[str] | None = None, payload: Any = None):
        super().__init__(message)
        self.command = command
        self.payload = payload


def loads_cli_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"data": parsed}
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(raw[start : end + 1])
            return parsed if isinstance(parsed, dict) else {"data": parsed}
        raise


def unwrap_cli_json(data: object) -> dict[str, Any]:
    if isinstance(data, dict) and data.get("success") is False:
        err = data.get("error")
        message = err.get("message") if isinstance(err, dict) else str(err or "unknown error")
        raise ByrealCliError(str(message), payload=data)
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return data["data"]
    return data if isinstance(data, dict) else {}


def redact_command(cmd: list[str]) -> list[str]:
    redacted: list[str] = []
    skip_next = False
    for part in cmd:
        if skip_next:
            redacted.append("<redacted>")
            skip_next = False
            continue
        if SECRET_PATTERN.search(part):
            redacted.append(part)
            skip_next = True
            continue
        redacted.append(part)
    return redacted


def resolve_mint(symbol_or_mint: str) -> str:
    token = (symbol_or_mint or "").strip()
    if not token:
        raise ByrealCliError("token symbol or mint is required")
    upper = token.upper()
    if upper in TOKEN_MINTS:
        return TOKEN_MINTS[upper]
    if len(token) >= 32:
        return token
    raise ByrealCliError(f"unknown token symbol: {token}")


def run_command(
    cli_path: str,
    args: list[str],
    *,
    timeout: Optional[int] = None,
    non_interactive: bool = True,
) -> dict[str, Any]:
    if not shutil.which(cli_path):
        raise ByrealCliError(f"CLI not found in PATH: {cli_path}")

    cmd = [cli_path]
    if non_interactive:
        cmd.append("--non-interactive")
    cmd.extend(args)

    timeout_s = timeout if timeout is not None else BYREAL_AGENT_RUN_TIMEOUT_SECONDS
    logger.debug("byreal-cli exec: %s", " ".join(redact_command(cmd)))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise ByrealCliError(f"CLI timed out after {timeout_s}s", command=cmd) from exc

    combined = (result.stdout or "").strip() or (result.stderr or "").strip()
    try:
        raw = loads_cli_json(combined)
    except json.JSONDecodeError as exc:
        snippet = combined[:240].replace("\n", " ")
        raise ByrealCliError(
            f"invalid CLI JSON output: {snippet}",
            command=cmd,
        ) from exc

    if result.returncode != 0 or raw.get("success") is False:
        err = raw.get("error") if isinstance(raw.get("error"), dict) else {}
        message = err.get("message") if isinstance(err, dict) else combined[:200]
        raise ByrealCliError(str(message or "CLI command failed"), command=cmd, payload=raw)

    return raw


def run_dex_command(args: list[str], **kwargs: Any) -> dict[str, Any]:
    return unwrap_cli_json(run_command(BYREAL_CLI_PATH, args, **kwargs))


def run_perps_command(args: list[str], **kwargs: Any) -> dict[str, Any]:
    return unwrap_cli_json(run_command(BYREAL_PERPS_CLI_PATH, args, **kwargs))


def check_cli_health() -> dict[str, Any]:
    status: dict[str, Any] = {"dex": None, "perps": None, "ok": False}
    for key, path in (("dex", BYREAL_CLI_PATH), ("perps", BYREAL_PERPS_CLI_PATH)):
        if not shutil.which(path):
            status[key] = {"installed": False, "path": path}
            continue
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            version = (result.stdout or result.stderr or "").strip()
            status[key] = {"installed": True, "path": path, "version": version}
        except Exception as exc:
            status[key] = {"installed": True, "path": path, "error": str(exc)}
    status["ok"] = bool(status.get("dex", {}).get("installed"))
    return status
