"""
OPERA-TEST-2015 | integration.byreal_agent_run_flow
====================================================

Risk tier: P1 — broken agent run lifecycle blocks Byreal DEX paper trading.

Flow under test:
  1. POST /api/byreal/agent/runs (create run, mode=paper)
  2. Worker processes run → status transitions pending→running→completed
  3. GET run returns result_json with summary

Owner: Byreal Integration
Gate: T1 (integration shard)

Complements: service/server/tests/test_byreal_agent.py (unit slice)
Does NOT duplicate wallet encryption tests (test_byreal_wallet.py).
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


@pytest.mark.integration
class TestByrealAgentRunFlow(unittest.TestCase):
    """
    OPERA-TEST-2015-A | Paper run lifecycle across API and worker.

    Integration-level validation of run state machine including
    failure paths and result_json schema contract.
    """

    @unittest.skip("Gate T1 — awaiting byreal integration staging (OPERA-REL-2.4)")
    def test_create_run_returns_pending_status(self) -> None:
        # Arrange: authenticated agent token

        # Act: POST /api/byreal/agent/runs {goal, mode=paper, product=dex}

        # Assert: 201; body.status=pending; run_id present
        pass

    @unittest.skip("Gate T1 — awaiting byreal integration staging (OPERA-REL-2.4)")
    def test_completed_run_exposes_result_summary(self) -> None:
        # Arrange: run_id in completed state with result_json

        # Act: GET /api/byreal/agent/runs/{run_id}

        # Assert: status=completed; result.summary is string
        pass

    @unittest.skip("Gate T1 — awaiting byreal integration staging (OPERA-REL-2.4)")
    def test_failed_run_preserves_error_for_debugging(self) -> None:
        # Arrange: run that terminates with CLI error

        # Act: GET run

        # Assert: status=failed; error_message non-empty; no secret leakage
        pass

    @unittest.skip("Gate T1 — awaiting byreal integration staging (OPERA-REL-2.4)")
    def test_skill_route_serves_byreal_markdown(self) -> None:
        # Arrange: GET /api/skills/byreal (unauthenticated OK)

        # Act: fetch skill content

        # Assert: 200; body contains "byreal-cli" token
        pass


if __name__ == "__main__":
    unittest.main()
