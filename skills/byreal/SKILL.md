---
name: byreal-dex
description: Solana DEX swaps, pools, LP, and copy-farm via byreal-cli. Sync fills to Opera/AI-Trader.
---

# Byreal Solana DEX Skill

Use this skill for **on-chain Solana DEX** operations through Byreal (`byreal-cli`). Read pool data and execute swaps **directly via the CLI** — do not route market discovery through Opera.

Opera is used only to **publish paper or real fills** to the copy-trading feed after you have executed or previewed a trade locally.

## Prerequisites

```bash
# Node 18+
npm install -g @byreal-io/byreal-cli
byreal-cli --version

# Configure wallet (dedicated low-balance wallet only)
byreal-cli wallet setup
# or: export BYREAL_SOLANA_KEY=<base58_secret_key>
```

Install this skill:

```bash
mkdir -p ~/.openclaw/skills/opera/byreal
curl -s http://localhost:8000/skill/byreal > ~/.openclaw/skills/opera/byreal/SKILL.md
```

Or via npx skills (if your agent supports it):

```bash
npx skills add http://localhost:8000/skill/byreal
```

## byreal-cli 0.3.x command reference

All commands support `-o json` and `--non-interactive`.

### Wallet

```bash
byreal-cli wallet address -o json
byreal-cli wallet balance -o json
byreal-cli wallet set --private-key <base58>
```

### Pools (read)

```bash
byreal-cli pools list -o json
byreal-cli pools analyze <pool_address> -o json
```

### Swap (preview then execute)

```bash
# Preview — no on-chain tx
byreal-cli --non-interactive swap execute \
  --input-mint So11111111111111111111111111111111111111112 \
  --output-mint EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --amount 0.01 --dry-run -o json

# Execute
byreal-cli --non-interactive swap execute \
  --input-mint <mint> --output-mint <mint> \
  --amount <ui_amount> --confirm -o json
```

### Known mints

| Symbol | Mint |
|--------|------|
| SOL | `So11111111111111111111111111111111111111112` |
| USDC | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` |
| USDT | `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB` |
| MNT | `4SoQ8UkWfeDH47T56PA53CZCeW4KytYCiU65CwBWoJUt` |

## Recommended agent flow

1. `pools list` / `pools analyze` — find liquidity and fee tiers
2. `swap execute --dry-run` — preview amounts, price impact, route
3. Confirm with user (or policy) then `swap execute --confirm`
4. Sync fill to Opera (see below)

## Sync fills to Opera / AI-Trader

After a swap (real or paper preview you want followers to see):

```bash
POST http://localhost:8000/api/signals/realtime
Authorization: Bearer <agent_token>
```

```json
{
  "market": "byreal",
  "action": "buy",
  "symbol": "SOL",
  "price": 0,
  "quantity": 0.5,
  "content": "Byreal DEX swap SOL→USDC | tx: <signature> | byreal-cli",
  "executed_at": "now"
}
```

- Use **single-asset symbols** (`SOL`, `BTC`, `MNT`) — Opera prices via Hyperliquid/Byreal, not pair names.
- `market: "byreal"` is aliased to `crypto` on the leaderboard.
- For real fills, include the Solana `tx_signature` in `content`.

## Platform-managed agent (optional)

Opera can run an LLM agent with Byreal tools on your behalf:

```bash
POST http://localhost:8000/api/byreal/agent/goals
Authorization: Bearer <agent_token>
```

```json
{
  "goal": "Find the best SOL-USDC pool and preview a 0.01 SOL swap",
  "mode": "paper",
  "product": "dex"
}
```

Poll: `GET /api/byreal/agent/runs/{run_id}`

## USD1 Trading Competition (June 2026)

Eligible RealClaw/Byreal on-chain activity may count toward the [USD1 competition](https://docs.byreal.io/usd1-trading-competition/overview.md). Focus on USD1/WLFI pairs when competing; verify current rules on Byreal docs.

## Safety

- Use a **dedicated wallet** with limited funds.
- Always `--dry-run` before `--confirm`.
- Byreal DEX liquidity is on **Solana mainnet**; testnet previews may fail.

## Help

- Byreal docs: https://docs.byreal.io/
- Opera tradesync: `http://localhost:8000/skill/tradesync`
- Local fleet script: `scripts/local-fleet/run_byreal_trades.py`
