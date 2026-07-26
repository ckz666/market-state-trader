# Discovery v8 — time stability of the LPL x regime_4h matrix

Generated 2026-07-26T18:52:24.913998+00:00.

Follow-up to discovery_v6/v7. Section A extends discovery_v6's per-year stability check (previously only done for 'trending') to all three regimes. Section B checks whether discovery_v7's surprising 'ranging' non-monotonicity (Q4 beating Q1) is a stable per-year feature or a pooled-period artifact. Purely descriptive; does not change decision_rule_v1. Same frozen LPL/quintile-edge parameters as hypothesis_validation.py. Vol=Q5 only. Discovery only; 2026 untouched. Cells with n < 15 are marked instead of reported.

---

## A. Per-regime, per-year: LPL=Q1 vs Q5 spread (Vol=Q5, 4h)

Extends discovery_v6's stability check (which only covered 'trending') to all three regimes -- is the ranging < transitioning < trending ordering of the spread itself stable per year, or driven by a subset of years?


### ranging

| Year | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread |
|---|---|---|---|---|---|
| 2020 | 67 | -0.1609% | 41 | +0.5146% | -0.6755% |
| 2021 | 315 | -0.0615% | 220 | -0.1115% | +0.0500% |
| 2022 | 85 | +0.1464% | 96 | +0.0318% | +0.1146% |
| 2024 | 41 | n too few | 7 | n too few | - |
| 2025 | 36 | -0.3019% | 19 | -0.2696% | -0.0322% |

Sign consistency: 2/4 years positive (Q1 > Q5 median)


### transitioning

| Year | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread |
|---|---|---|---|---|---|
| 2020 | 73 | +0.1830% | 78 | +0.2762% | -0.0932% |
| 2021 | 253 | +0.2908% | 241 | -0.0107% | +0.3015% |
| 2022 | 74 | +0.2766% | 60 | +0.2488% | +0.0278% |
| 2023 | 4 | n too few | 0 | n too few | - |
| 2024 | 25 | +0.3513% | 22 | -0.5430% | +0.8943% |
| 2025 | 48 | n too few | 12 | n too few | - |

Sign consistency: 3/4 years positive (Q1 > Q5 median)


### trending

| Year | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread |
|---|---|---|---|---|---|
| 2020 | 390 | +0.3906% | 367 | -0.2173% | +0.6079% |
| 2021 | 832 | +0.4420% | 882 | +0.0541% | +0.3879% |
| 2022 | 532 | +0.0538% | 324 | -0.2934% | +0.3472% |
| 2023 | 66 | +0.1103% | 163 | -0.1078% | +0.2181% |
| 2024 | 291 | +0.3715% | 232 | -0.1713% | +0.5427% |
| 2025 | 144 | +0.3961% | 118 | -0.2418% | +0.6379% |

Sign consistency: 6/6 years positive (Q1 > Q5 median)


---

## B. Is 'ranging' regime's non-monotone LPL shape stable per year?

discovery_v7 found Q4's median return beating Q1's within 'ranging' (Vol=Q5, pooled 2020-2025). Full Q1-Q5 median row per year, to see whether Q4 > Q1 is a recurring feature or a one/two-year artifact.

| Year | Q1 | Q2 | Q3 | Q4 | Q5 | Q4 > Q1? |
|---|---|---|---|---|---|---|
| 2020 | -0.1609% | +0.8209% | n too few | n too few | +0.5146% | n/a |
| 2021 | -0.0615% | -0.2206% | +0.0915% | +0.3407% | -0.1115% | yes |
| 2022 | +0.1464% | +0.9220% | +0.8855% | +0.2407% | +0.0318% | yes |
| 2024 | +0.0562% | -0.0896% | -0.2813% | n too few | n too few | n/a |
| 2025 | -0.3019% | n too few | n too few | n too few | -0.2696% | n/a |

Q4 > Q1 in 2/2 years with sufficient n.

