# decision_rule_v2 trending-filter OOS v1 -- 2026 validation

Generated 2026-07-26T19:04:36.246663+00:00.

Single, unmodified OOS run per decision_rule_v2_trending_filter_hypothesis.md (pre-registered BEFORE this script was run). No tuning of any kind performed here. LPL/volatility quintile edges fit on 2020-2025 only, applied unchanged to 2026.

---

## Baseline (unfiltered decision_rule_v1) vs. trending-filtered, 2026 OOS

| Population | Stats |
|---|---|
| All decision_rule_v1 trades (baseline) | n=39, win 51.3%, mean -0.0893%, median +0.1787%, P05 -3.09%, PF 0.868 |
| ...restricted to regime_4h == trending | n=34, win 50.0%, mean -0.1876%, median +0.0776%, P05 -3.23%, PF 0.742 |
| ...restricted to regime_4h != trending | n=5 (n < 15, directional only), win 60.0%, mean +0.5788%, median +0.4969%, P05 +nan%, PF 2.781 |
