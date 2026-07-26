# Phase C baseline v1 — minimal honest execution test (long_candidate only)

Generated 2026-07-26T14:35:25.946233+00:00.

Entry: first real 1m close at/after the signal's state timestamp. Exit: first real 1m close at/after entry+4h (fixed — not optimized). Fees: mst_config.TAKER_FEE, round trip. Slippage: a STATED ASSUMPTION of 5bps/side (no historical order-book data exists to measure this from — not a real fill), round trip. Position logic: Option A — a signal opens a trade only if no prior trade from this rule is still open; overlapping signals are skipped, not stacked. avoid_long is NOT traded as a short in this version — it remains a long-avoidance signal only. No stop-loss/take-profit, no position sizing, no re-fitting of any state parameters.

---

## Results

### Discovery (2020-2025, in-sample)

- n_signals (long_candidate fired): 3,276
- n_trades actually executed (Option A: non-overlapping, gaps excluded): 1,064
- signals skipped (overlapping position or data gap at entry/exit): 2,212

| Metric | Value |
|---|---|
| Win rate | 51.4% |
| Mean gross return/trade | +0.0894% |
| Total fees (sum) | 127.6800% of notional, summed |
| Total slippage (assumed, sum) | 106.4000% of notional, summed |
| Mean net return/trade | -0.1306% |
| Median net return/trade | +0.0473% |
| Profit factor (gross wins / gross losses) | 0.85 |
| Final compounded equity (100% of capital re-bet every trade, starting at 1.0) | 0.1731 |
| Max drawdown (of that same 100%-of-capital equity curve) | -82.94% |

**Caveat on the last two rows:** this equity curve assumes every trade risks the ENTIRE account with no position sizing at all — nobody would actually trade this way. It's included only to show the qualitative shape of compounding risk (does the tail risk from the median>mean gap above compound badly?), not as a projection of real capital growth. Position sizing is explicitly out of scope for this baseline.


### Validation (2026, out-of-sample)

- n_signals (long_candidate fired): 113
- n_trades actually executed (Option A: non-overlapping, gaps excluded): 39
- signals skipped (overlapping position or data gap at entry/exit): 74

| Metric | Value |
|---|---|
| Win rate | 51.3% |
| Mean gross return/trade | +0.1307% |
| Total fees (sum) | 4.6800% of notional, summed |
| Total slippage (assumed, sum) | 3.9000% of notional, summed |
| Mean net return/trade | -0.0893% |
| Median net return/trade | +0.1787% |
| Profit factor (gross wins / gross losses) | 0.87 |
| Final compounded equity (100% of capital re-bet every trade, starting at 1.0) | 0.9609 |
| Max drawdown (of that same 100%-of-capital equity curve) | -15.36% |

**Caveat on the last two rows:** this equity curve assumes every trade risks the ENTIRE account with no position sizing at all — nobody would actually trade this way. It's included only to show the qualitative shape of compounding risk (does the tail risk from the median>mean gap above compound badly?), not as a projection of real capital growth. Position sizing is explicitly out of scope for this baseline.


