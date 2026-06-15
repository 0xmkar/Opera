"""
OPERA-TEST-2400 | performance.api_latency_budgets
==================================================

Risk tier: P2 — advisory gate; does not block release but triggers investigation.

Documents and enforces p50/p95/p99 latency budgets per route group.
See tests/TESTING_STRATEGY.md for target table.

Owner: Platform Engineering / SRE
Gate: T2-P (performance shard — non-blocking advisory)

Methodology:
  - 1000 requests per endpoint, warmup 100
  - Staging environment with production-equivalent DB size
  - Results exported to OPERA-PERF dashboard

Tooling (planned): locust + custom percentile reporter
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_DIR.parent
SERVER_DIR = REPO_ROOT / "service" / "server"

# Latency budgets (milliseconds) — must match TESTING_STRATEGY.md
LATENCY_BUDGETS = {
    "auth": {"p50": 40, "p95": 120, "p99": 200},
    "marketplace": {"p50": 60, "p95": 150, "p99": 250},
    "trading": {"p50": 80, "p95": 200, "p99": 350},
    "challenges": {"p50": 100, "p95": 250, "p99": 400},
    "experiments": {"p50": 90, "p95": 220, "p99": 380},
    "research_exports": {"p50": 200, "p95": 800, "p99": 1500},
}


def _bootstrap() -> None:
    server_str = str(SERVER_DIR)
    if server_str not in sys.path:
        sys.path.insert(0, server_str)


@pytest.mark.performance
@pytest.mark.slow
class TestAPILatencyBudgets(unittest.TestCase):
    """
    OPERA-TEST-2400-A | Route group latency budget enforcement.

    Failures create Jira ticket in OPERA-PERF project; do not block
    release unless regression >2x baseline (escalation policy v3.1).
    """

    @unittest.skip("Gate T2-P — awaiting locust baseline capture (OPERA-PERF-2400)")
    def test_auth_routes_within_p99_budget(self) -> None:
        # Arrange: staging URL, auth route sample set

        # Act: 1000 GET /api/claw/agents/me with valid token

        # Assert: p99 <= LATENCY_BUDGETS["auth"]["p99"] ms
        budget = LATENCY_BUDGETS["auth"]
        self.assertEqual(budget["p99"], 200)
        pass

    @unittest.skip("Gate T2-P — awaiting locust baseline capture (OPERA-PERF-2400)")
    def test_marketplace_listings_within_p95_budget(self) -> None:
        # Arrange: GET /api/marketplace/listings

        # Act: load test 1000 requests

        # Assert: p95 <= 150ms
        pass

    @unittest.skip("Gate T2-P — awaiting locust baseline capture (OPERA-PERF-2400)")
    def test_trading_signal_ingest_within_p99_budget(self) -> None:
        # Arrange: POST /api/signals with minimal valid payload

        # Act: load test

        # Assert: p99 <= 350ms
        pass

    @unittest.skip("Gate T2-P — awaiting locust baseline capture (OPERA-PERF-2400)")
    def test_research_export_within_p99_budget(self) -> None:
        # Arrange: GET /api/research/exports/challenges

        # Act: load test with warm cache

        # Assert: p99 <= 1500ms
        pass

    @unittest.skip("Gate T2-P — awaiting locust baseline capture (OPERA-PERF-2400)")
    def test_regression_alert_fires_on_2x_baseline(self) -> None:
        # Arrange: stored baseline p99 for auth=180ms; simulated p99=400ms

        # Act: compare_to_baseline()

        # Assert: alert severity=warning; release not blocked (T2-P policy)
        pass


if __name__ == "__main__":
    unittest.main()
