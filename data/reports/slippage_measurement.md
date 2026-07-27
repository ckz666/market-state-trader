# Slippage measurement — Bitget order book

Generated 2026-07-27T06:18:01.129223+00:00.

`SLIPPAGE_BPS_PER_SIDE = 5` has been a stated assumption since Phase C, never measured. This walks Bitget's live order book — the venue all prices in this project come from — to price a market order of various sizes.

**Two limitations, stated rather than buried:** (1) Bitget exposes only the current book, so this is a present-day snapshot, not the 2020-2025 conditions the backtests cover; liquidity was very likely worse in 2020-2022. (2) Sample window is minutes, so it does not capture stressed markets, which is exactly when this strategy's high-volatility entries fire.

---

Samples collected: **10** | Top-of-book spread: mean **0.02 bps**, median 0.02, max 0.02

## Slippage by order size (one side, market order)

| Notional | Buy slippage (bps) | Sell slippage (bps) | Mean both sides | vs. 5 bps assumption |
|---|---|---|---|---|
| $1,000 | 0.02 | 0.01 | **0.01** | **-4.99 bps** — assumption too pessimistic |
| $5,000 | 0.04 | 0.01 | **0.02** | **-4.98 bps** — assumption too pessimistic |
| $10,000 | 0.04 | 0.01 | **0.02** | **-4.98 bps** — assumption too pessimistic |
| $50,000 | 0.07 | 0.01 | **0.04** | **-4.96 bps** — assumption too pessimistic |
| $100,000 | 0.11 | 0.05 | **0.08** | **-4.92 bps** — assumption too pessimistic |

## What this changes

The project applies 5 bps per side, i.e. 10 bps round trip, inside a total round-trip cost of 22 bps (the rest being taker fees). Since the measured 4h net median is only about +4.7 bps per trade, a few bps of error either way is decisive at that hold; the 24h candidate (net median ~+50 bps) has far more headroom.


---

## Sensitivity: how much was the assumption costing?

Same trades, only `SLIPPAGE_BPS_PER_SIDE` varied. The measured value is ~0.2 bps; the project assumed 5.

| Hold | Slippage/side | n | Median | Mean | PF | Equity |
|---|---|---|---|---|---|---|
| 240m | 0.2 bps ← measured | 1,064 | +0.1433% | -0.0346% | 0.959 | 0.4813 |
| 240m | 1.0 bps | 1,064 | +0.1273% | -0.0506% | 0.940 | 0.4059 |
| 240m | 2.0 bps | 1,064 | +0.1073% | -0.0706% | 0.918 | 0.3280 |
| 240m | 5.0 bps ← assumed | 1,064 | +0.0473% | -0.1306% | 0.853 | 0.1731 |
| 240m | 10.0 bps | 1,064 | -0.0527% | -0.2306% | 0.754 | 0.0596 |
| 1440m | 0.2 bps ← measured | 365 | +0.6139% | +0.4678% | 1.330 | 3.2216 |
| 1440m | 1.0 bps | 365 | +0.5979% | +0.4518% | 1.317 | 3.0391 |
| 1440m | 2.0 bps | 365 | +0.5779% | +0.4318% | 1.301 | 2.8254 |
| 1440m | 5.0 bps ← assumed | 365 | +0.5179% | +0.3718% | 1.255 | 2.2701 |
| 1440m | 10.0 bps | 365 | +0.4179% | +0.2718% | 1.181 | 1.5759 |
