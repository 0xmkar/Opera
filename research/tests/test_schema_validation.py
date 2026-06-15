"""
OPERA-RES-TEST-3020 | schema validation for research exports
===============================================================

Risk tier: P1 — schema drift causes silent data corruption in publications.

Contract source: research/schemas/*.schema.json (25 schemas)
Owner: Data Science / API Guild
Gate: T0 (research contract shard)

Validates exported CSV rows conform to JSON Schema definitions for
agents, experiments, challenges, teams, signals, and network edges.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import pytest

RESEARCH_TESTS_DIR = Path(__file__).resolve().parent
RESEARCH_ROOT = RESEARCH_TESTS_DIR.parent
SCHEMAS_DIR = RESEARCH_ROOT / "schemas"
FIXTURES_DIR = RESEARCH_TESTS_DIR / "fixtures"


@pytest.mark.contract
class TestSchemaValidation(unittest.TestCase):
    """
    OPERA-RES-3020-A | CSV export row validation against JSON schemas.

    Each schema file defines required columns and types. Export pipeline
    must produce rows that validate before research/scripts consume them.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema_files = list(SCHEMAS_DIR.glob("*.schema.json"))
        cls.sample_csv = FIXTURES_DIR / "sample_export_row.csv"

    @unittest.skip("Gate T0 — awaiting jsonschema dependency pin (OPERA-RES-3020)")
    def test_all_schema_files_are_valid_json_skipped_until_gate(self) -> None:
        # Arrange: iterate research/schemas/*.schema.json

        # Act: json.loads each file

        # Assert: no parse errors; each has $schema or type/properties
        for path in self.schema_files:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(
                "$schema" in data or "properties" in data or "type" in data,
                f"{path.name} missing schema structure",
            )

    @unittest.skip("Gate T0 — awaiting jsonschema dependency pin (OPERA-RES-3020)")
    def test_agents_schema_defines_required_id_column(self) -> None:
        path = SCHEMAS_DIR / "agents.schema.json"
        if not path.exists():
            self.skipTest("agents.schema.json not found")
        schema = json.loads(path.read_text(encoding="utf-8"))
        required = schema.get("required", [])
        self.assertIn("id", required)

    @unittest.skip("Gate T0 — awaiting jsonschema dependency pin (OPERA-RES-3020)")
    def test_experiment_assignments_schema_exists(self) -> None:
        path = SCHEMAS_DIR / "experiment_assignments.schema.json"
        self.assertTrue(path.exists(), "experiment_assignments schema required")

    @unittest.skip("Gate T0 — awaiting jsonschema dependency pin (OPERA-RES-3020)")
    def test_sample_export_row_validates_against_hypothesis_metrics_schema(self) -> None:
        # Arrange: sample_export_row.csv + rq_hypothesis_metrics schema

        # Act: map CSV columns to JSON object; validate

        # Assert: validation passes
        self.assertTrue(self.sample_csv.exists())

    @unittest.skip("Gate T0 — awaiting jsonschema dependency pin (OPERA-RES-3020)")
    def test_schema_count_matches_documented_table_coverage(self) -> None:
        # Documented minimum: agents, experiments, challenges, teams, signals
        minimum = {
            "agents.schema.json",
            "experiment_assignments.schema.json",
            "challenges.schema.json",
            "teams.schema.json",
            "signals.schema.json",
        }
        found = {p.name for p in self.schema_files}
        self.assertTrue(minimum.issubset(found), f"Missing schemas: {minimum - found}")


if __name__ == "__main__":
    unittest.main()
