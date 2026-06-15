"""
REST API for platform-managed Byreal agent runs and wallets.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from byreal_agent import create_agent_run, get_agent_run, list_agent_runs, run_byreal_agent
from byreal_cli import check_cli_health
from byreal_wallet import ByrealWalletError, delete_wallet_config, get_wallet_status, save_wallet_config
from routes_models import ByrealAgentGoalRequest, ByrealWalletConnectRequest
from routes_shared import RouteContext
from utils import _extract_token
from services import _get_agent_by_token


def register_byreal_agent_routes(app: FastAPI, ctx: RouteContext) -> None:
    @app.get("/api/byreal/health")
    async def byreal_health():
        return check_cli_health()

    @app.post("/api/byreal/agent/goals")
    async def submit_byreal_goal(
        data: ByrealAgentGoalRequest,
        authorization: str = Header(None),
        wait: bool = False,
    ):
        token = _extract_token(authorization)
        agent = _get_agent_by_token(token)
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid token")

        mode = (data.mode or "paper").strip().lower()
        if mode not in {"paper", "real"}:
            raise HTTPException(status_code=400, detail="mode must be paper or real")
        product = (data.product or "auto").strip().lower()
        if product not in {"auto", "dex", "perps"}:
            raise HTTPException(status_code=400, detail="product must be auto, dex, or perps")

        run_id = create_agent_run(
            agent["id"],
            data.goal,
            mode=mode,
            product=product,
        )

        if data.wait or wait:
            try:
                result = await asyncio.to_thread(run_byreal_agent, run_id)
                run = get_agent_run(run_id, agent_id=agent["id"])
                return {"run_id": run_id, "status": result.get("status"), "run": run}
            except Exception as exc:
                run = get_agent_run(run_id, agent_id=agent["id"])
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {"run_id": run_id, "status": "pending", "poll": f"/api/byreal/agent/runs/{run_id}"}

    @app.get("/api/byreal/agent/runs")
    async def list_runs(authorization: str = Header(None), limit: int = 20):
        token = _extract_token(authorization)
        agent = _get_agent_by_token(token)
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"runs": list_agent_runs(agent["id"], limit=min(limit, 50))}

    @app.get("/api/byreal/agent/runs/{run_id}")
    async def get_run(run_id: int, authorization: str = Header(None)):
        token = _extract_token(authorization)
        agent = _get_agent_by_token(token)
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid token")
        run = get_agent_run(run_id, agent_id=agent["id"])
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @app.get("/api/byreal/agent/runs/{run_id}/events")
    async def stream_run_events(run_id: int, authorization: str = Header(None)):
        token = _extract_token(authorization)
        agent = _get_agent_by_token(token)
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid token")
        run = get_agent_run(run_id, agent_id=agent["id"])
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        async def event_generator():
            last_len = 0
            for _ in range(120):
                current = get_agent_run(run_id, agent_id=agent["id"]) or {}
                transcript = current.get("transcript") or []
                if len(transcript) > last_len:
                    chunk = transcript[last_len:]
                    last_len = len(transcript)
                    payload = json.dumps({"transcript": chunk, "status": current.get("status")})
                    yield f"data: {payload}\n\n"
                if current.get("status") in {"completed", "failed"}:
                    payload = json.dumps(
                        {
                            "status": current.get("status"),
                            "result": current.get("result"),
                            "error_message": current.get("error_message"),
                            "done": True,
                        }
                    )
                    yield f"data: {payload}\n\n"
                    break
                await asyncio.sleep(1)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.get("/api/byreal/wallet")
    async def get_wallet(authorization: str = Header(None), chain: Optional[str] = None):
        token = _extract_token(authorization)
        agent = _get_agent_by_token(token)
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid token")
        return get_wallet_status(agent["id"], chain=chain)

    @app.post("/api/byreal/wallet")
    async def connect_wallet(data: ByrealWalletConnectRequest, authorization: str = Header(None)):
        token = _extract_token(authorization)
        agent = _get_agent_by_token(token)
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid token")
        try:
            status = save_wallet_config(
                agent["id"],
                data.chain,
                data.secret,
                pubkey=data.pubkey,
            )
            return status
        except ByrealWalletError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/byreal/wallet")
    async def disconnect_wallet(authorization: str = Header(None), chain: Optional[str] = None):
        token = _extract_token(authorization)
        agent = _get_agent_by_token(token)
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid token")
        delete_wallet_config(agent["id"], chain=chain)
        return {"ok": True}
