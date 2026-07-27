# Funding rate backfill

Generated 2026-07-27T06:14:19.897369+00:00.

**Source mismatch, stated plainly:** every price/kline in this project comes from **Bitget**, but Bitget's funding history is capped at ~100 records (~33 days) and ignores `since` (verified directly via ccxt). Complete history back to 2020 is only available from **Binance** (data.binance.vision). These figures therefore pair Binance funding with Bitget prices — an approximation whose error is measured below rather than assumed.

---

## Coverage

- Intervals: **7,119** (8h funding)
- Range: 2020-01-01 00:00:00+00:00 to 2026-06-30 16:00:00.005000+00:00

| Year | Intervals | Mean rate per 8h | Median rate per 8h | Annualized cost to a LONG |
|---|---|---|---|---|
| 2020 | 1,098 | +0.01570% | +0.01000% | +17.19% |
| 2021 | 1,095 | +0.02795% | +0.01000% | +30.61% |
| 2022 | 1,095 | +0.00380% | +0.00513% | +4.16% |
| 2023 | 1,095 | +0.00718% | +0.00826% | +7.87% |
| 2024 | 1,098 | +0.01089% | +0.01000% | +11.92% |
| 2025 | 1,095 | +0.00468% | +0.00483% | +5.13% |
| 2026 | 543 | +0.00103% | +0.00152% | +1.13% |

---

## Proxy error: Binance funding vs. Bitget's own

Overlapping funding intervals compared: **10** (2026-06-25 00:00:00 to 2026-06-30 08:00:00)

- Correlation Binance vs Bitget: **+0.7982**
- Mean Bitget rate: +0.00623% per 8h
- Mean Binance rate: +0.00384% per 8h
- Mean absolute difference: **0.284 bps per 8h interval** (= 0.85 bps/day, 3.11%/year)
- Max absolute difference: 0.64 bps

This is the measured cost of using Binance funding as a stand-in for Bitget. It is small relative to typical funding levels but not zero, and it is a real limitation of every funding-adjusted number downstream.
