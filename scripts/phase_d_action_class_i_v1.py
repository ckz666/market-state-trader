"""
Phase D Action Class I v1 -- the first real position-management
intervention test. Per phase_d_path_state_hypothesis.md SS21 (frozen
2026-07-26): binary HOLD/EXIT, triggered by CURRENT status (not episode
count) at the existing checkpoint grid (1h/2h/3h) -- no new parameter is
introduced beyond what was already frozen for other reasons earlier in
Phase D (deep threshold -0.75%, Def 1 recovery, the 1h/2h/3h grid).

Rule: at each checkpoint in order, if the trade is CURRENTLY in a deep
episode (state S1/S3/S5 from SS20 -- currently_deep(t) True, regardless
of episode count), EXIT immediately at that checkpoint's price. If
currently recovered or never deep (S0/S2/S4), HOLD and check the next
checkpoint, or the normal 4h close if none remain.

This is a Discovery-only backtest (2020-2025) against decision_rule_v1's
existing baseline (hold-to-4h, no intervention) -- NOT an OOS validation.
Per SS18/SS21's roadmap, 2026 stays untouched until this is reviewed and,
if it holds up, formally frozen.

Usage:
    .venv/bin/python scripts/phase_d_action_class_i_v1.py
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
from phase_d_episode_history_landmark_v1 import episode_state_at, CHECKPOINT_MINUTES
import mst_config as config

TOL_MS = ENTRY_EXIT_TOLERANCE_SEC * 1000


def apply_action_class_i(trades: list, price_history: dict, sorted_ts: list) -> pd.DataFrame:
    rows = []
    for t in trades:
        entry_ts, entry_price = t["entry_ts"], t["entry_price"]
        entry_ms = int(entry_ts.timestamp() * 1000)
        action = "hold_4h"
        net_return = t["net_return"]  # baseline hold-to-4h, used unless an earlier exit triggers

        for label, minutes in CHECKPOINT_MINUTES:
            st = episode_state_at(entry_ts, entry_price, price_history, sorted_ts, minutes)
            if st is None:
                continue
            if st["currently_deep"]:
                exit_ms = entry_ms + minutes * 60_000
                exit_price = lookup_price(price_history, sorted_ts, exit_ms, TOL_MS)
                if exit_price is None:
                    break  # data gap at this checkpoint -- fall back to baseline hold_4h
                gross_return = (exit_price - entry_price) / entry_price
                fee_cost = 2 * config.TAKER_FEE
                slippage_cost = 2 * (SLIPPAGE_BPS_PER_SIDE / 10000)
                net_return = gross_return - fee_cost - slippage_cost
                action = f"exit_{label}"
                break

        rows.append({
            "action": action,
            "intervention_net_return": net_return,
            "baseline_net_return": t["net_return"],
        })
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


def section_overall(df: pd.DataFrame) -> str:
    b = _stats(df["baseline_net_return"].to_numpy())
    iv = _stats(df["intervention_net_return"].to_numpy())
    lines = [
        "## Overall: baseline (hold-to-4h) vs. Action Class I intervention\n",
        "Same n, same underlying trades (paired) -- only the exit rule differs.\n",
        "| | n | Win rate | Mean | Median | P05 | Profit factor | Final equity (unit-sized, compounding) | Max drawdown |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| Baseline (hold-to-4h) | {b['n']} | {b['win_rate']*100:.1f}% | {b['mean']*100:+.4f}% | "
        f"{b['median']*100:+.4f}% | {b['p05']*100:+.2f}% | {b['profit_factor']:.3f} | {b['final_equity']:.4f} | {b['max_dd']*100:.2f}% |",
        f"| Action Class I | {iv['n']} | {iv['win_rate']*100:.1f}% | {iv['mean']*100:+.4f}% | "
        f"{iv['median']*100:+.4f}% | {iv['p05']*100:+.2f}% | {iv['profit_factor']:.3f} | {iv['final_equity']:.4f} | {iv['max_dd']*100:.2f}% |",
    ]
    return "\n".join(lines) + "\n"


def section_by_action(df: pd.DataFrame) -> str:
    lines = [
        "## By action taken: intervention outcome vs. what holding to 4h would have done\n",
        "For trades that got exited early, this is the direct trade-off: "
        "what did the early exit actually realize, vs. what would have "
        "happened had the rule not intervened (paired, same trades).\n",
        "| Action | n | % of trades | Intervention: mean / median | Baseline (would-have-held): mean / median |",
        "|---|---|---|---|---|",
    ]
    n_total = len(df)
    for action in ["hold_4h", "exit_1h", "exit_2h", "exit_3h"]:
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
    p.add_argument("--out", default="data/reports/phase_d_action_class_i_v1.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()  # Discovery only -- SS21: 2026 untouched

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
    result_df = apply_action_class_i(trades, price_history, sorted_ts)

    body = section_overall(result_df) + "\n---\n\n" + section_by_action(result_df)

    header = (
        "# Phase D Action Class I v1 -- first intervention backtest (Discovery only)\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Frozen rule per phase_d_path_state_hypothesis.md SS21: at each "
        "of 1h/2h/3h in order, EXIT immediately if currently in a deep "
        "episode (any episode count); otherwise HOLD to the next "
        "checkpoint or the normal 4h close. No new parameter introduced "
        "-- deep threshold, recovery definition, and checkpoint grid were "
        "all frozen earlier for other reasons. Same fee/slippage "
        "assumptions as phase_c_baseline_v1.py. **Discovery only "
        "(2020-2025), NOT an OOS validation** -- 2026 stays untouched "
        "until this is reviewed and, if it holds up, formally frozen.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
