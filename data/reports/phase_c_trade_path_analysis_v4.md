# Phase C trade-path analysis v4 — Volatility x Time x Drawdown -> P(winner)

Generated 2026-07-26T14:58:58.665341+00:00.

Last purely-analytical step before formulating a position-management hypothesis (a separate, later, frozen-and-OOS-tested step — not built here). LPL==Q1 widened across all volatility quintiles, per v3's scope note (decision_rule_v1 itself only fires at Volatility==Q5). Cells with n < 15 are marked instead of reported, per the same discipline used throughout this project (v3's bb_position x vwap_distance sparse-cell lesson).

---

## Results

### Discovery (2020-2025, in-sample)

| Volatility | Time | <= -0.5% | <= -1.0% | <= -1.5% | <= -2.0% |
|---|---|---|---|---|---|
| Q1 | 15m | n=8 | n=5 | n=2 | n=0 |
| Q1 | 1h | 12% (n=40) | n=10 | n=3 | n=2 |
| Q1 | 2h | 11% (n=79) | 9% (n=34) | 0% (n=15) | n=7 |
| Q1 | 4h | 9% (n=142) | 5% (n=63) | 0% (n=32) | 0% (n=15) |
| Q2 | 15m | 11% (n=46) | n=12 | n=4 | n=0 |
| Q2 | 1h | 19% (n=139) | 4% (n=48) | 0% (n=19) | n=8 |
| Q2 | 2h | 17% (n=224) | 6% (n=94) | 0% (n=40) | 0% (n=19) |
| Q2 | 4h | 14% (n=310) | 4% (n=167) | 0% (n=87) | 0% (n=47) |
| Q3 | 15m | 25% (n=68) | 18% (n=17) | n=2 | n=1 |
| Q3 | 1h | 22% (n=237) | 13% (n=89) | 4% (n=23) | n=10 |
| Q3 | 2h | 20% (n=323) | 11% (n=149) | 6% (n=63) | 3% (n=31) |
| Q3 | 4h | 18% (n=415) | 8% (n=227) | 4% (n=122) | 3% (n=78) |
| Q4 | 15m | 29% (n=129) | 17% (n=30) | n=10 | n=6 |
| Q4 | 1h | 26% (n=341) | 20% (n=135) | 15% (n=62) | 6% (n=33) |
| Q4 | 2h | 25% (n=472) | 17% (n=226) | 12% (n=121) | 8% (n=71) |
| Q4 | 4h | 23% (n=584) | 13% (n=356) | 8% (n=232) | 6% (n=142) |
| Q5 | 15m | 44% (n=321) | 40% (n=119) | 45% (n=44) | 59% (n=22) |
| Q5 | 1h | 40% (n=575) | 35% (n=331) | 31% (n=205) | 32% (n=107) |
| Q5 | 2h | 39% (n=682) | 33% (n=448) | 28% (n=313) | 23% (n=203) |
| Q5 | 4h | 37% (n=770) | 29% (n=568) | 23% (n=442) | 15% (n=309) |

### Validation (2026, out-of-sample)

| Volatility | Time | <= -0.5% | <= -1.0% | <= -1.5% | <= -2.0% |
|---|---|---|---|---|---|
| Q1 | 15m | n=6 | n=2 | n=1 | n=0 |
| Q1 | 1h | 0% (n=19) | n=6 | n=2 | n=2 |
| Q1 | 2h | 0% (n=26) | n=10 | n=4 | n=2 |
| Q1 | 4h | 0% (n=34) | 0% (n=15) | n=9 | n=4 |
| Q2 | 15m | n=7 | n=1 | n=1 | n=0 |
| Q2 | 1h | 25% (n=20) | n=4 | n=1 | n=1 |
| Q2 | 2h | 18% (n=33) | n=9 | n=3 | n=1 |
| Q2 | 4h | 14% (n=56) | 5% (n=21) | n=8 | n=6 |
| Q3 | 15m | n=5 | n=0 | n=0 | n=0 |
| Q3 | 1h | 28% (n=18) | n=4 | n=1 | n=0 |
| Q3 | 2h | 19% (n=27) | n=13 | n=5 | n=4 |
| Q3 | 4h | 11% (n=45) | 0% (n=26) | 0% (n=16) | n=8 |
| Q4 | 15m | n=5 | n=1 | n=1 | n=1 |
| Q4 | 1h | 39% (n=28) | n=9 | n=2 | n=2 |
| Q4 | 2h | 32% (n=38) | 35% (n=17) | n=5 | n=3 |
| Q4 | 4h | 29% (n=49) | 19% (n=32) | 0% (n=18) | n=11 |
| Q5 | 15m | n=12 | n=2 | n=1 | n=0 |
| Q5 | 1h | 48% (n=21) | n=11 | n=7 | n=4 |
| Q5 | 2h | 42% (n=24) | n=14 | n=11 | n=8 |
| Q5 | 4h | 39% (n=28) | 30% (n=20) | 28% (n=18) | n=13 |

