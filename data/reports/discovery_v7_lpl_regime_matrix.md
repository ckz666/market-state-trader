# Discovery v7 — full LPL quintile x regime_4h outcome matrix

Generated 2026-07-26T18:49:45.433269+00:00.

Direct follow-up to discovery_v6: decomposes the LPL=Q1 vs Q5 spread (which widened monotonically ranging -> transitioning -> trending) into the full quintile matrix, to see whether Q1 improves, Q5 degrades, or there's a genuine interaction/non-monotone shape. Vol=Q5 only (decision_rule_v1's actual traded regime). Purely descriptive; does not change decision_rule_v1. Same frozen LPL/quintile-edge parameters as hypothesis_validation.py / discovery_v6. Discovery only; 2026 untouched. Cells with n < 15 are marked instead of reported.

---

## Full LPL quintile x regime_4h matrix (Vol=Q5, 4h forward return)

| LPL | ranging | transitioning | trending |
|---|---|---|---|
| Q1 | n=544, win 48.9%, mean -0.2589%, median -0.0167%, P05 -3.41%, PF 0.67 | n=477, win 59.1%, mean +0.1318%, median +0.2824%, P05 -3.31%, PF 1.20 | n=2255, win 58.2%, mean +0.1496%, median +0.3159%, P05 -4.11%, PF 1.18 |
| Q2 | n=200, win 53.5%, mean +0.1208%, median +0.1282%, P05 -2.45%, PF 1.21 | n=192, win 57.3%, mean +0.1650%, median +0.1922%, P05 -2.71%, PF 1.31 | n=1097, win 59.9%, mean +0.2324%, median +0.2882%, P05 -2.90%, PF 1.44 |
| Q3 | n=166, win 55.4%, mean +0.3029%, median +0.0970%, P05 -2.22%, PF 1.65 | n=218, win 59.2%, mean +0.0721%, median +0.2395%, P05 -3.20%, PF 1.11 | n=1091, win 52.4%, mean +0.0924%, median +0.0737%, P05 -2.70%, PF 1.16 |
| Q4 | n=173, win 59.5%, mean +0.3163%, median +0.2717%, P05 -1.91%, PF 1.71 | n=208, win 48.1%, mean +0.0136%, median -0.0640%, P05 -3.18%, PF 1.02 | n=1009, win 48.1%, mean -0.0167%, median -0.0467%, P05 -2.90%, PF 0.97 |
| Q5 | n=383, win 47.5%, mean -0.0345%, median -0.0896%, P05 -2.63%, PF 0.94 | n=413, win 51.8%, mean +0.1600%, median +0.0652%, P05 -2.57%, PF 1.29 | n=2086, win 46.1%, mean -0.0068%, median -0.1162%, P05 -3.03%, PF 0.99 |

---

## Which hypothesis does the shape support?

Median 4h return by LPL quintile, per regime (from the matrix above):

| Regime | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| ranging | -0.0167% | +0.1282% | +0.0970% | +0.2717% | -0.0896% |
| transitioning | +0.2824% | +0.1922% | +0.2395% | -0.0640% | +0.0652% |
| trending | +0.3159% | +0.2882% | +0.0737% | -0.0467% | -0.1162% |

Q1 movement (trending - ranging): +0.3326%
Q5 movement (trending - ranging): -0.0266%

**Hypothesis A dominant: Q1 improves much more than Q5 degrades as regime shifts toward trending.**
