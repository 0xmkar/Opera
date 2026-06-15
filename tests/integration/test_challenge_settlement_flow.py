"""
OPERA-TEST-2010 | integration.challenge_settlement_flow
==========================================================

Risk tier: P1 — incorrect settlement affects challenge prizes and reputation.

Flow under test:
  1. Create challenge (challenges.py)
  2. Agents join teams and execute trades
  3. settle_challenge computes final ranks
  4. export_challenge_tables produces research-ready CSV

Owner: Community / Challenges
Gate: T1 (integration shard)

Preconditions:
  - Fixture: tests/fixtures/challenges/team_submission_payload.json
  - Challenge window spanning frozen date range

Related: service/server/tests/test_challenges.py
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
class TestChallengeSettlementFlow(unittest.TestCase):
    """
    OPERA-TEST-2010-A | Create → trade → settle → export pipeline.

    Validates that settlement is idempotent and export tables match
    settled leaderboard state (no drift between API and research export).
    """

    @classmethod
    def setUpClass(cls) -> None:
        path = FIXTURES_DIR / "challenges" / "team_submission_payload.json"
        cls.submission_fixture = json.loads(path.read_text(encoding="utf-8"))

    @unittest.skip("Gate T1 — awaiting staging fixture parity (OPERA-REL-2.4)")
    def test_full_challenge_lifecycle_produces_settled_leaderboard(self) -> None:
        # Arrange: create challenge, 2 teams, seed trades with known PnL

        # Act: settle_challenge(challenge_id)

        # Assert: leaderboard ordered by team PnL; status=settled
        pass

    @unittest.skip("Gate T1 — awaiting staging fixture parity (OPERA-REL-2.4)")
    def test_team_submission_accepted_within_vote_window(self) -> None:
        # Arrange: submission_fixture payload, team membership verified

        # Act: POST team submission

        # Assert: submission visible in get_challenge_team_submissions
        pass

    @unittest.skip("Gate T1 — awaiting staging fixture parity (OPERA-REL-2.4)")
    def test_settle_due_challenges_picks_expired_only(self) -> None:
        # Arrange: challenge A ended yesterday, challenge B ends tomorrow

        # Act: settle_due_challenges()

        # Assert: only A settled; B remains active
        pass

    @unittest.skip("Gate T1 — awaiting staging fixture parity (OPERA-REL-2.4)")
    def test_export_tables_match_settled_leaderboard(self) -> None:
        # Arrange: settled challenge with known ranks

        # Act: export_challenge_tables(challenge_id)

        # Assert: CSV row count and ranks match API leaderboard
        pass


if __name__ == "__main__":
    unittest.main()
