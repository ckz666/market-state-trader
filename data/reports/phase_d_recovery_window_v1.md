# Phase D recovery-window v1 -- landmark test: does absence of recovery predict outcome LIVE

Generated 2026-07-26T16:39:05.584206+00:00.

Still not a position-management rule. Tests `P(winner | deep episode started at t0, not yet recovered at t0+w)` using only information available at t0+w (a proper landmark cut, not the 'never recovered by close' hindsight cut from phase_d_time_in_state3_v1.py). Same frozen deep threshold (Def 1, -0.75%) and population (decision_rule_v1's actual Discovery trades) as the rest of Phase D. Cells with n < 15 are marked instead of reported. 2026 untouched.

**Caveat, quantified in phase_d_time_in_state3_v1.md's re-entry check:** 'recovered by t0+w' here means recovered from the FIRST deep episode, not 'clear for the rest of the hold' -- 40.0% of first-episode 'recovered' trades (246/615) are back at/below the deep threshold again by the 4h close. This likely means the true gap between a genuinely-clear path and a not-yet-recovered one is understated here, not overstated: the 'recovered' column in section A is diluted by this ~40% backslide fraction rather than representing a clean population.

---

## A. Landmark test: no recovery by t0+w vs. recovered by t0+w

Only trades whose deep episode starts early enough that t0+w still falls within the 4h hold are eligible for a given w (a trade with no runway left to observe w is excluded from that row, not counted as 'not recovered'). 'Not yet recovered' uses only information available at t0+w -- unlike the prior script's 'never recovered by close' cut, this is a live-observable split.

| Window w | n eligible | Recovered by t0+w | Not yet recovered by t0+w |
|---|---|---|---|
| 15m | 652 | 35.0% (n=515) | 28.5% (n=137) |
| 30m | 639 | 35.8% (n=537) | 25.5% (n=102) |
| 60m | 614 | 37.5% (n=547) | 13.4% (n=67) |
| 90m | 589 | 38.6% (n=536) | 5.7% (n=53) |
| 120m | 545 | 39.1% (n=504) | 4.9% (n=41) |

---

## B. Runway-controlled: is 'not yet recovered' just a runway proxy?

Within each window's 'not yet recovered by t0+w' group, split by how much runway remains after t0+w (>= 60m left vs. < 60m left before the 4h close). If the win rate still drops within the 'ample runway left' rows too, 'not yet recovered' carries information beyond just having less time -- if it only drops in the 'tight runway' rows, the effect may just be the runway confound already seen in the t_enter split.

| Window w | Runway left after t0+w | n | P(Winner) |
|---|---|---|---|
| 15m | >= 60m ample | 129 | 30.2% (n=129) |
| 15m | < 60m tight | 8 | n=8 |
| 30m | >= 60m ample | 93 | 28.0% (n=93) |
| 30m | < 60m tight | 9 | n=9 |
| 60m | >= 60m ample | 59 | 15.3% (n=59) |
| 60m | < 60m tight | 8 | n=8 |
| 90m | >= 60m ample | 44 | 6.8% (n=44) |
| 90m | < 60m tight | 9 | n=9 |
| 120m | >= 60m ample | 31 | 6.5% (n=31) |
| 120m | < 60m tight | 10 | n=10 |
