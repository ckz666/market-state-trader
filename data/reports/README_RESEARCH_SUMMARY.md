# Research summary — market-state-trader

Status as of 2026-07-27. Navigation aid for 26 discovery scripts, 4
decision-rule candidates and one position-management phase. Every claim
here links to the report that produced it.

**Bottom line:** no trade-ready system. Two genuinely OOS-validated
predictive factors, one hold-length candidate that passed its first OOS
test, and a clear measured reason why this is hard — the edge is roughly
the same size as the transaction costs. Nine seriously-tested ideas came
back negative, which is itself the main output.

---

## 1. What is actually established

| Finding | Evidence | Status |
|---|---|---|
| **LPL × Volatility** predicts forward returns | `hypothesis_validation.md` — 5/5 volatility quintiles held sign OOS on 2026 | **Validated.** Basis of `decision_rule_v1`. |
| **`micro_return_5m`** (5-min pre-signal move) predicts, independently of LPL | `hypothesis_validation_micro_return_5m.md` — 3/3 horizons held sign OOS; `discovery_v11` r=0.127 vs LPL, own PCA component; `discovery_v13` survives the shared-price artifact test | **Validated as a factor.** Never converted into a working rule. |
| **Longer holds beat 4h** | `discovery_v19` monotone across 8 hold lengths; `discovery_v21` walk-forward 4/5 folds; `decision_rule_v4` OOS all 3 primary metrics same direction | **Best open candidate.** n=16 OOS — promising, not proven. |
| Costs ≈ edge | `discovery_v19` gross median +0.267% vs 0.22% round-trip cost at 4h | **The central problem.** |

## 2. The frozen production rule

`decision_rule_v1` (unchanged since Phase B, and unchanged by everything
below): `LPL==Q1 & Vol==Q5 → long_candidate`, 4h hold, Option A position
logic. Realized on Discovery: win 51.4%, net median +0.047%, profit
factor 0.853.

## 3. What was tested and rejected

Each of these was a real hypothesis with a real test, not a strawman.

| Idea | Report | Why it failed |
|---|---|---|
| Regime filter (`trending` only) | `decision_rule_v2_*` | Strong on 735 Discovery trades; **refuted OOS** — all 3 primary metrics moved against it |
| `micro_return_5m` as entry filter | `decision_rule_v3_*`, `discovery_v16` | Trade-level and candidate-level views disagreed, and the direction **flipped between periods**. Mechanism found: Option A retention jumps 32.5%→55.1% under the filter, so the filtered trade set is a different sequence, not a subset |
| Volume (all 3 normalizations) | `discovery_v17` | Spreads an order of magnitude below LPL; 4/6 year stability; does not amplify LPL |
| Entry timing (delay 0-30 min) | `discovery_v18` | Flat overall; **actively harmful** on the sharp-drop subgroup — the mean reversion has already happened at signal time |
| Shorter holds (15m-2h) | `discovery_v19` | Monotonically worse; fixed 0.22% cost dominates the smaller gross move |
| Short side (`avoid_long`) | `discovery_v20`, `discovery_v26` | Loses at every hold, worse than long on every metric, 1/4 years positive. Still loses after crediting received funding |
| Position sizing (inverse-vol, LPL-extremity) | `discovery_v23` | Neither beats unit sizing on equity; both worsen drawdown badly. LPL-extremity raises mean/PF but the concentration wrecks the compounding path |
| State transitions (origin matters) | `discovery_v24` → `discovery_v25` | Looked significant at 15m and 4h; **the 4h result was an artifact** of 75% overlapping forward windows. Survives at 15m only, where it is the smallest effect |
| Instant exit on drawdown | `phase_d_path_state_hypothesis.md` §22 | Net negative vs holding — low P(winner) does not imply negative EV, because rare large recoveries outweigh frequent small losses |

## 4. Position management (Phase D)

`phase_d_path_state_hypothesis.md`, 27 sections. Went through a full
hypothesis → test → revision → OOS cycle:

- **Recovery-state definition frozen** (§11): 3 states from `DD_current`
  + `MAE_so_far` jointly. Confirmed on real trades (P(winner) 60/51/24%
  at 1h across states).
- Duration-in-state hypothesis (§13) **tested and revised away** (§15) —
  no reliable gradient.
- Reframed as a landmark test (§16): `P(winner | no recovery by t0+w)`
  decays cleanly and survives runway control.
- Action Class I (instant exit) **net negative** (§22).
- Action Class II (Recovery-Timeout, w=120m) — Discovery-positive, OOS
  direction-consistent but only 6 interventions. **Classified
  "provisionally consistent"** (§27), frozen, awaiting ~20-30
  intervened trades.

## 5. Cost side — finally measured, not assumed

| Component | Before | Now |
|---|---|---|
| Funding | **Absent from the dataset entirely** | `funding_backfill.md` — 7,119 intervals from 2020. Costs a long +17%/yr (2020), +31% (2021), +4-12% since. Applied in `discovery_v26`: 24h candidate **survives** (PF 1.255→1.222) |
| Slippage | Assumed 5 bps/side, never measured | `slippage_measurement.md` — measured on Bitget's book: **0.01-0.08 bps**. Sensitivity: 4h PF 0.853→0.959, 24h PF 1.255→1.330 |

**Both carry real caveats.** Funding rates are Binance (Bitget's history
is capped at 33 days); measured proxy error 0.284 bps per 8h interval.
Slippage is a present-day calm-market snapshot, while this strategy
trades exclusively Vol==Q5 — spreads widen precisely when it fires. The
true slippage sits somewhere between 0.2 and 5 bps.

## 6. Method rules this project established

Learned the hard way, each from a concrete near-miss:

1. Median over mean — a COVID-era bin showed mean +0.34% vs median +0.006%.
2. `MIN_CELL_N` on every cross-tab — a fake interaction nearly emerged from two 11/16-sample corners.
3. Option A trade logic — overlapping signals re-measure the same move.
4. Fit transforms on Discovery only, freeze, never re-fit on test data.
5. **Low P(winner) ≠ negative EV of holding** — check the payoff distribution before acting (Action Class I cost us this lesson).
6. Pre-register OOS criteria in writing *before* running the script.
7. **Check whether a feature shares a price point with the outcome** — `micro_return_5m` did; an OOS test does *not* catch this (`discovery_v13`).
8. **Check for overlapping forward windows before any significance test** — `discovery_v25` invalidated `discovery_v24`'s headline on exactly this.
9. Verify cited literature actually exists before writing novelty claims.

## 7. Open threads, in priority order

1. **`decision_rule_v4` (24h hold)** — needs ~30-40 OOS trades (has 16). Known weakness: 2022 bear year is the one walk-forward fold where it loses.
2. **Phase D Recovery-Timeout** — needs ~20-30 intervened trades (has 6).
3. **Slippage under stress** — the measurement should be repeated during a high-volatility episode, since that is when the strategy actually trades.
4. Not obtainable without new collection: order-book history, liquidations, cross-asset.

Both live candidates are blocked on the same thing: prospective data.
The paper-trading service (`market-state-trader.service`) continues
collecting under frozen rules.
