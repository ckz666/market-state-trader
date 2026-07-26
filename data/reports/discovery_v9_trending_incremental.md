# Discovery v9 — does regime_4h=='trending' add incremental value on decision_rule_v1's real trades?

Generated 2026-07-26T19:03:10.230339+00:00.

Direct follow-up to discovery_v6-v8's candidate-level regime conditioning. This uses decision_rule_v1's REAL trade set (Option A de-duplicated, fees/slippage included -- same trades phase_c_baseline_v1.py backtests), split by regime_4h at entry, rather than the raw candidate-level population. Purely descriptive; does NOT change decision_rule_v1. Discovery only; 2026 untouched. Cells with n < 15 are marked instead of reported.

---

## Real decision_rule_v1 trades, split by regime_4h at entry

Same trades as phase_c_baseline_v1.py's Discovery backtest -- fees/slippage included, Option A de-duplication already applied. No LPL quintile split is possible here (long_candidate is LPL==Q1 by construction); this checks only the regime split.

| Population | Stats |
|---|---|
| All decision_rule_v1 trades (baseline) | n=1064, win 51.4%, mean -0.1306%, median +0.0473%, P05 -4.19%, PF 0.85 |
| ...restricted to regime_4h == trending | n=735, win 54.0%, mean -0.0454%, median +0.1730%, P05 -4.46%, PF 0.95 |
| ...restricted to regime_4h != trending | n=329, win 45.6%, mean -0.3210%, median -0.1319%, P05 -3.50%, PF 0.63 |

---

## Per-year stability of the trending-restricted subset

| Year | n (trending) | Win rate | Median | Mean |
|---|---|---|---|---|
| 2020 | 133 | 57.9% | +0.2256% | +0.0173% |
| 2021 | 273 | 55.3% | +0.3889% | +0.0834% |
| 2022 | 166 | 51.8% | +0.0747% | -0.2131% |
| 2023 | 27 | 48.1% | -0.1314% | +0.0946% |
| 2024 | 94 | 53.2% | +0.0980% | -0.1683% |
| 2025 | 42 | 47.6% | -0.1287% | -0.2335% |

---

## Diagnostic: why do 2023 and 2025 diverge?

Per-year regime mix for ALL decision_rule_v1 trades (not just trending), to check whether the weak years are a real regime-specific effect or simply thin overall signal years.

| Year | ranging | transitioning | trending | total |
|---|---|---|---|---|
| 2020 | 20 | 24 | 133 | 177 |
| 2021 | 99 | 78 | 273 | 450 |
| 2022 | 30 | 25 | 166 | 221 |
| 2023 | 0 | 1 | 27 | 28 |
| 2024 | 16 | 9 | 94 | 119 |
| 2025 | 13 | 14 | 42 | 69 |

**2023**: only 28 decision_rule_v1 trades total, 27 of them already `trending` -- essentially no ranging/transitioning signals fired at all that year (a quiet, low-volatility year, consistent with the general BTC narrative for 2023). Median -0.13% and mean +0.09% straddle zero in opposite directions (n=27, tight distribution, max loss only -1.47%) -- this reads as ordinary small-sample noise around zero, not a breakdown of the effect.

**2025**: n=42 trending trades, mean pulled down by two larger losses (-4.94%, -4.90%) out of 42 -- a higher-volatility year (std 2.18% vs. 2023's 1.06%) where a couple of bigger-than-typical losing trades move the mean; the median stays close to zero. Consistent with the known median-over-mean tail-risk gap already documented throughout this project (see the house rules), not evidence the regime-conditioning itself failed.

**Reading:** both weak years are the two thinnest-signal years in the whole Discovery period. Their negative averages look like ordinary variance around a small n, not a second, contradicting regime effect. This tempers concern about the 4/6 count somewhat, but does not turn it into a clean 6/6 -- there just isn't enough data in 2023/2025 to say much either way.

