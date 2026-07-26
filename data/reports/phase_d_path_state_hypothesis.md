# Phase D — Frozen Path-State Hypothesis

Status: **DRAFT, not yet frozen.** This document precedes any code. It exists
to fix the hypothesis, its allowed inputs, its success criterion, and its
excluded mechanisms *before* a single line of position-management logic is
written — the same discipline used for the LPL x Volatility hypothesis in
Phase A (frozen in `hypothesis_validation.py`, OOS-tested unchanged).

Nothing below is a stop-loss percentage, a parameter, or a backtest result.
This is a design contract for the Discovery work that comes after it.

---

## 1. Where this comes from

Phase C (`phase_c_trade_path_analysis.py` through `v4.py`) established, purely
descriptively:

- Winner/loser paths diverge from the first 15m checkpoint on.
- Recovery probability after a given drawdown falls with elapsed time.
- Recovery probability after the *same* drawdown rises with entry-volatility
  quintile (Q1 -> Q5) — e.g. at 4h, DD <= -1.0%: Q1 5% (n=63) vs. Q5 29%
  (n=568); at DD <= -1.5%, Q1 reaches 0% (n=32) while Q5 still shows 23%
  (n=442).
- The relationship is globally structured but **not strictly monotone
  cell-by-cell** (e.g. Q5 @ 15m: 44% / 40% / 45% / 59% across the four
  thresholds) — almost certainly small-n and early-extreme-move artifacts,
  not a real reversal. The robust claim is directional and joint, not "each
  additional 0.5% of drawdown strictly lowers P(winner) in every cell."

Conclusion drawn from this: **a given drawdown does not have a fixed
meaning.** The same -1.5% excursion is close to terminal for a Q1-volatility
entry and still informative for a Q5-volatility entry. Any management logic
that reads drawdown without its volatility/time context is throwing away
signal that v4 shows is there.

Scope note carried over from v3/v4: the Q1-Q5 volatility split was built on
the widened `LPL==Q1` population (`decision_rule_v1` itself only ever fires
at `Volatility==Q5`), for diagnostic purposes only. It is not a proposal to
trade LPL==Q1 at low volatility.

## 2. The hypothesis (single sentence, no thresholds)

> The probability that an open trade eventually closes as a 4h winner is not
> static after entry — it depends jointly on entry volatility, elapsed time,
> and the drawdown observed so far. A position-management mechanism that
> conditions on this joint path-state should produce a better risk/reward
> distribution than a mechanism that reacts to drawdown alone, independent
> of entry-volatility context or elapsed time.

This is the entire hypothesis. It does not say which mechanism, by how much,
or with what parameters.

## 3. The observed path-state (inputs the mechanism is allowed to use)

Three variables, all already computed in v2-v4:

1. **Entry-volatility quintile** (`volatility_atr_norm`, quintile edges
   frozen on 2020-2025, per Phase A/B) — fixed at entry, never updated
   mid-trade.
2. **Time since entry** — one of the existing checkpoints (15m, 30m, 1h, 2h,
   3h, 4h).
3. **Drawdown state** — two variables, both now tabulated:
   - `MAE_so_far(t)`: running minimum of unrealized return from entry to t.
   - `DD_current(t)`: unrealized return at t itself (may be less negative
     than MAE_so_far if the trade has partially recovered).

   Both tables are now built (`phase_c_trade_path_analysis_v4.py`, sections A
   and B). They carry different information: at every pre-terminal
   checkpoint, `DD_current` predicts slightly worse recovery odds than
   `MAE_so_far` at the same threshold/quintile/time cell (Discovery Q5 @ 1h,
   DD<=-1.0%: A=24% (n=155) vs. B=35% (n=331) — a trade still sitting at
   -1.0% right now is a worse sign than one that merely touched -1.0% at
   some point since entry and may have partly recovered). Expected
   direction, and it confirms the two variables are not interchangeable.

   One degeneracy to note: table A's 4h row is not informative — at the
   terminal checkpoint `DD_current` is essentially the trade's final
   return, so "current DD <= threshold at 4h" is close to a restatement of
   "closed a loser" (every cell in that row reads ~0%), not an independent
   path observation. Only A's pre-terminal rows (15m/1h/2h) carry real
   path-vs-outcome information; B does not have this problem at any
   checkpoint.

No other variable is in scope for this hypothesis (not RSI, not structure,
not microstructure — those belong to a different hypothesis if pursued
later).

## 4. Information boundary at time t

Only the path observable up to and including checkpoint t may be used to
construct the state at t. The 4h outcome label may be used afterward to
*measure* the state's predictive value (that is the entire point), but must
never leak into the state's construction. This is the same no-lookahead
discipline already enforced in `build_trade_frame` (v2) and reused unchanged
through v3/v4.

## 5. Goal of the management rule

Not return maximization on Discovery data. The goal is a better realized
risk/reward *distribution* on the existing `decision_rule_v1` trade set,
relative to two baselines that must both be reported side by side with any
candidate mechanism:

- **Baseline 1 — fixed-horizon exit:** hold to 4h regardless of path (the
  current, mechanism-free baseline already measured in `phase_c_baseline_v1`
  / the trade-path reports).
- **Baseline 2 — naive hard stop:** a single fixed drawdown stop, with no
  volatility or time conditioning (Class A below). This exists only as a
  reference point to show what conditioning on path-state buys you, not as
  a real candidate.

"Better" means: not worse median net return, and a demonstrably improved
left-tail (P05, or fraction of trades hitting some large-loss threshold),
without materially cutting the win rate through premature exits on trades
that would have recovered. This must be pre-specified before any mechanism
is scored, precisely to avoid picking whichever metric happens to favor the
result.

## 6. What counts as success

A candidate mechanism is considered validated only if, on the **2026 holdout
set, using parameters fit exclusively on 2020-2025**, it still shows the
same directional improvement over both baselines that was seen on Discovery
— the same bar Phase A/B/C have used throughout (LPL x Volatility sign held
5/5 quintiles OOS; decision_rule_v1's realized distribution direction held
OOS). A mechanism that only looks good in-sample is not success, regardless
of the in-sample margin.

## 7. Data usage

- **Construction / mechanic definition:** Discovery period (2020-2025)
  only. This includes choosing the mechanism class itself (see §8) and any
  of its internal structure.
- **Validation:** 2026, untouched, exactly as in every prior phase. No
  parameter, threshold, or structural choice may be re-fit or adjusted after
  looking at 2026 results.

## 8. Mechanisms explicitly excluded from this phase

- **Grid-searching many stop thresholds against Discovery and keeping the
  best-performing one.** This reintroduces the exact multiple-testing
  problem this project has avoided at every previous phase — enough
  variants tried against the same data will always produce an
  apparent winner.
- **A single fitted "confidence" formula** combining drawdown, time, and
  volatility into one scalar (e.g. `confidence = a*DD + b*t + c*vol`).
  Flagged by the user explicitly: this recreates the old `entry_belief`
  problem — several distinct dimensions compressed into one number whose
  weights would themselves need fitting (and thus tuning against Discovery
  outcomes, i.e. the same multiple-testing risk one level down).
- **Choosing between mechanism classes (A-D, see below) by running all of
  them on Discovery and picking whichever backtests best.** The mechanism
  *class* must be chosen on structural/descriptive grounds (i.e., which
  class's shape actually matches what v4 showed) before any of them is
  scored numerically. Only the internal implementation details of the
  chosen class may then be worked out empirically on Discovery.

## 9. Candidate mechanism classes for the next Discovery step (not decided yet)

Listed for scoping only — picking one is the next decision, to be made
before any code is written, and justified structurally rather than by
trying all four:

- **Class A — hard stop** (`DD < X -> exit`, no context). Reference
  baseline only (§5), not a real candidate — known from v3/v4 to ignore
  exactly the volatility-context effect the whole phase is about.
- **Class B — volatility-adjusted stop** (allowed drawdown scaled by entry
  volatility quintile, no time dimension).
- **Class C — time x drawdown** (how much a given drawdown is "allowed" to
  mean shrinks with elapsed time, no volatility dimension).
- **Class D — full path-state** (volatility x time x drawdown jointly, e.g.
  a small number of empirically-defined path-state buckets rather than a
  fitted formula). Structurally the closest match to what v4 actually
  found (early + deep + low-vol behaves differently from late + same-depth
  + high-vol).
- **Class D' — recovery-state** (a refinement of D, added after §1's
  `DD_current` vs. `MAE_so_far` comparison was actually run): three
  qualitatively distinct path states per trade at time t, instead of one
  drawdown number —
  1. never reached a deep drawdown (current behavior looks "normal"),
  2. reached a deep drawdown but has since recovered from it (path
     survived stress; current state improved relative to the low point),
  3. reached a deep drawdown and is still there (current state
     unimproved).

  This is not a new dimension on top of D — it is D's drawdown axis split
  into two (`DD_current`, `MAE_so_far`) instead of collapsed into one,
  because §1 showed those two are not interchangeable (Discovery Q5 @ 1h,
  DD<=-1.0%: `DD_current` 24% (n=155) vs. `MAE_so_far` 35% (n=331) — same
  volatility, same time, same threshold, different outcome distribution
  depending on which drawdown definition is used). A single scalar
  drawdown feature (as in plain Class D) cannot represent this distinction;
  a state built from both can.

## 10. Chosen mechanism class

**Class D' (recovery-state), chosen 2026-07-26.** Justification: it is the
only candidate class that represents the `DD_current` != `MAE_so_far`
finding directly, rather than discarding it into a single drawdown number.
Not chosen by backtesting D vs. D' against each other — chosen because D'
is structurally the only class consistent with a result Discovery already
demonstrated (§1), which is exactly the "structural grounds, not
performance grounds" bar §8 requires.

This is a class choice, not a finished rule. Left open, deliberately, for
Discovery to define empirically on 2020-2025 only (not decided here, to
avoid quietly baking in a threshold under the cover of "just choosing a
class"):

- What counts as "reached a deep drawdown" — which threshold, and does it
  vary by volatility quintile (plausible, given §1/v4's finding that the
  same drawdown number means different things at different volatility
  levels)?
- What counts as "recovered" for state 2 — back above the threshold
  entirely, or merely off the low point by some margin? This distinction
  is currently undefined and must not be silently fixed later; Discovery's
  first job is to test whether the three-state split is even sensitive to
  this choice before treating any specific definition as settled.
- Whether the three states are enough, or whether "recovered how long ago"
  turns out to matter too (a fourth path dimension, time-since-low-point,
  not yet in scope — only add it if the three-state split proves
  insufficient, not preemptively).

## 11. Recovery-state definition, frozen 2026-07-26

Based on `phase_d_recovery_state_discovery_v1.py`'s stability scan (§9's two
open questions, now answered):

- **Recovery definition: Def 1 — `DD_current(t) > deep_threshold`** (back
  above the same threshold the trade dropped below). Chosen over Def 2
  (margin from own low) and Def 3 (absolute residual) because it needs no
  extra free parameter and already has the largest per-cell n of the three
  — Def 3 separated states more sharply only because its stricter bar
  shrinks the "recovered" group, not because it carries more information.
- **Deep-drawdown threshold: −0.5% to −1.0%.** This is a range, not a single
  fitted point — deliberately, since the discovery scan's whole purpose was
  to show the 3-state ordering is stable across a band, not optimal at one
  number. Below −0.5% the separation gets noisier (closer to the general
  drawdown noise band); above −1.0% too many quintile/checkpoint cells drop
  under `MIN_CELL_N`. Any single value from this band may be used for
  implementation without that choice being a fitted parameter.
- **Time checkpoints: 1h and later only** (1h/2h/3h). 15m/30m excluded —
  the discovery scan's "ordering holds" flag was inconsistent there,
  concentrated in cells with n just above the floor, most likely noise
  from too little elapsed path rather than a real early-time effect. The
  4h (terminal) checkpoint remains excluded per the pre-existing
  `DD_current`-at-terminal degeneracy (§3 / v4's caveat on table A).
- **Volatility Q1 explicitly unsupported.** At the −0.5%/−1.0% band and
  1h+, Q1's diagnostic population is too thin to populate State 2/3 cells
  (e.g. only n=6-13 recovered/impaired at 1h). The recovery-state mechanism
  is frozen as **defined only for Q2-Q5**; Q1 is left out rather than
  patched with a lower-n exception, and must not be silently included
  later without its own dedicated check. This matters little in practice
  since `decision_rule_v1` only ever trades Q5 — Q1 exists here purely as
  part of the widened diagnostic population, not as a traded quintile.

This is now a concrete, checkable definition (three states, one threshold
band, one recovery rule, Q2-Q5, checkpoints 1h/2h/3h) — but still not a
position-management action. Nothing here says what happens to a trade in
State 3.

## 12. Next step

Two remaining steps before any real position-management mechanism exists:

1. **Concretize on the actual traded population.** Everything so far
   (discovery_v1's stability scan, this freeze) used the widened
   LPL==Q1-across-all-quintiles diagnostic population. Q5 in that
   population *is* `decision_rule_v1`'s actual trade set (LPL==Q1 &
   Vol==Q5), so no separate re-check is structurally required — but the
   next script should apply this exact frozen definition (not re-scan a
   range) to that real trade set and report the outcome distribution
   (n, win rate, median, mean, P05) per state per checkpoint, Discovery
   only, as a single confirmatory descriptive step before moving on.
2. **Only after that: design the execution-mechanic hypothesis** — what
   actually happens to a trade classified into State 3 (exit? partial size
   reduction? tightened remaining-time stop?). This is a new decision that
   needs its own explicit, frozen hypothesis (same discipline as §2-§8
   above, not decided here) before any code touches real position
   management, and before 2026 is looked at again.
