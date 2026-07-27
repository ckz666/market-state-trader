# Discovery v16 — explaining decision_rule_v3's trade-vs-candidate OOS discrepancy

Generated 2026-07-27T05:04:09.086033+00:00.

The 2026 OOS run disagreed between its trade-level (n=24, filter looks strong) and candidate-level (n=45, filter looks mildly harmful) views. This reproduces both views on Discovery, where they have ~1,000 trades and ~3,000 candidates, to distinguish small-sample noise from a systematic Option-A-de-duplication mechanism. Purely diagnostic; does not change decision_rule_v1 and re-tunes nothing. Discovery only (2020-2025).

---

## A. Both views on Discovery (2020-2025) — 40x the OOS sample

| View | Population | Stats |
|---|---|---|
| Trade level (Option A, fees) | Baseline | n=1,064, win 51.4%, mean -0.1306%, median +0.0473%, PF 0.853 |
| Trade level (Option A, fees) | + micro_return_5m==Q1 | n=724, win 50.7%, mean -0.0915%, median +0.0260%, PF 0.897 |
| Candidate level (raw signals) | Baseline | n=3,276, win 56.8%, mean +0.0792%, median +0.2324%, PF 1.100 |
| Candidate level (raw signals) | + micro_return_5m==Q1 | n=1,313, win 58.2%, mean +0.1106%, median +0.3118%, PF 1.128 |

**Direction of the filter's effect, per view:**

| Metric | Trade level | Candidate level | Agree? |
|---|---|---|---|
| Win rate | -0.7192pp | +1.3803pp | **NO** |
| Median | -0.0213pp | +0.0795pp | **NO** |
| Profit factor | +0.044 | +0.028 | yes |

---

## B. Does the filter interact with Option A de-duplication itself?

Option A keeps the FIRST signal of a cluster and skips the rest while that position is open. If filtered signals sit at systematically different positions within clusters, the filter changes *which* signals survive de-duplication, not just how many — a mechanism that would produce a trade-vs-candidate discrepancy with no predictive content involved.

**Signal-to-trade retention rate:**

| Population | Candidates | Trades | Retention |
|---|---|---|---|
| Baseline | 3,276 | 1,064 | 32.5% |
| Filtered (ret5m==Q1) | 1,313 | 724 | 55.1% |

**Position within signal cluster (0 = first signal, which Option A always takes):**

| Population | n | Mean position | Median position | % at position 0 |
|---|---|---|---|---|
| All signals | 3,276 | 6.75 | 5.0 | 13.1% |
| Filtered (ret5m==Q1) | 1,313 | 6.67 | 5.0 | 15.9% |
| Non-filtered | 1,963 | 6.80 | 5.0 | 11.3% |

If the filtered population sits disproportionately at position 0, it is over-represented among exactly the signals Option A would have taken anyway — meaning the filter's apparent trade-level benefit partly reflects cluster timing rather than signal quality.


---

## Reference: the 2026 OOS numbers this is explaining

Quoted unchanged from `decision_rule_v3_micro_return_filter_oos_v1.md` (not recomputed here).

| View | Baseline | Filtered |
|---|---|---|
| Trade level | n=39, win 51.3%, median +0.1787%, PF 0.868 | n=24, win 54.2%, median +0.3772%, PF 1.565 |
| Candidate level | n=113, win 59.3%, median +0.3110%, PF 1.122 | n=45, win 57.8%, median +0.3110%, PF 0.965 |
