"""
Phase D Action Class II v1 -- Recovery-Timeout intervention, directly
testing SS16's original landmark hypothesis as an actual action (rather
than Action Class I's instant, unconditional exit-on-detection, which
SS22 showed is a net negative). Per the project discussion following
SS22's result:

    P(win) falling in a state does not imply E[return | HOLD] falling --
    Action Class I cut losses on trades whose rare survivors were large
    enough to make holding better in expectation despite a low win rate.
    Action Class II tests whether GIVING the episode a bounded chance to
    resolve itself before acting changes that conclusion.

Rule: whenever a deep episode starts (the first one, or any later
re-entry -- each evaluated independently and in order), wait up to `w`
minutes past that episode's start. If it recovers (Def 1) within `w`,
take no action (continue holding normally -- if a LATER episode occurs,
that gets its own independent w-timeout check). If it has NOT recovered
by episode_start + w, EXIT immediately at that point. Only the first
episode that ever times out triggers an exit (the position is closed at
that point; no further episodes are evaluated).

Per the user's explicit preference: only two pre-specified values of `w`
are tested here (60 and 120 minutes, both directly motivated by SS16's
finding that the landmark effect is present by w=60m and clear by
w=90-120m) -- NOT a sweep over many candidate w values with the best one
kept. Same trades, same entry, same fee/slippage assumptions, same
paired comparison against the unmodified hold-to-4h baseline as
phase_d_action_class_i_v1.py. Results are broken down by which episode
(1st, 2nd, 3rd+) triggered the exit, matching the project's concern that
an aggregate result can hide heterogeneous subpopulations (SS22).

Discovery only (2020-2025). NOT an OOS validation -- 2026 untouched.

Usage:
    .venv/bin/python scripts/phase_d_action_class_ii_v1.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from discovery_report import load_candidates
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile
from decision_rule_v1 import apply_decision_rule
from phase_c_baseline_v1 import (
    load_1m_price_series, simulate, lookup_price, ENTRY_EXIT_TOLERANCE_SEC, SLIPPAGE_BPS_PER_SIDE,
)
from phase_d_time_in_state3_v1 import HOLD_MINUTES
from phase_d_episode_reentry_v1 import detect_episodes
import mst_config as config

TOL_MS = ENTRY_EXIT_TOLERANCE_SEC * 1000
W_VARIANTS = [60, 120]  # minutes; both pre-specified from SS16, not swept


def apply_action_class_ii(trades: list, price_history: dict, sorted_ts: list, w_minutes: int) -> pd.DataFrame:
    hold_ms = HOLD_MINUTES * 60_000
    rows = []
    for t in trades:
        entry_ts, entry_price = t["entry_ts"], t["entry_price"]
        entry_ms = int(entry_ts.timestamp() * 1000)
        hold_close_ms = entry_ms + hold_ms
        episodes = detect_episodes(entry_ts, entry_price, price_history, sorted_ts)

        action = "hold_4h"
        net_return = t["net_return"]

        for idx, ep in enumerate(episodes, start=1):
            deadline_ms = ep["start_ms"] + w_minutes * 60_000
            if deadline_ms >= hold_close_ms:
                break  # no time left before the natural close -- equivalent to holding
            recovered_in_time = (not ep["censored"]) and (ep["end_ms"] <= deadline_ms)
            if recovered_in_time:
                continue  # this episode resolved itself in time -- check the next episode, if any
            exit_price = lookup_price(price_history, sorted_ts, deadline_ms, TOL_MS)
            if exit_price is None:
                break  # data gap -- fall back to hold_4h
            gross_return = (exit_price - entry_price) / entry_price
            fee_cost = 2 * config.TAKER_FEE
            slippage_cost = 2 * (SLIPPAGE_BPS_PER_SIDE / 10000)
            net_return = gross_return - fee_cost - slippage_cost
            action = f"timeout_exit_episode_{idx}" if idx <= 2 else "timeout_exit_episode_3+"
            break

        rows.append({"action": action, "intervention_net_return": net_return, "baseline_net_return": t["net_return"]})
    return pd.DataFrame(rows)


def _stats(net: np.ndarray) -> dict:
    wins = net > 0
    equity = np.cumprod(1 + net)
    peak = np.maximum.accumulate(equity)
    max_dd = ((equity - peak) / peak).min()
    gross_wins = net[wins].sum()
    gross_losses = -net[~wins].sum()
    pf = gross_wins / gross_losses if gross_losses > 0 else float("inf")
    return {
        "n": len(net), "win_rate": wins.mean(), "mean": net.mean(), "median": np.median(net),
        "p05": np.quantile(net, 0.05), "profit_factor": pf, "final_equity": equity[-1], "max_dd": max_dd,
    }


def section_for_w(df: pd.DataFrame, w_minutes: int) -> str:
    b = _stats(df["baseline_net_return"].to_numpy())
    iv = _stats(df["intervention_net_return"].to_numpy())
    lines = [
        f"## w = {w_minutes}m\n",
        "### Overall: baseline (hold-to-4h) vs. Action Class II\n",
        "| | n | Win rate | Mean | Median | P05 | Profit factor | Final equity | Max drawdown |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| Baseline (hold-to-4h) | {b['n']} | {b['win_rate']*100:.1f}% | {b['mean']*100:+.4f}% | "
        f"{b['median']*100:+.4f}% | {b['p05']*100:+.2f}% | {b['profit_factor']:.3f} | {b['final_equity']:.4f} | {b['max_dd']*100:.2f}% |",
        f"| Action Class II (w={w_minutes}m) | {iv['n']} | {iv['win_rate']*100:.1f}% | {iv['mean']*100:+.4f}% | "
        f"{iv['median']*100:+.4f}% | {iv['p05']*100:+.2f}% | {iv['profit_factor']:.3f} | {iv['final_equity']:.4f} | {iv['max_dd']*100:.2f}% |",
        "",
        "### By triggering episode (which episode timed out, if any)\n",
        "| Action | n | % of trades | Intervention: mean / median | Baseline (would-have-held): mean / median |",
        "|---|---|---|---|---|",
    ]
    n_total = len(df)
    for action in ["hold_4h", "timeout_exit_episode_1", "timeout_exit_episode_2", "timeout_exit_episode_3+"]:
        sub = df[df["action"] == action]
        if sub.empty:
            continue
        iv_mean, iv_med = sub["intervention_net_return"].mean(), sub["intervention_net_return"].median()
        bl_mean, bl_med = sub["baseline_net_return"].mean(), sub["baseline_net_return"].median()
        lines.append(
            f"| {action} | {len(sub)} | {len(sub)/n_total*100:.1f}% | "
            f"{iv_mean*100:+.4f}% / {iv_med*100:+.4f}% | {bl_mean*100:+.4f}% / {bl_med*100:+.4f}% |"
        )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_d_action_class_ii_v1.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()  # Discovery only

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    disc_lpl_q = apply_quintile(disc["local_price_location"], lpl_edges)
    disc_vol_q = apply_quintile(disc["volatility_atr_norm"], vol_edges)
    disc_decision = apply_decision_rule(disc_lpl_q, disc_vol_q)

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    signals = disc[disc_decision == "long_candidate"].sort_values("timestamp")
    trades, _ = simulate(signals, price_history, sorted_ts)
    print(f"decision_rule_v1 Discovery trades: {len(trades)}")

    body = ""
    for w in W_VARIANTS:
        print(f"Applying Action Class II with w={w}m...")
        result_df = apply_action_class_ii(trades, price_history, sorted_ts, w)
        body += section_for_w(result_df, w) + "\n---\n\n"

    header = (
        "# Phase D Action Class II v1 -- Recovery-Timeout intervention (Discovery only)\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Per the project discussion after SS22: rather than Action Class "
        "I's instant exit-on-detection (a net negative), this gives each "
        "deep episode up to `w` minutes to recover on its own before "
        "acting -- directly testing SS16's original landmark hypothesis "
        "as an action. Only w=60m and w=120m are tested (both "
        "pre-specified from SS16's finding, not a sweep). Same "
        "trades/fees/slippage as phase_d_action_class_i_v1.py. Each "
        "episode (including re-entries) gets its own independent "
        "timeout check, in order; the position closes at the first "
        "timeout, if any. **Discovery only (2020-2025), NOT an OOS "
        "validation** -- 2026 untouched.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
