# Phase D episode-history landmark v1 -- live-observable episode_count_so_far(t)

Generated 2026-07-26T17:21:04.021482+00:00.

Still not a position-management rule; no `w` or Action Class is chosen here. Fixes phase_d_episode_reentry_v1.py's hindsight problem (whole-hold episode count) by reconstructing `episode_count_so_far(t)` using only the path observable up to t. Same frozen deep threshold (Def 1, -0.75%) and population (decision_rule_v1's actual Discovery trades) as the rest of Phase D. Cells with n < 15 are marked instead of reported. 2026 untouched.

---

## A. P(winner | episode_count_so_far(t), t) -- live-observable

Live-observable analogue of phase_d_episode_reentry_v1.py's section A: episodes counted only up to t, not over the whole hold.

| t | 0 episodes | 1 episode | 2 episodes | 3+ episodes |
|---|---|---|---|---|
| 1h | 57.3% (n=707) | 47.6% (n=124) | 34.5% (n=87) | 36.3% (n=146) |
| 2h | 62.1% (n=581) | 45.9% (n=133) | 40.3% (n=77) | 34.4% (n=273) |
| 3h | 66.7% (n=502) | 48.5% (n=134) | 39.0% (n=82) | 33.2% (n=346) |

---

## B. P(winner | path-state, t) -- checkpoint snapshot of history + current status

Combines episode_count_so_far(t) with whether the trade is CURRENTLY deep at t into one of six path-states.

| t | Path-state | n | P(Winner) |
|---|---|---|---|
| 1h | 0: stable, never deep | 637 | 60.4% (n=637) |
| 1h | in episode 1 (ongoing) | 70 | 28.6% (n=70) |
| 1h | recovered after 1 episode, no re-entry | 80 | 57.5% (n=80) |
| 1h | in episode 2 / re-entry (ongoing) | 44 | 29.5% (n=44) |
| 1h | recovered after 2+ episodes | 138 | 47.1% (n=138) |
| 1h | in episode 3+ (ongoing) | 95 | 18.9% (n=95) |
| 2h | 0: stable, never deep | 519 | 67.1% (n=519) |
| 2h | in episode 1 (ongoing) | 62 | 21.0% (n=62) |
| 2h | recovered after 1 episode, no re-entry | 96 | 62.5% (n=96) |
| 2h | in episode 2 / re-entry (ongoing) | 37 | 2.7% (n=37) |
| 2h | recovered after 2+ episodes | 190 | 55.3% (n=190) |
| 2h | in episode 3+ (ongoing) | 160 | 12.5% (n=160) |
| 3h | 0: stable, never deep | 450 | 74.0% (n=450) |
| 3h | in episode 1 (ongoing) | 52 | 3.8% (n=52) |
| 3h | recovered after 1 episode, no re-entry | 89 | 68.5% (n=89) |
| 3h | in episode 2 / re-entry (ongoing) | 45 | 8.9% (n=45) |
| 3h | recovered after 2+ episodes | 265 | 53.2% (n=265) |
| 3h | in episode 3+ (ongoing) | 163 | 3.7% (n=163) |
