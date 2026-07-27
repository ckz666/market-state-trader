# Discovery v11 — do the new 15m/1m candidates add information beyond LPL?

Generated 2026-07-27T04:19:20.118543+00:00.

Purely descriptive; does not change decision_rule_v1. Mirrors discovery_v2's original bb_position/vwap_distance correlation check, applied to discovery_v10's standout 15m/1m candidates (`short_term_rsi_15m`, `short_term_range_position_20_15m`, `micro_return_5m`, `short_term_direction_15m`). Same frozen LPL/quintile-edge parameters as hypothesis_validation.py. Discovery only; 2026 untouched. Cells with n < 15 are marked instead of reported.

---

## A. Correlation matrix (Pearson) with frozen LPL

`short_term_direction_15m_enc`: bearish=-1, neutral=0, bullish=+1.

| | local_price_location | short_term_rsi_15m | short_term_range_position_20_15m | micro_return_5m | short_term_direction_15m_enc |
|---|---|---|---|---|---|
| local_price_location | +1.000 | +0.822 | +0.537 | +0.127 | +0.479 |
| short_term_rsi_15m | +0.822 | +1.000 | +0.818 | +0.186 | +0.738 |
| short_term_range_position_20_15m | +0.537 | +0.818 | +1.000 | +0.213 | +0.828 |
| micro_return_5m | +0.127 | +0.186 | +0.213 | +1.000 | +0.123 |
| short_term_direction_15m_enc | +0.479 | +0.738 | +0.828 | +0.123 | +1.000 |

**PCA on standardized [LPL, short_term_rsi_15m, short_term_range_position_20_15m, micro_return_5m]:**

- PC1 explains 63.0% of variance (loadings: local_price_location=-0.539, short_term_rsi_15m=-0.610, short_term_range_position_20_15m=-0.547, micro_return_5m=-0.196)
- PC2 explains 23.7% of variance (loadings: local_price_location=-0.194, short_term_rsi_15m=-0.125, short_term_range_position_20_15m=-0.019, micro_return_5m=+0.973)

If PC1 alone explained the large majority of variance with all loadings the same sign, these fields would mostly be measuring the same thing (as bb_position/vwap_distance did before collapsing into LPL). If variance is spread across multiple components, they carry more independent information.


---

## B. Conditional incremental test: LPL quintile x candidate (Q1 vs Q5), Vol=Q5, 4h


### short_term_rsi_15m

| LPL | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread |
|---|---|---|---|---|---|
| Q1 | 1752 | n too few | 1 | n too few | - |
| Q2 | 214 | +0.3085% | 37 | +0.0416% | +0.2669% |
| Q3 | 111 | +0.3380% | 134 | +0.0148% | +0.3233% |
| Q4 | 19 | +0.0835% | 243 | -0.0927% | +0.1762% |
| Q5 | 7 | n too few | 1686 | n too few | - |

### short_term_range_position_20_15m

| LPL | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread |
|---|---|---|---|---|---|
| Q1 | 1270 | +0.4417% | 153 | -0.1611% | +0.6028% |
| Q2 | 316 | +0.2577% | 227 | +0.0509% | +0.2068% |
| Q3 | 246 | +0.1329% | 270 | -0.0061% | +0.1390% |
| Q4 | 155 | +0.2282% | 323 | -0.1323% | +0.3605% |
| Q5 | 117 | +0.2196% | 1130 | -0.1037% | +0.3233% |

### micro_return_5m

| LPL | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread |
|---|---|---|---|---|---|
| Q1 | 872 | +0.3464% | 662 | +0.1818% | +0.1646% |
| Q2 | 290 | +0.3502% | 228 | +0.1625% | +0.1877% |
| Q3 | 266 | +0.0936% | 246 | -0.0499% | +0.1434% |
| Q4 | 205 | -0.0590% | 250 | +0.0499% | -0.1089% |
| Q5 | 473 | -0.0242% | 716 | -0.1372% | +0.1130% |

### short_term_direction_15m

| LPL | n (bearish) | bearish median | n (bullish) | bullish median | Spread |
|---|---|---|---|---|---|
| Q1 | 1800 | +0.3427% | 244 | -0.0862% | +0.4290% |
| Q2 | 617 | +0.3572% | 542 | +0.0856% | +0.2716% |
| Q3 | 583 | +0.1358% | 661 | +0.0795% | +0.0563% |
| Q4 | 363 | +0.1238% | 687 | -0.0966% | +0.2204% |
| Q5 | 183 | +0.1439% | 1566 | -0.1166% | +0.2605% |
