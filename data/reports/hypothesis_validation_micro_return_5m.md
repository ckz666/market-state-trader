# Hypothesis Validation — micro_return_5m

Generated 2026-07-27T04:31:35.294238+00:00.

Freezes discovery_v10-v12's micro_return_5m finding and tests it OOS, same discipline as hypothesis_validation.py's original LPL validation. Quintile edges fit ONLY on 2020-2025, applied unchanged to 2026. Does not change decision_rule_v1 or propose a rule -- purely tests whether the Discovery-period finding survives contact with unseen data.

---

## 1. Discovery vs. Validation — Q1 (very negative) vs Q5 (very positive) micro_return_5m

Frozen quintile edges (fit on Discovery only) applied unchanged to both periods.

| Horizon | Period | n (Q1) | Q1 win% | Q1 median | n (Q5) | Q5 win% | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|---|---|---|
| 15m | Discovery | 10531 | 57.3% | +0.0551% | 10519 | 44.9% | -0.0371% | +0.0922% |
| 15m | Validation | 720 | 54.2% | +0.0256% | 655 | 49.2% | -0.0049% | +0.0305% |
| 1h | Discovery | 10531 | 55.4% | +0.0689% | 10519 | 47.6% | -0.0250% | +0.0939% |
| 1h | Validation | 720 | 52.2% | +0.0140% | 655 | 46.3% | -0.0333% | +0.0473% |
| 4h | Discovery | 10531 | 53.5% | +0.0739% | 10519 | 50.2% | +0.0049% | +0.0690% |
| 4h | Validation | 720 | 50.7% | +0.0209% | 655 | 49.2% | -0.0176% | +0.0385% |

---

## 2. Verdict

| Horizon | Discovery spread | Validation spread | Same sign? |
|---|---|---|---|
| 15m | +0.0922% | +0.0305% | yes |
| 1h | +0.0939% | +0.0473% | yes |
| 4h | +0.0690% | +0.0385% | yes |

**3/3 horizons held the same sign out-of-sample.**

