# Phase D episode-reentry v1 -- does re-entry carry information beyond first-episode recovery

Generated 2026-07-26T17:13:57.853962+00:00.

Still not a position-management rule; no `w` or Action Class is chosen here. Same frozen deep threshold (Def 1, -0.75%) and population (decision_rule_v1's actual Discovery trades) as the rest of Phase D. Cells with n < 15 are marked instead of reported. 2026 untouched.

---

## A. P(winner) by total number of distinct deep episodes

Does episode COUNT itself (not just whether one ever happened) carry information about the eventual outcome?

| Episodes | n | P(Winner), median |
|---|---|---|
| 0 | 402 | 81.6% (n=402), median +0.8485% |
| 1 | 131 | 50.4% (n=131), median +0.0551% |
| 2 | 85 | 36.5% (n=85), median -0.7683% |
| 3 | 91 | 31.9% (n=91), median -0.7573% |
| 4+ | 355 | 26.2% (n=355), median -0.8671% |

---

## B. Among trades that recovered from episode 1: does re-entry matter?

Restricted to the 615 Discovery trades that recovered from their first deep episode (phase_d_time_in_state3_v1.py's 'recovered' population). Split by whether a second (or later) deep episode ever happens.

| Group | n | P(Winner), median |
|---|---|---|
| no re-entry (exactly 1 episode) | 84 | 78.6% (n=84), median +0.7003% |
| re-entry (2+ episodes) | 531 | 28.8% (n=531), median -0.8030% |
