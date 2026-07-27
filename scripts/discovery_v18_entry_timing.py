"""
Discovery v18 — entry timing: does delaying entry by N minutes improve
`decision_rule_v1`'s realized trades?

Motivation: discovery_v14's gap-decay curve showed micro_return_5m's
mean-reversion signal is alive for roughly 5-10 minutes and gone by
10-15. decision_rule_v1 enters at `state_ts` — the exact moment that
signal is strongest, i.e. the moment price has just moved sharply.
Entering a few minutes later might get a better fill for the same trade.

This is a different question from decision_rule_v3's entry FILTER, and
avoids that candidate's fatal problem (discovery_v16): delaying entry
keeps the SAME signal set and therefore the same trade sequence, so
trade-level and candidate-level views cannot diverge through Option A
retention effects. Only the entry price changes.

Method: for each delay N in {0, 1, 2, 3, 5, 10, 15, 30} minutes, re-run
the same Option A simulation with entry at `state_ts + N` and exit at
`state_ts + N + 4h` (holding period length held constant, so this
isolates entry timing rather than confounding it with a shorter hold).
Fees and the stated 5bps/side slippage assumption are unchanged.

N=0 reproduces `phase_c_baseline_v1.py` exactly and serves as the
control.

Purely descriptive; does not change decision_rule_v1 or propose a rule.
Discovery only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v18_entry_timing.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import discovery_report as dr
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile
from decision_rule_v1 import apply_decision_rule
from phase_c_baseline_v1 import (
    load_1m_price_series, lookup_price, ENTRY_EXIT_TOLERANCE_SEC,
    SLIPPAGE_BPS_PER_SIDE, HOLD_HOURS,
)
import mst_config as config

DELAYS = [0, 1, 2, 3, 5, 10, 15, 30]
TOL_MS = ENTRY_EXIT_TOLERANCE_SEC * 1000
NEW_DIMENSIONS = [("micro_return_5m", ("micro_1m", "return_5m"), False)]


def simulate_delayed(signals: pd.DataFrame, price_history: dict, sorted_ts: list,
                     delay_min: int) -> list:
    """Option A, but entry is delay_min minutes after the signal. The hold
    length is unchanged, so exit moves out by the same amount and the
    position stays open exactly HOLD_HOURS."""
    trades = []
    position_open_until = None
    hold_ms = HOLD_HOURS * 3600 * 1000
    delay_ms = delay_min * 60_000

    for _, row in signals.iterrows():
        state_ts = row["timestamp"]
        if position_open_until is not None and state_ts < position_open_until:
            continue  # Option A gate uses the SIGNAL time, identical across delays
        entry_ms = int(state_ts.timestamp() * 1000) + delay_ms
        exit_ms = entry_ms + hold_ms
        entry_price = lookup_price(price_history, sorted_ts, entry_ms, TOL_MS)
        exit_price = lookup_price(price_history, sorted_ts, exit_ms, TOL_MS)
        if entry_price is None or exit_price is None:
            continue
        gross = (exit_price - entry_price) / entry_price
        net = gross - 2 * config.TAKER_FEE - 2 * (SLIPPAGE_BPS_PER_SIDE / 10000)
        trades.append({"net_return": net})
        position_open_until = state_ts + pd.Timedelta(hours=HOLD_HOURS)
    return trades


def _stats(net: np.ndarray) -> dict:
    n = len(net)
    if n == 0:
        return {"n": 0}
    wins = net > 0
    gw, gl = net[wins].sum(), -net[~wins].sum()
    eq = np.cumprod(1 + net)
    peak = np.maximum.accumulate(eq)
    return {"n": n, "win_rate": wins.mean(), "mean": net.mean(), "median": np.median(net),
            "p05": np.quantile(net, 0.05), "profit_factor": gw / gl if gl > 0 else float("inf"),
            "final_equity": eq[-1], "max_dd": ((eq - peak) / peak).min()}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/discovery_v18_entry_timing.md")
    args = p.parse_args()

    print("Loading candidates...")
    dr.DIMENSIONS = dr.DIMENSIONS + NEW_DIMENSIONS
    df = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    ret_edges = fit_quintile_edges(disc["micro_return_5m"].dropna())
    lpl_q = apply_quintile(disc["local_price_location"], lpl_edges)
    vol_q = apply_quintile(disc["volatility_atr_norm"], vol_edges)
    disc["ret5m_q"] = apply_quintile(disc["micro_return_5m"], ret_edges)
    signals = disc[apply_decision_rule(lpl_q, vol_q) == "long_candidate"].sort_values("timestamp")

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    lines_all = ["## A. All decision_rule_v1 trades, entry delayed by N minutes\n",
                 "Hold length held constant at 4h, so this isolates entry "
                 "timing. N=0 reproduces `phase_c_baseline_v1.py`.\n",
                 "| Delay | n | Win rate | Median | Mean | P05 | Profit factor | Final equity | Max DD |",
                 "|---|---|---|---|---|---|---|---|---|"]
    for d in DELAYS:
        print(f"  simulating delay={d}m...")
        s = _stats(np.array([t["net_return"] for t in simulate_delayed(signals, price_history, sorted_ts, d)]))
        label = f"{d}m (baseline)" if d == 0 else f"{d}m"
        lines_all.append(
            f"| {label} | {s['n']:,} | {s['win_rate']*100:.1f}% | {s['median']*100:+.4f}% | "
            f"{s['mean']*100:+.4f}% | {s['p05']*100:+.2f}% | {s['profit_factor']:.3f} | "
            f"{s['final_equity']:.4f} | {s['max_dd']*100:.2f}% |")

    # the subgroup where the entry-timing idea should matter most: signals
    # that fired right after a sharp drop (micro_return_5m == Q1)
    sig_q1 = signals[signals["ret5m_q"] == "Q1"]
    lines_q1 = ["## B. Subgroup: signals following a sharp 5m drop (micro_return_5m == Q1)\n",
                "If delaying entry helps because price is still moving when "
                "the signal fires, the effect should be strongest here.\n",
                "| Delay | n | Win rate | Median | Mean | Profit factor |",
                "|---|---|---|---|---|---|"]
    for d in DELAYS:
        s = _stats(np.array([t["net_return"] for t in simulate_delayed(sig_q1, price_history, sorted_ts, d)]))
        label = f"{d}m (baseline)" if d == 0 else f"{d}m"
        lines_q1.append(
            f"| {label} | {s['n']:,} | {s['win_rate']*100:.1f}% | {s['median']*100:+.4f}% | "
            f"{s['mean']*100:+.4f}% | {s['profit_factor']:.3f} |")

    header = (
        "# Discovery v18 — entry timing (delay entry by N minutes)\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Unlike decision_rule_v3's entry FILTER, delaying entry keeps the "
        "same signal set and the same trade sequence, so it cannot "
        "produce the Option-A retention artifact that sank that "
        "candidate (discovery_v16) -- only the entry price changes. Hold "
        "length is held constant at 4h. Fees and the stated 5bps/side "
        "slippage assumption unchanged. Purely descriptive; does not "
        "change decision_rule_v1. Discovery only (2020-2025); 2026 "
        "untouched.\n\n"
        "---\n\n"
    )
    full = header + "\n".join(lines_all) + "\n\n---\n\n" + "\n".join(lines_q1) + "\n"

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
