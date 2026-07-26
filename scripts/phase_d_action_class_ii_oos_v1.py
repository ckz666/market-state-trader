"""
Phase D Action Class II OOS v1 -- the single, unmodified 2026 validation
run for the frozen Recovery-Timeout rule (w=120m), per
phase_d_path_state_hypothesis.md SS24's pre-registration (written and
committed BEFORE this script was run).

Frozen, not re-decided here: Action Class II exactly as in
phase_d_action_class_ii_v1.py, w=120m only (w=60m is not carried
forward), decision_rule_v1's existing hold-to-4h as the baseline, same
fee/slippage assumptions, LPL/volatility quintile edges fit on
2020-2025 only and applied unchanged to 2026 (same discipline as
hypothesis_validation.py throughout this project). No tuning: no new w,
no new states, no new filters.

Reports exactly the metrics SS24 pre-registered: primary (paired
delta-return distribution, profit factor, max drawdown), secondary
(median, win rate, final equity), and the by-triggering-episode
breakdown for transparency (with explicit small-n caution, since 2026
has far fewer trades than Discovery).

Usage:
    .venv/bin/python scripts/phase_d_action_class_ii_oos_v1.py
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
from phase_c_baseline_v1 import load_1m_price_series, simulate
from phase_c_trade_path_analysis_v4 import MIN_CELL_N
from phase_d_action_class_ii_v1 import apply_action_class_ii

W_FROZEN = 120  # SS24: frozen, not re-chosen


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
        "p05": np.quantile(net, 0.05) if len(net) >= 20 else float("nan"),
        "profit_factor": pf, "final_equity": equity[-1], "max_dd": max_dd,
    }


def section_overall(df: pd.DataFrame) -> str:
    b = _stats(df["baseline_net_return"].to_numpy())
    iv = _stats(df["intervention_net_return"].to_numpy())
    lines = [
        "## Overall: baseline (hold-to-4h) vs. frozen Action Class II (w=120m) -- 2026 OOS\n",
        "| | n | Win rate | Mean | Median | P05 | Profit factor | Final equity | Max drawdown |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| Baseline (hold-to-4h) | {b['n']} | {b['win_rate']*100:.1f}% | {b['mean']*100:+.4f}% | "
        f"{b['median']*100:+.4f}% | {b['p05']*100:+.2f}% | {b['profit_factor']:.3f} | {b['final_equity']:.4f} | {b['max_dd']*100:.2f}% |",
        f"| Action Class II (w=120m) | {iv['n']} | {iv['win_rate']*100:.1f}% | {iv['mean']*100:+.4f}% | "
        f"{iv['median']*100:+.4f}% | {iv['p05']*100:+.2f}% | {iv['profit_factor']:.3f} | {iv['final_equity']:.4f} | {iv['max_dd']*100:.2f}% |",
    ]
    return "\n".join(lines) + "\n"


def section_delta(df: pd.DataFrame) -> str:
    delta = df["intervention_net_return"] - df["baseline_net_return"]
    n = len(delta)
    pct_positive = (delta > 0).mean() * 100
    pct_zero = (delta == 0).mean() * 100
    lines = [
        "## Primary: paired delta-return distribution (SS24)\n",
        "`delta = return(Action II) - return(Baseline)`, per trade. This "
        "is the primary metric SS24 pre-registered -- not just "
        "aggregate PnL, to check whether any edge is broad or driven by "
        "a few trades.\n",
        "| n | Mean delta | Median delta | % trades with delta > 0 | % trades unchanged (delta = 0) |",
        "|---|---|---|---|---|",
        f"| {n} | {delta.mean()*100:+.4f}% | {delta.median()*100:+.4f}% | {pct_positive:.1f}% | {pct_zero:.1f}% |",
    ]
    return "\n".join(lines) + "\n"


def section_by_action(df: pd.DataFrame) -> str:
    lines = [
        "## By triggering episode (transparency only -- see SS24's small-n caution)\n",
        "| Action | n | Intervention: mean / median | Baseline (would-have-held): mean / median |",
        "|---|---|---|---|",
    ]
    n_total = len(df)
    for action in ["hold_4h", "timeout_exit_episode_1", "timeout_exit_episode_2", "timeout_exit_episode_3+"]:
        sub = df[df["action"] == action]
        if sub.empty:
            continue
        flag = " (n too small to interpret as a validated effect)" if len(sub) < MIN_CELL_N else ""
        iv_mean, iv_med = sub["intervention_net_return"].mean(), sub["intervention_net_return"].median()
        bl_mean, bl_med = sub["baseline_net_return"].mean(), sub["baseline_net_return"].median()
        lines.append(
            f"| {action}{flag} | {len(sub)} | {iv_mean*100:+.4f}% / {iv_med*100:+.4f}% | "
            f"{bl_mean*100:+.4f}% / {bl_med*100:+.4f}% |"
        )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_d_action_class_ii_oos_v1.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()
    val = df[df["timestamp"] >= cutoff].copy()  # 2026 -- untouched until now

    params = fit_params(disc)  # fit ONLY on Discovery
    disc["local_price_location"] = apply_lpl(disc, params)
    val["local_price_location"] = apply_lpl(val, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    val_lpl_q = apply_quintile(val["local_price_location"], lpl_edges)
    val_vol_q = apply_quintile(val["volatility_atr_norm"], vol_edges)
    val_decision = apply_decision_rule(val_lpl_q, val_vol_q)

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    signals = val[val_decision == "long_candidate"].sort_values("timestamp")
    trades, _ = simulate(signals, price_history, sorted_ts)
    print(f"decision_rule_v1 2026 (OOS) trades: {len(trades)}")
    result_df = apply_action_class_ii(trades, price_history, sorted_ts, W_FROZEN)

    body = (
        section_overall(result_df) + "\n---\n\n" +
        section_delta(result_df) + "\n---\n\n" +
        section_by_action(result_df)
    )

    header = (
        "# Phase D Action Class II OOS v1 -- 2026 validation of the frozen w=120m Recovery-Timeout\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Single, unmodified OOS run per phase_d_path_state_hypothesis.md "
        "SS24 (pre-registered BEFORE this script was run). w=120m frozen "
        "from Discovery (SS23); no tuning of any kind performed here. "
        "LPL/volatility quintile edges fit on 2020-2025 only, applied "
        "unchanged to 2026.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
