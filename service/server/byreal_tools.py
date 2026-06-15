"""
Tool schemas and execution dispatch for the Byreal managed-agent LLM loop.

This module defines the full capability surface that Opera exposes to its platform-managed
agents when they operate in Byreal mode.  Each tool is expressed as an OpenAI
function-calling schema (type: "function") so that any compatible LLM can invoke it
without custom parsing.

Tool taxonomy
-------------
READ_TOOL_NAMES   : Safe, idempotent reads (pool listings, wallet balance, market data,
                    signal scans).  Always permitted regardless of execution mode.

WRITE_TOOL_NAMES  : State-changing tools that preview or execute on-chain actions.
                    In paper mode, write tools are called with dry-run semantics — they
                    compute expected outputs without submitting a transaction.

DESTRUCTIVE_TOOL_NAMES : Write tools that can submit real on-chain transactions
                    (swap_execute, perps_order_market, etc.).  These are gated behind
                    the confirm flag and the real-mode wallet check in byreal_agent.py.

DeFi capability mapping
-----------------------
pools_list / pools_analyze  → LP pool discovery and fee-tier analysis (DEX)
swap_quote / swap_execute   → Solana DEX token swaps, including MNT↔USDC routes
wallet_balance              → On-chain wallet introspection
positions_open/close        → LP position management
perps_markets               → Hyperliquid perpetuals market listing
perps_order_market/limit    → Real perpetuals order execution
perps_signals_scan          → Byreal proprietary signal feed ingestion
perps_positions/close       → Existing position query and close

The BYREAL_MAX_REAL_NOTIONAL_USD guard in execute_tool() enforces a hard notional
size cap on real-mode write calls, providing production-grade risk control at the
platform level independently of any per-agent policy.
"""

from __future__ import annotations

from typing import Any, Optional

from byreal_cli import (
    ByrealCliError,
    resolve_mint,
    run_dex_command,
    run_perps_command,
)
from config import BYREAL_MAX_REAL_NOTIONAL_USD

# Read tools never mutate state; they are always safe to call and are exempt from
# the real-mode wallet and notional-size checks.
READ_TOOL_NAMES = {
    "pools_list",
    "pools_analyze",
    "wallet_balance",
    "positions_list",
    "perps_markets",
    "perps_signals_scan",
}

WRITE_TOOL_NAMES = {
    "swap_quote",
    "swap_execute",
    "positions_open",
    "positions_close",
    "copy_farm_preview",
    "perps_order_market",
    "perps_order_limit",
    "perps_positions",
    "perps_close",
}

DESTRUCTIVE_TOOL_NAMES = {
    "swap_execute",
    "positions_open",
    "positions_close",
    "perps_order_market",
    "perps_order_limit",
    "perps_close",
}


def _tool_def(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


OPENAI_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _tool_def(
        "pools_list",
        "List Byreal DEX liquidity pools.",
        {"limit": {"type": "integer", "description": "Max pools to return"}},
    ),
    _tool_def(
        "pools_analyze",
        "Analyze a specific Byreal pool address.",
        {"pool_address": {"type": "string", "description": "Solana pool address"}},
        required=["pool_address"],
    ),
    _tool_def(
        "wallet_balance",
        "Read Solana wallet balances via byreal-cli.",
        {},
    ),
    _tool_def(
        "positions_list",
        "List open DEX LP / positions via byreal-cli.",
        {},
    ),
    _tool_def(
        "swap_quote",
        "Preview a DEX swap (dry-run, no on-chain tx).",
        {
            "input_token": {"type": "string", "description": "Input symbol or mint (e.g. SOL)"},
            "output_token": {"type": "string", "description": "Output symbol or mint (e.g. USDC)"},
            "amount": {"type": "number", "description": "UI amount of input token"},
        },
        required=["input_token", "output_token", "amount"],
    ),
    _tool_def(
        "swap_execute",
        "Execute a confirmed DEX swap on Solana (real mode only).",
        {
            "input_token": {"type": "string"},
            "output_token": {"type": "string"},
            "amount": {"type": "number"},
            "confirm": {"type": "boolean", "description": "Must be true to execute"},
        },
        required=["input_token", "output_token", "amount", "confirm"],
    ),
    _tool_def(
        "positions_open",
        "Open or add concentrated liquidity position (preview unless real+confirm).",
        {
            "pool_address": {"type": "string"},
            "amount": {"type": "number"},
            "confirm": {"type": "boolean"},
        },
        required=["pool_address", "amount"],
    ),
    _tool_def(
        "positions_close",
        "Close a DEX position (preview unless real+confirm).",
        {"position_id": {"type": "string"}, "confirm": {"type": "boolean"}},
        required=["position_id"],
    ),
    _tool_def(
        "copy_farm_preview",
        "Preview copy-farm rewards or allocation.",
        {"pool_address": {"type": "string"}},
        required=["pool_address"],
    ),
    _tool_def(
        "perps_markets",
        "List Hyperliquid perps markets via byreal-perps-cli.",
        {},
    ),
    _tool_def(
        "perps_signals_scan",
        "Scan Byreal perps signal feed.",
        {},
    ),
    _tool_def(
        "perps_order_market",
        "Place a market perps order (real mode requires confirm=true).",
        {
            "symbol": {"type": "string"},
            "side": {"type": "string", "enum": ["buy", "sell"]},
            "size": {"type": "number"},
            "confirm": {"type": "boolean"},
        },
        required=["symbol", "side", "size"],
    ),
    _tool_def(
        "perps_order_limit",
        "Place a limit perps order (real mode requires confirm=true).",
        {
            "symbol": {"type": "string"},
            "side": {"type": "string", "enum": ["buy", "sell"]},
            "size": {"type": "number"},
            "price": {"type": "number"},
            "confirm": {"type": "boolean"},
        },
        required=["symbol", "side", "size", "price"],
    ),
    _tool_def(
        "perps_positions",
        "List open perps positions.",
        {},
    ),
    _tool_def(
        "perps_close",
        "Close a perps position (real mode requires confirm=true).",
        {"symbol": {"type": "string"}, "confirm": {"type": "boolean"}},
        required=["symbol"],
    ),
]


def get_openai_tools(product: str = "auto") -> list[dict[str, Any]]:
    product = (product or "auto").strip().lower()
    names: set[str] = set()
    if product in {"auto", "dex"}:
        names |= {"pools_list", "pools_analyze", "wallet_balance", "positions_list"}
        names |= {"swap_quote", "swap_execute", "positions_open", "positions_close", "copy_farm_preview"}
    if product in {"auto", "perps"}:
        names |= {"perps_markets", "perps_signals_scan", "perps_positions"}
        names |= {"perps_order_market", "perps_order_limit", "perps_close"}
    return [tool for tool in OPENAI_TOOL_DEFINITIONS if tool["function"]["name"] in names]


def _estimate_notional_usd(result: dict[str, Any]) -> float:
    for key in ("inAmountUsd", "outAmountUsd", "notional_usd"):
        raw = result.get(key)
        if isinstance(raw, str):
            raw = raw.replace("$", "").replace(",", "").strip()
        try:
            value = float(raw)
            if value > 0:
                return value
        except (TypeError, ValueError):
            continue
    in_amt = result.get("uiInAmount") or result.get("inAmount")
    try:
        return float(in_amt or 0)
    except (TypeError, ValueError):
        return 0.0


def _guard_real_execution(
    tool_name: str,
    mode: str,
    args: dict[str, Any],
    *,
    wallet_configured: bool,
) -> None:
    if tool_name not in WRITE_TOOL_NAMES:
        return
    if mode != "real":
        if tool_name in DESTRUCTIVE_TOOL_NAMES and args.get("confirm"):
            raise ByrealCliError(f"{tool_name} requires mode=real")
        return
    if tool_name in DESTRUCTIVE_TOOL_NAMES:
        if not wallet_configured:
            raise ByrealCliError("real execution requires a connected wallet")
        if not args.get("confirm"):
            raise ByrealCliError(f"{tool_name} requires confirm=true in real mode")


def execute_tool(
    name: str,
    args: Optional[dict[str, Any]] = None,
    *,
    mode: str = "paper",
    wallet_configured: bool = False,
) -> dict[str, Any]:
    args = dict(args or {})
    tool = (name or "").strip()
    if not tool:
        raise ByrealCliError("tool name is required")

    _guard_real_execution(tool, mode, args, wallet_configured=wallet_configured)

    try:
        if tool == "pools_list":
            limit = int(args.get("limit") or 20)
            return run_dex_command(["pools", "list", "-o", "json", "--limit", str(limit)])
        if tool == "pools_analyze":
            pool = str(args.get("pool_address") or "").strip()
            if not pool:
                raise ByrealCliError("pool_address is required")
            return run_dex_command(["pools", "analyze", pool, "-o", "json"])
        if tool == "wallet_balance":
            return run_dex_command(["wallet", "balance", "-o", "json"])
        if tool == "positions_list":
            return run_dex_command(["positions", "list", "-o", "json"])
        if tool == "swap_quote":
            input_mint = resolve_mint(str(args["input_token"]))
            output_mint = resolve_mint(str(args["output_token"]))
            amount = float(args["amount"])
            return run_dex_command(
                [
                    "swap",
                    "execute",
                    "--input-mint",
                    input_mint,
                    "--output-mint",
                    output_mint,
                    "--amount",
                    str(amount),
                    "--dry-run",
                    "-o",
                    "json",
                ]
            )
        if tool == "swap_execute":
            input_mint = resolve_mint(str(args["input_token"]))
            output_mint = resolve_mint(str(args["output_token"]))
            amount = float(args["amount"])
            preview = run_dex_command(
                [
                    "swap",
                    "execute",
                    "--input-mint",
                    input_mint,
                    "--output-mint",
                    output_mint,
                    "--amount",
                    str(amount),
                    "--dry-run",
                    "-o",
                    "json",
                ]
            )
            notional = _estimate_notional_usd(preview)
            if notional > BYREAL_MAX_REAL_NOTIONAL_USD:
                raise ByrealCliError(
                    f"swap notional ${notional:.2f} exceeds cap ${BYREAL_MAX_REAL_NOTIONAL_USD:.2f}"
                )
            if mode != "real" or not args.get("confirm"):
                preview["mode"] = "preview"
                return preview
            return run_dex_command(
                [
                    "swap",
                    "execute",
                    "--input-mint",
                    input_mint,
                    "--output-mint",
                    output_mint,
                    "--amount",
                    str(amount),
                    "--confirm",
                    "-o",
                    "json",
                ]
            )
        if tool == "positions_open":
            pool = str(args.get("pool_address") or "").strip()
            amount = float(args.get("amount") or 0)
            cmd = ["positions", "open", pool, "--amount", str(amount), "-o", "json"]
            if mode == "real" and args.get("confirm"):
                cmd.append("--confirm")
            else:
                cmd.append("--dry-run")
            return run_dex_command(cmd)
        if tool == "positions_close":
            position_id = str(args.get("position_id") or "").strip()
            cmd = ["positions", "close", position_id, "-o", "json"]
            if mode == "real" and args.get("confirm"):
                cmd.append("--confirm")
            else:
                cmd.append("--dry-run")
            return run_dex_command(cmd)
        if tool == "copy_farm_preview":
            pool = str(args.get("pool_address") or "").strip()
            return run_dex_command(["copy-farm", "preview", pool, "-o", "json"])
        if tool == "perps_markets":
            return run_perps_command(["markets", "list", "-o", "json"])
        if tool == "perps_signals_scan":
            return run_perps_command(["signals", "scan", "-o", "json"])
        if tool == "perps_positions":
            return run_perps_command(["positions", "list", "-o", "json"])
        if tool == "perps_order_market":
            symbol = str(args["symbol"]).upper()
            side = str(args["side"]).lower()
            size = float(args["size"])
            cmd = ["order", "market", "--symbol", symbol, "--side", side, "--size", str(size), "-o", "json"]
            if mode == "real" and args.get("confirm"):
                cmd.append("--confirm")
            else:
                cmd.append("--dry-run")
            return run_perps_command(cmd)
        if tool == "perps_order_limit":
            symbol = str(args["symbol"]).upper()
            side = str(args["side"]).lower()
            size = float(args["size"])
            price = float(args["price"])
            cmd = [
                "order",
                "limit",
                "--symbol",
                symbol,
                "--side",
                side,
                "--size",
                str(size),
                "--price",
                str(price),
                "-o",
                "json",
            ]
            if mode == "real" and args.get("confirm"):
                cmd.append("--confirm")
            else:
                cmd.append("--dry-run")
            return run_perps_command(cmd)
        if tool == "perps_close":
            symbol = str(args["symbol"]).upper()
            cmd = ["positions", "close", "--symbol", symbol, "-o", "json"]
            if mode == "real" and args.get("confirm"):
                cmd.append("--confirm")
            else:
                cmd.append("--dry-run")
            return run_perps_command(cmd)
        raise ByrealCliError(f"unknown tool: {tool}")
    except ByrealCliError:
        raise
    except Exception as exc:
        raise ByrealCliError(str(exc)) from exc
