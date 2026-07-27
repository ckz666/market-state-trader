# Discovery v22 — concurrent positions

Generated 2026-07-27T05:37:04.295941+00:00.

Option A discards every signal arriving while a position is open — 68% of signals at the 4h hold, 89% at the 24h candidate. Whether those discarded signals are worth taking has never been tested. Section A answers that directly (per-slot trade quality, no capital assumptions); section B gives an approximate portfolio view. Purely descriptive; does not change decision_rule_v1. Discovery only (2020-2025); 2026 untouched. ⚠ marks fewer than 15 trades.

---

## Hold 240m

### A. Per-slot trade quality (unlimited slots)

Slot 0 is exactly what Option A takes today; slots 1+ are the signals it discards. No capital assumptions involved.

| Slot | Stats |
|---|---|
| 0 (= Option A) | n=1,064, win 51.4%, median +0.0473%, mean -0.1306%, PF 0.853 |
| 1 | n=886, win 50.0%, median -0.0019%, mean -0.0875%, PF 0.899 |
| 2 | n=741, win 49.1%, median -0.0253%, mean -0.1902%, PF 0.784 |
| 3 | n=585, win 49.6%, median -0.0240%, mean -0.1599%, PF 0.830 |

Total trades with unlimited slots: **3,276** of 3,276 signals.

### B. Portfolio approximation by slot count

Equity assumes equal 1/K allocation per slot, compounded in exit order. **Approximation:** it ignores capital sitting idle when fewer than K slots are filled, which flatters higher K. Included for scale, not as a precise backtest.

| Slots (K) | n trades | Win rate | Median | Mean | PF | Approx. equity |
|---|---|---|---|---|---|---|
| 1 (= Option A) | 1,064 | 51.4% | +0.0473% | -0.1306% | 0.853 | 0.1731 |
| 2 | 1,950 | 50.8% | +0.0224% | -0.1110% | 0.873 | 0.2898 |
| 3 | 2,691 | 50.3% | +0.0106% | -0.1328% | 0.849 | 0.2768 |
| 5 | 3,276 | 50.2% | +0.0070% | -0.1377% | 0.845 | 0.3889 |
| unlimited | 3,276 | 50.2% | +0.0070% | -0.1377% | 0.845 | 0.7960 |

## Hold 1440m

### A. Per-slot trade quality (unlimited slots)

Slot 0 is exactly what Option A takes today; slots 1+ are the signals it discards. No capital assumptions involved.

| Slot | Stats |
|---|---|
| 0 (= Option A) | n=365, win 56.4%, median +0.5179%, mean +0.3718%, PF 1.255 |
| 1 | n=316, win 55.7%, median +0.5483%, mean +0.2386%, PF 1.157 |
| 2 | n=286, win 56.6%, median +0.5745%, mean +0.2064%, PF 1.134 |
| 3 | n=255, win 57.3%, median +0.4851%, mean +0.3224%, PF 1.220 |
| 4 | n=240, win 60.0%, median +0.9261%, mean +0.4461%, PF 1.290 |
| 5 | n=218, win 60.6%, median +0.8202%, mean +0.6678%, PF 1.432 |
| 6+ | n=1,596, win 62.4%, median +0.8937%, mean +0.9740%, PF 1.745 |

Total trades with unlimited slots: **3,276** of 3,276 signals.

### B. Portfolio approximation by slot count

Equity assumes equal 1/K allocation per slot, compounded in exit order. **Approximation:** it ignores capital sitting idle when fewer than K slots are filled, which flatters higher K. Included for scale, not as a precise backtest.

| Slots (K) | n trades | Win rate | Median | Mean | PF | Approx. equity |
|---|---|---|---|---|---|---|
| 1 (= Option A) | 365 | 56.4% | +0.5179% | +0.3718% | 1.255 | 2.2701 |
| 2 | 681 | 56.1% | +0.5391% | +0.3100% | 1.208 | 2.3088 |
| 3 | 967 | 56.3% | +0.5528% | +0.2794% | 1.186 | 2.1591 |
| 5 | 1,462 | 57.0% | +0.5836% | +0.3142% | 1.209 | 2.3329 |
| unlimited | 3,276 | 59.9% | +0.7320% | +0.6592% | 1.468 | 2.9131 |
