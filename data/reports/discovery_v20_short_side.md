# Discovery v20 — the short side (`avoid_long`), tested for the first time

Generated 2026-07-27T05:23:52.757423+00:00.

`avoid_long` (LPL==Q5 & Vol==Q5) has been explicitly non-tradeable since Phase B and was never revisited, despite discovery_v5 finding a negative 4h median in 7/7 years. Purely descriptive; does not change decision_rule_v1 and does not propose trading shorts. Discovery only (2020-2025); 2026 untouched.

---

## A. Short trades from `avoid_long`, by hold length

The long side is shown at the same hold for reference. Both pay identical fees and the same stated 5bps/side slippage assumption.

| Hold | Side | Stats |
|---|---|---|
| 240m | **short (avoid_long)** | n=945, win 45.2%, median -0.1056%, mean -0.1903%, P05 -3.62%, PF 0.760, equity 0.1372, maxDD -88.43% |
| 240m | long (reference) | n=1,064, win 51.4%, median +0.0473%, mean -0.1306%, P05 -4.19%, PF 0.853, equity 0.1731, maxDD -82.94% |
| 480m | **short (avoid_long)** | n=585, win 45.3%, median -0.1836%, mean -0.2379%, P05 -4.80%, PF 0.782, equity 0.2014, maxDD -83.89% |
| 480m | long (reference) | n=674, win 54.0%, median +0.1844%, mean -0.0390%, P05 -4.99%, PF 0.964, equity 0.5139, maxDD -67.70% |
| 1440m | **short (avoid_long)** | n=315, win 47.6%, median -0.0944%, mean -0.2221%, P05 -7.21%, PF 0.869, equity 0.3539, maxDD -80.92% |
| 1440m | long (reference) | n=365, win 56.4%, median +0.5179%, mean +0.3718%, P05 -6.76%, PF 1.255, equity 2.2701, maxDD -49.62% |

---

## B. Unmodelled cost: funding

Verified absent from both the stored candidate state and the raw backfill cache (which holds OHLCV only): **funding rate is not in this dataset**. A real perpetual-futures short pays or receives funding every 8h, and during sustained bull periods a short typically *pays*. The simulation above therefore **overstates** short-side returns by an unknown amount that grows with hold length — the 1440m rows are the most affected. `exchange_client.py` can fetch funding history, but Bitget caps it at roughly 100 records (~33 days), so backfilling it to 2020 is not possible; only prospective collection would fix this.

This is a hard limit on how far the short-side numbers can be trusted, not a rounding detail.

---

## C. Year stability — short side at 1440m (its best hold by profit factor)

A short that only worked in one bear year is a directional bet on that period, not an edge.

| Year | n | Win rate | Median | Mean |
|---|---|---|---|---|
| 2020 | 56 | 50.0% | -0.0110% | +0.3016% |
| 2021 | 135 | 46.7% | -0.2839% | -0.4389% |
| 2022 | 57 | 52.6% | +0.2161% | +0.0446% |
| 2023 | 17 | n too few | - | - |
| 2024 | 32 | 46.9% | -0.0622% | -0.3568% |
| 2025 | 18 | n too few | - | - |

Years with positive median: 1/4

