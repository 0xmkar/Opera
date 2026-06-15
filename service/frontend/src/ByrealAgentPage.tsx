import { useEffect, useRef, useState, type FormEvent } from 'react'

import { API_BASE } from './appShared'

type ByrealAgentPageProps = {
  token?: string | null
}

type RunRecord = {
  id: number
  goal: string
  mode: string
  product: string
  status: string
  error_message?: string
  transcript?: Array<Record<string, unknown>>
  result?: { summary?: string; signal_ids?: number[] }
}

export function ByrealAgentPage({ token }: ByrealAgentPageProps) {
  const [goal, setGoal] = useState('Preview a 0.01 SOL to USDC swap on Byreal')
  const [mode, setMode] = useState<'paper' | 'real'>('paper')
  const [product, setProduct] = useState<'auto' | 'dex' | 'perps'>('dex')
  const [wait, setWait] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [runs, setRuns] = useState<RunRecord[]>([])
  const [activeRun, setActiveRun] = useState<RunRecord | null>(null)
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  const [walletChain, setWalletChain] = useState('solana')
  const [walletSecret, setWalletSecret] = useState('')
  const [walletPubkey, setWalletPubkey] = useState('')
  const [walletStatus, setWalletStatus] = useState<Record<string, unknown> | null>(null)
  const pollRef = useRef<number | null>(null)

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}

  const loadRuns = async () => {
    if (!token) return
    const resp = await fetch(`${API_BASE}/byreal/agent/runs?limit=10`, { headers: authHeaders })
    if (!resp.ok) return
    const data = await resp.json()
    setRuns(data.runs || [])
  }

  const loadHealth = async () => {
    const resp = await fetch(`${API_BASE}/byreal/health`)
    if (resp.ok) setHealth(await resp.json())
  }

  const loadWallet = async () => {
    if (!token) return
    const resp = await fetch(`${API_BASE}/byreal/wallet`, { headers: authHeaders })
    if (resp.ok) setWalletStatus(await resp.json())
  }

  const pollRun = (runId: number) => {
    if (pollRef.current) window.clearInterval(pollRef.current)
    pollRef.current = window.setInterval(async () => {
      const resp = await fetch(`${API_BASE}/byreal/agent/runs/${runId}`, { headers: authHeaders })
      if (!resp.ok) return
      const run = await resp.json()
      setActiveRun(run)
      if (run.status === 'completed' || run.status === 'failed') {
        if (pollRef.current) window.clearInterval(pollRef.current)
        loadRuns()
      }
    }, 1500)
  }

  useEffect(() => {
    loadHealth()
    loadRuns()
    loadWallet()
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
    }
  }, [token])

  const submitGoal = async (event: FormEvent) => {
    event.preventDefault()
    if (!token) {
      setError('Login required')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const resp = await fetch(`${API_BASE}/byreal/agent/goals`, {
        method: 'POST',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, mode, product, wait }),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || 'Failed to submit goal')
      if (data.run) {
        setActiveRun(data.run)
      } else if (data.run_id) {
        pollRun(data.run_id)
      }
      loadRuns()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setBusy(false)
    }
  }

  const connectWallet = async () => {
    if (!token || !walletSecret.trim()) return
    setBusy(true)
    setError(null)
    try {
      const resp = await fetch(`${API_BASE}/byreal/wallet`, {
        method: 'POST',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chain: walletChain,
          secret: walletSecret.trim(),
          pubkey: walletPubkey.trim() || undefined,
        }),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || 'Wallet connect failed')
      setWalletSecret('')
      setWalletStatus(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Wallet connect failed')
    } finally {
      setBusy(false)
    }
  }

  const disconnectWallet = async () => {
    if (!token) return
    await fetch(`${API_BASE}/byreal/wallet?chain=${walletChain}`, {
      method: 'DELETE',
      headers: authHeaders,
    })
    loadWallet()
  }

  if (!token) {
    return <div className="card">Please log in to use the Byreal agent.</div>
  }

  return (
    <div className="card" style={{ display: 'grid', gap: 20 }}>
      <div>
        <h2 style={{ margin: 0 }}>Byreal Agent</h2>
        <p style={{ opacity: 0.8 }}>
          Platform-managed LLM agent with Byreal DEX and perps tools. Paper mode is default; real mode
          requires a dedicated wallet (hackathon-grade storage).
        </p>
        {health && (
          <p style={{ fontSize: 13, opacity: 0.7 }}>
            CLI health: dex={String((health.dex as any)?.installed)} perps={String((health.perps as any)?.installed)}
          </p>
        )}
      </div>

      <form onSubmit={submitGoal} style={{ display: 'grid', gap: 12 }}>
        <label>
          Goal
          <textarea value={goal} onChange={(e) => setGoal(e.target.value)} rows={3} style={{ width: '100%' }} />
        </label>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <label>
            Mode
            <select value={mode} onChange={(e) => setMode(e.target.value as 'paper' | 'real')}>
              <option value="paper">Paper</option>
              <option value="real">Real</option>
            </select>
          </label>
          <label>
            Product
            <select value={product} onChange={(e) => setProduct(e.target.value as 'auto' | 'dex' | 'perps')}>
              <option value="auto">Auto</option>
              <option value="dex">DEX</option>
              <option value="perps">Perps</option>
            </select>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={wait} onChange={(e) => setWait(e.target.checked)} />
            Wait for completion
          </label>
        </div>
        <button type="submit" disabled={busy}>{busy ? 'Running…' : 'Submit goal'}</button>
        {error && <div style={{ color: 'var(--danger, #f66)' }}>{error}</div>}
      </form>

      <div style={{ borderTop: '1px solid var(--border, #333)', paddingTop: 16 }}>
        <h3>Wallet (real mode)</h3>
        <p style={{ fontSize: 13, opacity: 0.75 }}>Use a dedicated low-balance wallet only.</p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
          <select value={walletChain} onChange={(e) => setWalletChain(e.target.value)}>
            <option value="solana">Solana (DEX)</option>
            <option value="hyperliquid">Hyperliquid (perps)</option>
          </select>
          <input
            type="password"
            placeholder="Private key (base58)"
            value={walletSecret}
            onChange={(e) => setWalletSecret(e.target.value)}
            style={{ flex: 1, minWidth: 200 }}
          />
          <input
            placeholder="Public address (optional)"
            value={walletPubkey}
            onChange={(e) => setWalletPubkey(e.target.value)}
            style={{ flex: 1, minWidth: 160 }}
          />
          <button type="button" onClick={connectWallet} disabled={busy}>Connect</button>
          <button type="button" onClick={disconnectWallet} disabled={busy}>Disconnect</button>
        </div>
        {walletStatus && <pre style={{ fontSize: 12 }}>{JSON.stringify(walletStatus, null, 2)}</pre>}
      </div>

      {activeRun && (
        <div>
          <h3>Active run #{activeRun.id}</h3>
          <p>Status: {activeRun.status}</p>
          {activeRun.result?.summary && <p>{activeRun.result.summary}</p>}
          {activeRun.error_message && <p style={{ color: '#f66' }}>{activeRun.error_message}</p>}
          <pre style={{ maxHeight: 320, overflow: 'auto', fontSize: 12 }}>
            {JSON.stringify(activeRun.transcript || [], null, 2)}
          </pre>
        </div>
      )}

      <div>
        <h3>Recent runs</h3>
        <ul>
          {runs.map((run) => (
            <li key={run.id}>
              <button type="button" onClick={() => setActiveRun(run)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0 }}>
                #{run.id} [{run.status}] {run.goal.slice(0, 80)}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
