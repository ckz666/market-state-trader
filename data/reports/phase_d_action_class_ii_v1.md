# Phase D Action Class II v1 -- Recovery-Timeout intervention (Discovery only)

Generated 2026-07-26T17:35:35.103639+00:00.

Per the project discussion after SS22: rather than Action Class I's instant exit-on-detection (a net negative), this gives each deep episode up to `w` minutes to recover on its own before acting -- directly testing SS16's original landmark hypothesis as an action. Only w=60m and w=120m are tested (both pre-specified from SS16's finding, not a sweep). Same trades/fees/slippage as phase_d_action_class_i_v1.py. Each episode (including re-entries) gets its own independent timeout check, in order; the position closes at the first timeout, if any. **Discovery only (2020-2025), NOT an OOS validation** -- 2026 untouched.

---

## w = 60m

### Overall: baseline (hold-to-4h) vs. Action Class II

| | n | Win rate | Mean | Median | P05 | Profit factor | Final equity | Max drawdown |
|---|---|---|---|---|---|---|---|---|
| Baseline (hold-to-4h) | 1064 | 51.4% | -0.1306% | +0.0473% | -4.19% | 0.853 | 0.1731 | -82.94% |
| Action Class II (w=60m) | 1064 | 49.9% | -0.1337% | -0.0085% | -3.37% | 0.846 | 0.1807 | -81.65% |

### By triggering episode (which episode timed out, if any)

| Action | n | % of trades | Intervention: mean / median | Baseline (would-have-held): mean / median |
|---|---|---|---|---|
| hold_4h | 812 | 76.3% | +0.6754% / +0.4630% | +0.6754% / +0.4630% |
| timeout_exit_episode_1 | 66 | 6.2% | -3.0193% / -2.5337% | -2.7241% / -2.0132% |
| timeout_exit_episode_2 | 43 | 4.0% | -2.6705% / -2.1473% | -2.9338% / -2.3099% |
| timeout_exit_episode_3+ | 143 | 13.4% | -2.6330% / -2.3918% | -2.6675% / -2.3255% |

---

## w = 120m

### Overall: baseline (hold-to-4h) vs. Action Class II

| | n | Win rate | Mean | Median | P05 | Profit factor | Final equity | Max drawdown |
|---|---|---|---|---|---|---|---|---|
| Baseline (hold-to-4h) | 1064 | 51.4% | -0.1306% | +0.0473% | -4.19% | 0.853 | 0.1731 | -82.94% |
| Action Class II (w=120m) | 1064 | 51.2% | -0.1061% | +0.0369% | -3.86% | 0.876 | 0.2368 | -76.66% |

### By triggering episode (which episode timed out, if any)

| Action | n | % of trades | Intervention: mean / median | Baseline (would-have-held): mean / median |
|---|---|---|---|---|
| hold_4h | 928 | 87.2% | +0.3655% / +0.2837% | +0.3655% / +0.2837% |
| timeout_exit_episode_1 | 41 | 3.9% | -3.4802% / -2.4811% | -3.5687% / -2.4977% |
| timeout_exit_episode_2 | 16 | 1.5% | -3.9620% / -2.8037% | -4.5991% / -2.9260% |
| timeout_exit_episode_3+ | 79 | 7.4% | -3.1138% / -2.8286% | -3.2695% / -2.7634% |

---

