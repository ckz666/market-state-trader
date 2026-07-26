# Phase D Action Class I v1 -- first intervention backtest (Discovery only)

Generated 2026-07-26T17:28:31.380192+00:00.

Frozen rule per phase_d_path_state_hypothesis.md SS21: at each of 1h/2h/3h in order, EXIT immediately if currently in a deep episode (any episode count); otherwise HOLD to the next checkpoint or the normal 4h close. No new parameter introduced -- deep threshold, recovery definition, and checkpoint grid were all frozen earlier for other reasons. Same fee/slippage assumptions as phase_c_baseline_v1.py. **Discovery only (2020-2025), NOT an OOS validation** -- 2026 stays untouched until this is reviewed and, if it holds up, formally frozen.

---

## Overall: baseline (hold-to-4h) vs. Action Class I intervention

Same n, same underlying trades (paired) -- only the exit rule differs.

| | n | Win rate | Mean | Median | P05 | Profit factor | Final equity (unit-sized, compounding) | Max drawdown |
|---|---|---|---|---|---|---|---|---|
| Baseline (hold-to-4h) | 1064 | 51.4% | -0.1306% | +0.0473% | -4.19% | 0.853 | 0.1731 | -82.94% |
| Action Class I | 1064 | 44.4% | -0.1668% | -0.2403% | -2.79% | 0.802 | 0.1329 | -86.58% |

---

## By action taken: intervention outcome vs. what holding to 4h would have done

For trades that got exited early, this is the direct trade-off: what did the early exit actually realize, vs. what would have happened had the rule not intervened (paired, same trades).

| Action | n | % of trades | Intervention: mean / median | Baseline (would-have-held): mean / median |
|---|---|---|---|---|
| hold_4h | 672 | 63.2% | +0.8399% / +0.5953% | +0.8399% / +0.5953% |
| exit_1h | 209 | 19.6% | -1.8832% / -1.5701% | -1.6563% / -1.1844% |
| exit_2h | 117 | 11.0% | -1.9776% / -1.6891% | -2.0878% / -1.8049% |
| exit_3h | 66 | 6.2% | -1.7717% / -1.5201% | -1.7118% / -1.4235% |
