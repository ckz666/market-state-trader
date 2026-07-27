# decision_rule_v3 micro_return_5m filter — 2026 OOS validation

Generated 2026-07-27T04:55:50.137427+00:00.

Single, unmodified OOS run per decision_rule_v3_micro_return_filter_hypothesis.md (pre-registered BEFORE this script was written). All quintile edges fit ONLY on 2020-2025, applied unchanged to 2026. No tuning performed.

---

## 1. Trade level (Option A de-duplicated, fees/slippage) — the real result

| Population | Stats |
|---|---|
| Baseline: all decision_rule_v1 trades | n=39, win 51.3%, mean -0.0893%, median +0.1787%, P05 -3.09%, PF 0.868 |
| Filtered: + micro_return_5m == Q1 | n=24, win 54.2%, mean +0.3037%, median +0.3772%, P05 -1.52%, PF 1.565 |

---

## 2. Candidate level (all long_candidate signals, NOT a tradeable sequence)

Higher n, but overlapping 4h windows — reported per the pre-registration as the higher-sample view only, never as a tradeable result.

| Population | Stats |
|---|---|
| Baseline: all long_candidate signals | n=113, win 59.3%, mean +0.0813%, median +0.3110%, P05 -3.46%, PF 1.122 |
| Filtered: + micro_return_5m == Q1 | n=45, win 57.8%, mean -0.0301%, median +0.3110%, P05 -4.19%, PF 0.965 |
