"""
Opera Backend Server — production-grade FastAPI application entrypoint.

Deployment model
----------------
Opera separates API serving from background work into two independent OS processes:

  API process  (this file, `main.py`):
    - Handles all HTTP and WebSocket traffic with fast response times.
    - Runs an optional in-process task scheduler when DISABLE_BACKGROUND_TASKS is unset
      (suitable for single-process local development or low-traffic deployments).
    - In production, background tasks are disabled here and delegated to the worker.

  Worker process (`worker.py`):
    - Runs background jobs at a safe cadence: price refresh, profit history, Polymarket
      settlement, market intel, and pending Byreal agent runs.
    - Fully decoupled from the API process — a slow price-fetch or long Byreal CLI call
      never increases API latency or blocks health checks.

This separation is a deliberate production-grade fault tolerance decision: the API
remains responsive even if a background job hangs or the external price source is slow.

Startup sequence
----------------
1. Rotating log file initialised (10 MB × 5 backups) — log aggregators can ingest
   `logs/server.log` without risking disk exhaustion.
2. `init_database()` runs schema migrations idempotently.
3. FastAPI app created with all route modules registered.
4. On `startup` event: database backend and cache are verified; trending cache is
   warmed so the first user request is never a cold cache miss.

Project layout:
- config.py   : configuration and environment variables
- database.py : database initialization and connections
- utils.py    : shared utility helpers
- tasks.py    : background tasks (API-side) and worker entry points
- services.py : business logic services
- routes.py   : API route definitions (registers all route modules)
- main.py     : application entrypoint (this file)
- worker.py   : standalone background worker process
"""

import secrets
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            os.path.join(LOG_DIR, "server.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
    ]
)

if os.getenv("API_STDERR_LOG", "false").strip().lower() in {"1", "true", "yes", "on"}:
    logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))

logger = logging.getLogger(__name__)

from cache import get_cache_status
from database import init_database, get_database_status
from routes import create_app
from routes_shared import api_access_log_enabled
from tasks import (
    _update_trending_cache,
    background_tasks_enabled_for_api,
    start_background_tasks,
)

if not api_access_log_enabled():
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.access").propagate = False

# Initialize database
init_database()

# Create app
app = create_app()


# ==================== Startup ====================

@app.on_event("startup")
async def startup_event():
    """Startup event — verify infrastructure and schedule background tasks.

    Each check here is a production readiness gate:
    - Database status confirms which backend is active (PostgreSQL vs SQLite) and
      that schema migrations have completed.
    - Cache status confirms Redis connectivity; the platform degrades gracefully to
      in-process dicts if Redis is unavailable, so this is advisory rather than fatal.
    - Trending cache warm-up ensures the first GET /api/signals/trending is served
      from cache rather than triggering a full database aggregation.
    """
    db_status = get_database_status()
    logger.info(
        "Database ready: backend=%s details=%s",
        db_status.get("backend"),
        {key: value for key, value in db_status.items() if key != "backend"},
    )
    cache_status = get_cache_status()
    logger.info(
        "Cache ready: enabled=%s configured=%s available=%s prefix=%s client_installed=%s error=%s",
        cache_status.get("enabled"),
        cache_status.get("configured"),
        cache_status.get("available"),
        cache_status.get("prefix"),
        cache_status.get("client_installed"),
        cache_status.get("last_error"),
    )
    logger.info("Initializing trending cache...")
    _update_trending_cache()
    if not background_tasks_enabled_for_api():
        logger.info(
            "API background tasks disabled. Run `python service/server/worker.py` "
            "to process prices, profit history, settlements, and market intel."
        )
        return

    started = start_background_tasks(logger)
    logger.info("Background tasks started: %s", len(started))


# ==================== Run ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=api_access_log_enabled())
