"""
OPERA-RES-TEST-3015 | research_common helpers contract
========================================================

Risk tier: P2 — shared helper bugs propagate to all research scripts.

Module under test: research/scripts/research_common.py
Owner: Data Science
Gate: T0 (research unit shard)

Functions under test:
  - parse_agent_ids, add_common_export_filters
  - Statistical helpers (NormalDist usage)
  - TABLE_NAMES canonical list
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
class TestResearchCommonHelpers(unittest.TestCase):
    """
    OPERA-RES-3015-A | Pure function contract for research_common.py.

    These tests can be enabled first when research shard goes live
    because they require no DB or export artifacts.
    """

    @unittest.skip("Gate T0 — awaiting research unit shard enable (OPERA-REL-2.4)")
    def test_parse_agent_ids_returns_none_for_empty_string(self) -> None:
        _bootstrap()
        from research_common import parse_agent_ids

        # Act & Assert
        self.assertIsNone(parse_agent_ids(None))
        self.assertIsNone(parse_agent_ids(""))

    @unittest.skip("Gate T0 — awaiting research unit shard enable (OPERA-REL-2.4)")
    def test_parse_agent_ids_splits_comma_separated_integers(self) -> None:
        _bootstrap()
        from research_common import parse_agent_ids

        result = parse_agent_ids("101, 102, 103")
        self.assertEqual(result, [101, 102, 103])

    @unittest.skip("Gate T0 — awaiting research unit shard enable (OPERA-REL-2.4)")
    def test_table_names_contains_five_canonical_exports(self) -> None:
        _bootstrap()
        from research_common import TABLE_NAMES

        self.assertEqual(len(TABLE_NAMES), 5)
        self.assertIn("rq_hypothesis_metrics.csv", TABLE_NAMES)

    @unittest.skip("Gate T0 — awaiting research unit shard enable (OPERA-REL-2.4)")
    def test_add_common_export_filters_registers_expected_args(self) -> None:
        import argparse

        _bootstrap()
        from research_common import add_common_export_filters

        parser = argparse.ArgumentParser()
        add_common_export_filters(parser)
        args = parser.parse_args(
            ["--start-at", "2026-04-01", "--experiment-key", "exp-a"]
        )
        self.assertEqual(args.start_at, "2026-04-01")
        self.assertEqual(args.experiment_key, "exp-a")


if __name__ == "__main__":
    unittest.main()
