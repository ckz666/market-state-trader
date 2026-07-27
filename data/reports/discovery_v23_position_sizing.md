# Discovery v23 — position sizing (never tested)

Generated 2026-07-27T05:38:46.800379+00:00.

Every prior simulation in this project was unit-sized; sizing is listed under "explicitly NOT included" in phase_c_baseline_v1's docstring and has never been examined. Three schemes, all computable at entry time with no look-ahead, each normalized to mean size 1.0 and capped at (0.25, 4.0) so one extreme observation cannot dominate. Win rate and the sign of each trade are unaffected by sizing, so the comparison focuses on mean, profit factor and compounded equity. Purely descriptive; does not change decision_rule_v1. Discovery only (2020-2025); 2026 untouched.

---

## Hold 240m

| Sizing | n | Mean size (sd) | Win rate | Sized mean | Sized median | PF | Equity | Max DD |
|---|---|---|---|---|---|---|---|---|
| 1. Unit (baseline) | 1,064 | 1.00 (0.00) | 51.4% | -0.1306% | +0.0473% | 0.853 | 0.1731 | -82.94% |
| 2. Inverse volatility | 1,064 | 1.00 (0.27) | 51.4% | -0.1736% | +0.0490% | 0.787 | 0.1239 | -87.76% |
| 3. LPL extremity | 1,064 | 1.00 (0.80) | 51.4% | +0.0445% | +0.0234% | 1.046 | 0.1122 | -96.47% |

## Hold 1440m

| Sizing | n | Mean size (sd) | Win rate | Sized mean | Sized median | PF | Equity | Max DD |
|---|---|---|---|---|---|---|---|---|
| 1. Unit (baseline) | 365 | 1.00 (0.00) | 56.4% | +0.3718% | +0.5179% | 1.255 | 2.2701 | -49.62% |
| 2. Inverse volatility | 365 | 1.00 (0.24) | 56.4% | +0.1834% | +0.5285% | 1.127 | 1.2030 | -57.52% |
| 3. LPL extremity | 365 | 1.00 (0.80) | 56.4% | +0.4441% | +0.2337% | 1.294 | 1.8622 | -68.38% |
