"""
On-chain-to-platform bridge: publishes Byreal fills as verifiable Opera signals.

Every swap or perpetuals fill executed through the Byreal CLIs produces a raw result dict
(amounts, tx signature, order ID). This module is responsible for translating that raw
execution record into an Opera signal that:

  1. Appears in the copy-trading feed — followers can mirror the position in real time.
  2. Updates the agent's paper portfolio — mark-to-market scoring and leaderboard ranking
     are based on this data, making performance fully auditable.
  3. Links back to the originating agent run via `byreal_trade_links` — every automated
     action is traceable from the UI run transcript to the on-chain transaction record.

The on-chain fill ID (Solana tx signature or Hyperliquid order ID) is preserved in the
signal's `content` field and in `byreal_trade_links.tx_signature`, forming an immutable
audit trail that any third party can verify independently against chain explorers.

Paper-mode fills follow the identical code path but carry a `[DRY RUN]` prefix in content,
so backtesting evidence is stored in exactly the same schema as live execution evidence —
making it straightforward to compare strategy performance across modes.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Optional

from database import get_db_connection
from routes_shared import normalize_market, utc_now_iso_z
from services import _reserve_signal_id, _update_position_from_signal


def _symbol_from_tokens(input_token: str, output_token: str, action: str) -> str:
    stables = {"USDC", "USDT", "USD", "USD1"}
    if action == "buy":
        sym = output_token if output_token.upper() not in stables else input_token
    else:
        sym = input_token if input_token.upper() not in stables else output_token
    return sym.upper()


def publish_byreal_signal(
    agent_id: int,
    *,
    action: str = "buy",
    symbol: Optional[str] = None,
    quantity: float,
    price: float,
    content: str,
    market: str = "byreal",
    tx_signature: Optional[str] = None,
    order_id: Optional[str] = None,
) -> int:
    """Insert a realtime operation signal and update paper portfolio."""
    market_norm = normalize_market(market)
    side = action.lower()
    if side not in {"buy", "sell", "short", "cover"}:
        side = "buy"

    qty = float(quantity)
    px = float(price)
    if not math.isfinite(qty) or qty <= 0:
        qty = 0.001
    if not math.isfinite(px) or px <= 0:
        px = 1.0

    now = utc_now_iso_z()
    executed_at = now
    timestamp = int(datetime.now(timezone.utc).timestamp())
    symbol_value = (symbol or "SOL").strip().upper()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        from database import begin_write_transaction

        begin_write_transaction(cursor)
        signal_id = _reserve_signal_id(cursor)
        cursor.execute(
            """
            INSERT INTO signals
            (signal_id, agent_id, message_type, market, signal_type, symbol, side, entry_price, quantity, content, timestamp, created_at, executed_at)
            VALUES (?, ?, 'operation', ?, 'realtime', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                agent_id,
                market_norm,
                symbol_value,
                side,
                px,
                qty,
                content,
                timestamp,
                now,
                executed_at,
            ),
        )
        _update_position_from_signal(
            agent_id,
            symbol_value,
            market_norm,
            side,
            qty,
            px,
            executed_at,
            cursor=cursor,
        )
        from fees import TRADE_FEE_RATE

        trade_value = px * qty
        fee = trade_value * TRADE_FEE_RATE
        if side in {"buy", "short"}:
            cursor.execute(
                "UPDATE agents SET cash = cash - ? WHERE id = ?",
                (trade_value + fee, agent_id),
            )
        elif side == "sell":
            cursor.execute(
                "UPDATE agents SET cash = cash + ? WHERE id = ?",
                (trade_value - fee, agent_id),
            )
        conn.commit()
        return signal_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def sync_tool_fill_to_signal(
    agent_id: int,
    tool_name: str,
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
    *,
    mode: str,
    run_id: Optional[int] = None,
) -> Optional[int]:
    """Map swap/perps tool output to an Opera signal and persist the on-chain link.

    Only fill-producing tools (swap_execute, swap_quote in paper mode,
    perps_order_market, perps_order_limit) generate signals.  Pure read tools and
    quote-only calls in real mode are intentionally excluded to keep the signal feed
    clean and actionable for copy-traders.
    """
    if tool_name not in {"swap_quote", "swap_execute", "perps_order_market", "perps_order_limit"}:
        return None
    if mode == "real" and tool_name.endswith("_quote"):
        return None

    input_token = str(tool_args.get("input_token") or tool_args.get("symbol") or "SOL")
    output_token = str(tool_args.get("output_token") or "USDC")
    in_amount = float(tool_result.get("uiInAmount") or tool_args.get("amount") or tool_args.get("size") or 0.001)
    out_amount = float(tool_result.get("uiOutAmount") or in_amount)
    tx_sig = ""
    signatures = tool_result.get("signatures") or []
    if signatures:
        tx_sig = signatures[0]
    tx_sig = tool_result.get("txSignature") or tool_result.get("signature") or tx_sig
    order_id = tool_result.get("orderId") or tool_result.get("order_id")

    action = "buy"
    if tool_name.startswith("perps"):
        action = "buy" if str(tool_args.get("side", "buy")).lower() == "buy" else "sell"
        symbol = input_token.upper()
        quantity = float(tool_args.get("size") or in_amount)
    else:
        symbol = _symbol_from_tokens(input_token, output_token, action)
        quantity = out_amount if action == "buy" else in_amount

    prefix = "[DRY RUN] " if mode != "real" or tool_result.get("mode") == "dry-run" else ""
    content = (
        f"{prefix}Byreal {tool_name} {input_token}→{output_token} | "
        f"in={in_amount:.4f} out={out_amount:.4f} | "
        f"tx={tx_sig or order_id or 'preview'}"
    )

    signal_id = publish_byreal_signal(
        agent_id,
        action=action,
        symbol=symbol,
        quantity=quantity,
        price=max(out_amount / max(in_amount, 1e-9), 0.0001),
        content=content,
        market="byreal",
        tx_signature=tx_sig or None,
        order_id=str(order_id) if order_id else None,
    )

    if run_id is not None:
        # Persist the run → signal → on-chain reference link so that the UI run
        # transcript, the Opera signal feed, and the raw tx signature are all
        # queryable from a single join.  This is the on-chain execution audit trail.
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO byreal_trade_links (run_id, agent_id, signal_id, tx_signature, order_id, cli_command, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                agent_id,
                signal_id,
                tx_sig or None,
                str(order_id) if order_id else None,
                tool_name,
                utc_now_iso_z(),
            ),
        )
        conn.commit()
        conn.close()

    return signal_id
