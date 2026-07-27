# decision_rule_v3 candidate — micro_return_5m entry filter, pre-registration

Written and committed BEFORE the OOS script exists, same discipline as
`decision_rule_v2_trending_filter_hypothesis.md` and Phase D §24. An
entry-selection refinement candidate (Phase B territory).

**Note on the immediately preceding attempt:** `decision_rule_v2`'s
trending filter looked strong in Discovery (n=735 real trades, every
metric better) and was **refuted** on 2026 with all three primary
metrics moving against it. That is the base rate this candidate is
being judged against — a strong Discovery result is, by itself, not
much evidence.

## 1. Where this comes from

- `discovery_v10`: `micro_return_5m` (1m price change over the 5 minutes
  before the state candle) showed a clean monotone win-rate gradient.
- `discovery_v11`: it is NOT redundant with LPL — r=0.127, its own PCA
  component (23.7% of variance, 0.973 loading), gradient persists when
  conditioned on LPL quintile. (By contrast `short_term_rsi_15m`, r=0.822,
  was found to be essentially a faster copy of LPL and dropped.)
- `discovery_v12`: 6/6 years sign-consistent at 15m/1h/4h.
- `hypothesis_validation_micro_return_5m.py`: 3/3 horizons held sign OOS
  on 2026 at the candidate level.
- `discovery_v13`: the shared-P_t / bid-ask-bounce artifact concern was
  raised and tested with a one-minute-gapped variant — effect largely
  survives (~15-25% of Discovery magnitude was artifact, the rest real).
- `discovery_v14`: gap-decay is smooth and monotone (gone by ~10-15 min);
  spread widens monotonically with volatility, on both `volatility_atr_norm`
  and `micro_volatility_1m`.
- `discovery_v15`: inside `decision_rule_v1`'s actual entry cell
  (LPL==Q1 & Vol==Q5), the micro_return_5m Q1-vs-Q5 median spread is
  **+0.1441% (15m) / +0.1501% (1h) / +0.1654% (4h)** — larger than the
  factor's unconditional spread, i.e. LPL concentrates rather than
  dilutes it. Best cell (LPL==Q1 & ret5m==Q1, n=1313): 58.2% win rate,
  +0.3118% median at 4h.

## 2. The hypothesis

> Restricting `decision_rule_v1`'s `long_candidate` signals to those
> where `micro_return_5m` is in its lowest quintile (Q1 — price fell
> most sharply in the 5 minutes before the signal) improves the realized
> trade outcome distribution versus the existing unfiltered rule.

## 3. Frozen definition — no new fitted parameter

- **Filter: `micro_return_5m` quintile == Q1**, on top of
  `decision_rule_v1`'s existing `LPL==Q1 & Vol==Q5 → long_candidate`.
- Quintile edges fit **only on 2020-2025**, applied unchanged to 2026 —
  same procedure as every other frozen transform in this project.
- Q1 (not a tuned percentile cut) is chosen because it is the extreme
  bucket of the same quintile scheme used throughout; no threshold search.
- Horizon stays 4h (`decision_rule_v1`'s frozen target). Nothing about
  LPL, volatility, or the underlying quintile edges changes.
- `avoid_long` out of scope, unchanged.

## 4. Pre-registered OOS metrics and classification

**Primary:** win rate, median return, profit factor — same three as
`decision_rule_v2`, so the two attempts are judged by an identical bar.
**Secondary:** mean return, P05, and trade count retained.

**Expected sample-size problem, stated upfront:** `decision_rule_v1`
produced only 39 real (Option-A-deduplicated) trades in 2026. A Q1
filter keeps roughly a fifth to a quarter of signals, so the filtered
2026 trade count will plausibly be **under 15** — below this project's
own `MIN_CELL_N` in most contexts. Therefore:

- The **trade-level** result will be reported but treated as
  directional only, not decisive, unless n >= 15.
- The **candidate-level** result (all `long_candidate` signals, not
  Option-A-deduplicated) is reported alongside it as the higher-n view,
  explicitly labeled as not being a tradeable-sequence result.

**Classification:**
- **A — OOS confirmed:** primary metrics point the same direction as
  Discovery, without materially worse P05, at a sample size that
  supports the claim.
- **B — OOS neutral / underpowered:** no clear advantage or harm, or
  the sample is too small to distinguish. Hold `decision_rule_v1`
  unchanged.
- **C — OOS refuted:** the Discovery edge disappears or reverses.

## 5. Explicitly not done here

- Not implemented as a change to `decision_rule_v1.py`. Parallel,
  labeled comparison only, unless and until formally adopted.
- No re-tuning of the quintile cut based on the OOS result. One frozen
  filter, one OOS run, honest result — regardless of outcome.
- Not combined with Phase D position-management logic (separate question).

## 6. OOS result and classification (2026-07-27)

`decision_rule_v3_micro_return_filter_oos_v1.py`, one unmodified run.

**Trade level** (Option A de-duplicated, fees/slippage — the real result;
n=24, above the pre-registered n>=15 bar, so NOT directional-only):

| Population | n | Win rate | Median | Mean | P05 | Profit factor |
|---|---|---|---|---|---|---|
| Baseline (all decision_rule_v1 trades) | 39 | 51.3% | +0.1787% | -0.0893% | -3.09% | 0.868 |
| **Filtered (+ micro_return_5m == Q1)** | **24** | **54.2%** | **+0.3772%** | **+0.3037%** | **-1.52%** | **1.565** |

Every pre-registered primary metric improves. Mean flips from negative to
positive; profit factor goes from below 1 to well above; P05 (tail)
improves substantially. On its own this is the best OOS result any
candidate rule has produced in this project.

**Candidate level** (all `long_candidate` signals, n=45 — higher sample,
but overlapping 4h windows, so not a tradeable sequence):

| Population | n | Win rate | Median | Mean | Profit factor |
|---|---|---|---|---|---|
| Baseline | 113 | 59.3% | +0.3110% | +0.0813% | 1.122 |
| Filtered | 45 | 57.8% | +0.3110% | -0.0301% | 0.965 |

**This does not corroborate the trade-level result — it mildly
contradicts it.** Win rate falls slightly, median is identical to four
decimal places, profit factor falls below 1.

**Classification: B — promising but not established.** Not A, despite
the trade-level numbers meeting §4's letter, because:

- The two views disagree, and the *disagreeing* one has nearly twice the
  sample (45 vs. 24). A real entry-selection edge should show up in both;
  a filter that only helps after Option-A de-duplication is suspicious,
  because de-duplication changes *which* trades get taken, not just how
  many. With 39 baseline trades total, the filter's 24 trades are a
  different, sparser sequence — several of the excluded ones were
  overlapping-window duplicates that the baseline had to skip anyway.
  Which specific 24 trades survive is partly an artifact of signal
  timing, and at this n a handful of them drive the entire result.
- n=24 clears the pre-registered bar but is still small in absolute
  terms. The single preceding attempt (`decision_rule_v2`) is a direct
  warning: it looked excellent on 735 Discovery trades and was refuted
  on 34 OOS trades.

**Decision: `decision_rule_v1` stays unchanged for now.** Not adopted,
not refuted, not re-tuned. Per §5, no second OOS attempt and no
threshold search follows from this.

**What would settle it:** more out-of-sample data, specifically at the
trade level. The live paper-trading service continues collecting; the
natural re-evaluation trigger is roughly 40-60 filtered trades (vs.
today's 24), at which point the trade-level and candidate-level views
should either converge or the discrepancy should become interpretable.
Until then this is the strongest open candidate in the project, and
explicitly not a validated one.

## 7. Downgraded to C after discovery_v16 (2026-07-27)

§6 said the discrepancy "is not resolved by this run" and that more data
would settle it. It turned out the question was answerable immediately,
on Discovery data, without waiting — `discovery_v16` did exactly that,
reproducing both views at ~40x the sample (1,064 trades / 3,276
candidates).

**The discrepancy is systematic, not small-sample noise — but its
direction is unstable, which is worse for this candidate than either
explanation §6 considered:**

| View | Discovery (n=1,064 / 3,276) | 2026 OOS (n=24 / 45) |
|---|---|---|
| Trade level | filter **hurts** (win −0.72pp, median −0.021pp) | filter helps strongly |
| Candidate level | filter **helps** (win +1.38pp, median +0.080pp) | filter mildly hurts |

The two periods disagree in *opposite* directions on both views. A filter
whose apparent benefit flips sign depending on which period and which
view you look at is not a stable edge — the favourable 2026 trade-level
numbers in §6 were, on this evidence, luck at n=24.

**Mechanism found (`discovery_v16` §B):** Option A signal-to-trade
retention rises from **32.5% (baseline) to 55.1% (filtered)**. Filtering
thins the signal stream, so far fewer signals are blocked by an
already-open position. **The filtered trade set is therefore not a subset
of the baseline trade set — it is a different, sparser entry sequence
altogether.** That is why the two views can disagree at all, and why
comparing them naively is misleading. (A milder secondary effect: 15.9%
of filtered signals sit at cluster position 0 vs. 11.3% of non-filtered.)

**Revised classification: C — not supported.** `decision_rule_v1` stays
unchanged. Per §5, no re-tuning and no further attempt on this
hypothesis. The underlying *factor* `micro_return_5m` remains a real,
OOS-validated, artifact-checked finding (discovery_v10-v15) — what fails
here is specifically its use as a Q1 entry filter on top of
`decision_rule_v1`, which is a narrower claim.

**Methodological note worth carrying forward:** trade-level and
candidate-level results are not two views of one thing. Under Option A
logic, changing the *signal* set changes the *trade* set
non-proportionally. Any future entry-filter candidate must be judged
against a baseline evaluated the same way, and a filter that improves
only one view should be treated as unproven until the mechanism is
understood.
