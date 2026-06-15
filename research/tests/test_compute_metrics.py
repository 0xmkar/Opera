"""
OPERA-RES-TEST-3001 | compute_metrics pipeline contract
=========================================================

Risk tier: P1 — incorrect metrics invalidate published research findings.

Module under test: research/scripts/compute_metrics.py
Owner: Data Science
Gate: T1 (research shard)

Preconditions:
  - Input: research/exports/*.csv from export_research_dataset
  - Output: rq_hypothesis_metrics.csv with documented column schema

SLA: compute_metrics for 100k rows <60s on CI runner.

Related: research/schemas/quality_scores.schema.json
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pytest

RESEARCH_TESTS_DIR = Path(__file__).resolve().parent
RESEARCH_SCRIPTS = RESEARCH_TESTS_DIR.parent / "scripts"


def _bootstrap() -> None:
    scripts_str = str(RESEARCH_SCRIPTS)
    if scripts_str not in sys.path:
        sys.path.insert(0, scripts_str)


@pytest.mark.unit
class TestComputeMetricsPipeline(unittest.TestCase):
    """
    OPERA-RES-3001-A | Hypothesis metric computation from export tables.

    Validates statistical functions, null handling, and output column order
    match research publication requirements (OPERA-RES-PUB-001).
    """

    @unittest.skip("Gate T1 — awaiting research export fixture pack (OPERA-REL-2.4)")
    def test_rq_hypothesis_metrics_columns_match_schema(self) -> None:
        # Arrange: seed exports/ with minimal agent event data

        # Act: run compute_metrics.main()

        # Assert: output columns match TABLE_NAMES[0] header contract
        pass

    @unittest.skip("Gate T1 — awaiting research export fixture pack (OPERA-REL-2.4)")
    def test_empty_input_produces_header_only_csv(self) -> None:
        # Arrange: no rows in date window

        # Act: compute_metrics with --start-at future date

        # Assert: CSV has header row only; exit code 0
        pass

    @unittest.skip("Gate T1 — awaiting research export fixture pack (OPERA-REL-2.4)")
    def test_agent_ids_filter_restricts_computation(self) -> None:
        # Arrange: --agent-ids=101,102

        # Act: compute_metrics

        # Assert: output rows only for agents 101 and 102
        pass

    @unittest.skip("Gate T1 — awaiting research export fixture pack (OPERA-REL-2.4)")
    def test_variant_key_stratification_produces_separate_rows(self) -> None:
        # Arrange: control and treatment assignments

        # Act: compute_metrics --experiment-key exp-notif-v2-rollout

        # Assert: distinct rows per variant_key
        pass


if __name__ == "__main__":
    unittest.main()
