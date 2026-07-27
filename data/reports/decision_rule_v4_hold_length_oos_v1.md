# decision_rule_v4 (24h hold) — 2026 OOS validation

Generated 2026-07-27T05:21:51.555901+00:00.

Single, unmodified OOS run per decision_rule_v4_hold_length_hypothesis.md (pre-registered BEFORE this script was written). Entry unchanged; only hold length differs. All quintile edges fit ONLY on 2020-2025. No tuning, and no other hold lengths tested here.

---

## 1. 2026 OOS — baseline 4h vs. candidate 24h

| Hold | Stats |
|---|---|
| 240m (baseline) | n=39, win 51.3%, median +0.1787%, mean -0.0893%, P05 -3.09%, PF 0.868, maxDD -15.36% |
| 1440m (candidate) | n=16, win 56.2%, median +1.3137%, mean +0.7982%, P05 -5.51%, PF 1.575, maxDD -12.34% |

---

## 2. Pre-registered Discovery-vs-OOS direction check

Per the pre-registration: because different hold lengths produce different trade sequences (not subsets), the decisive question is whether each primary metric moves the SAME direction in both periods — the failure mode that sank decision_rule_v3.

| Metric | Discovery (4h -> 24h) | OOS (4h -> 24h) | Same direction? |
|---|---|---|---|
| Win rate | +5.0000pp | +4.9679pp | yes |
| Net median | +0.4706pp | +1.1350pp | yes |
| Profit factor | +0.402 | +0.707 | yes |
