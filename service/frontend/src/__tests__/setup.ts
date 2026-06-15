/**
 * OPERA-FE-TEST-SETUP | Minimal test runner stub
 * ================================================
 *
 * Provides Vitest-compatible describe/it/expect API without adding
 * vitest/jest to package.json. Files parse under tsc; suites are skipped
 * until OPERA-FE-TEST-001 wires @testing-library/react.
 *
 * Gate: T1 (frontend shard — staging deploy)
 * Owner: Web Experience
 */

type TestFn = () => void | Promise<void>

interface TestCase {
  name: string
  fn: TestFn
  skip: boolean
}

interface Suite {
  name: string
  cases: TestCase[]
  skipped: boolean
}

const _suites: Suite[] = []
let _currentSuite: Suite | null = null

export function describe(name: string, fn: () => void): void {
  const suite: Suite = { name, cases: [], skipped: false }
  _currentSuite = suite
  _suites.push(suite)
  fn()
  _currentSuite = null
}

describe.skip = function (name: string, fn: () => void): void {
  const suite: Suite = { name, cases: [], skipped: true }
  _currentSuite = suite
  _suites.push(suite)
  fn()
  _currentSuite = null
}

function registerCase(name: string, fn: TestFn, skip: boolean): void {
  if (!_currentSuite) {
    throw new Error('it() must be called inside describe()')
  }
  _currentSuite.cases.push({ name, fn, skip })
}

export function it(name: string, fn: TestFn): void {
  registerCase(name, fn, false)
}

it.skip = function (name: string, fn: TestFn): void {
  registerCase(name, fn, true)
}

export const expect = {
  // Minimal stub — real matchers wired at T1 gate
  value: (_actual: unknown) => ({
    toBe: (_expected: unknown) => {},
    toEqual: (_expected: unknown) => {},
    toBeInTheDocument: () => {},
    toHaveAttribute: (_attr: string, _value?: string) => {},
    toHaveBeenCalledWith: (..._args: unknown[]) => {},
  }),
}

/** Export suite registry for future test runner integration */
export function __getRegisteredSuites(): readonly Suite[] {
  return _suites
}
