# Discovery v18 — entry timing (delay entry by N minutes)

Generated 2026-07-27T05:15:21.436670+00:00.

Unlike decision_rule_v3's entry FILTER, delaying entry keeps the same signal set and the same trade sequence, so it cannot produce the Option-A retention artifact that sank that candidate (discovery_v16) -- only the entry price changes. Hold length is held constant at 4h. Fees and the stated 5bps/side slippage assumption unchanged. Purely descriptive; does not change decision_rule_v1. Discovery only (2020-2025); 2026 untouched.

---

## A. All decision_rule_v1 trades, entry delayed by N minutes

Hold length held constant at 4h, so this isolates entry timing. N=0 reproduces `phase_c_baseline_v1.py`.

| Delay | n | Win rate | Median | Mean | P05 | Profit factor | Final equity | Max DD |
|---|---|---|---|---|---|---|---|---|
| 0m (baseline) | 1,064 | 51.4% | +0.0473% | -0.1306% | -4.19% | 0.853 | 0.1731 | -82.94% |
| 1m | 1,064 | 51.6% | +0.0562% | -0.1349% | -4.20% | 0.849 | 0.1618 | -84.00% |
| 2m | 1,064 | 51.7% | +0.0763% | -0.1424% | -4.22% | 0.842 | 0.1497 | -85.15% |
| 3m | 1,064 | 51.5% | +0.0586% | -0.1436% | -4.31% | 0.840 | 0.1490 | -85.23% |
| 5m | 1,064 | 51.2% | +0.0352% | -0.1410% | -4.11% | 0.842 | 0.1527 | -84.70% |
| 10m | 1,064 | 52.1% | +0.0740% | -0.1291% | -3.96% | 0.854 | 0.1739 | -84.01% |
| 15m | 1,064 | 50.6% | +0.0143% | -0.1252% | -4.04% | 0.858 | 0.1725 | -84.07% |
| 30m | 1,064 | 50.8% | +0.0232% | -0.1296% | -4.13% | 0.850 | 0.1778 | -86.10% |

---

## B. Subgroup: signals following a sharp 5m drop (micro_return_5m == Q1)

If delaying entry helps because price is still moving when the signal fires, the effect should be strongest here.

| Delay | n | Win rate | Median | Mean | Profit factor |
|---|---|---|---|---|---|
| 0m (baseline) | 724 | 50.7% | +0.0260% | -0.0915% | 0.897 |
| 1m | 724 | 50.7% | +0.0270% | -0.0861% | 0.903 |
| 2m | 724 | 50.7% | +0.0263% | -0.1018% | 0.887 |
| 3m | 724 | 49.6% | -0.0303% | -0.1264% | 0.861 |
| 5m | 724 | 49.3% | -0.0128% | -0.1461% | 0.841 |
| 10m | 724 | 50.1% | +0.0042% | -0.1477% | 0.840 |
| 15m | 724 | 48.9% | -0.0498% | -0.1308% | 0.857 |
| 30m | 724 | 49.7% | -0.0053% | -0.1808% | 0.807 |
