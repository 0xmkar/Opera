---
name: byreal-perps
description: Hyperliquid perps via byreal-perps-cli. Scan signals, place orders, sync fills to Opera. Supports MNT (Mantle Network) and all major crypto perps with verifiable on-chain execution records.
---

# Byreal Perps Skill

Use this skill for **Hyperliquid perpetuals** through `byreal-perps-cli`. Read markets and execute perps orders **directly via the CLI** — not through Opera market APIs.

Opera receives **paper or real fill notifications** via `/api/signals/realtime` with `market: "crypto"` (or `byreal` alias).

## Mantle narrative: bridge flow & why MNT on Byreal matters

**Bridge flow:** MNT originates on Mantle Network. Bridged MNT trades on Solana DEX via `byreal-cli`; MNT perpetuals trade on Hyperliquid via `byreal-perps-cli`. Both paths produce on-chain references (tx signature or order ID) that Opera links to signals in `byreal_trade_links`.

```
Mantle L2 (MNT) → bridge → Solana / Hyperliquid markets → byreal-perps-cli → Opera signal feed
```

**Why this matters for Mantle:** MNT perps on Byreal give Mantle token holders and builders leveraged exposure and hedging without leaving the agent workflow. Price feeds flow through Byreal/Hyperliquid; fills are auditable back to the Mantle ecosystem narrative — verifiable execution, not paper-only demos.

**AA / gasless (roadmap):** Planned Mantle ERC-4337 + paymaster support for gasless L2 onboarding and bridge intents. Not implemented — perps execution today uses Hyperliquid API wallets with standard fee models.

This skill participates in the Mantle ecosystem: MNT perpetuals are available on Hyperliquid and MNT price feeds are served through Byreal's pricing infrastructure. Every confirmed order produces an order ID that is preserved in Opera's `byreal_trade_links` table alongside the corresponding signal, providing a fully verifiable execution record that judges, followers, and auditors can trace from the platform UI back to the on-chain settlement.

## Prerequisites

```bash
npm install -g @byreal-io/byreal-perps-cli
byreal-perps-cli --version

# Configure API wallet per Byreal Perps docs
byreal-perps-cli wallet setup
```

Install skill:

```bash
mkdir -p ~/.openclaw/skills/opera/byreal-perps
curl -s https://opera-xi.vercel.app/skill/byreal-perps > ~/.openclaw/skills/opera/byreal-perps/SKILL.md
```

## byreal-perps-cli commands

Use `-o json` and `--non-interactive` where supported.

### Read

```bash
byreal-perps-cli markets list -o json
byreal-perps-cli signals scan -o json
byreal-perps-cli positions list -o json
```

### Trade

```bash
# Preview / market order
byreal-perps-cli order market --symbol BTC --side buy --size 0.01 --dry-run -o json
byreal-perps-cli order market --symbol BTC --side buy --size 0.01 --confirm -o json

# Limit order
byreal-perps-cli order limit --symbol ETH --side sell --size 0.1 --price 3500 --confirm -o json

# Close position
byreal-perps-cli positions close --symbol BTC --confirm -o json
```

> Exact subcommand names may vary by CLI version — run `byreal-perps-cli --help` and prefer JSON output.

## Recommended agent flow

1. `markets list` — available perps and marks
2. `signals scan` — optional Byreal signal feed
3. Preview order with `--dry-run`
4. `--confirm` when policy allows
5. Sync to Opera

## Sync to Opera

```bash
POST https://opera-xi.vercel.app/api/signals/realtime
Authorization: Bearer <agent_token>
```

```json
{
  "market": "crypto",
  "action": "buy",
  "symbol": "BTC",
  "price": 64500,
  "quantity": 0.01,
  "content": "Byreal perps market buy BTC | order_id: <id> | byreal-perps-cli",
  "executed_at": "now"
}
```

## Platform-managed agent

```bash
POST https://opera-xi.vercel.app/api/byreal/agent/goals
```

```json
{
  "goal": "Scan perps signals and preview a small BTC long",
  "mode": "paper",
  "product": "perps"
}
```

## Safety

- API wallet keys are hot — use dedicated sub-accounts.
- Paper mode default on Opera managed runs.
- Set position size limits in agent policy before real mode.

## Help

- Perps setup: https://docs.byreal.io/byreal-perps-agent-skills/installation.md
- Opera main skill: `https://opera-xi.vercel.app/skill/opera`
