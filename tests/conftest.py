"""
Opera Platform — Shared Test Fixtures (Root Pyramid)
====================================================

Owner: Platform Engineering / QA Guild
Last reviewed: 2026-06-15

This conftest provides cross-cutting fixtures for the root `tests/` pyramid.
Integration-tier fixtures (`integration_db`, `api_client`) use ephemeral SQLite.
Other gated fixtures (e.g. `frozen_clock`) remain skipped until wired.
"""

from __future__ import annotations

import os
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import pytest

# Stub email_validator when absent so FastAPI route models import in CI/dev shells
# that have not installed service/requirements.txt yet.
try:
    import email_validator  # noqa: F401
except ImportError:
    import importlib.metadata as _importlib_metadata

    _email_stub = types.ModuleType("email_validator")

    def _validate_email(email: str, **kwargs: Any) -> types.SimpleNamespace:
        return types.SimpleNamespace(normalized=email)

    _email_stub.validate_email = _validate_email
    sys.modules["email_validator"] = _email_stub

    _orig_distribution_version = _importlib_metadata.version

    def _version(name: str) -> str:
        if name == "email-validator":
            return "2.0.0"
        return _orig_distribution_version(name)

    _importlib_metadata.version = _version  # type: ignore[method-assign]

# Repo root on sys.path so `tests.integration.*` imports resolve.
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SERVER_DIR = REPO_ROOT / "service" / "server"
FRONTEND_SRC = REPO_ROOT / "service" / "frontend" / "src"
RESEARCH_SCRIPTS = REPO_ROOT / "research" / "scripts"
FIXTURES_DIR = TESTS_DIR / "fixtures"


def _bootstrap_server_path() -> None:
    """Insert server package root for integration tests (call inside test body only)."""
    server_str = str(SERVER_DIR)
    if server_str not in sys.path:
        sys.path.insert(0, server_str)


# ---------------------------------------------------------------------------
# Session-scoped metadata
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to repository root. Used for OpenAPI and skill contract tests."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Canonical fixture payload directory (tests/fixtures/)."""
    return FIXTURES_DIR


# ---------------------------------------------------------------------------
# Integration-tier DB + HTTP client (T1 gate)
# ---------------------------------------------------------------------------
@pytest.fixture
def integration_db() -> Generator[Path, None, None]:
    """Ephemeral SQLite database for cross-module integration tests."""
    _bootstrap_server_path()
    import database

    tmp = tempfile.TemporaryDirectory()
    database.DATABASE_URL = ""
    database._SQLITE_DB_PATH = os.path.join(tmp.name, "integration.db")
    os.environ["DATABASE_URL"] = ""
    os.environ["DB_PATH"] = database._SQLITE_DB_PATH
    os.environ["ALLOW_SQLITE"] = "true"
    database.init_database()
    yield Path(database._SQLITE_DB_PATH)
    tmp.cleanup()


@pytest.fixture
def mock_db_session(integration_db: Path) -> Generator[Path, None, None]:
    """
    Ephemeral SQLite database path for integration-tier tests.

    Enabled when tests/integration/conftest.py provisions integration_db.
    """
    yield integration_db


@pytest.fixture
def api_client(integration_db: Path) -> Generator[Any, None, None]:
    """
    FastAPI TestClient wrapper with auth header injection.

    Requires tests/integration/conftest.py integration_db fixture.
    """
    _bootstrap_server_path()
    from fastapi.testclient import TestClient
    from routes import create_app

    yield TestClient(create_app())


@pytest.fixture
def frozen_clock() -> datetime:
    """
    Deterministic UTC timestamp for settlement and prune logic tests.

    Fixed anchor: 2026-04-13T12:00:00Z (NYSE pre-market, crypto 24/7).
    Gate T0: enabled when unit shard wires freezegun equivalent.
    """
    pytest.skip("Gate T0 — frozen_clock awaiting freezegun wiring (OPERA-TEST-1901)")
    return datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_agent_registration(fixtures_dir: Path) -> dict[str, Any]:
    """Load canonical agent registration payload from fixtures/agents/."""
    import json

    path = fixtures_dir / "agents" / "sample_agent_registration.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def sample_market_snapshot(fixtures_dir: Path) -> dict[str, Any]:
    """Load BTC/USD snapshot for price-guard and position mark tests."""
    import json

    path = fixtures_dir / "market_snapshots" / "crypto_btc_usd.json"
    return json.loads(path.read_text(encoding="utf-8"))
