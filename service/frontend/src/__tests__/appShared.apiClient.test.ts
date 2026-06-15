/**
 * OPERA-FE-TEST-0125 | appShared API client and auth helpers
 * =============================================================
 *
 * Scope: hasPermission, isVerifiedAgent, API_BASE, fetch error handling
 * patterns used across all pages.
 *
 * Risk tier: P1 — shared helpers affect every authenticated request.
 * Owner: Web Experience
 * Gate: T1 (frontend shard)
 *
 * Not testing React components here — pure function contract only.
 */

import { describe, it } from './setup'

describe.skip('appShared API client', () => {
  it.skip('hasPermission returns true only when permission flag set', () => {
    // Arrange: agent from fixtures/agent_me_response.json
    // Assert: hasPermission(agent, 'research_exports') === true
    // Assert: hasPermission(agent, 'experiment_admin') === false
  })

  it.skip('isVerifiedAgent accepts identity_status verified', () => {
    // Arrange: { identity_status: 'verified', is_verified: false }
    // Assert: isVerifiedAgent(record) === true
  })

  it.skip('API_BASE defaults to /api for same-origin deployment', () => {
    // Assert: API_BASE === '/api'
  })

  it.skip('fetch wrapper surfaces 401 as session expired message', () => {
    // Arrange: mock fetch 401
    // Act: authenticated GET helper
    // Assert: throws or returns error with 'session' keyword
  })

  it.skip('fetch wrapper retries once on 503 with backoff', () => {
    // Arrange: first 503, second 200
    // Assert: fetch called twice; final data returned
  })

  it.skip('AgentName renders verified badge with aria-label', () => {
    // Arrange: <AgentName name="Test" verified={true} />
    // Assert: aria-label="Verified agent" present
  })
})
