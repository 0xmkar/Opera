"""
OPERA-TEST-2100 | contract.openapi_compliance
==============================================

Risk tier: P1 — API drift breaks external agent integrations and SDK codegen.

Contract source: docs/api/openapi.yaml (OpenAPI 3.0.3)
Owner: API Guild
Gate: T0 (contract shard — pre-merge)

Validation scope:
  - All documented paths return declared status codes
  - Request/response schemas match Pydantic models in routes_models.py
  - Breaking changes require OPERA-API-MAJOR version bump

Tooling (planned): schemathesis + custom path inventory diff
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_DIR.parent
OPENAPI_PATH = REPO_ROOT / "docs" / "api" / "openapi.yaml"
SERVER_DIR = REPO_ROOT / "service" / "server"


def _bootstrap() -> None:
    server_str = str(SERVER_DIR)
    if server_str not in sys.path:
        sys.path.insert(0, server_str)


@pytest.mark.contract
class TestOpenAPICompliance(unittest.TestCase):
    """
    OPERA-TEST-2100-A | Live routes vs OpenAPI path inventory.

    Ensures every route registered in FastAPI app appears in openapi.yaml
    and no undocumented public endpoints exist (security audit requirement).
    """

    @unittest.skip("Gate T0 — awaiting schemathesis wiring (OPERA-API-2100)")
    def test_all_fastapi_routes_documented_in_openapi(self) -> None:
        # Arrange: load openapi.yaml paths; introspect FastAPI app routes

        # Act: diff(route_paths, openapi_paths)

        # Assert: symmetric difference is empty for /api/* public routes
        pass

    @unittest.skip("Gate T0 — awaiting schemathesis wiring (OPERA-API-2100)")
    def test_self_register_response_matches_agent_schema(self) -> None:
        # Arrange: POST /api/claw/agents/selfRegister with valid body

        # Act: validate response against openapi components.schemas.Agent

        # Assert: all required fields present; types match
        pass

    @unittest.skip("Gate T0 — awaiting schemathesis wiring (OPERA-API-2100)")
    def test_undocumented_5xx_responses_logged_as_contract_gap(self) -> None:
        # Arrange: trigger internal error on documented endpoint

        # Act: capture response schema

        # Assert: either documented in openapi or flagged in contract report
        pass

    @unittest.skip("Gate T0 — awaiting schemathesis wiring (OPERA-API-2100)")
    def test_openapi_version_matches_package_version(self) -> None:
        # Arrange: parse info.version from openapi.yaml

        # Act: compare to service release tag

        # Assert: major.minor aligned; patch may drift
        assert OPENAPI_PATH.exists(), "Contract source openapi.yaml must exist"
        pass


if __name__ == "__main__":
    unittest.main()
