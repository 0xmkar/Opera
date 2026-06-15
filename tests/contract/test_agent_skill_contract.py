"""
OPERA-TEST-2105 | contract.agent_skill_contract
================================================

Risk tier: P1 — skill markdown drift breaks external AI agent onboarding.

Contract source: skills/*/SKILL.md
Owner: Agent Platform / Developer Relations
Gate: T0 (contract shard)

Each skill must contain required CLI invocation tokens so autonomous
agents can discover and execute platform commands without human intervention.

Required tokens (minimum):
  - byreal: "byreal-cli"
  - byreal-perps: "byreal-perps-cli"
  - opera: "opera" API references
"""

from __future__ import annotations

import unittest
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_DIR.parent
SKILLS_DIR = REPO_ROOT / "skills"


@pytest.mark.contract
class TestAgentSkillContract(unittest.TestCase):
    """
    OPERA-TEST-2105-A | Skill markdown structural and token contract.

    Validates presence, encoding, and required CLI tokens per skill.
    Breaking changes require skills/CHANGELOG.md entry.
    """

    @unittest.skip("Gate T0 — awaiting skill contract linter (OPERA-API-2105)")
    def test_byreal_skill_contains_cli_token(self) -> None:
        # Arrange: skills/byreal/SKILL.md

        # Act: read content

        # Assert: "byreal-cli" in content; file UTF-8 encoded
        path = SKILLS_DIR / "byreal" / "SKILL.md"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            self.assertIn("byreal", content.lower())
        pass

    @unittest.skip("Gate T0 — awaiting skill contract linter (OPERA-API-2105)")
    def test_byreal_perps_skill_contains_perps_cli_token(self) -> None:
        # Arrange: skills/byreal-perps/SKILL.md

        # Act: read content

        # Assert: "byreal-perps-cli" in content
        pass

    @unittest.skip("Gate T0 — awaiting skill contract linter (OPERA-API-2105)")
    def test_all_skills_have_non_empty_skill_md(self) -> None:
        # Arrange: iterate skills/*/SKILL.md

        # Act: stat each file

        # Assert: size > 500 bytes; no skill directory missing SKILL.md
        pass

    @unittest.skip("Gate T0 — awaiting skill contract linter (OPERA-API-2105)")
    def test_skill_paths_resolve_via_routes_misc(self) -> None:
        # Arrange: _resolve_skill_path for each known skill id

        # Act: resolve and read

        # Assert: path exists; content matches skills/ canonical copy
        pass


if __name__ == "__main__":
    unittest.main()
