"""
OPERA-TEST-2015 | integration.byreal_agent_run_flow
"""

from __future__ import annotations

import unittest

import pytest

from tests.integration._harness import IntegrationHarness


@pytest.mark.integration
class TestByrealAgentRunFlow(IntegrationHarness, unittest.TestCase):
    def test_create_run_returns_pending_status(self) -> None:
        agent = self.register_agent("byreal-run-create")
        response = self.client.post(
            "/api/byreal/agent/goals",
            headers={"Authorization": f"Bearer {agent['token']}"},
            json={
                "goal": "Preview a small SOL swap",
                "mode": "paper",
                "product": "dex",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "pending")
        self.assertTrue(body["run_id"])

    def test_completed_run_exposes_result_summary(self) -> None:
        from byreal_agent import _update_run, create_agent_run

        agent = self.create_agent("byreal-run-complete")
        run_id = create_agent_run(agent["id"], "completed integration run", mode="paper", product="dex")
        _update_run(run_id, status="completed", result_json='{"summary":"paper swap preview ok"}')

        response = self.client.get(
            f"/api/byreal/agent/runs/{run_id}",
            headers={"Authorization": f"Bearer {agent['token']}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["result"]["summary"], "paper swap preview ok")

    def test_failed_run_preserves_error_for_debugging(self) -> None:
        from byreal_agent import _update_run, create_agent_run

        agent = self.create_agent("byreal-run-failed")
        run_id = create_agent_run(agent["id"], "failing run", mode="paper", product="dex")
        _update_run(run_id, status="failed", error_message="byreal-cli swap preview failed: insufficient SOL")

        response = self.client.get(
            f"/api/byreal/agent/runs/{run_id}",
            headers={"Authorization": f"Bearer {agent['token']}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "failed")
        self.assertIn("insufficient SOL", body["error_message"])
        self.assertNotIn("private", body["error_message"].lower())

    def test_skill_route_serves_byreal_markdown(self) -> None:
        response = self.client.get("/skill/byreal")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("byreal-cli", response.text)


if __name__ == "__main__":
    unittest.main()
