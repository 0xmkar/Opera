/**
 * OPERA-FE-TEST-0120 | AppPages routing and route guards
 * ========================================================
 *
 * User story: As any user, I navigate between platform sections via
 * client-side routing with correct auth and permission guards.
 *
 * Risk tier: P1 — broken routing exposes admin pages or breaks deep links.
 * Owner: Web Experience
 * Gate: T1 (frontend shard)
 *
 * Scope: AppPages.tsx route table (~2877 LOC) — guard logic only,
 * not full page render snapshots (deferred to visual regression OPERA-FE-0200).
 *
 * Routes under test (sample):
 *   /challenges, /team-missions, /byreal, /experiments/admin,
 *   /research/exports, /community/*
 *
 * Guard matrix:
 *   - Unauthenticated → login redirect or public view
 *   - Authenticated → feature pages
 *   - Permission-gated → hasPermission() check
 */

import { describe, it } from './setup'

describe.skip('AppPages routing', () => {
  it.skip('navigates to /byreal when authenticated', () => {
    // Arrange: MemoryRouter initialEntries=['/byreal'], token set
    // Assert: ByrealAgentPage mounted
  })

  it.skip('blocks /experiments/admin without experiment_admin permission', () => {
    // Arrange: token without permission
    // Assert: redirect to home or 403 view
  })

  it.skip('preserves query params on challenge deep link', () => {
    // Arrange: /challenges?id=42
    // Assert: ChallengePage receives challengeId=42
  })

  it.skip('lazy-loaded community routes do not block initial paint', () => {
    // Arrange: navigate to /community/*
    // Assert: Suspense fallback shown then resolved
  })

  it.skip('unknown route renders not-found without crashing', () => {
    // Arrange: /nonexistent-path
    // Assert: 404 component; no uncaught router error
  })
})
