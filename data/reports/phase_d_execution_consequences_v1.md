# Phase D execution-consequences v1 -- what follows a recovery-state classification

Generated 2026-07-26T16:18:17.464769+00:00.

Still not a position-management rule. Same frozen state definition and population as phase_d_recovery_state_v1.py (Def 1 recovery, deep threshold -0.75%, decision_rule_v1's actual Discovery trades). Looks at the trade-off between remaining upside and remaining downside per state, rather than just P(winner), before any exit/partial-reduction hypothesis is written. Cells with n < 15 are marked instead of reported. 2026 untouched.

---

## A. Outcome and remaining path, by state and checkpoint

'Remaining MAE/MFE' = mae_4h - mae_t / mfe_4h - mfe_t: how much FURTHER the running extremes (from entry) moved between checkpoint t and the 4h close. Not a fresh from-t recomputation -- a lower bound on how much more happened after t, in the same entry-relative units used throughout Phase C/D.

| Time | State | n | P(Winner) | Median return | Mean return | P05 | Median remaining MAE | Median remaining MFE |
|---|---|---|---|---|---|---|---|---|
| 1h | 1: never deep | 637 | 60.4% | +0.3650% | +0.2802% | -2.51% | -0.1029% | +0.4399% |
| 1h | 2: deep, recovered | 218 | 50.9% | +0.0294% | +0.1315% | -4.48% | +0.0000% | +0.6259% |
| 1h | 3: deep, still impaired | 209 | 24.4% | -1.1844% | -1.6563% | -6.16% | -0.4898% | +0.0000% |
| 2h | 1: never deep | 519 | 67.1% | +0.5164% | +0.5930% | -1.79% | +0.0000% | +0.1743% |
| 2h | 2: deep, recovered | 286 | 57.7% | +0.1937% | +0.4713% | -2.76% | +0.0000% | +0.2828% |
| 2h | 3: deep, still impaired | 259 | 13.1% | -1.8885% | -2.2454% | -6.09% | -0.3343% | +0.0000% |
| 3h | 1: never deep | 450 | 74.0% | +0.7306% | +0.8413% | -1.02% | +0.0000% | +0.0000% |
| 3h | 2: deep, recovered | 354 | 57.1% | +0.1559% | +0.5623% | -1.87% | +0.0000% | +0.0000% |
| 3h | 3: deep, still impaired | 260 | 4.6% | -2.1207% | -2.7562% | -6.61% | +0.0000% | +0.0000% |

---

## B. State 3 deep dive: eventual winners vs. losers

Among trades classified as State 3 (deep, still impaired) at each checkpoint: how big is the eventual-winner minority, and how does its return compare to the eventual-loser majority?

| Time | Outcome | n | % of State 3 | Median return | Mean return | P05 |
|---|---|---|---|---|---|---|
| 1h | eventual winner | 51 | 24.4% | +0.6714% | +1.1869% | +0.08% |
| 1h | eventual loser | 158 | 75.6% | -1.9682% | -2.5740% | -6.95% |
| 2h | eventual winner | 34 | 13.1% | +0.8758% | +1.0757% | +0.12% |
| 2h | eventual loser | 225 | 86.9% | -2.0703% | -2.7473% | -6.40% |
| 3h | eventual winner | 12 | 4.6% | n too few | - | - |
| 3h | eventual loser | 248 | 95.4% | -2.2221% | -2.9403% | -6.79% |

---

## C. Recovery transitions out of State 3

Of trades in State 3 at an early checkpoint, what fraction have recovered (Def 1: DD_current back above the deep threshold) by a later checkpoint -- and what's the eventual win rate of the still-impaired remainder at that later point?

| From (State 3 @) | To checkpoint | n (State 3 @ from) | Recovered by 'to' | Still impaired at 'to' |
|---|---|---|---|---|
| 1h | 2h | 209 | 52% winrate (n=67) | 11% winrate (n=142) |
| 1h | 3h | 209 | 47% winrate (n=97) | 4% winrate (n=112) |
| 1h | 4h | 209 | 53% winrate (n=97) | 0% winrate (n=112) |
| 2h | 3h | 259 | 38% winrate (n=80) | 2% winrate (n=179) |
| 2h | 4h | 259 | 41% winrate (n=83) | 0% winrate (n=176) |
| 3h | 4h | 260 | 29% winrate (n=42) | 0% winrate (n=218) |
