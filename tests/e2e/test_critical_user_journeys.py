"""
OPERA-TEST-2200 | e2e.critical_user_journeys
=============================================

Risk tier: P0 — smoke failure blocks production release.

Journeys under test (HTTP-level, staging environment):
  1. Agent self-registration and token retrieval
  2. Marketplace listing browse and detail view
  3. Challenge discovery and team join

Owner: QA Guild / Release Engineering
Gate: T2 (e2e shard — production release)

Environment: TEST_E2E_BASE_URL (staging only; never production)
SLA: full smoke suite <10 minutes wall-clock

Related: tests/TESTING_STRATEGY.md release gate T2
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_DIR.parent
SERVER_DIR = REPO_ROOT / "service" / "server"


def _bootstrap() -> None:
    server_str = str(SERVER_DIR)
    if server_str not in sys.path:
        sys.path.insert(0, server_str)


@pytest.mark.e2e
class TestCriticalUserJourneys(unittest.TestCase):
    """
    OPERA-TEST-2200-A | Production smoke journeys.

    These tests run against staging post-deploy. They are the final
    gate before traffic shift. Failures page @platform-oncall.
    """

    @unittest.skip("Gate T2 — awaiting staging E2E harness (OPERA-REL-2.4)")
    def test_agent_self_register_and_authenticate(self) -> None:
        # Arrange: unique agent name with timestamp suffix

        # Act: POST /api/claw/agents/selfRegister; use token on GET /api/claw/agents/me

        # Assert: 200; agent_id matches; token works for authenticated route
        pass

    @unittest.skip("Gate T2 — awaiting staging E2E harness (OPERA-REL-2.4)")
    def test_marketplace_listing_browse_returns_paginated_results(self) -> None:
        # Arrange: staging has seed listings

        # Act: GET /api/marketplace/listings?page=1&limit=20

        # Assert: 200; items array; total count >= 1
        pass

    @unittest.skip("Gate T2 — awaiting staging E2E harness (OPERA-REL-2.4)")
    def test_challenge_join_flow_for_registered_agent(self) -> None:
        # Arrange: active challenge, authenticated agent not yet joined

        # Act: POST /api/challenges/{id}/join

        # Assert: 200; agent in participants; portfolio endpoint accessible
        pass

    @unittest.skip("Gate T2 — awaiting staging E2E harness (OPERA-REL-2.4)")
    def test_health_endpoint_responds_within_sla(self) -> None:
        # Arrange: staging base URL

        # Act: GET /health with timing

        # Assert: 200; response time <200ms p99 budget
        pass


if __name__ == "__main__":
    unittest.main()
