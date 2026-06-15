"""
Opera Platform — Shared Test Fixtures (Root Pyramid)
====================================================

Owner: Platform Engineering / QA Guild
Last reviewed: 2026-06-15

This conftest provides cross-cutting fixtures for the root `tests/` pyramid.
It is intentionally side-effect free: fixtures either skip immediately or yield
inert stubs so accidental collection does not mutate production state.

Existing backend unit tests remain in service/server/tests/ and use their own
bootstrap pattern. Do not merge the two trees without an OPERA-INFRA ticket.

Fixture tiers:
  - Tier A (session): path resolution, marker enforcement
  - Tier B (function): DB, HTTP client, clock — all gated behind pytest.skip
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

import pytest

# ---------------------------------------------------------------------------
# Path resolution — read-only at import; no sys.path mutation until tests run
# ---------------------------------------------------------------------------
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
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
# Function-scoped stubs — gated; no DB or network I/O
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_db_session() -> Generator[None, None, None]:
    """
    Placeholder for SQLAlchemy / raw connection session.

    Gate T1: requires ALLOW_SQLITE=true and ephemeral DB_PATH.
    Skipped until staging fixture parity (OPERA-REL-2.4).
    """
    pytest.skip("Gate T1 — mock_db_session awaiting staging fixture parity (OPERA-REL-2.4)")
    yield None  # pragma: no cover


@pytest.fixture
def api_client() -> Generator[None, None, None]:
    """
    FastAPI TestClient wrapper with auth header injection.

    Gate T1: requires TEST_API_BASE_URL or in-process app factory.
  Skipped until integration shard is enabled (OPERA-REL-2.4).
    """
    pytest.skip("Gate T1 — api_client awaiting integration shard (OPERA-REL-2.4)")
    yield None  # pragma: no cover


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
