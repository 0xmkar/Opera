/**
 * OPERA-FE-TEST-0115 | ExperimentAdminPage component contract
 * ==============================================================
 *
 * User story: As an experiment admin, I can create A/B tests, assign
 * cohorts, and monitor primary/secondary metrics in real time.
 *
 * Risk tier: P1 — incorrect admin UI can misconfigure live experiments.
 * Owner: Web Experience / Data Platform
 * Gate: T1 (frontend shard)
 *
 * Accessibility checklist:
 *   - Cohort allocation inputs have min/max validation messages
 *   - Data tables support keyboard row selection
 *   - Destructive actions (pause/delete) require confirmation modal
 *
 * States: no permission, draft experiment, active, paused, concluded
 *
 * Mock API contract:
 *   GET  /api/experiments
 *   POST /api/experiments
 *   PATCH /api/experiments/:id
 *   GET  /api/experiments/:id/metrics
 */

import { describe, it } from './setup'

describe.skip('ExperimentAdminPage', () => {
  it.skip('redirects or hides UI when agent lacks experiment_admin permission', () => {
    // Arrange: agent_me_response without experiment_admin
    // Assert: admin controls not rendered; permission message shown
  })

  it.skip('validates cohort allocation sums to 100 percent', () => {
    // Arrange: control=60, treatment=50
    // Act: submit create form
    // Assert: inline validation error; no POST
  })

  it.skip('renders primary metric chart for active experiment', () => {
    // Arrange: active experiment with metrics time series
    // Assert: recharts container mounted; legend labels match API
  })

  it.skip('pause confirmation modal prevents accidental pause', () => {
    // Arrange: click Pause on active experiment
    // Assert: modal open; confirm required before PATCH
  })

  it.skip('displays unread experiment notices badge', () => {
    // Arrange: 3 unread notices in API response
    // Assert: badge shows "3"; clears on dismiss
  })
})
