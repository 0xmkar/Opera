"""
OPERA-TEST-2001 | integration.trading_signal_pipeline
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pytest

from tests.integration._harness import IntegrationHarness


@pytest.mark.integration
class TestTradingSignalPipeline(IntegrationHarness, unittest.TestCase):
    def test_long_signal_opens_position_and_updates_leaderboard(self) -> None:
        agent = self.create_agent("signal-pipeline-long")
        with patch("routes_signals.is_market_open", return_value=True), \
             patch("price_fetcher.get_price_from_market", return_value=50000.0):
            trade = self.client.post(
                "/api/signals/realtime",
                headers={"Authorization": f"Bearer {agent['token']}"},
                json={
                    "market": "crypto",
                    "symbol": "BTC",
                    "action": "buy",
                    "quantity": 0.1,
                    "price": 1,
                    "content": "Integration long BTC",
                    "executed_at": "2026-06-15T12:00:00Z",
                },
            )
        self.assertEqual(trade.status_code, 200, trade.text)

        leaderboard = self.client.get("/api/profit/history?limit=10&offset=0&include_history=false")
        self.assertEqual(leaderboard.status_code, 200, leaderboard.text)
        names = [row["name"] for row in leaderboard.json()["top_agents"]]
        self.assertIn("signal-pipeline-long", names)

        conn = self.database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT quantity FROM positions WHERE agent_id = ? AND symbol = 'BTC'",
            (agent["id"],),
        )
        position = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(position)
        self.assertGreater(float(position["quantity"]), 0)

    def test_close_signal_zeros_position_quantity(self) -> None:
        agent = self.create_agent("signal-pipeline-close")
        headers = {"Authorization": f"Bearer {agent['token']}"}
        payload_base = {
            "market": "crypto",
            "symbol": "BTC",
            "quantity": 0.1,
            "price": 1,
            "executed_at": "2026-06-15T12:00:00Z",
        }
        with patch("routes_signals.is_market_open", return_value=True), \
             patch("price_fetcher.get_price_from_market", return_value=50000.0):
            open_trade = self.client.post(
                "/api/signals/realtime",
                headers=headers,
                json={**payload_base, "action": "buy", "content": "open"},
            )
            self.assertEqual(open_trade.status_code, 200, open_trade.text)
            close_trade = self.client.post(
                "/api/signals/realtime",
                headers=headers,
                json={**payload_base, "action": "sell", "content": "close"},
            )
        self.assertEqual(close_trade.status_code, 200, close_trade.text)

        conn = self.database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS count FROM positions WHERE agent_id = ? AND symbol = 'BTC'",
            (agent["id"],),
        )
        position_count = int(cursor.fetchone()["count"])
        conn.close()
        self.assertEqual(position_count, 0)

    def test_invalid_signal_rejected_before_position_mutation(self) -> None:
        agent = self.create_agent("signal-pipeline-invalid")
        with patch("routes_signals.is_market_open", return_value=True), \
             patch("price_fetcher.get_price_from_market", return_value=50000.0):
            response = self.client.post(
                "/api/signals/realtime",
                headers={"Authorization": f"Bearer {agent['token']}"},
                json={
                    "market": "crypto",
                    "symbol": "BTC",
                    "action": "buy",
                    "quantity": -0.1,
                    "price": 1,
                    "content": "invalid quantity",
                    "executed_at": "2026-06-15T12:00:00Z",
                },
            )
        self.assertGreaterEqual(response.status_code, 400)

        conn = self.database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM positions WHERE agent_id = ?", (agent["id"],))
        position_count = int(cursor.fetchone()["count"])
        conn.close()
        self.assertEqual(position_count, 0)

    def test_realtime_price_guard_blocks_stale_mark(self) -> None:
        agent = self.create_agent("signal-pipeline-guard")
        with patch("routes_signals.is_market_open", return_value=True), \
             patch("price_fetcher.get_price_from_market", return_value=None):
            response = self.client.post(
                "/api/signals/realtime",
                headers={"Authorization": f"Bearer {agent['token']}"},
                json={
                    "market": "us-stock",
                    "symbol": "TSLA",
                    "action": "buy",
                    "quantity": 1,
                    "price": 10,
                    "content": "stale mark attempt",
                    "executed_at": "2026-06-15T12:00:00Z",
                },
            )
        self.assertEqual(response.status_code, 400, response.text)

        conn = self.database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM signals WHERE agent_id = ?", (agent["id"],))
        signal_count = int(cursor.fetchone()["count"])
        conn.close()
        self.assertEqual(signal_count, 0)


if __name__ == "__main__":
    unittest.main()
