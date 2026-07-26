# Decision Rule v1 — signal frequency and raw realized distribution

Generated 2026-07-26T14:28:33.886126+00:00.

**Phase B (Decision Design) only** — NOT a backtest. No fees, no slippage, no position sizing, no stop-loss/take-profit, no walk-forward. This measures exactly two things: how often the frozen rule fires, and what the raw realized forward-return distribution of its signals looks like, in both the discovery period (for reference) and the untouched validation period. Phase C (Trading Validation) is a deliberately separate, later step.

**Rule** (frozen, no thresholds tuned on 2026 — see module docstring for the exact frozen parameters):

```
IF   LPL == Q1 (lowest quintile)  AND Volatility == Q5 (highest): long_candidate
ELIF LPL == Q5 (highest quintile) AND Volatility == Q5 (highest): avoid_long
ELSE: no_signal
```

Target horizon: 4h.

---

## Signal frequency and realized outcomes

### Discovery (2020-2025, in-sample) (n=52,608)

| Decision | Count | % of period | Signals/day (approx) |
|---|---|---|---|
| long_candidate | 3,276 | 6.2% | 1.495 |
| avoid_long | 2,882 | 5.5% | 1.315 |
| no_signal | 46,450 | 88.3% | 21.191 |

**Realized 4h forward-return distribution per decision:**

| Decision | n | Mean | Median | Win Rate | Std | P05 | P95 |
|---|---|---|---|---|---|---|---|
| long_candidate | 3,276 | +0.0792% | +0.2324% | 56.8% | 2.547% | -3.93% | +3.55% |
| avoid_long | 2,882 | +0.0134% | -0.0922% | 47.1% | 1.920% | -2.90% | +3.28% |

### Validation (2026, out-of-sample) (n=4,957)

| Decision | Count | % of period | Signals/day (approx) |
|---|---|---|---|
| long_candidate | 113 | 2.3% | 0.547 |
| avoid_long | 70 | 1.4% | 0.339 |
| no_signal | 4,774 | 96.3% | 23.119 |

**Realized 4h forward-return distribution per decision:**

| Decision | n | Mean | Median | Win Rate | Std | P05 | P95 |
|---|---|---|---|---|---|---|---|
| long_candidate | 113 | +0.0813% | +0.3110% | 59.3% | 1.852% | -3.46% | +2.82% |
| avoid_long | 70 | +0.1901% | -0.0790% | 47.1% | 1.667% | -1.88% | +2.92% |
