"""Shared helpers for root integration tests."""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

TESTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_DIR.parent
SERVER_DIR = REPO_ROOT / "service" / "server"


def bootstrap_server_path() -> None:
    server_str = str(SERVER_DIR)
    if server_str not in sys.path:
        sys.path.insert(0, server_str)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class IntegrationHarness:
    """Ephemeral DB for unittest-style integration suites. TestClient is lazy."""

    def setUp(self) -> None:
        bootstrap_server_path()
        import database

        self._tmp = tempfile.TemporaryDirectory()
        database.DATABASE_URL = ""
        database._SQLITE_DB_PATH = os.path.join(self._tmp.name, "integration.db")
        os.environ["DATABASE_URL"] = ""
        os.environ["DB_PATH"] = database._SQLITE_DB_PATH
        os.environ["ALLOW_SQLITE"] = "true"
        database.init_database()
        self.database = database
        self._client: TestClient | None = None

    @property
    def client(self) -> TestClient:
        if self._client is None:
            from routes import create_app

            self._client = TestClient(create_app())
        return self._client

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def create_agent(self, name: str, *, token: str | None = None, role: str = "agent") -> dict[str, Any]:
        from routes_shared import utc_now_iso_z

        token = token or f"token-{name}"
        now = utc_now_iso_z()
        conn = self.database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO agents (name, token, points, cash, role, created_at, updated_at)
            VALUES (?, ?, 0, 100000.0, ?, ?, ?)
            """,
            (name, token, role, now, now),
        )
        agent_id = int(cursor.lastrowid)
        conn.commit()
        conn.close()
        return {"id": agent_id, "name": name, "token": token}

    def register_agent(self, name: str, password: str = "password123") -> dict[str, Any]:
        response = self.client.post(
            "/api/claw/agents/selfRegister",
            json={"name": name, "password": password},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        return {"id": body["agent_id"], "name": name, "token": body["token"]}
