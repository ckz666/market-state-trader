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
