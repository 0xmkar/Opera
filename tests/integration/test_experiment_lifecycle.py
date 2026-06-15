"""
OPERA-TEST-2005 | integration.experiment_lifecycle
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import pytest

from tests.integration._harness import IntegrationHarness

TESTS_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = TESTS_DIR / "fixtures"


@pytest.mark.integration
class TestExperimentLifecycle(IntegrationHarness, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = FIXTURES_DIR / "experiment_scenarios" / "ab_assignment_cohort.json"
        cls.cohort_fixture = json.loads(path.read_text(encoding="utf-8"))

    def test_create_experiment_and_assign_agents_to_cohorts(self) -> None:
        from experiments import assign_unit_to_experiment, create_experiment, get_experiment_assignments

        meta = self.cohort_fixture
        create_experiment({
            "experiment_key": meta["experiment_id"],
            "title": meta["name"],
            "variants_json": [
                {"key": "control", "weight": 1},
                {"key": "treatment", "weight": 1},
            ],
        })
        agents = [self.create_agent(f"cohort-agent-{idx}") for idx in range(6)]

        for agent in agents:
            assign_unit_to_experiment(meta["experiment_id"], "agent", agent["id"])

        assignments = get_experiment_assignments(meta["experiment_id"])
        self.assertEqual(len(assignments["assignments"]), len(agents))
        variants = {row["variant_key"] for row in assignments["assignments"]}
        self.assertTrue({"control", "treatment"}.issubset(variants))

    def test_experiment_event_recorded_with_correct_cohort_tag(self) -> None:
        from experiment_events import record_event
        from experiments import assign_unit_to_experiment, create_experiment

        experiment_key = "event-cohort-tag"
        create_experiment({
            "experiment_key": experiment_key,
            "title": "Cohort tag events",
            "variants_json": [{"key": "control", "weight": 1}, {"key": "treatment", "weight": 1}],
        })
        treatment_agent = self.create_agent("treatment-agent-201")
        assignment = assign_unit_to_experiment(experiment_key, "agent", treatment_agent["id"])
        self.assertEqual(assignment["variant_key"], "treatment")

        record_event(
            "notification_click_through",
            actor_agent_id=treatment_agent["id"],
            experiment_key=experiment_key,
            variant_key=assignment["variant_key"],
            metadata={"surface": "integration-test"},
        )

        conn = self.database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT variant_key, event_type
            FROM experiment_events
            WHERE experiment_key = ? AND actor_agent_id = ?
            """,
            (experiment_key, treatment_agent["id"]),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()

        self.assertTrue(any(row["event_type"] == "notification_click_through" for row in rows))
        self.assertTrue(all(row["variant_key"] == "treatment" for row in rows))

    def test_notification_created_on_assignment(self) -> None:
        from experiments import assign_unit_to_experiment, create_experiment

        experiment_key = "assignment-notify"
        create_experiment({
            "experiment_key": experiment_key,
            "title": "Assignment notification",
            "variants_json": [{"key": "control", "weight": 1}, {"key": "treatment", "weight": 1}],
        })
        agent = self.create_agent("notify-agent-102")
        assign_unit_to_experiment(experiment_key, "agent", agent["id"])

        conn = self.database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT event_type, experiment_key, variant_key
            FROM experiment_events
            WHERE actor_agent_id = ? AND experiment_key = ?
            """,
            (agent["id"], experiment_key),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()

        self.assertTrue(any(row["event_type"] == "experiment_assigned" for row in rows))

    def test_experiment_pause_stops_new_assignments(self) -> None:
        from experiments import ExperimentError, assign_unit_to_experiment, create_experiment, update_experiment_status

        experiment_key = "pause-guard"
        create_experiment({
            "experiment_key": experiment_key,
            "title": "Pause guard",
            "variants_json": [{"key": "control", "weight": 1}, {"key": "treatment", "weight": 1}],
        })
        first_agent = self.create_agent("pause-agent-1")
        assign_unit_to_experiment(experiment_key, "agent", first_agent["id"])

        update_experiment_status(experiment_key, "paused")
        second_agent = self.create_agent("pause-agent-2")

        with self.assertRaises(ExperimentError) as ctx:
            assign_unit_to_experiment(experiment_key, "agent", second_agent["id"])
        self.assertIn("not active", str(ctx.exception).lower())

        conn = self.database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS count FROM experiment_assignments WHERE experiment_key = ?",
            (experiment_key,),
        )
        count = int(cursor.fetchone()["count"])
        conn.close()
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
