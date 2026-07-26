# Phase C trade-path analysis v3 — drawdown x time x volatility, time-to-recovery

Generated 2026-07-26T14:52:53.217159+00:00.

Still purely descriptive — no exit rule is chosen or tested here. Section B widens the population beyond decision_rule_v1's actual signals for diagnostic purposes only (see its note).

---

# Discovery (2020-2025, in-sample)

## A. Drawdown x Time — P(eventual winner)

For each checkpoint, among only the trades whose RUNNING MAE (from entry up to that checkpoint, not the whole trade) has reached at least this much adverse excursion, what fraction still closed as a winner? Rows = drawdown depth, columns = how long into the trade.

| Drawdown | 15m | 30m | 1h | 2h | 3h | 4h |
|---|---|---|---|---|---|---|
| <= -0.25% | 45% (n=570) | 45% (n=669) | 44% (n=771) | 44% (n=839) | 43% (n=874) | 43% (n=894) |
| <= -0.50% | 44% (n=321) | 41% (n=444) | 40% (n=575) | 39% (n=682) | 39% (n=735) | 37% (n=770) |
| <= -1.00% | 40% (n=119) | 37% (n=206) | 35% (n=331) | 33% (n=448) | 31% (n=519) | 29% (n=568) |
| <= -1.50% | 45% (n=44) | 39% (n=101) | 31% (n=205) | 28% (n=313) | 26% (n=388) | 23% (n=442) |
| <= -2.00% | 59% (n=22) | 38% (n=52) | 32% (n=107) | 23% (n=203) | 18% (n=259) | 15% (n=309) |

## B. Drawdown x Volatility (diagnostic — widened population, not a change to decision_rule_v1)

decision_rule_v1 only fires at Volatility==Q5, so its actual trades have no volatility variation to compare. This uses LPL==Q1 at every volatility quintile instead, each an independent Option-A trade sequence, purely to see whether the drawdown-recovery relationship changes with entry volatility. Not a proposal to trade these other quintiles.

| Drawdown | Vol=Q1 | Vol=Q2 | Vol=Q3 | Vol=Q4 | Vol=Q5 |
|---|---|---|---|---|---|
| (baseline win rate) | 35% (n=466) | 44% (n=687) | 45% (n=839) | 44% (n=981) | 51% (n=1064) |
| <= -0.25% | 18% (n=266) | 24% (n=442) | 30% (n=601) | 32% (n=762) | 43% (n=894) |
| <= -0.50% | 9% (n=142) | 14% (n=310) | 18% (n=415) | 23% (n=584) | 37% (n=770) |
| <= -1.00% | 5% (n=63) | 4% (n=167) | 8% (n=227) | 13% (n=356) | 29% (n=568) |
| <= -1.50% | 0% (n=32) | 0% (n=87) | 4% (n=122) | 8% (n=232) | 23% (n=442) |
| <= -2.00% | 0% (n=15) | 0% (n=47) | 3% (n=78) | 6% (n=142) | 15% (n=309) |

## C. Time to first positive MFE

How long, typically, until a trade's running price first exceeds entry (i.e. unrealized PnL first turns positive, before fees)? Winners vs. losers.

| Group | n | Never went positive | Median time-to-positive (of those that did) |
|---|---|---|---|
| Winners | 547 | 0 (0.0%) | 1 min |
| Losers | 517 | 39 (7.5%) | 1 min |

---

# Validation (2026, out-of-sample)

## A. Drawdown x Time — P(eventual winner)

For each checkpoint, among only the trades whose RUNNING MAE (from entry up to that checkpoint, not the whole trade) has reached at least this much adverse excursion, what fraction still closed as a winner? Rows = drawdown depth, columns = how long into the trade.

| Drawdown | 15m | 30m | 1h | 2h | 3h | 4h |
|---|---|---|---|---|---|---|
| <= -0.25% | 50% (n=24) | 48% (n=29) | 47% (n=32) | 45% (n=33) | 44% (n=34) | 44% (n=34) |
| <= -0.50% | 58% (n=12) | 50% (n=18) | 48% (n=21) | 42% (n=24) | 37% (n=27) | 39% (n=28) |
| <= -1.00% | n=2 (too few) | n=8 (too few) | 36% (n=11) | 29% (n=14) | 35% (n=17) | 30% (n=20) |
| <= -1.50% | n=1 (too few) | n=2 (too few) | n=7 (too few) | 27% (n=11) | 33% (n=15) | 28% (n=18) |
| <= -2.00% | n=0 (too few) | n=1 (too few) | n=4 (too few) | n=8 (too few) | 27% (n=11) | 23% (n=13) |

## B. Drawdown x Volatility (diagnostic — widened population, not a change to decision_rule_v1)

decision_rule_v1 only fires at Volatility==Q5, so its actual trades have no volatility variation to compare. This uses LPL==Q1 at every volatility quintile instead, each an independent Option-A trade sequence, purely to see whether the drawdown-recovery relationship changes with entry volatility. Not a proposal to trade these other quintiles.

| Drawdown | Vol=Q1 | Vol=Q2 | Vol=Q3 | Vol=Q4 | Vol=Q5 |
|---|---|---|---|---|---|
| (baseline win rate) | 25% (n=73) | 40% (n=123) | 41% (n=88) | 44% (n=78) | 51% (n=39) |
| <= -0.25% | 0% (n=44) | 23% (n=87) | 19% (n=58) | 34% (n=62) | 44% (n=34) |
| <= -0.50% | 0% (n=34) | 14% (n=56) | 11% (n=45) | 29% (n=49) | 39% (n=28) |
| <= -1.00% | 0% (n=15) | 5% (n=21) | 0% (n=26) | 19% (n=32) | 30% (n=20) |
| <= -1.50% | n=9 (too few) | n=8 (too few) | 0% (n=16) | 0% (n=18) | 28% (n=18) |
| <= -2.00% | n=4 (too few) | n=6 (too few) | n=8 (too few) | 0% (n=11) | 23% (n=13) |

## C. Time to first positive MFE

How long, typically, until a trade's running price first exceeds entry (i.e. unrealized PnL first turns positive, before fees)? Winners vs. losers.

| Group | n | Never went positive | Median time-to-positive (of those that did) |
|---|---|---|---|
| Winners | 20 | 0 (0.0%) | 1 min |
| Losers | 19 | 2 (10.5%) | 3 min |

---

