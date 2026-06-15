"""
OPERA-TEST-1862 | experiment_metrics.cohort_kpis
==================================================

Risk tier: P2 — incorrect cohort KPIs invalidate A/B experiment conclusions.

Module under test: service/server/experiment_metrics.py
Owner: Data Platform / Experiments
Gate: T0 (unit shard)

Preconditions:
  - Fixture: tests/fixtures/experiment_scenarios/ab_assignment_cohort.json
  - Frozen assignment window 2026-04-01 → 2026-04-30

SLA: cohort aggregate for 10k agents must complete <200ms.

Related tickets: OPERA-1862, OPERA-1863
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = TESTS_DIR.parent
SERVER_DIR = REPO_ROOT / "service" / "server"
FIXTURES_DIR = TESTS_DIR / "fixtures"


def _bootstrap() -> None:
    server_str = str(SERVER_DIR)
    if server_str not in sys.path:
        sys.path.insert(0, server_str)


@pytest.mark.unit
class TestCohortKPIAggregation(unittest.TestCase):
    """
    OPERA-TEST-1862-A | Primary and secondary metric rollups per cohort.

    Validates windowed aggregates respect experiment assignment boundaries
    and do not leak pre-assignment events into treatment metrics.
    """

    @classmethod
    def setUpClass(cls) -> None:
        fixture_path = FIXTURES_DIR / "experiment_scenarios" / "ab_assignment_cohort.json"
        cls.cohort_fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    @unittest.skip("Gate T0 — awaiting experiment metrics baseline (OPERA-REL-2.4)")
    def test_control_cohort_excludes_treatment_agents(self) -> None:
        # Arrange: load ab_assignment_cohort.json, seed event log

        # Act: compute primary_metric for cohort_id=control

        # Assert: only agent_ids [101..105] included; treatment agents excluded
        pass

    @unittest.skip("Gate T0 — awaiting experiment metrics baseline (OPERA-REL-2.4)")
    def test_window_boundary_excludes_out_of_range_events(self) -> None:
        # Arrange: event at 2026-03-31T23:59:59Z (before window_start)

        # Act: aggregate within experiment window

        # Assert: event not counted in any cohort KPI
        pass

    @unittest.skip("Gate T0 — awaiting experiment metrics baseline (OPERA-REL-2.4)")
    def test_secondary_metrics_computed_independently(self) -> None:
        # Arrange: primary metric has data; secondary has sparse events

        # Act: rollup all secondary_metrics from fixture

        # Assert: each metric returns distinct value; no cross-contamination
        pass


@pytest.mark.unit
class TestWindowedAggregates(unittest.TestCase):
    """
    OPERA-TEST-1863 | Sliding and fixed window aggregate functions.

    Supports daily, weekly, and full-experiment-window rollups used by
    ExperimentAdminPage and research export pipeline.
    """

    @unittest.skip("Gate T0 — awaiting experiment metrics baseline (OPERA-REL-2.4)")
    def test_daily_rollup_aligns_to_utc_midnight(self) -> None:
        # Arrange: events spanning 2026-04-13 00:00 → 23:59 UTC

        # Act: daily_rollup(metric, date=2026-04-13)

        # Assert: single bucket; count matches seeded events
        pass

    @unittest.skip("Gate T0 — awaiting experiment metrics baseline (OPERA-REL-2.4)")
    def test_empty_cohort_returns_zero_not_null(self) -> None:
        # Arrange: cohort with zero assigned agents

        # Act: compute primary_metric

        # Assert: returns 0.0 (not None) for dashboard compatibility
        pass

    @unittest.skip("Gate T0 — awaiting experiment metrics baseline (OPERA-REL-2.4)")
    def test_allocation_pct_preserved_in_export_metadata(self) -> None:
        # Arrange: cohort_fixture with 50/50 split

        # Act: build export row for experiment

        # Assert: allocation_pct echoed in metadata; sums to 100
        pass


if __name__ == "__main__":
    unittest.main()
