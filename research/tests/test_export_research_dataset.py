"""
OPERA-RES-TEST-3010 | export_research_dataset pipeline contract
=================================================================

Risk tier: P1 — corrupt exports break downstream analysis and publications.

Module under test: research/scripts/export_research_dataset.py
Owner: Data Science / Platform
Gate: T1 (research shard)

Preconditions:
  - Live or snapshot DB with research_exports API parity
  - Output directory research/exports/

Validates: all TABLE_NAMES from research_common exported with correct dtypes
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pytest

RESEARCH_TESTS_DIR = Path(__file__).resolve().parent
RESEARCH_SCRIPTS = RESEARCH_TESTS_DIR.parent / "scripts"
RESEARCH_ROOT = RESEARCH_TESTS_DIR.parent


def _bootstrap() -> None:
    scripts_str = str(RESEARCH_SCRIPTS)
    if scripts_str not in sys.path:
        sys.path.insert(0, scripts_str)


@pytest.mark.integration
class TestExportResearchDatasetPipeline(unittest.TestCase):
    """
    OPERA-RES-3010-A | Full dataset export from platform DB.

    Export must be idempotent: second run with same filters produces
    identical row counts and checksums (OPERA-RES-DATA-010).
    """

    @unittest.skip("Gate T1 — awaiting research DB snapshot (OPERA-REL-2.4)")
    def test_all_table_names_produced_in_output_directory(self) -> None:
        # Arrange: ephemeral DB with seed data

        # Act: export_research_dataset --output research/exports/test_run

        # Assert: all TABLE_NAMES files exist
        _bootstrap()
        from research_common import TABLE_NAMES  # noqa: F401 — wired at gate

        pass

    @unittest.skip("Gate T1 — awaiting research DB snapshot (OPERA-REL-2.4)")
    def test_experiment_key_filter_reduces_row_counts(self) -> None:
        # Arrange: 2 experiments in DB

        # Act: export with --experiment-key exp-a only

        # Assert: experiment_assignments rows only for exp-a
        pass

    @unittest.skip("Gate T1 — awaiting research DB snapshot (OPERA-REL-2.4)")
    def test_export_idempotent_on_unchanged_db(self) -> None:
        # Arrange: run export twice without DB mutations

        # Act: compare SHA256 of output CSVs

        # Assert: checksums identical
        pass

    @unittest.skip("Gate T1 — awaiting research DB snapshot (OPERA-REL-2.4)")
    def test_market_filter_applies_to_trades_and_positions(self) -> None:
        # Arrange: --market=crypto

        # Act: export

        # Assert: trades.csv market column all "crypto"
        pass


if __name__ == "__main__":
    unittest.main()
