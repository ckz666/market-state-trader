# Phase C trade-path analysis v2 — time-dependent MAE/MFE

Generated 2026-07-26T14:47:34.573797+00:00.

Same exact trades as phase_c_baseline_v1.py / phase_c_trade_path_analysis.py. Still purely descriptive — no stop-loss, take-profit, or exit rule is chosen or tested here.

---

# Discovery (2020-2025, in-sample)

## 1. Time-dependent MAE/MFE (running, not final)

Return, running MAE, and running MFE AT each checkpoint (i.e. MAE/MFE computed only from entry up to that point, not over the whole 4h hold) — winners vs. losers.

Winners: 547, Losers: 517

| Checkpoint | Ret (W) | Ret (L) | MAE-so-far (W) | MAE-so-far (L) | MFE-so-far (W) | MFE-so-far (L) |
|---|---|---|---|---|---|---|
| 15m | +0.1334% | -0.1286% | -0.4023% | -0.4956% | +0.4841% | +0.3241% |
| 30m | +0.2749% | -0.2217% | -0.5249% | -0.7534% | +0.7063% | +0.4248% |
| 1h | +0.5115% | -0.4372% | -0.6754% | -1.1547% | +1.0859% | +0.5470% |
| 2h | +0.8850% | -0.8411% | -0.8011% | -1.7897% | +1.5707% | +0.6806% |
| 3h | +1.3026% | -1.2180% | -0.8540% | -2.3258% | +2.0151% | +0.7415% |
| 4h | +1.6889% | -1.6030% | -0.8639% | -2.8379% | +2.3826% | +0.7704% |

## 2. Winner drawdown-depth distribution

v1 found 90.5%/85.0% of winners dip negative at some point. How deep, typically?

n winners = 547

| MAE bucket | Count | % of winners |
|---|---|---|
| 0 to -0.25% | 162 | 29.6% |
| -0.25% to -0.5% | 98 | 17.9% |
| -0.5% to -1.0% | 124 | 22.7% |
| -1.0% to -2.0% | 116 | 21.2% |
| under -2.0% | 47 | 8.6% |
| never dipped (MAE >= 0) | 52 | 9.5% |

## 3. P(eventual winner | trade reached this much drawdown)

Purely descriptive — no threshold is chosen or recommended as a stop. Among only the trades whose full-trade MAE reached at least this much adverse excursion at some point, what fraction still closed as a winner?

| Drawdown reached | n trades that reached it | Win rate among them |
|---|---|---|
| (baseline, all trades) | 1,064 | 51.4% |
| <= -0.25% | 894 | 43.1% |
| <= -0.50% | 770 | 37.3% |
| <= -1.00% | 568 | 28.7% |
| <= -1.50% | 442 | 22.6% |
| <= -2.00% | 309 | 15.2% |
| <= -3.00% | 194 | 10.8% |

---

# Validation (2026, out-of-sample)

## 1. Time-dependent MAE/MFE (running, not final)

Return, running MAE, and running MFE AT each checkpoint (i.e. MAE/MFE computed only from entry up to that point, not over the whole 4h hold) — winners vs. losers.

Winners: 20, Losers: 19

| Checkpoint | Ret (W) | Ret (L) | MAE-so-far (W) | MAE-so-far (L) | MFE-so-far (W) | MFE-so-far (L) |
|---|---|---|---|---|---|---|
| 15m | +0.2272% | -0.0746% | -0.3629% | -0.4483% | +0.5794% | +0.3298% |
| 30m | +0.3372% | -0.2401% | -0.5057% | -0.7449% | +0.8008% | +0.4594% |
| 1h | +0.3899% | -0.3473% | -0.7205% | -1.0705% | +1.1217% | +0.5094% |
| 2h | +0.8004% | -0.5849% | -1.0086% | -1.5683% | +1.5480% | +0.5919% |
| 3h | +1.2017% | -0.8956% | -1.1039% | -1.8889% | +1.9726% | +0.8012% |
| 4h | +1.3612% | -1.1646% | -1.1217% | -2.1538% | +2.1575% | +0.8020% |

## 2. Winner drawdown-depth distribution

v1 found 90.5%/85.0% of winners dip negative at some point. How deep, typically?

n winners = 20

| MAE bucket | Count | % of winners |
|---|---|---|
| 0 to -0.25% | 5 | 25.0% |
| -0.25% to -0.5% | 4 | 20.0% |
| -0.5% to -1.0% | 5 | 25.0% |
| -1.0% to -2.0% | 3 | 15.0% |
| under -2.0% | 3 | 15.0% |
| never dipped (MAE >= 0) | 3 | 15.0% |

## 3. P(eventual winner | trade reached this much drawdown)

Purely descriptive — no threshold is chosen or recommended as a stop. Among only the trades whose full-trade MAE reached at least this much adverse excursion at some point, what fraction still closed as a winner?

| Drawdown reached | n trades that reached it | Win rate among them |
|---|---|---|
| (baseline, all trades) | 39 | 51.3% |
| <= -0.25% | 34 | 44.1% |
| <= -0.50% | 28 | 39.3% |
| <= -1.00% | 20 | 30.0% |
| <= -1.50% | 18 | 27.8% |
| <= -2.00% | 13 | 23.1% |
| <= -3.00% | 5 | 40.0% |

---

