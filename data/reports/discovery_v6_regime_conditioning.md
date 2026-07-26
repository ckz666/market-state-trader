# Discovery v6 — regime conditioning of the frozen LPL x Volatility edge

Generated 2026-07-26T18:43:55.824637+00:00.

Purely descriptive; does not change decision_rule_v1 or propose a new rule. Tests whether the already-validated LPL x Volatility edge (restricted to Vol=Q5, decision_rule_v1's actual traded regime) is uniform across `context_4h.regime` / `context_4h.structure_trend` -- fields already collected in every candidate but never used in discovery_v1-v5. Same frozen LPL/quintile-edge parameters as hypothesis_validation.py (fit on 2020-2025 only). Discovery only; 2026 untouched -- this is a new sub-hypothesis and would get its own OOS step later if it survives this descriptive pass. Cells with n < 15 are marked instead of reported.

---

n Discovery candidates: 52,608. `regime_4h` value counts: {'trending': 30584, 'ranging': 12744, 'transitioning': 9280}. `structure_trend_4h` value counts: {'sideways': 26432, 'uptrend': 9224, 'downtrend': 7280, 'contracting': 5204, 'expanding': 4468}.

---

## LPL=Q1 vs LPL=Q5 (4h return), split by `regime_4h` (Vol=Q5 only)

| Regime | n (Q1) | LPL=Q1 | n (Q5) | LPL=Q5 | Spread (Q1 - Q5 median) |
|---|---|---|---|---|---|
| ranging | 544 | n=544, median -0.0167%, mean -0.2589%, win 48.9% | 383 | n=383, median -0.0896%, mean -0.0345%, win 47.5% | +0.0730% |
| transitioning | 477 | n=477, median +0.2824%, mean +0.1318%, win 59.1% | 413 | n=413, median +0.0652%, mean +0.1600%, win 51.8% | +0.2172% |
| trending | 2255 | n=2255, median +0.3159%, mean +0.1496%, win 58.2% | 2086 | n=2086, median -0.1162%, mean -0.0068%, win 46.1% | +0.4321% |

---

## LPL=Q1 vs LPL=Q5 (4h return), split by `structure_trend_4h` (Vol=Q5 only)

| Structure trend | n (Q1) | LPL=Q1 | n (Q5) | LPL=Q5 | Spread (Q1 - Q5 median) |
|---|---|---|---|---|---|
| contracting | 219 | n=219, median +0.3774%, mean +0.3864%, win 64.8% | 252 | n=252, median +0.0117%, mean +0.1666%, win 50.4% | +0.3658% |
| downtrend | 479 | n=479, median +0.3448%, mean +0.2671%, win 59.1% | 522 | n=522, median +0.0450%, mean +0.1551%, win 51.5% | +0.2999% |
| expanding | 252 | n=252, median +0.0863%, mean -0.1491%, win 53.6% | 200 | n=200, median -0.2211%, mean -0.1062%, win 39.5% | +0.3075% |
| sideways | 1851 | n=1851, median +0.1918%, mean +0.0092%, win 55.3% | 1503 | n=1503, median -0.0969%, mean -0.0265%, win 46.7% | +0.2887% |
| uptrend | 475 | n=475, median +0.2536%, mean +0.1418%, win 58.3% | 405 | n=405, median -0.2348%, mean -0.0570%, win 44.4% | +0.4884% |

---

## Time stability: `regime_4h == 'trending'`, LPL=Q1 vs Q5, Vol=Q5, 4h

Widest spread from the cut above (widest spread in section A). Per-year check, same convention as discovery_v5 SS5 -- an effect that flips sign across years is not a finding.

| Year | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread |
|---|---|---|---|---|---|
| 2020 | 390 | +0.3906% | 367 | -0.2173% | +0.6079% |
| 2021 | 832 | +0.4420% | 882 | +0.0541% | +0.3879% |
| 2022 | 532 | +0.0538% | 324 | -0.2934% | +0.3472% |
| 2023 | 66 | +0.1103% | 163 | -0.1078% | +0.2181% |
| 2024 | 291 | +0.3715% | 232 | -0.1713% | +0.5427% |
| 2025 | 144 | +0.3961% | 118 | -0.2418% | +0.6379% |

Sign consistency: 6/6 years positive (Q1 > Q5 median)

