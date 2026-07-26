# decision_rule_v2 candidate — trending-regime filter, pre-registration

Written and committed BEFORE the OOS script exists, same discipline as
`phase_d_path_state_hypothesis.md` §24. This is an entry-selection
refinement candidate (Phase B territory — it changes which signals
`decision_rule_v1` acts on, not how an open position is managed), kept
as its own document rather than folded into Phase D's position-
management hypothesis, which is a separate question.

## 1. Where this comes from

`discovery_v6` → `v9` (Discovery only, 2020-2025):

- v6: the frozen LPL x Volatility edge's Q1-vs-Q5 spread (at Vol=Q5,
  `decision_rule_v1`'s actual traded regime) varies by `context_4h.regime`
  — widest in `trending`, narrowest in `ranging` — with no sign flip.
- v7: decomposed into the full LPL quintile matrix. The widening spread
  is driven almost entirely by LPL=Q1 improving in `trending` (Q5 stays
  roughly flat) — and the clean monotone LPL gradient itself mostly only
  holds cleanly within `trending`.
- v8: per-year stability check. `trending`: 6/6 years sign-consistent on
  the raw candidate population. `ranging`/`transitioning`: much weaker
  (2/4, 3/4 evaluable years) — not treated as robust findings.
- v9: moved from the raw candidate-level diagnostic population to
  `decision_rule_v1`'s REAL, Option-A-deduplicated, fee-adjusted trades.
  Restricting those real trades to `regime_4h=='trending'` (69% of all
  trades, n=735/1064) shows win 54.0% / median +0.1730% / mean -0.0454% /
  profit factor 0.95, vs. the unconditioned baseline's win 51.4% /
  median +0.0473% / mean -0.1306% / profit factor 0.85. Per-year: median
  positive in 4/6 years; the two negative years (2023, 2025) are the two
  thinnest-signal years in the period and read as ordinary small-sample
  variance, not a contradicting effect (see v9's diagnostic section).

## 2. The hypothesis

> Restricting `decision_rule_v1`'s `long_candidate` signals to those
> occurring while `context_4h.regime == 'trending'` improves the realized
> trade outcome distribution (win rate, median, profit factor) compared
> to the existing unconditioned rule, without materially worsening tail
> risk (P05) or discarding most of the trade opportunity set.

## 3. Frozen definition — no new parameters

- **Filter: `regime_4h == 'trending'` at entry**, applied on top of
  `decision_rule_v1`'s existing `LPL==Q1 & Vol==Q5 → long_candidate`
  rule. Nothing about LPL, volatility, or the underlying quintile edges
  changes.
- No threshold is fit or chosen here — `regime_4h` is an existing
  categorical field from `context/classifier.py`, already computed the
  same way for every candidate; this only adds a filter on an existing
  category, not a new fitted cut.
- `avoid_long` is out of scope for this hypothesis (unchanged).

## 4. Pre-registered OOS metrics and classification

**Primary:** win rate, median return, profit factor — the three metrics
that moved most clearly in Discovery (v9).
**Secondary:** mean return, P05, trade count retained (must remain a
majority of baseline trades — a filter that discards most trades to
gain a small edge is a different, riskier proposition than what was
found here).

**Classification** (same A/B/C convention as Phase D §24):
- **A — OOS confirmed:** primary metrics point the same direction as
  Discovery, without materially worse P05.
- **B — OOS neutral:** no clear advantage, no clear harm.
- **C — OOS refuted:** the Discovery-observed edge disappears or
  reverses.

Given `decision_rule_v1` only produced 39 trades in 2026 so far (per
Phase D §25), the trending-restricted OOS subset will be smaller still
— this must be read with the same small-sample caution as Phase D's OOS
result, not as a high-powered test.

## 5. Explicitly not done here

- Not implemented as a change to `decision_rule_v1.py` itself. This
  stays a parallel, labeled comparison until (if ever) formally adopted.
- Not combined with any Phase D position-management logic — this is an
  entry-selection question, independent of what happens after entry.
- No re-tuning of the filter based on the OOS result, per the same rule
  as every other OOS step in this project.

## 6. OOS result and classification (2026-07-26)

`decision_rule_v2_trending_filter_oos_v1.py` ran the exact frozen filter
on 2026. Result:

| Population | n | Win rate | Median | Mean | Profit factor |
|---|---|---|---|---|---|
| Baseline (unfiltered) | 39 | 51.3% | +0.1787% | -0.0893% | 0.868 |
| Restricted to `trending` | 34 | 50.0% | +0.0776% | -0.1876% | 0.742 |
| Restricted to non-`trending` | 5 | 60.0% | +0.4969% | +0.5788% | 2.781 |

**All three pre-registered primary metrics (win rate, median, profit
factor) move in the WRONG direction** for the trending-restricted subset
— worse than the unfiltered baseline, not better. The non-trending
subset looks much stronger, but n=5 is far too small to read (the
opposite of what Discovery would have predicted, if it were reliable at
this n).

**Classification, applying §4's criteria as written: C — OOS refuted.**
Not a marginal miss — every primary metric moved against the hypothesis,
not just "failed to improve." This is a real result, not overridden by
appeals to small n: n=34 for the trending subset is not tiny (larger
than most of Phase D's OOS subsets), and the direction is consistently
wrong across win rate, median, and profit factor simultaneously, which
is harder to write off as pure noise than a single metric moving.

**Decision: do not adopt the trending filter.** `decision_rule_v1`
remains unchanged, exactly as before this investigation. No re-tuning,
no searching for a different regime cut, no second OOS attempt on this
same hypothesis — per §5, the rule from the start was one frozen filter,
one OOS run, honest result.

**What this does and doesn't mean:** it does not retroactively invalidate
discovery_v6-v9's Discovery-period findings — the regime-conditioning
effect was real and reasonably well-evidenced *in that period*. It does
mean that effect did not carry forward into 2026 in a way that survives
a real OOS test, at least not yet, at this sample size. This is exactly
the kind of result the Discovery→freeze→OOS discipline exists to catch:
a plausible, well-evidenced-in-sample pattern that still doesn't survive
contact with new data. Filed as a completed, negative research result,
not left open for further tinkering.
