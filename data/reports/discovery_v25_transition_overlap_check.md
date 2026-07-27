# Discovery v25 — overlap check on the state-transition finding

Generated 2026-07-27T06:04:48.532496+00:00.

discovery_v24 reported that transition origin exceeds chance at 15m and 4h but not 1h. Consecutive hourly candidates have **75% overlapping 4h forward windows** (none at 15m/1h), so v24's permutation test — which treats rows as exchangeable — has a null that is too narrow at 4h specifically. That is the same autocorrelation problem Option A was introduced to handle in Phase C. This re-tests on non-overlapping subsamples. Purely diagnostic. Discovery only (2020-2025).

---

## Non-overlapping re-test of discovery_v24's permutation result

15m and 1h have no window overlap between consecutive hourly candidates and are re-run unchanged as method controls. 4h overlaps 75%, so it is re-run on each of the 4 disjoint every-4th-hour subsamples — all four reported, so no single lucky slice can carry the conclusion.

| Horizon | Subsample | n | Observed | Null mean | Null 95th | Pct | Verdict |
|---|---|---|---|---|---|---|---|
| 15m | full (no overlap) | 52,607 | 0.0381pp | 0.0217pp | 0.0305pp | 100.0 | **exceeds chance** |
| 1h | full (no overlap) | 52,607 | 0.0446pp | 0.0361pp | 0.0494pp | 88.5 | within chance |
| 4h | offset 0/4 | 13,152 | 0.0910pp | 0.0949pp | 0.1411pp | 49.5 | within chance |
| 4h | offset 1/4 | 13,152 | 0.1138pp | 0.0886pp | 0.1262pp | 83.5 | within chance |
| 4h | offset 2/4 | 13,152 | 0.1237pp | 0.0900pp | 0.1275pp | 93.5 | within chance |
| 4h | offset 3/4 | 13,151 | 0.1165pp | 0.0956pp | 0.1304pp | 85.0 | within chance |

**How to read this:** if 4h exceeds chance on all four disjoint subsamples, the v24 finding survives the overlap correction. If it exceeds on none or only some, v24's 4h result was inflated by re-measuring the same price moves, and the honest summary of the transition work becomes 15m-only — a much weaker claim, since 1h already sat within chance.

