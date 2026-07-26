# Phase D time-in-state-3 v1 -- duration in the impaired state vs. eventual outcome

Generated 2026-07-26T16:24:22.138514+00:00.

Still not a position-management rule. Measures `duration_in_state_3` from the 1-minute price path (finer than the checkpoint grid used in phase_c/phase_d v1-v4): minutes from the first crossing at/below the deep threshold (-0.75%, Def 1, same as phase_d_recovery_state_v1.py) to the first subsequent crossing back above it, for decision_rule_v1's actual Discovery trades. Trades that never recover within the 4h hold are reported as a separate censored group, not folded into the duration buckets. Only the first deep episode per trade is measured (re-entries after a recovery are out of scope here). Cells with n < 15 are marked instead of reported. 2026 untouched.

---

## Duration-in-state-3 vs. eventual outcome

n trades ever reaching the deep threshold within the 4h hold: 662

| Group | n | P(Winner), median/mean/P05 |
|---|---|---|
| recovered, duration <15m | 515 | 34.8% (n=515), median -0.5511%, mean -0.6200%, P05 -4.53% |
| recovered, duration 15-30m | 36 | 33.3% (n=36), median -0.7810%, mean -0.9730%, P05 -4.65% |
| recovered, duration 30-60m | 32 | 56.2% (n=32), median +0.1853%, mean -0.3363%, P05 -3.91% |
| recovered, duration 60-120m | 21 | 38.1% (n=21), median -0.5426%, mean -0.5921%, P05 -2.07% |
| recovered, duration 120-240m | 11 | n=11 |
| **never recovered within 4h (censored)** | 47 | 0.0% (n=47), median -2.6765%, mean -3.8771%, P05 -9.77% |

---

## When the deep episode starts (confound check)

Secondary check: trades that first reach the deep threshold LATE in the hold have mechanically less remaining time to recover, which could confound the duration bucketing above if late-entering trades cluster into 'never recovered.' Split by when the deep episode started:

| First reached deep threshold at | n | Never recovered within hold | P(Winner) overall |
|---|---|---|---|
| 0-1h | 421 | 22 (5%) | 38.2% (n=421), median -0.5533%, mean -0.7443%, P05 -5.38% |
| 1-2h | 123 | 8 (7%) | 30.9% (n=123), median -0.7232%, mean -1.0716%, P05 -4.59% |
| 2-3h | 69 | 7 (10%) | 21.7% (n=69), median -0.7975%, mean -1.0158%, P05 -3.25% |
| 3-4h | 48 | 9 (19%) | 10.4% (n=48), median -1.0112%, mean -1.0830%, P05 -2.67% |
