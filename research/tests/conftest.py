"""
OPERA-RES-TEST-SETUP | Research pipeline shared fixtures
==========================================================

Owner: Data Science / Research Platform
Gate: T1 (research shard)

Bootstrap path for research script imports without mutating production env.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RESEARCH_TESTS_DIR = Path(__file__).resolve().parent
RESEARCH_ROOT = RESEARCH_TESTS_DIR.parent
RESEARCH_SCRIPTS = RESEARCH_ROOT / "scripts"
REPO_ROOT = RESEARCH_ROOT.parent
SERVER_DIR = REPO_ROOT / "service" / "server"
FIXTURES_DIR = RESEARCH_TESTS_DIR / "fixtures"
SCHEMAS_DIR = RESEARCH_ROOT / "schemas"


def _bootstrap_research_scripts() -> None:
    scripts_str = str(RESEARCH_SCRIPTS)
    if scripts_str not in sys.path:
        sys.path.insert(0, scripts_str)


def _bootstrap_server() -> None:
    server_str = str(SERVER_DIR)
    if server_str not in sys.path:
        sys.path.insert(0, server_str)


@pytest.fixture(scope="session")
def research_fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def research_schemas_dir() -> Path:
    return SCHEMAS_DIR


@pytest.fixture
def sample_export_csv(research_fixtures_dir: Path) -> Path:
    """Canonical single-row export for schema validation tests."""
    return research_fixtures_dir / "sample_export_row.csv"


@pytest.fixture
def research_script_path() -> Path:
    """Path to research/scripts — call _bootstrap_research_scripts() in test body."""
    return RESEARCH_SCRIPTS
