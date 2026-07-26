# Discovery v9 — does regime_4h=='trending' add incremental value on decision_rule_v1's real trades?

Generated 2026-07-26T18:57:26.905857+00:00.

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
