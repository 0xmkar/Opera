"""
OPERA-TEST-2010 | integration.challenge_settlement_flow
"""

from __future__ import annotations

import csv
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.integration._harness import IntegrationHarness, iso

TESTS_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = TESTS_DIR / "fixtures"


@pytest.mark.integration
class TestChallengeSettlementFlow(IntegrationHarness, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = FIXTURES_DIR / "challenges" / "team_submission_payload.json"
        cls.submission_fixture = json.loads(path.read_text(encoding="utf-8"))

    def _create_active_challenge(self, *, challenge_key: str, creator_id: int):
        from challenges import create_challenge

        now = datetime.now(timezone.utc)
        return create_challenge(
            {
                "challenge_key": challenge_key,
                "title": "Integration BTC sprint",
                "market": "crypto",
                "symbol": "BTC",
                "challenge_type": "multi-agent",
                "scoring_method": "return-only",
                "initial_capital": 1000.0,
                "max_position_pct": 100.0,
                "max_drawdown_pct": 20.0,
                "start_at": iso(now - timedelta(minutes=5)),
                "end_at": iso(now + timedelta(hours=1)),
                "rules_json": {"reward_points": {"1": 100, "2": 25}},
            },
            creator_id,
        )

    def _submit_trade(self, challenge_key: str, agent_id: int, side: str, price: float, quantity: float) -> None:
        from challenges import create_challenge_trade

        with patch("price_fetcher.get_price_from_market", return_value=price):
            create_challenge_trade(
                challenge_key,
                agent_id,
                {
                    "symbol": "BTC",
                    "side": side,
                    "price": price,
                    "quantity": quantity,
                    "executed_at": iso(datetime.now(timezone.utc)),
                },
            )

    def test_full_challenge_lifecycle_produces_settled_leaderboard(self) -> None:
        from challenges import join_challenge, settle_challenge

        creator = self.create_agent("challenge-creator")
        challenge = self._create_active_challenge(challenge_key="integration-settle-full", creator_id=creator["id"])
        agent_a = self.create_agent("challenge-agent-a")
        agent_b = self.create_agent("challenge-agent-b")
        join_challenge(challenge["challenge_key"], agent_a["id"])
        join_challenge(challenge["challenge_key"], agent_b["id"])
        self._submit_trade(challenge["challenge_key"], agent_a["id"], "buy", 100.0, 10.0)
        self._submit_trade(challenge["challenge_key"], agent_a["id"], "sell", 110.0, 10.0)
        self._submit_trade(challenge["challenge_key"], agent_b["id"], "buy", 100.0, 10.0)
        self._submit_trade(challenge["challenge_key"], agent_b["id"], "sell", 105.0, 10.0)

        conn = self.database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE challenges SET end_at = ? WHERE id = ?",
            (iso(datetime.now(timezone.utc) - timedelta(seconds=1)), challenge["id"]),
        )
        conn.commit()
        conn.close()

        result = settle_challenge(challenge["challenge_key"])
        self.assertEqual(result["challenge"]["status"], "settled")
        self.assertEqual(result["leaderboard"][0]["agent_id"], agent_a["id"])
        self.assertEqual(result["leaderboard"][0]["rank"], 1)

    def test_team_submission_accepted_within_vote_window(self) -> None:
        from challenges import (
            create_challenge,
            create_challenge_team,
            create_challenge_team_submission,
            get_challenge_team_submissions,
            join_challenge_team,
        )

        creator = self.create_agent("team-challenge-creator")
        challenge = create_challenge(
            {
                "challenge_key": "integration-team-submit",
                "title": "Team submission sprint",
                "market": "crypto",
                "symbol": "BTC",
                "challenge_type": "multi-agent",
                "mode": "team",
                "scoring_method": "return-only",
                "initial_capital": 1000.0,
                "start_at": iso(datetime.now(timezone.utc) - timedelta(minutes=5)),
                "end_at": iso(datetime.now(timezone.utc) + timedelta(hours=1)),
                "rules_json": {"team_size_max": 3},
            },
            creator["id"],
        )
        submitter = self.create_agent("team-submitter")
        teammate = self.create_agent("team-mate")
        created = create_challenge_team(
            challenge["challenge_key"],
            submitter["id"],
            {"team_key": "team-alpha", "name": "Team Alpha"},
        )
        team_id = created["team"]["id"]
        join_challenge_team(challenge["challenge_key"], team_id, teammate["id"])

        payload = self.submission_fixture
        submission = create_challenge_team_submission(
            challenge["challenge_key"],
            team_id,
            submitter["id"],
            {
                "submission_type": payload["submission_type"],
                "content": payload["content"],
            },
        )
        self.assertIn("submission", submission)

        listed = get_challenge_team_submissions(
            challenge["challenge_key"],
            team_id,
            viewer_agent_id=teammate["id"],
        )
        self.assertEqual(listed["total"], 1)

    def test_settle_due_challenges_picks_expired_only(self) -> None:
        from challenges import create_challenge, join_challenge, settle_due_challenges

        creator = self.create_agent("due-settle-creator")
        now = datetime.now(timezone.utc)
        expired = create_challenge(
            {
                "challenge_key": "integration-expired",
                "title": "Expired",
                "market": "crypto",
                "symbol": "BTC",
                "challenge_type": "multi-agent",
                "scoring_method": "return-only",
                "initial_capital": 1000.0,
                "start_at": iso(now - timedelta(days=2)),
                "end_at": iso(now - timedelta(seconds=1)),
            },
            creator["id"],
        )
        active = self._create_active_challenge(challenge_key="integration-still-active", creator_id=creator["id"])
        agent = self.create_agent("due-settle-agent")
        join_challenge(expired["challenge_key"], agent["id"])
        join_challenge(active["challenge_key"], agent["id"])

        settled = settle_due_challenges()
        settled_keys = {item["challenge"]["challenge_key"] for item in settled}
        self.assertIn(expired["challenge_key"], settled_keys)
        self.assertNotIn(active["challenge_key"], settled_keys)

    def test_export_tables_match_settled_leaderboard(self) -> None:
        from challenges import get_challenge_leaderboard, join_challenge, settle_challenge
        from research_exports import export_challenge_tables

        creator = self.create_agent("export-creator")
        challenge = self._create_active_challenge(challenge_key="integration-export", creator_id=creator["id"])
        winner = self.create_agent("export-winner")
        runner_up = self.create_agent("export-runner-up")
        join_challenge(challenge["challenge_key"], winner["id"])
        join_challenge(challenge["challenge_key"], runner_up["id"])
        self._submit_trade(challenge["challenge_key"], winner["id"], "buy", 100.0, 10.0)
        self._submit_trade(challenge["challenge_key"], winner["id"], "sell", 120.0, 10.0)
        self._submit_trade(challenge["challenge_key"], runner_up["id"], "buy", 100.0, 10.0)
        self._submit_trade(challenge["challenge_key"], runner_up["id"], "sell", 105.0, 10.0)

        conn = self.database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE challenges SET end_at = ? WHERE id = ?",
            (iso(datetime.now(timezone.utc) - timedelta(seconds=1)), challenge["id"]),
        )
        conn.commit()
        conn.close()

        result = settle_challenge(challenge["challenge_key"])
        api_leaderboard = get_challenge_leaderboard(challenge["challenge_key"])
        export_dir = Path(self._tmp.name) / "exports"
        paths = export_challenge_tables(export_dir, challenge_key=challenge["challenge_key"])
        with open(paths["challenge_results.csv"], newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), len(api_leaderboard["leaderboard"]))
        self.assertEqual(int(rows[0]["rank"]), result["leaderboard"][0]["rank"])


if __name__ == "__main__":
    unittest.main()
