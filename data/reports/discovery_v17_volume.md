# Discovery v17 — volume (never tested in discovery_v1-v16)

Generated 2026-07-27T05:13:58.327074+00:00.

`volume` is stored for every candidate but appears in no dimension of discovery_report.py. Raw volume is non-stationary across 2020-2025 (a raw quintile split would largely encode *which year* a sample came from), so three trailing-window normalized variants are used instead, none of which look past the state candle. Purely descriptive; does not change decision_rule_v1. Discovery only (2020-2025); 2026 untouched. Cells with n < 30 are marked instead of reported.

---

## A. Univariate — normalized volume variants


### volume_rel_24h  (n=52,432)

| Quintile | 15m win% / median | 1h win% / median | 4h win% / median |
|---|---|---|---|
| Q1 | 49.2% / -0.0027% | 50.8% / +0.0061% | 50.8% / +0.0108% |
| Q2 | 49.7% / +0.0000% | 50.4% / +0.0046% | 51.8% / +0.0219% |
| Q3 | 50.1% / +0.0014% | 50.7% / +0.0073% | 51.2% / +0.0195% |
| Q4 | 50.6% / +0.0044% | 50.9% / +0.0088% | 51.2% / +0.0215% |
| Q5 | 51.2% / +0.0089% | 50.9% / +0.0105% | 51.5% / +0.0305% |

4h Q5-Q1 median spread: **+0.0197%**


### volume_rel_7d  (n=52,576)

| Quintile | 15m win% / median | 1h win% / median | 4h win% / median |
|---|---|---|---|
| Q1 | 49.8% / +0.0000% | 51.1% / +0.0070% | 51.4% / +0.0159% |
| Q2 | 49.1% / -0.0025% | 50.4% / +0.0046% | 50.8% / +0.0119% |
| Q3 | 50.6% / +0.0041% | 51.0% / +0.0102% | 51.4% / +0.0207% |
| Q4 | 50.6% / +0.0053% | 51.2% / +0.0115% | 51.6% / +0.0303% |
| Q5 | 51.4% / +0.0103% | 50.8% / +0.0095% | 51.9% / +0.0425% |

4h Q5-Q1 median spread: **+0.0266%**


### volume_trend_24h  (n=52,432)

| Quintile | 15m win% / median | 1h win% / median | 4h win% / median |
|---|---|---|---|
| Q1 | 49.2% / -0.0023% | 50.3% / +0.0024% | 51.7% / +0.0195% |
| Q2 | 50.8% / +0.0046% | 50.8% / +0.0090% | 50.6% / +0.0112% |
| Q3 | 50.0% / +0.0008% | 51.0% / +0.0104% | 51.6% / +0.0260% |
| Q4 | 50.0% / +0.0008% | 50.7% / +0.0077% | 50.7% / +0.0129% |
| Q5 | 50.8% / +0.0052% | 50.9% / +0.0090% | 51.8% / +0.0383% |

4h Q5-Q1 median spread: **+0.0188%**


---

## B. Year stability — `volume_rel_7d` (widest 4h spread from section A)

Frozen quintile edges (fit on the full Discovery period) applied per year.

| Year | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| 2020 | 1,037 | +0.2287% | 1,729 | +0.0439% | -0.1848% |
| 2021 | 1,203 | -0.0092% | 1,873 | +0.1399% | +0.1491% |
| 2022 | 1,621 | -0.0136% | 1,778 | -0.0176% | -0.0040% |
| 2023 | 1,428 | +0.0191% | 1,572 | +0.0313% | +0.0122% |
| 2024 | 1,933 | +0.0329% | 1,685 | +0.0752% | +0.0423% |
| 2025 | 3,294 | -0.0042% | 1,878 | +0.0249% | +0.0291% |

Sign consistency: 4/6 years


---

## C. Interaction — `volume_rel_7d`

Correlation with `volatility_atr_norm`: **+0.119**; with `local_price_location` (LPL): **-0.028**. High correlation with volatility would mean this is largely a re-measurement of a factor already in use.


**LPL=Q1 vs Q5 (4h median), split by volume quintile — does volume amplify the LPL edge?**

| Volume quintile | n (LPL Q1) | LPL Q1 median | n (LPL Q5) | LPL Q5 median | Spread |
|---|---|---|---|---|---|
| Q1 | 1,076 | +0.1125% | 1,214 | -0.0999% | +0.2124% |
| Q2 | 1,533 | +0.1124% | 1,698 | -0.0911% | +0.2036% |
| Q3 | 1,976 | +0.1479% | 2,029 | -0.0381% | +0.1860% |
| Q4 | 2,436 | +0.1136% | 2,511 | -0.0802% | +0.1938% |
| Q5 | 3,466 | +0.1303% | 3,034 | -0.0299% | +0.1601% |
