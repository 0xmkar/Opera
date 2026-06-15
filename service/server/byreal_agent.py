"""
Platform-managed Byreal agent — OpenRouter tool-calling loop.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from openrouter import OpenRouter
except ImportError:  # pragma: no cover
    OpenRouter = None

from byreal_cli import ByrealCliError
from byreal_sync import sync_tool_fill_to_signal
from byreal_tools import execute_tool, get_openai_tools
from byreal_wallet import configure_cli_wallet, get_wallet_config
from config import BYREAL_AGENT_RUN_TIMEOUT_SECONDS
from database import get_db_connection

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "").strip()
BYREAL_AGENT_MAX_STEPS = int(os.getenv("BYREAL_AGENT_MAX_STEPS", "8"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _extract_openrouter_text(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if choices is None and isinstance(response, dict):
        choices = response.get("choices")
    if not choices:
        return ""
    first = choices[0]
    message = getattr(first, "message", None) or (first.get("message") if isinstance(first, dict) else None)
    if not message:
        return ""
    content = getattr(message, "content", None) if not isinstance(message, dict) else message.get("content")
    if isinstance(content, str):
        return content.strip()
    return ""


def _extract_tool_calls(response: Any) -> list[dict[str, Any]]:
    choices = getattr(response, "choices", None)
    if choices is None and isinstance(response, dict):
        choices = response.get("choices")
    if not choices:
        return []
    first = choices[0]
    message = getattr(first, "message", None) or (first.get("message") if isinstance(first, dict) else None)
    if not message:
        return []
    tool_calls = getattr(message, "tool_calls", None) if not isinstance(message, dict) else message.get("tool_calls")
    if not tool_calls:
        return []
    normalized: list[dict[str, Any]] = []
    for call in tool_calls:
        if isinstance(call, dict):
            fn = call.get("function") or {}
            normalized.append(
                {
                    "id": call.get("id"),
                    "name": fn.get("name"),
                    "arguments": fn.get("arguments") or "{}",
                }
            )
        else:
            fn = getattr(call, "function", None)
            normalized.append(
                {
                    "id": getattr(call, "id", None),
                    "name": getattr(fn, "name", None) if fn else None,
                    "arguments": getattr(fn, "arguments", "{}") if fn else "{}",
                }
            )
    return normalized


def _load_run(run_id: int) -> dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM byreal_agent_runs WHERE id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise ValueError(f"run {run_id} not found")
    return dict(row)


def _update_run(run_id: int, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = _utc_now_iso()
    columns = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [run_id]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE byreal_agent_runs SET {columns} WHERE id = ?", values)
    conn.commit()
    conn.close()


def _append_transcript(run_id: int, entry: dict[str, Any]) -> list[dict[str, Any]]:
    run = _load_run(run_id)
    transcript = []
    raw = run.get("transcript_json")
    if raw:
        try:
            transcript = json.loads(raw)
        except json.JSONDecodeError:
            transcript = []
    transcript.append(entry)
    _update_run(run_id, transcript_json=json.dumps(transcript))
    return transcript


def run_byreal_agent(run_id: int) -> dict[str, Any]:
    """Execute a pending Byreal agent run (blocking)."""
    run = _load_run(run_id)
    if run["status"] not in {"pending", "running"}:
        return {"run_id": run_id, "status": run["status"], "skipped": True}

    agent_id = int(run["agent_id"])
    goal = run["goal"]
    mode = (run.get("mode") or "paper").strip().lower()
    product = (run.get("product") or "auto").strip().lower()

    if not OPENROUTER_API_KEY or not OPENROUTER_MODEL or OpenRouter is None:
        _update_run(run_id, status="failed", error_message="OPENROUTER_API_KEY/MODEL not configured", completed_at=_utc_now_iso())
        raise RuntimeError("OpenRouter is not configured")

    wallet_chain = "solana" if product in {"auto", "dex"} else "hyperliquid"
    wallet_configured = get_wallet_config(agent_id, wallet_chain) is not None
    if mode == "real" and wallet_configured:
        try:
            configure_cli_wallet(agent_id, wallet_chain)
        except Exception as exc:
            logger.warning("wallet configure failed for agent %s: %s", agent_id, exc)

    _update_run(run_id, status="running", started_at=_utc_now_iso())
    tools = get_openai_tools(product)
    system_prompt = (
        "You are a Byreal trading agent. Use tools to analyze pools/markets and preview trades. "
        f"Execution mode is {mode}. In paper mode only preview tools; never set confirm=true. "
        "In real mode, only execute after explicit preview and set confirm=true on write tools. "
        "Summarize findings and recommended next steps concisely."
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": goal},
    ]
    signal_ids: list[int] = []
    final_summary = ""

    try:
        with OpenRouter(api_key=OPENROUTER_API_KEY) as client:
            for step in range(BYREAL_AGENT_MAX_STEPS):
                response = client.chat.send(
                    model=OPENROUTER_MODEL,
                    messages=messages,
                    tools=tools,
                )
                tool_calls = _extract_tool_calls(response)
                assistant_text = _extract_openrouter_text(response)
                if assistant_text:
                    final_summary = assistant_text

                if not tool_calls:
                    _append_transcript(
                        run_id,
                        {"type": "assistant", "step": step, "content": assistant_text},
                    )
                    break

                assistant_message: dict[str, Any] = {"role": "assistant", "content": assistant_text or ""}
                assistant_message["tool_calls"] = [
                    {
                        "id": call.get("id") or f"call_{step}_{idx}",
                        "type": "function",
                        "function": {"name": call.get("name"), "arguments": call.get("arguments")},
                    }
                    for idx, call in enumerate(tool_calls)
                ]
                messages.append(assistant_message)

                for idx, call in enumerate(tool_calls):
                    tool_name = call.get("name") or ""
                    try:
                        tool_args = json.loads(call.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        tool_args = {}
                    entry: dict[str, Any] = {
                        "type": "tool",
                        "step": step,
                        "tool": tool_name,
                        "args": tool_args,
                    }
                    try:
                        result = execute_tool(
                            tool_name,
                            tool_args,
                            mode=mode,
                            wallet_configured=wallet_configured,
                        )
                        entry["result"] = result
                        entry["ok"] = True
                        signal_id = sync_tool_fill_to_signal(
                            agent_id,
                            tool_name,
                            tool_args,
                            result,
                            mode=mode,
                            run_id=run_id,
                        )
                        if signal_id:
                            signal_ids.append(signal_id)
                            entry["signal_id"] = signal_id
                    except ByrealCliError as exc:
                        entry["ok"] = False
                        entry["error"] = str(exc)
                        result = {"error": str(exc)}
                    _append_transcript(run_id, entry)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id") or f"call_{step}_{idx}",
                            "content": json.dumps(result, default=str)[:8000],
                        }
                    )
            else:
                final_summary = final_summary or "Stopped after max tool steps."

        result_payload = {
            "summary": final_summary,
            "signal_ids": signal_ids,
            "mode": mode,
            "product": product,
        }
        _update_run(
            run_id,
            status="completed",
            result_json=json.dumps(result_payload),
            completed_at=_utc_now_iso(),
        )
        return {"run_id": run_id, "status": "completed", **result_payload}
    except Exception as exc:
        logger.exception("byreal agent run %s failed", run_id)
        _update_run(
            run_id,
            status="failed",
            error_message=str(exc)[:500],
            completed_at=_utc_now_iso(),
        )
        raise


def create_agent_run(
    agent_id: int,
    goal: str,
    *,
    mode: str = "paper",
    product: str = "auto",
) -> int:
    now = _utc_now_iso()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO byreal_agent_runs (agent_id, goal, mode, product, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """,
        (agent_id, goal.strip(), mode.strip().lower(), product.strip().lower(), now, now),
    )
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return int(run_id)


def list_agent_runs(agent_id: int, limit: int = 20) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, agent_id, goal, mode, product, status, error_message, created_at, updated_at, started_at, completed_at
        FROM byreal_agent_runs
        WHERE agent_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (agent_id, limit),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_agent_run(run_id: int, agent_id: Optional[int] = None) -> Optional[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if agent_id is not None:
        cursor.execute(
            "SELECT * FROM byreal_agent_runs WHERE id = ? AND agent_id = ?",
            (run_id, agent_id),
        )
    else:
        cursor.execute("SELECT * FROM byreal_agent_runs WHERE id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    for key in ("transcript_json", "result_json"):
        if data.get(key):
            try:
                data[key.replace("_json", "")] = json.loads(data[key])
            except json.JSONDecodeError:
                data[key.replace("_json", "")] = data[key]
    return data


def process_pending_runs(limit: int = 3) -> dict[str, Any]:
    """Worker entry: process up to N pending runs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM byreal_agent_runs
        WHERE status = 'pending'
        ORDER BY id ASC
        LIMIT ?
        """,
        (limit,),
    )
    run_ids = [int(row["id"]) for row in cursor.fetchall()]
    conn.close()

    completed = 0
    failed = 0
    for run_id in run_ids:
        try:
            run_byreal_agent(run_id)
            completed += 1
        except Exception:
            failed += 1
    return {"processed": len(run_ids), "completed": completed, "failed": failed}
