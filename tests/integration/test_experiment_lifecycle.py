"""
OPERA-TEST-2005 | integration.experiment_lifecycle
====================================================

Risk tier: P1 — broken experiment flow invalidates product analytics.

Flow under test:
  1. Admin creates experiment (routes_experiments)
  2. Agent assigned to cohort (experiments.py)
  3. Event recorded (experiment_events.py)
  4. Notification dispatched (experiment_notifications.py)

Owner: Data Platform / Experiments
Gate: T1 (integration shard)

Preconditions:
  - Fixture: tests/fixtures/experiment_scenarios/ab_assignment_cohort.json
  - Admin API token with experiment:write scope

Related: service/server/tests/test_experiment_*.py
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_DIR.parent
SERVER_DIR = REPO_ROOT / "service" / "server"
FIXTURES_DIR = TESTS_DIR / "fixtures"


def _bootstrap() -> None:
    server_str = str(SERVER_DIR)
    if server_str not in sys.path:
        sys.path.insert(0, server_str)


@pytest.mark.integration
class TestExperimentLifecycle(unittest.TestCase):
    """
    OPERA-TEST-2005-A | Register → assign → event → notification chain.

    End-to-end validation that experiment state machine transitions are
    atomic and notification fan-out respects cohort boundaries.
    """

    @classmethod
    def setUpClass(cls) -> None:
        path = FIXTURES_DIR / "experiment_scenarios" / "ab_assignment_cohort.json"
        cls.cohort_fixture = json.loads(path.read_text(encoding="utf-8"))

    @unittest.skip("Gate T1 — awaiting staging fixture parity (OPERA-REL-2.4)")
    def test_create_experiment_and_assign_agents_to_cohorts(self) -> None:
        # Arrange: POST experiment from cohort_fixture metadata

        # Act: bulk assign agent_ids to control/treatment

        # Assert: assignment rows match fixture allocation_pct
        pass

    @unittest.skip("Gate T1 — awaiting staging fixture parity (OPERA-REL-2.4)")
    def test_experiment_event_recorded_with_correct_cohort_tag(self) -> None:
        # Arrange: treatment agent 201 assigned

        # Act: POST experiment event (click_through) for agent 201

        # Assert: event.cohort_id=treatment; not visible in control rollup
        pass

    @unittest.skip("Gate T1 — awaiting staging fixture parity (OPERA-REL-2.4)")
    def test_notification_created_on_assignment(self) -> None:
        # Arrange: newly assigned agent 102

        # Act: trigger assignment webhook / internal notification job

        # Assert: unread notice exists; GET /api/experiments/notices returns it
        pass

    @unittest.skip("Gate T1 — awaiting staging fixture parity (OPERA-REL-2.4)")
    def test_experiment_pause_stops_new_assignments(self) -> None:
        # Arrange: active experiment

        # Act: PATCH status=paused; attempt new assignment

        # Assert: HTTP 409; no new assignment rows
        pass


if __name__ == "__main__":
    unittest.main()
