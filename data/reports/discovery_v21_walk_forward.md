# Discovery v21 — walk-forward validation of the 24h hold

Generated 2026-07-27T05:29:22.048281+00:00.

**Read the caveats before the numbers.** This is expanding-origin walk-forward: for each test year, all transform parameters are fit on prior years only and applied frozen. But this is NOT out-of-sample — every year 2020-2025 has been examined repeatedly across discovery_v1-v20, and the idea of testing a 24h hold came from having already looked at this data (discovery_v19). It does not replace the 2026 validation (decision_rule_v4's n=16 result remains the only genuine OOS evidence), and it *increases* multiple-testing exposure rather than reducing it. What it can legitimately show is whether the 24h advantage is consistent across regimes or carried by one or two periods.

---

## A. Per-fold results (parameters fit on prior years only)

| Test year | Train rows | Hold | n | Win rate | Net median | Mean | Profit factor |
|---|---|---|---|---|---|---|---|
| 2021 | 8,784 | 4h | 458 | 50.9% | +0.0237% | -0.1174% | 0.878 |
| 2021 | 8,784 | 24h | 145 | 55.9% | +0.5179% | +0.3716% | 1.248 |
| 2022 | 17,544 | 4h | 114 | 44.7% | -0.1957% | -0.3694% | 0.678 |
| 2022 | 17,544 | 24h | 35 | 37.1% | -0.7908% | -0.6181% | 0.741 |
| 2023 | 26,304 | 4h | 11 ⚠ | 54.5% | +0.1856% | +0.4768% | 3.121 |
| 2023 | 26,304 | 24h | 5 ⚠ | 80.0% | +2.8188% | +2.9296% | 20.359 |
| 2024 | 35,064 | 4h | 93 | 51.6% | +0.0789% | +0.0243% | 1.038 |
| 2024 | 35,064 | 24h | 36 | 69.4% | +1.0119% | +0.8200% | 2.118 |
| 2025 | 43,848 | 4h | 62 | 45.2% | -0.2109% | -0.2147% | 0.735 |
| 2025 | 43,848 | 24h | 21 | 52.4% | +0.0019% | +0.3284% | 1.303 |

⚠ = fewer than 15 trades in that fold; treat as directional only.


## B. Does 24h beat 4h, fold by fold?

| Test year | Win rate | Net median | Profit factor | All three? |
|---|---|---|---|---|
| 2021 | yes | yes | yes | **yes** |
| 2022 | no | no | yes | no |
| 2023 (n<15) | yes | yes | yes | **yes** |
| 2024 | yes | yes | yes | **yes** |
| 2025 | yes | yes | yes | **yes** |

**Folds where 24h beat 4h:** win rate 4/5, net median 4/5, profit factor 5/5. All three simultaneously: 4/5.

