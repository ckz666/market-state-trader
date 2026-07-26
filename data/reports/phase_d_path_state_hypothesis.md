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

Both steps are now done. `phase_d_recovery_state_v1.py` confirmed the
definition on the real trade set (§11's numbers). `phase_d_execution_
consequences_v1.py` then showed State 3 is not static: P(winner|S3)
24.4% @1h -> 13.1% @2h -> 4.6% @3h, and the recovery-transition rate out
of S3 decays the same way (§C of that report). This directly motivates
§13 below.

## 13. Execution-mechanic hypothesis (Time-Conditioned Recovery Management), frozen 2026-07-26 — SUPERSEDED, see §18

**Superseded 2026-07-26.** `duration_in_state_3` (this section's central
variable) showed no reliable gradient once tested (§15) — see §18 for the
replacement hypothesis. Left in place, unedited, as the record of what
was tried and why it didn't hold; do not implement against this section.

> When a trade enters recovery-state 3, position management should not
> condition on S3 alone, but on how long the trade has continuously
> remained in S3 (`time_in_state_3`) — which is not the same variable as
> time-since-entry. A trade can enter S3 late and recover quickly, or
> enter S3 early and stay impaired for the rest of the hold; these are
> different situations that time-since-entry alone cannot distinguish.

Formally: replace `P(winner | S3)` with `P(winner | S3, duration_in_S3)`.

This is a hypothesis about *which variable matters*, not yet an action.
No specific action ("hold through duration X, then do Y") is chosen here —
doing so now would reintroduce untested parameters under a new name, the
same risk already flagged in §8.

### Candidate action classes (not chosen — scoping only)

To avoid colliding with the *state*-mechanism-class labels in §9 (Class
A-D there), these are labeled separately as **Action Classes I-IV** —
they describe what a management action could look like once
`duration_in_state_3` exists as a variable, not which one is chosen:

- **Action Class I — delayed binary exit.** Hold through S3 for a
  "recovery window"; exit only if no recovery happens by its end.
- **Action Class II — graduated reduction.** Reduce position size in
  stages as `duration_in_state_3` grows.
- **Action Class III — state-dependent sizing.** Not applicable to an
  already-open position; would only matter for entry sizing — out of
  scope for a position-*management* hypothesis about open trades.
- **Action Class IV — dynamic remaining-risk band.** Position stays open,
  but the tolerated further loss shrinks as `duration_in_state_3` grows.

## 14. Next step

Before choosing among Action Classes I-IV: one more purely descriptive
step. Measure `duration_in_state_3` directly from the 1-minute price path
(finer-grained than the 15m/30m/1h/2h/3h/4h checkpoints used so far), for
every trade that ever enters S3 within its 4h hold:

- `time_to_recovery` = minutes from the first crossing below the deep
  threshold to the first subsequent crossing back above it (Def 1), if
  that happens before the 4h close.
- Trades that never recover within the 4h window form a separate,
  **censored** group — not folded into the same duration buckets, since
  "never recovered by close" is qualitatively different from "recovered
  slowly."
- Then: `P(winner | duration_in_state_3 bucket)`, again looking for a
  stable degrading structure across bucket boundaries rather than one
  optimal cutoff — same discipline as §11's threshold-band freeze.

Only after that structure is confirmed (or not) does an Action Class get
chosen, on the same "structural grounds, not backtested-performance
grounds" basis as §10.

## 15. Result — §14's descriptive step, and a partial revision

`phase_d_time_in_state3_v1.py` measured `duration_in_state_3` on the
1-minute path for all 662 Discovery trades that ever reach the deep
threshold within their 4h hold. The result does **not** confirm the clean
monotone gradient the hypothesis in §13 anticipated:

| Duration bucket (recovered trades only) | n | P(winner) |
|---|---|---|
| <15m | 515 | 34.8% |
| 15-30m | 36 | 33.3% |
| 30-60m | 32 | 56.2% |
| 60-120m | 21 | 38.1% |
| 120-240m | 11 | too few |
| **never recovered by close** | 47 | **0.0%** |

Among trades that *do* recover, `duration_in_state_3` shows no reliable
gradient — 30-60m (56.2%) is actually higher than the two buckets before
it, almost certainly noise from small, overlapping-CI samples (n=32-36),
not a real reversal. **The variable that actually separates outcomes
cleanly is binary — recovered vs. never-recovered-by-close (34-56% vs.
0%) — not how long recovery took once it happened.**

A second cut, splitting by *when* the deep episode first starts
(`t_enter_min`, i.e. how early vs. late in the 4h hold the trade first
goes deep), shows the clean monotone structure instead:

| Deep episode starts at | n | Never recovers by close | P(winner) |
|---|---|---|---|
| 0-1h | 421 | 5% | 38.2% |
| 1-2h | 123 | 7% | 30.9% |
| 2-3h | 69 | 10% | 21.7% |
| 3-4h | 48 | 19% | 10.4% |

This lines up with the earlier checkpoint-based finding (§ discovery in
`phase_c_trade_path_analysis_v4.py`/`phase_d_execution_consequences_v1.py`)
but reframes it: it is not really "how long has the trade been impaired"
that degrades outcomes. It is closer to "how much runway is left before
the 4h close when the deep episode starts" — a trade going deep at 3h
mechanically has little time left to either recover or produce a large
favorable move, regardless of how quickly it would otherwise recover.

**Revision to §13's hypothesis:** `duration_in_state_3` is not supported
as the operative variable by this data. What is supported: (a) a sharp
binary split between ever-recovering and never-recovering by close, and
(b) a monotone decay in outcome by how early vs. late the deep episode
starts (i.e. remaining runway, closer to `time_since_entry` after all,
but conditioned specifically on the *moment the deep episode begins*
rather than on elapsed time in general). Any Action Class chosen next
should condition on runway-at-deep-episode-start and the eventual
recovered/not-recovered split, not on a continuous recovery-duration
gradient.

## 16. Revision — Recovery-Window (landmark) framing, and its result

§15's "never recovered by close" cut is only knowable in hindsight, at
the close itself — it cannot be used as a live signal. The corrected
question is a landmark one:

> P(winner | deep episode started at t0, not yet recovered at t0 + w)

using only information available at t0+w, for a range of window widths w
— never peeking past t0+w to decide the split itself (the eventual
outcome is still used afterward to measure the split's value, same
information-boundary discipline as §4).

`phase_d_recovery_window_v1.py` ran this on the same population/threshold.
**Section A result — clean and monotone, unlike §15's duration buckets:**

| Window w | Recovered by t0+w | Not yet recovered by t0+w |
|---|---|---|
| 15m | 35.0% (n=515) | 28.5% (n=137) |
| 30m | 35.8% (n=537) | 25.5% (n=102) |
| 60m | 37.5% (n=547) | 13.4% (n=67) |
| 90m | 38.6% (n=536) | 5.7% (n=53) |
| 120m | 39.1% (n=504) | 4.9% (n=41) |

The "recovered" group stays roughly flat (~35-39%); the "not yet
recovered" group falls steadily from 28.5% to 4.9% as w grows — this time
a real gradient, not noise (monotone, decent n at every step).

**Section B — runway-controlled, to rule out the confound §15 raised:**
within "not yet recovered by t0+w", split by how much runway is still
left afterward (>= 60m vs. < 60m). The decay persists in the *ample*-
runway rows alone (30.2% @15m -> 28.0% @30m -> 15.3% @60m -> 6.8% @90m ->
6.5% @120m, all with n>=31) — so this is not merely a restatement of "less
time left." Even when a trade still has a full hour or more of runway
remaining, having not yet recovered by t0+w is itself informative. The
tight-runway rows have too few trades (n=8-10) to read.

**Conclusion:** the recovery-window landmark effect is the strongest,
cleanest, most clearly live-observable structure found in Phase D so far
— stronger than §11's state definition alone and more precise than §13's
original duration hypothesis. It is now a legitimate candidate basis for
an Action Class decision (§13's Classes I-IV), since it answers the
question §13 originally posed but got wrong: *is there a point at which
the absence of recovery itself becomes a robust, live signal?* Yes —
starting somewhere around w=60m, and clearly by w=90-120m.

**Still not decided:** which Action Class, and at which specific w. That
remains the next step, deliberately not decided in the same breath as
confirming the underlying structure.

## 17. Verification pass (2026-07-26)

At the user's request, all Phase D steps (`phase_c_trade_path_analysis_v4.py`
through `phase_d_recovery_window_v1.py`) were re-verified:

- **Reproducibility:** every script re-run from scratch produced output
  byte-identical to the committed report (aside from the timestamp line).
- **Cross-script consistency:** `phase_d_time_in_state3_v1.py`'s 662
  ever-deep trades and its `t_enter` time buckets (69 starting 2-3h, 48
  starting 3-4h) exactly reconcile with `phase_d_recovery_window_v1.py`'s
  per-window eligible counts (662 - 545 = 117 = 69 + 48 at w=120m; 662 -
  614 = 48 at w=60m) — confirms both scripts' underlying episode
  detection agrees.
- **Manual single-trade check:** a COVID-crash-day trade (entry
  2020-03-12 18:00 UTC) was hand-recomputed directly from the 1-minute
  CSV outside any script; `mae_1h`/`ret_1h` matched the pipeline exactly.
- **A real, previously-unquantified limitation, now measured and fixed:**
  both `phase_d_time_in_state3_v1.py` and `phase_d_recovery_window_v1.py`
  track only a trade's FIRST deep episode (documented as a scope
  limitation from the start, §14). Manually inspecting that same
  COVID-day trade showed 10 separate below-threshold episodes within one
  4h hold — not a rare pattern. Quantified project-wide: of the 615
  Discovery trades that "recovered" by the first-episode definition,
  **246 (40.0%) are back at/below the deep threshold again at the actual
  4h close** — i.e. "recovered" in these two reports means "recovered
  from its first dip," not "clear for the rest of the hold." Both
  reports now state this explicitly (`phase_d_time_in_state3_v1.py` gained
  a dedicated re-entry-check section; `phase_d_recovery_window_v1.py`
  gained a header caveat). This does not overturn §16's finding — if
  anything it means the true gap between a genuinely-recovered path and
  a not-yet-recovered one is understated by the current numbers, since
  the "recovered" comparison group is diluted by this ~40% backslide
  fraction — but it is a real limitation of the current episode-detection
  method, not just a theoretical one, and should be kept in mind before
  any Action Class is designed on top of it.
- No other logic errors were found in the reviewed scripts (index
  handling, checkpoint monotonicity, `MIN_CELL_N` gating, threshold
  direction, and the `DD_current`/`MAE_so_far` distinction all checked
  out).

## 18. Revision — Recovery-Window hypothesis (replaces §13), frozen 2026-07-26

§13's hypothesis (`duration_in_state_3` as the operative variable) is
replaced, not patched. §15 showed it directly: among trades that do
recover, how long they took shows no reliable gradient (34.8/33.3/56.2/
38.1% across duration buckets — not monotone). What the data actually
supports, confirmed by §16's landmark test and sharpened by §17's
verification pass:

> A deep episode opens a time-bounded recovery window. The **absence** of
> recovery within that window is a live-observable, increasingly negative
> path signal — `P(winner | no recovery by t0+w)` degrades monotonically
> in w and survives runway control (§16). Recovery *within* the window is
> not, however, a permanent clearance: 40.0% of trades that recover from
> their first deep episode re-enter the deep state later and are still
> there at the actual 4h close (§17). "Recovered" should be read as
> "cleared this episode," not "safe for the rest of the hold."

Formally: the operative variable is `P(winner | no recovery by t0+w)`,
not `duration_in_state_3` and not a permanent `recovered` flag.

### Two things this section deliberately does NOT do

1. **Does not pick a value for `w`.** §16's table shows the effect
   starting around w=60m and clearly present by w=90-120m — that is a
   Discovery finding about where the structure lives, not a selection of
   "the best w." Choosing a specific w to act on is its own design
   decision, to be made explicitly (and justified structurally, not by
   picking whichever w backtests best — the same discipline as §8/§10),
   not smuggled in here under the cover of restating the hypothesis.
2. **Does not yet define re-entry handling.** The 40% backslide rate
   means a real execution mechanic cannot use a single permanent
   `recovered = True` flag per trade. Each deep episode needs its own,
   independently-evaluated recovery window — episode 2 is not "still
   covered" by episode 1's recovery. This must be defined explicitly
   before any execution code exists, not assumed.

### Confirmed roadmap from here (nothing beyond step 1 done yet)

1. Choose an Action Class from §13's list (I-IV) on structural grounds —
   Action Class I (delayed binary exit keyed to the recovery window) is
   the closest fit to what §16/§18 actually found, but this is a
   recommendation for the next discussion, not decided in this document.
2. Freeze a specific `w` as a design decision, with its justification
   written down (not picked because it backtests best).
3. Formally define episode re-entry handling (each deep episode gets its
   own independent recovery-window evaluation).
4. Only then: work out any remaining discovery-level mechanic detail on
   2020-2025.
5. Execution backtest on Discovery.
6. Freeze the mechanic.
7. Only then: a single, unmodified 2026 OOS validation run.

No code for any of steps 1-6 exists yet. This section is the hypothesis
freeze that must precede it.

## 19. Result — does re-entry itself carry information?

Per the user's plan, before freezing `w` or re-entry handling (§18's open
items 2-3): `phase_d_episode_reentry_v1.py` checked, purely descriptively,
whether episode count / re-entry carries information beyond first-episode
recovery status. Answer: **yes, substantially.**

**Section A — P(winner) by total distinct deep-episode count (whole 4h
hold):**

| Episodes | n | P(winner) |
|---|---|---|
| 0 | 402 | 81.6% |
| 1 | 131 | 50.4% |
| 2 | 85 | 36.5% |
| 3 | 91 | 31.9% |
| 4+ | 355 | 26.2% |

Clean, monotone decay. Also notable: 355 of the 662 ever-deep trades
(53.6%) have 4 or more distinct episodes — oscillating back and forth
across the deep threshold is the *common* case, not an edge case, once a
trade goes deep at all.

**Section B — among the 615 trades that recovered from episode 1,
split by whether a later episode ever happens:**

| Group | n | P(winner) |
|---|---|---|
| no re-entry (exactly 1 episode) | 84 | 78.6% |
| re-entry (2+ episodes) | 531 | 28.8% |

This directly answers the user's question: re-entry is not neutral —
"a new independent negative path begins" understates it. A trade that
re-enters the deep state after recovering is, on average, in a
substantially worse position than one that stays clear, even though both
are labeled "recovered" by the first-episode definition alone.

**Important caveat — this is not yet a live signal.** Both tables count
episodes over the *entire* 4h hold, which is only fully known at the
close (the same hindsight problem §16 fixed for "never recovered by
close"). Reformulating this as a live-observable feature — e.g. "number
of deep episodes observed so far, as of time t" — would need the same
landmark treatment §16 applied to recovery, and has not been done here.
Section A/B establish that episode count/re-entry matters descriptively;
they do not yet show it is usable live at a specific point in a trade.

**Implication for §18's open items:** re-entry handling should not
default to "each episode independently, no memory of prior episodes" (the
user's initial structural preference) without qualification — §19 shows
prior-episode history clearly carries information. The open question is
now sharper: not *whether* re-entry matters (it does), but how to build a
live-observable version of "how many deep episodes has this trade already
had by time t" into whatever Action Class is eventually chosen.

## 20. Result — live-observable episode history, and a refinement of §19

`phase_d_episode_history_landmark_v1.py` rebuilt §19's episode-count
finding as a proper landmark measure: `episode_count_so_far(t)` and
`currently_deep(t)`, both using only the path observable up to checkpoint
t (1h/2h/3h) — fixing §19's explicitly-flagged hindsight problem.

**Section A** (episode count alone, live) reproduces the broad shape of
§19's whole-hold table — win rate falls from ~57-67% at 0 episodes to
~33-36% at 3+ — but is noticeably noisier (e.g. at 1h, 3+ episodes shows
36.3% vs. 2 episodes' 34.5%, a small non-monotonicity). That noise turns
out to have a clean explanation in Section B.

**Section B** (episode count **and** current deep/recovered status,
combined) is the important refinement:

| t | 0: never deep | in ep. 1 (ongoing) | recovered after 1, no re-entry | in ep. 2 (ongoing) | recovered after 2+ | in ep. 3+ (ongoing) |
|---|---|---|---|---|---|---|
| 1h | 60.4% | 28.6% | 57.5% | 29.5% | 47.1% | 18.9% |
| 2h | 67.1% | 21.0% | 62.5% | 2.7% | 55.3% | 12.5% |
| 3h | 74.0% | 3.8% | 68.5% | 8.9% | 53.2% | 3.7% |

**This meaningfully revises how §19's stark 78.6% vs. 28.8% split should
be read.** That split mixed two different current-status populations
together inside "re-entry (2+ episodes)": trades currently stuck in a
later episode (here: 2.7-29.5%, consistently bad) and trades that
re-entered but are currently clear again (here: "recovered after 2+
episodes", 47.1-55.3% — moderate, not catastrophic). Once current status
is disaggregated from episode count:

- **Current status dominates.** "Currently in an episode" is bad at every
  checkpoint regardless of episode count (18.9-29.5% at 1h, decaying
  further with elapsed time — consistent with §16's landmark effect).
  "Currently recovered" stays moderate-to-good regardless of how many
  episodes it took to get there.
- **Episode count still adds a real, smaller, secondary effect.**
  "Recovered after 1 episode, no re-entry" (57.5-68.5%) consistently
  beats "recovered after 2+ episodes" (47.1-55.3%) at every checkpoint —
  a real, moderate gap, not noise (holds at all three checkpoints,
  decent n throughout). It is just much smaller than §19's raw 78.6% vs.
  28.8% made it look, because that number wasn't controlling for current
  status.

**Conclusion for §18's open items:** the live-observable path-state is
better represented as the joint (current status × episode count so far)
in Section B's 6-way split than as either dimension alone. Neither "just
use the recovery-window landmark effect (§16)" nor "just use total
episode count (§19)" is the full picture; §20's 6-way state is the
current best live-observable summary of what actually predicts outcome.
This is now a reasonable basis for finally choosing an Action Class and
freezing `w` (§18's open items 1-2) — no further broadening of Discovery
is planned before that decision.

## 21. Action Class decision, frozen 2026-07-26

State Discovery ends here. §20's 6-way path-state is treated as the input;
this section decides what a trade does in each state — a genuinely new
decision, not derivable from the descriptive tables alone.

**Action Class chosen: binary HOLD / EXIT** (a restriction of §13's
Action Class I). No partial reduction, no dynamic risk band, no sizing
change — those remain out of scope for this first intervention test, per
the user's explicit preference to test the simplest action space before
any more elaborate one. Two actions only:

- **HOLD** — continue to the normal 4h close, unchanged from
  `decision_rule_v1`'s existing baseline behavior.
- **EXIT** — close the position immediately at the current price, before
  the 4h close.

**Trigger rule, using §20's 6 states directly (no new threshold or
parameter introduced):**

> At each of the existing checkpoints (1h, 2h, 3h, in order): if the
> trade is **currently in a deep episode** at that checkpoint (states S1,
> S3, S5 — "in episode 1/2/3+ (ongoing)", regardless of episode count),
> EXIT immediately. If the trade is in S0, S2, or S4 (never deep, or
> currently recovered — regardless of how many prior episodes it took to
> get there), HOLD and continue to the next checkpoint, or to the normal
> 4h close if no checkpoint remains.

**Structural justification (not backtested-performance justification,
per §8/§10's discipline):** §20 showed current status dominates and
episode count is a secondary modifier of a trade that IS currently
recovered — it is not, on its own, a reason to act on a trade that is
currently clear. The trigger therefore keys on current status
(deep/recovered) rather than on episode count or a cumulative "penalty
counter," matching the user's stated conclusion: *"Episode-Status ist
der primäre Action-Kandidat. Episodenzahl ist ein Modifikator der
Erholungsqualität, nicht der primäre Exit-Trigger."*

**Why no new `w` was fit:** the checkpoint grid (1h/2h/3h) already used
throughout §11-§20 is reused as-is for the decision points, rather than
fitting a bespoke exit-timing parameter on top of it. This keeps the
intervention test free of any newly-introduced, backtest-chosen
parameter — the only "parameters" here (deep threshold -0.75%, Def 1
recovery, the checkpoint grid) were all already frozen for other reasons
earlier in Phase D, not tuned for this action.

**What this section explicitly does NOT claim:** that EXIT is the
correct action, that 1h/2h/3h are the correct decision points, or that a
richer action space (partial reduction, dynamic risk band) wouldn't do
better. It claims only that this is the simplest, most directly
data-motivated first intervention to actually test — on Discovery only,
against the existing `decision_rule_v1`/baseline-hold-to-4h trades as the
comparison, per §18's roadmap steps 4-5. 2026 remains untouched until
this is backtested, reviewed, and (if it holds up) frozen.

## 22. Result — Action Class I's first Discovery backtest does NOT clearly improve on holding

`phase_d_action_class_i_v1.py` ran §21's rule on the same 1,064 Discovery
trades as `decision_rule_v1`'s baseline. Reported without cherry-picking:

| | Win rate | Mean | Median | P05 | Profit factor | Final equity | Max DD |
|---|---|---|---|---|---|---|---|
| Baseline (hold-to-4h) | 51.4% | -0.1306% | +0.0473% | -4.19% | 0.853 | 0.1731 | -82.94% |
| Action Class I | 44.4% | -0.1668% | **-0.2403%** | -2.79% | 0.802 | 0.1329 | -86.58% |

Action Class I is worse on win rate, mean, median, profit factor, final
equity, AND max drawdown. The only metric that improves is P05 (tail
return: -2.79% vs. -4.19%). This is a real, not a marginal, result: the
baseline's median trade is a small winner (+0.0473%); Action Class I's
median trade is a real loser (-0.2403%).

**Why, given §20's clean descriptive structure:** the by-action breakdown
shows the mechanism directly. For `exit_1h` (209 trades — the trades in
state S1/S3/S5 at 1h), the intervention's realized outcome
(mean -1.8832%, median -1.5701%) is *worse* than what holding to 4h would
have produced for the exact same trades (mean -1.6563%, median -1.1844%).
Only 24.4% of these trades go on to win if held (§11) — but that
minority's gains are large enough, and the early-exit's locked-in loss
plus round-trip fee/slippage cost is real enough, that cutting losses at
1h has a *worse* expectation than holding, despite the correct and
well-verified low win rate. Low P(winner) alone does not imply "exit is
correct" once the size of the outcomes (not just their sign) is
accounted for — this is exactly the asymmetric-payoff trap the project's
median-over-mean discipline (see the house rules) exists to catch, now
observed directly in an action, not just a raw distribution.

**What this does and doesn't mean:**

- It does **not** mean §11-§20's descriptive findings are wrong — the
  state definitions, the landmark effect, and the episode-history
  structure all still hold as *descriptions* of what happens.
- It does mean Action Class I, specifically *as frozen in §21* (exit
  immediately and unconditionally whenever currently in an episode, at
  any of 1h/2h/3h), is not a good position-management rule on this
  metric set. A win-rate-based intuition ("this state usually loses, so
  exit it") does not survive contact with the actual payoff distribution.
- The one genuine improvement (P05, tail risk) is a real risk/return
  trade-off, not a free lunch — it comes at the cost of every other
  metric, most importantly the median flipping from a small win to a
  real loss.

**Not yet frozen or ruled out:** whether some other trigger design (e.g.
requiring the episode to persist for some duration before exiting,
closer to §16's original `w`-based landmark idea, rather than exiting
the instant a trade enters a deep episode) or some other Action Class
(partial reduction, dynamic risk band) could do better. §21's specific
binary immediate-exit rule is the one result established here — it is
not evidence against position management in general, only against this
first, simplest version of it. This is the natural next discussion,
not decided in this document.

## 23. Action Class II — Recovery-Timeout, tested at two pre-specified w values

Per the user's diagnosis of §22 (`P(win) falling` does not imply
`E[return | HOLD] falling`, because rare-but-large recoveries can
outweigh frequent small losses), Action Class II gives each deep episode
(including re-entries, each independently) up to `w` minutes to recover
on its own before acting, instead of exiting the instant a trade is
detected in an episode. Only `w=60m` and `w=120m` were tested — both
pre-specified from §16's finding (effect present by 60m, clear by
90-120m), not a sweep with the best kept.

| | Win rate | Mean | Median | P05 | Profit factor | Final equity | Max DD |
|---|---|---|---|---|---|---|---|
| Baseline (hold-to-4h) | 51.4% | -0.1306% | +0.0473% | -4.19% | 0.853 | 0.1731 | -82.94% |
| Action Class II, w=60m | 49.9% | -0.1337% | -0.0085% | -3.37% | 0.846 | 0.1807 | -81.65% |
| Action Class II, w=120m | 51.2% | -0.1061% | **+0.0369%** | -3.86% | **0.876** | **0.2368** | **-76.66%** |

**w=60m** is close to neutral — median dips slightly negative, but final
equity and max drawdown both improve modestly.

**w=120m is a clearer result, and a meaningfully different picture from
§22's Action Class I:** win rate and median are essentially unchanged
from baseline (51.2% vs. 51.4%; +0.0369% vs. +0.0473%), while mean,
profit factor, final equity (+37%), and max drawdown (-76.66% vs.
-82.94%) all improve. Unlike §22, the by-episode breakdown now shows the
timeout-exit subgroups roughly matching or beating their would-have-held
baseline (e.g. `timeout_exit_episode_1`: -3.4802%/-2.4811% intervention
vs. -3.5687%/-2.4977% baseline) rather than being worse, as Action Class
I's instant version was. Giving the episode a bounded chance to resolve
itself before acting appears to filter out exactly the trades that would
have recovered anyway, leaving a genuinely worse-off subset for the
timeout to act on.

**Caveats, stated plainly, not smoothed over:**
- Still Discovery-only (2020-2025). **Not OOS-validated.** Nothing here
  should be treated as frozen or ready to trade.
- `timeout_exit_episode_2` at w=120m has only n=16 — informative as a
  direction, not as a precise estimate.
- Two w values is not an exhaustive test; it is a deliberately small,
  pre-justified set, consistent with the project's anti-overfitting
  discipline (§8) — not a claim that 120m is *the* optimal window.
- Compounding/final-equity improvements are partly a variance-reduction
  effect (smaller realized drawdowns compound better), not purely an
  improvement in the arithmetic edge — worth keeping the metrics
  separate rather than reading "final equity up 37%" as "37% more
  profitable" in isolation.

**Where this leaves Phase D:** w=120m Recovery-Timeout is the first
Action Class tested that does not clearly hurt the baseline and improves
several risk metrics. It is a candidate for the next roadmap step (§18:
OOS validation on 2026) if the user wants to proceed — but that decision,
and any final freeze of the exact mechanic, is deliberately left open
here, not made in this document.

## 24. Pre-registration for OOS validation, frozen 2026-07-26 — written BEFORE the OOS run

Per the user's decision: no further Discovery on the Action Class itself.
`w=120m` is frozen and carried into a single OOS run on 2026, per §7/§18's
original discipline (fit/decide on Discovery only, freeze, then one
unmodified validation run — no iteration against 2026 results). This
section is written and committed *before* that run's output exists, so
the criteria cannot be adjusted after seeing the result.

**Frozen, not re-decided:**
- Action Class II, Recovery-Timeout, exactly as coded in
  `phase_d_action_class_ii_v1.py`.
- `w = 120 minutes`. Not re-optimized, not re-swept — `w=60m` was also
  tested on Discovery (§23) but is not carried forward.
- Baseline = `decision_rule_v1`'s existing hold-to-4h behavior (identical
  fee/slippage assumptions on both sides).
- Population = the actual 2026 `decision_rule_v1` trades (LPL/volatility
  quintile edges frozen on 2020-2025, applied unchanged — same discipline
  as `hypothesis_validation.py`/`decision_rule_v1.py` throughout this
  project).

**Primary metrics** (the ones that decide the outcome):
- Paired `ΔReturn = return(Action II) - return(Baseline)` per trade —
  its distribution (mean, median, % of trades with `ΔReturn > 0`), not
  just aggregate PnL, specifically to check whether any edge is broad or
  driven by a few outliers.
- Profit factor.
- Max drawdown.

**Secondary metrics** (reported, not decisive alone):
- Median return, win rate, final compounded equity.

**No tuning permitted in this run:** no new `w`, no new states, no new
filters, no re-fitting of the deep threshold or recovery definition. The
by-triggering-episode breakdown (episode 1/2/3+) is reported for
transparency, matching Discovery's own breakdown — but per the user's
explicit caution, any single-digit-to-teens `n` cell (as `episode_2` was
at n=16 in Discovery) is read as a directional note only, never as a
validated effect, especially given 2026's much smaller trade count than
Discovery's.

**Outcome classification, fixed in advance:**
- **A — OOS confirmed:** paired performance improves (primary metrics
  point the same direction as Discovery) without materially worsening
  robustness metrics.
- **B — OOS neutral:** no clear advantage, but no clear harm either.
  Hold-to-4h remains the default in this case.
- **C — OOS refuted:** the Discovery-observed edge disappears or reverses
  materially. The hypothesis is dropped, not re-tuned.

The next commit after this one is the OOS run itself, using this section
as the fixed yardstick.
