# Phase D Action Class II OOS v1 -- 2026 validation of the frozen w=120m Recovery-Timeout

Generated 2026-07-26T18:12:21.357720+00:00.

Single, unmodified OOS run per phase_d_path_state_hypothesis.md SS24 (pre-registered BEFORE this script was run). w=120m frozen from Discovery (SS23); no tuning of any kind performed here. LPL/volatility quintile edges fit on 2020-2025 only, applied unchanged to 2026.

---

## Overall: baseline (hold-to-4h) vs. frozen Action Class II (w=120m) -- 2026 OOS

| | n | Win rate | Mean | Median | P05 | Profit factor | Final equity | Max drawdown |
|---|---|---|---|---|---|---|---|---|
| Baseline (hold-to-4h) | 39 | 51.3% | -0.0893% | +0.1787% | -3.09% | 0.868 | 0.9609 | -15.36% |
| Action Class II (w=120m) | 39 | 51.3% | -0.0289% | +0.1787% | -2.42% | 0.953 | 0.9847 | -12.63% |

---

## Primary: paired delta-return distribution (SS24)

`delta = return(Action II) - return(Baseline)`, per trade. This is the primary metric SS24 pre-registered -- not just aggregate PnL, to check whether any edge is broad or driven by a few trades.

| n | Mean delta | Median delta | % trades with delta > 0 | % trades unchanged (delta = 0) |
|---|---|---|---|---|
| 39 | +0.0604% | +0.0000% | 7.7% | 84.6% |

---

## By triggering episode (transparency only -- see SS24's small-n caution)

| Action | n | Intervention: mean / median | Baseline (would-have-held): mean / median |
|---|---|---|---|
| hold_4h | 33 | +0.3830% / +0.4733% | +0.3830% / +0.4733% |
| timeout_exit_episode_1 (n too small to interpret as a validated effect) | 2 | -2.2774% / -2.2774% | -3.8184% / -3.8184% |
| timeout_exit_episode_3+ (n too small to interpret as a validated effect) | 4 | -2.3026% / -2.0479% | -2.1211% / -1.8708% |
