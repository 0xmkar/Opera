# Opera Service — Deployment Guide

This directory contains the production FastAPI backend (`server/`) and React frontend (`frontend/`) for Opera — the agent-native trading platform for the **Mantle ecosystem**, with on-chain execution via **Byreal** (MNT DEX routes on Solana, MNT perps on Hyperliquid).

### Mantle narrative (bridge flow)

```
Mantle L2 (MNT) → bridge → Solana SPL MNT → Byreal CLIs → byreal_sync → Opera signals
```

MNT is registered in `server/byreal_cli.py` (`TOKEN_MINTS`) and priced via Hyperliquid/Byreal fallbacks. Every real fill links to `byreal_trade_links` for audit. See [docs/README_GTM.md](../docs/README_GTM.md).

**AA / gasless (roadmap):** Mantle ERC-4337 smart accounts + paymasters for gasless agent UserOps on L2 — not implemented; wallet encryption (`byreal_wallet.py`) handles Solana keys today.

---

## Quick Start (local)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Copy and configure environment
cp ../.env.example ../.env
# Edit .env — at minimum set DB_PATH or DATABASE_URL

# 3. Start the API server (includes in-process background tasks)
python server/main.py
```

The server listens on `http://0.0.0.0:8000` by default.

---

## Docker (recommended for production)

```bash
# Build
docker build -t opera-server ./service

# Run (single process — API + background tasks)
docker run -p 8000:8000 --env-file .env opera-server

# Run (production split — API and worker as separate containers)
docker run -p 8000:8000 --env-file .env -e DISABLE_BACKGROUND_TASKS=true opera-server
docker run --env-file .env opera-server python server/worker.py
```

The Dockerfile installs Python 3.12, Node 20, `@byreal-io/byreal-cli`, and `@byreal-io/byreal-perps-cli`. The built-in `HEALTHCHECK` calls `/health` every 30 seconds and verifies Byreal CLI availability.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | No | PostgreSQL DSN (`postgresql://user:pass@host/db`). If unset, SQLite is used. |
| `DB_PATH` | No | SQLite file path (default: `server/data/opera.db`). Ignored when `DATABASE_URL` is set. |
| `REDIS_URL` | No | Redis DSN for shared cache. Degrades gracefully to in-process dict when absent. |
| `BYREAL_WALLET_ENCRYPTION_KEY` | For real execution | Fernet key for per-agent wallet encryption. Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `OPENROUTER_API_KEY` | For platform-managed agent | LLM routing API key (OpenRouter). |
| `OPENROUTER_MODEL` | For platform-managed agent | Model slug, e.g. `openai/gpt-4o`. |
| `BYREAL_AGENT_MAX_STEPS` | No | Max tool-calling iterations per agent run (default: 8). |
| `BYREAL_MAX_REAL_NOTIONAL_USD` | No | Hard notional cap for real-mode Byreal executions. |
| `DISABLE_BACKGROUND_TASKS` | No | Set `true` to run API without in-process background jobs (use with `worker.py`). |
| `API_STDERR_LOG` | No | Set `true` to mirror server logs to stderr (useful for Docker log drivers). |

See `.env.example` at the repository root for the full list.

---

## Process Model

Opera is designed for a two-process production deployment:

```
┌─────────────────────────────────────┐   ┌────────────────────────────────────┐
│  API process  (main.py)             │   │  Worker process  (worker.py)       │
│                                     │   │                                    │
│  - FastAPI / Uvicorn                │   │  - Price refresh (crypto, stocks)  │
│  - All HTTP + WebSocket routes      │   │  - Polymarket settlement           │
│  - Auth, signals, copy trading      │   │  - Profit history snapshots        │
│  - Byreal agent goal submission     │   │  - Byreal agent run execution      │
│  - /health readiness probe          │   │  - Trending cache population       │
└─────────────────────────────────────┘   └────────────────────────────────────┘
            shared PostgreSQL + Redis
```

This separation ensures that slow background work (price fetches, LLM calls, on-chain
CLI execution) never increases API latency or delays health-check responses.

---

## Health Check

```bash
GET /health
```

Returns JSON with database backend, cache status, Byreal CLI availability, and uptime.
Use as a Kubernetes readiness/liveness probe or Docker HEALTHCHECK target.

---

## Logging

The API writes rotating log files to `server/logs/server.log` (10 MB per file, 5 backups).
Set `API_STDERR_LOG=true` to also emit logs to stderr for Docker log-driver capture.

Log format: `%(asctime)s - %(levelname)s - %(message)s`

---

## Frontend

```bash
cd frontend
npm install
npm run dev      # local dev server (Vite, port 5173)
npm run build    # production build → frontend/dist/
```

The FastAPI server serves the built frontend from `frontend/dist/` at `/`.

---

## Running Tests

```bash
# Backend unit tests
python -m pytest server/tests/

# Root test pyramid (integration, contract, e2e — see tests/TESTING_STRATEGY.md)
python -m pytest ../tests/ -c ../tests/pytest.ini
```
