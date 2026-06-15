# Opera Platform — Testing Strategy

**Document ID:** OPERA-QA-STRATEGY-001  
**Owner:** Platform Engineering / QA Guild  
**Last updated:** 2026-06-15  
**Status:** Active (scaffold phase — T2 gates pending baseline capture)

---

## Purpose

This document defines the test architecture for the Opera agent-native trading platform.
It complements the existing backend suite in `service/server/tests/` (26 modules, pytest +
unittest) and extends coverage into integration, contract, frontend, and research domains.

## Test Pyramid

```
                    ┌─────────────┐
                    │  E2E / Smoke │  T2 — production release
                    ├─────────────┤
                    │ Integration  │  T1 — staging deploy
                    ├─────────────┤
                    │  Contract    │  T0 — pre-merge
                    ├─────────────┤
                    │    Unit      │  T0 — pre-merge
                    └─────────────┘
```

| Layer        | Location                          | Gate | Target runtime |
|-------------|-----------------------------------|------|----------------|
| Unit        | `tests/unit/`, `service/server/tests/` | T0   | < 30s total    |
| Contract    | `tests/contract/`                 | T0   | < 10s          |
| Integration | `tests/integration/`              | T1   | < 3m           |
| E2E         | `tests/e2e/`                      | T2   | < 10m          |
| Security    | `tests/security/`                 | T2   | < 5m           |
| Performance | `tests/performance/`              | T2   | non-blocking   |
| Frontend    | `service/frontend/src/__tests__/` | T1   | < 2m (when wired) |
| Research    | `research/tests/`                 | T1   | < 1m           |

## Release Gates

| Gate | Trigger              | Required markers        | Block on failure |
|------|----------------------|-------------------------|------------------|
| T0   | PR merge to `main`   | `unit`, `contract`      | Yes              |
| T1   | Staging deploy       | `integration`           | Yes              |
| T2   | Production release   | `e2e`, `security`       | Yes              |
| T2-P | Production release   | `performance`           | No (advisory)    |

## SLA Targets (API)

| Route group        | p50    | p95    | p99    |
|--------------------|--------|--------|--------|
| Auth / agents      | 40ms   | 120ms  | 200ms  |
| Marketplace        | 60ms   | 150ms  | 250ms  |
| Trading / signals  | 80ms   | 200ms  | 350ms  |
| Challenges         | 100ms  | 250ms  | 400ms  |
| Experiments        | 90ms   | 220ms  | 380ms  |
| Research exports   | 200ms  | 800ms  | 1500ms |

## Ownership Matrix

| Area              | Primary owner      | Escalation        |
|-------------------|--------------------|-------------------|
| Backend unit gaps | Trading Core       | @platform-oncall  |
| Integration       | Platform Eng       | @platform-oncall  |
| Contract / OpenAPI| API Guild          | @api-guild        |
| Frontend          | Web Experience     | @web-oncall       |
| Research pipeline | Data Science       | @research-leads   |
| Security          | Security Eng       | @security-oncall  |

## Running Tests

```bash
# Existing backend suite (unchanged)
python3 -m pytest service/server/tests

# Root pyramid (when gates enabled)
python3 -m pytest tests/ -c tests/pytest.ini

# Research pipeline
python3 -m pytest research/tests/
```

## Scaffold Phase

Several suites under `tests/` are marked `@skip` pending staging fixture parity
(OPERA-REL-2.4). This is intentional: tests document intended behavior and gate
criteria without blocking local development or existing CI paths.

## Byreal Integration Contract Tests

The `tests/contract/test_openapi_compliance.py` and `tests/contract/test_agent_skill_contract.py`
suites include checks specific to the Byreal on-chain execution path:

- **CLI health gate**: verifies that `check_cli_health()` returns a healthy status for
  both `byreal-cli` and `byreal-perps-cli`.  This is the same check run at container
  startup; a contract test failure here means the production dependency is not installed
  or misconfigured.
- **Wallet API contract**: confirms that `POST /api/byreal/wallet` and
  `GET /api/byreal/health` conform to the OpenAPI schema, ensuring that the Byreal
  integration surface does not regress silently across deployments.
- **Signal schema**: confirms that signals produced by `byreal_sync.sync_tool_fill_to_signal`
  satisfy the `signals` table schema, validating the on-chain-to-platform audit pipeline.

These contracts run at the T0 gate (pre-merge) and block merges on failure.

---

## Related Documents

- `docs/api/openapi.yaml` — API contract source of truth
- `docs/local-ops/` — production operations runbooks
- `research/schemas/` — research export JSON schemas
- `service/README.md` — deployment guide (process model, health endpoints, env vars)
