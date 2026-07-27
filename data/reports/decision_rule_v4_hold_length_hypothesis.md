# decision_rule_v4 candidate — 24h hold length, pre-registration

Written and committed BEFORE the OOS script exists. Third candidate in
this series; the two before it both failed.

## 0. A methodological concern that has to be stated first

`discovery_v19` tested **eight** hold lengths (15m, 30m, 60m, 120m,
240m, 480m, 720m, 1440m) and this pre-registration picks the best one.
That is, structurally, exactly the parameter search this project's own
rules warn against (`phase_d_path_state_hypothesis.md` §8: grid-search
many variants on Discovery, keep the winner).

Three things partially — **not fully** — mitigate it:

1. The relationship is **monotone across all eight values**, not a noisy
   peak: 0.445 → 0.552 → 0.639 → 0.729 → 0.853 → 0.964 → 0.998 → 1.255
   profit factor. Cherry-picking a lucky cell in a noisy grid looks
   different from this.
2. There is a **mechanical explanation independent of the data**:
   round-trip cost is fixed at 0.2200% regardless of hold, so a longer
   hold amortizes it over a larger gross move. The gross-median column
   confirms this directly (+0.034% at 15m → +0.738% at 24h).
3. The original 4h choice was itself never optimized — it was inherited
   from the horizon the LPL hypothesis happened to be validated on.

What is **not** mitigated: 1440m was the largest value tested, so
"best of the tested range" may just mean "we stopped there". Longer holds
were not tried, and the true optimum (if any) is unknown. This candidate
should be read as "longer than 4h helps", not "24h is the right number".

## 1. The hypothesis

> Holding `decision_rule_v1`'s `long_candidate` trades for 24h instead
> of 4h improves the realized outcome distribution.

## 2. Frozen definition

- Entry: unchanged (`LPL==Q1 & Vol==Q5`, at `state_ts`).
- **Hold: 1440 minutes (24h)** instead of 240.
- Option A logic unchanged (a new signal is ignored while a position is
  open — which at 24h blocks considerably more signals).
- Fees and the stated 5bps/side slippage assumption unchanged.
- All quintile edges still fit on 2020-2025 only.

## 3. Discovery evidence being carried forward

| Hold | n | Win rate | Net median | Mean | P05 | Profit factor | Final equity | Max DD |
|---|---|---|---|---|---|---|---|---|
| 240m (current) | 1,064 | 51.4% | +0.0473% | -0.1306% | -4.19% | 0.853 | 0.1731 | -82.94% |
| 1440m (candidate) | 365 | 56.4% | +0.5179% | +0.3718% | -6.76% | 1.255 | 2.2701 | -49.62% |

Note P05 worsens (-4.19% → -6.76%): this is partly a risk-for-return
trade, not a pure improvement.

## 4. Pre-registered OOS metrics and classification

**Primary:** win rate, net median, profit factor (same three used for
`decision_rule_v2` and `v3`, so all three candidates face an identical
bar).

**Secondary:** mean, P05, max drawdown, trade count.

**Sample-size expectation, stated upfront:** `decision_rule_v1` produced
39 trades in 2026 at a 4h hold. At 24h, Option A will block far more
signals — the 2026 trade count will plausibly land near **10-20**. Per
the precedent set in `decision_rule_v3`, results below n=15 are
pre-declared **directional only**.

**Additional pre-registered check (learned from `discovery_v16`):**
because changing hold length changes which signals become trades, the
filtered and baseline trade sets are *different sequences*, not subsets.
The candidate-level view cannot be computed here (there is no stored
24h forward return), so instead the **Discovery-vs-OOS direction of each
primary metric** is compared explicitly. If Discovery and OOS disagree
in direction — the failure mode that sank v3 — that is reported as such
rather than resolved in the candidate's favour.

**Classification:**
- **A — confirmed:** primary metrics move the same direction as
  Discovery, at a sample size that supports the claim.
- **B — neutral / underpowered.**
- **C — refuted:** the Discovery edge disappears or reverses.

## 5. Explicitly not done here

- `decision_rule_v1.py` is not modified. Parallel comparison only.
- **No search for a better hold length based on the OOS result**, and no
  testing of holds beyond 1440m after seeing 2026. One frozen value, one
  run.
- Not combined with Phase D position management or any entry filter.
