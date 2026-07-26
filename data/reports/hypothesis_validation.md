# Hypothesis Validation — frozen LPL x Volatility, tested out-of-sample

Generated 2026-07-26T14:08:16.391754+00:00.

Discovery (train) period: 2020-01-01 00:00:00+00:00 -> 2025-12-31 23:00:00+00:00 (52,608 samples).

Validation (test) period: 2026-01-01 00:00:00+00:00 -> 2026-07-26 12:00:00+00:00 (4,957 samples) — never used to fit LPL's z-score parameters or either dimension's quintile bin edges.

---

## 1. Discovery vs. Validation — LPL spread by volatility quintile

Same table as discovery_v5 section 1, computed separately on each period using the frozen quintile edges. If the hypothesis is real (not overfit to the discovery period), the validation column should show the same sign and a similar growing-with-volatility pattern, even if the exact magnitudes differ.

### 15m

**Discovery (2020-2025, in-sample):**

| Volatility | n (Q1) | LPL=Q1 median | n (Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 1,051 | +0.0243% | 1,121 | -0.0095% | -0.0338% |
| Q2 | 1,598 | +0.0275% | 1,641 | -0.0091% | -0.0366% |
| Q3 | 1,987 | +0.0337% | 2,195 | -0.0210% | -0.0547% |
| Q4 | 2,575 | +0.0231% | 2,648 | -0.0224% | -0.0455% |
| Q5 | 3,276 | +0.0424% | 2,882 | -0.0244% | -0.0668% |

**Validation (2026, out-of-sample, frozen bins):**

| Volatility | n (Q1) | LPL=Q1 median | n (Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 169 | +0.0144% | 153 | -0.0015% | -0.0159% |
| Q2 | 301 | +0.0421% | 239 | -0.0242% | -0.0663% |
| Q3 | 200 | +0.0379% | 171 | +0.0051% | -0.0328% |
| Q4 | 215 | +0.0422% | 155 | -0.0796% | -0.1218% |
| Q5 | 113 | -0.0704% | 70 | +0.0030% | +0.0734% |

### 30m

**Discovery (2020-2025, in-sample):**

| Volatility | n (Q1) | LPL=Q1 median | n (Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 1,051 | +0.0356% | 1,121 | -0.0177% | -0.0533% |
| Q2 | 1,598 | +0.0501% | 1,641 | -0.0299% | -0.0800% |
| Q3 | 1,987 | +0.0543% | 2,195 | -0.0195% | -0.0738% |
| Q4 | 2,575 | +0.0421% | 2,648 | -0.0202% | -0.0622% |
| Q5 | 3,276 | +0.0842% | 2,882 | -0.0327% | -0.1169% |

**Validation (2026, out-of-sample, frozen bins):**

| Volatility | n (Q1) | LPL=Q1 median | n (Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 169 | -0.0050% | 153 | -0.0275% | -0.0225% |
| Q2 | 301 | +0.0322% | 239 | -0.0225% | -0.0547% |
| Q3 | 200 | +0.0418% | 171 | -0.0257% | -0.0675% |
| Q4 | 215 | +0.0544% | 155 | -0.0667% | -0.1211% |
| Q5 | 113 | +0.1399% | 70 | -0.0404% | -0.1804% |

### 1h

**Discovery (2020-2025, in-sample):**

| Volatility | n (Q1) | LPL=Q1 median | n (Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 1,051 | +0.0342% | 1,121 | -0.0307% | -0.0649% |
| Q2 | 1,598 | +0.0451% | 1,641 | -0.0282% | -0.0733% |
| Q3 | 1,987 | +0.0686% | 2,195 | -0.0279% | -0.0965% |
| Q4 | 2,575 | +0.0579% | 2,648 | -0.0304% | -0.0883% |
| Q5 | 3,276 | +0.0880% | 2,882 | -0.0258% | -0.1138% |

**Validation (2026, out-of-sample, frozen bins):**

| Volatility | n (Q1) | LPL=Q1 median | n (Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 169 | +0.0171% | 153 | -0.0304% | -0.0475% |
| Q2 | 301 | +0.0453% | 239 | -0.0352% | -0.0805% |
| Q3 | 200 | +0.0318% | 171 | -0.0992% | -0.1310% |
| Q4 | 215 | +0.0689% | 155 | -0.0465% | -0.1154% |
| Q5 | 113 | +0.1120% | 70 | +0.0016% | -0.1103% |

### 4h

**Discovery (2020-2025, in-sample):**

| Volatility | n (Q1) | LPL=Q1 median | n (Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 1,051 | +0.0618% | 1,121 | -0.0610% | -0.1228% |
| Q2 | 1,598 | +0.0872% | 1,641 | -0.0503% | -0.1375% |
| Q3 | 1,987 | +0.1293% | 2,195 | -0.0749% | -0.2042% |
| Q4 | 2,575 | +0.1231% | 2,648 | -0.0610% | -0.1841% |
| Q5 | 3,276 | +0.2324% | 2,882 | -0.0922% | -0.3246% |

**Validation (2026, out-of-sample, frozen bins):**

| Volatility | n (Q1) | LPL=Q1 median | n (Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 169 | +0.0131% | 153 | +0.0095% | -0.0036% |
| Q2 | 301 | +0.0420% | 239 | -0.0654% | -0.1074% |
| Q3 | 200 | -0.0514% | 171 | -0.0826% | -0.0312% |
| Q4 | 215 | +0.1962% | 155 | -0.0916% | -0.2878% |
| Q5 | 113 | +0.3110% | 70 | -0.0790% | -0.3901% |


---

## 2. Validation period — full outcome distribution, extreme cells (4h)

Same check as discovery_v5 section 3, on validation data only.

| Cell | n | Mean | Median | Win Rate | Std | P05 | P25 | P75 | P95 |
|---|---|---|---|---|---|---|---|---|---|
| LPL=Q1 (lowest) + Volatility=Q5 (highest) | 113 | +0.0813% | +0.3110% | 59.3% | 1.852% | -3.46% | -0.85% | +1.30% | +2.82% |
| LPL=Q5 (highest) + Volatility=Q5 (highest) | 70 | +0.1901% | -0.0790% | 47.1% | 1.667% | -1.88% | -0.71% | +0.87% | +2.92% |

---

## 3. Verdict

| Volatility | Discovery spread (4h) | Validation spread (4h) | Same sign? |
|---|---|---|---|
| Q1 | -0.1228% | -0.0036% | yes |
| Q2 | -0.1375% | -0.1074% | yes |
| Q3 | -0.2042% | -0.0312% | yes |
| Q4 | -0.1841% | -0.2878% | yes |
| Q5 | -0.3246% | -0.3901% | yes |

**5/5 volatility quintiles: validation spread has the same sign as discovery.**

Discovery spread monotonically grows (more negative) with volatility: False

Validation spread monotonically grows (more negative) with volatility: False (n is much smaller out-of-sample — 1,786 samples total vs. discovery's 20,974 — so some noise in the exact ordering is expected even if the hypothesis holds)

**The core directional claim survives out-of-sample validation on 2026 data that played no part in defining Local Price Location, its quintile boundaries, or the volatility quintile boundaries.**

