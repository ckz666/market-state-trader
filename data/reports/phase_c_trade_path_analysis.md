# Phase C trade-path analysis — MAE/MFE, not optimization

Generated 2026-07-26T14:40:31.760324+00:00.

Same exact trades as phase_c_baseline_v1.py (same signals, same Option A logic, same entry/exit). This is analysis of the existing hypothesis's trade paths — no stop-loss, take-profit, or exit timing is chosen or tested here. The question is only: does the negative mean / profit-factor<1 result come from a few extreme tail losses, or a broadly negative-skew profile across most trades — and are winners/losers distinguishable early?

---

## Results

### Discovery (2020-2025, in-sample) (n=1,064 trades with full path data)

Winners: 547 (51.4%). Losers: 517 (48.6%).

**Average return at each checkpoint, winners vs. losers:**

| Checkpoint | Winners (mean) | Losers (mean) |
|---|---|---|
| 15m | +0.1334% | -0.1286% |
| 30m | +0.2749% | -0.2217% |
| 1h | +0.5115% | -0.4372% |
| 2h | +0.8850% | -0.8411% |
| 3h | +1.3026% | -1.2180% |
| 4h | +1.6889% | -1.6030% |

**MAE / MFE, winners vs. losers:**

| Group | Mean MAE | Median MAE | Mean MFE | Median MFE |
|---|---|---|---|---|
| Winners | -0.8639% | -0.5401% | +2.3826% | +1.8260% |
| Losers | -2.8379% | -2.0323% | +0.7704% | +0.6099% |

- Winners that dipped negative at some point before closing positive (MAE < 0): 90.5%
- Losers that rose above entry at some point before closing negative (MFE > 0): 92.5%

**Loser MAE distribution** (is the negative mean driven by a few extreme tail trades, or broadly negative across most losers?):

| Percentile | MAE |
|---|---|
| P10 | -5.8583% |
| P25 | -3.5081% |
| P50 | -2.0323% |
| P75 | -1.1259% |
| P90 | -0.6088% |

Worst 10% of losers by MAE: 52 trades, mean MAE -9.0461% vs. the other 90% of losers' mean MAE -2.1436%


### Validation (2026, out-of-sample) (n=39 trades with full path data)

Winners: 20 (51.3%). Losers: 19 (48.7%).

**Average return at each checkpoint, winners vs. losers:**

| Checkpoint | Winners (mean) | Losers (mean) |
|---|---|---|
| 15m | +0.2272% | -0.0746% |
| 30m | +0.3372% | -0.2401% |
| 1h | +0.3899% | -0.3473% |
| 2h | +0.8004% | -0.5849% |
| 3h | +1.2017% | -0.8956% |
| 4h | +1.3612% | -1.1646% |

**MAE / MFE, winners vs. losers:**

| Group | Mean MAE | Median MAE | Mean MFE | Median MFE |
|---|---|---|---|---|
| Winners | -1.1217% | -0.6318% | +2.1575% | +2.2684% |
| Losers | -2.1538% | -2.0623% | +0.8020% | +0.7085% |

- Winners that dipped negative at some point before closing positive (MAE < 0): 85.0%
- Losers that rose above entry at some point before closing negative (MFE > 0): 89.5%

**Loser MAE distribution** (is the negative mean driven by a few extreme tail trades, or broadly negative across most losers?):

| Percentile | MAE |
|---|---|
| P10 | -4.5206% |
| P25 | -2.5230% |
| P50 | -2.0623% |
| P75 | -1.0444% |
| P90 | -0.5042% |

Worst 10% of losers by MAE: 2 trades, mean MAE -5.5451% vs. the other 90% of losers' mean MAE -1.7548%


