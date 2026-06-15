/**
 * OPERA-FE-TEST-0105 | ChallengePage component contract
 * =======================================================
 *
 * User story: As an agent, I can browse active challenges, view my
 * portfolio, and join team-based competitions.
 *
 * Risk tier: P1 — challenge UI is primary community engagement surface.
 * Owner: Web Experience / Community
 * Gate: T1 (frontend shard)
 *
 * Accessibility checklist:
 *   - Leaderboard table has <caption> or aria-label
 *   - Sort controls are keyboard navigable
 *   - PnL color indicators have non-color redundant cues
 *
 * States: loading challenges, empty state, joined vs not joined, settled
 *
 * Mock API contract:
 *   GET /api/challenges
 *   GET /api/challenges/:id/portfolio
 *   POST /api/challenges/:id/join
 */

import { describe, it } from './setup'

describe.skip('ChallengePage', () => {
  it.skip('renders challenge list with status badges', () => {
    // Arrange: mock GET /api/challenges with active + settled
    // Assert: active challenges show "Active"; settled show "Settled"
  })

  it.skip('shows empty state when no challenges match filter', () => {
    // Arrange: empty challenges array
    // Assert: empty state copy visible; no table rendered
  })

  it.skip('join button disabled when challenge window closed', () => {
    // Arrange: challenge with ends_at in the past
    // Assert: join CTA disabled with explanatory tooltip
  })

  it.skip('portfolio panel reflects agent positions after join', () => {
    // Arrange: joined challenge with seed portfolio
    // Assert: symbol, quantity, PnL columns populated
  })

  it.skip('team leaderboard updates after team trade signal', () => {
    // Arrange: team challenge with 2 teams
    // Act: simulate WebSocket or poll refresh
    // Assert: rank order matches API response
  })
})
