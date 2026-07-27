"""
Discovery v19 — shorter target horizon: is 4h the right hold length?

`decision_rule_v1` targets 4h, frozen back in Phase B because that was
the horizon the LPL hypothesis was validated on. It has never been
revisited. Two reasons to check it now:

  1. discovery_v12/v14 found micro_return_5m's edge is strongest at 15m
     and largely decayed by 4h -- but that factor isn't what the rule
     trades on.
  2. More directly: phase_c_baseline_v1 showed the 4h rule's realized
     median is barely positive (+0.047%) with profit factor 0.853, i.e.
     fees and tail risk eat most of the edge over a 4h hold. A shorter
     hold pays the same round-trip cost over less price movement, so
     this is NOT automatically better -- shorter holds mean the fixed
     fee/slippage cost is amortized over a smaller move, which usually
     hurts. Worth measuring rather than assuming either way.

Method: same Option A logic, same signals, same fees/slippage; only the
hold length varies. Note that a shorter hold also frees the position
sooner, so MORE signals become trades -- unlike discovery_v18's entry
delay, the trade count legitimately changes here, and the comparison is
therefore between different trade sequences (the same caveat
discovery_v16 raised for decision_rule_v3). Trade counts are reported
per horizon so this is visible.

Purely descriptive; does not change decision_rule_v1 or propose a rule.
Discovery only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v19_shorter_horizon.py
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
    load_1m_price_series, lookup_price, ENTRY_EXIT_TOLERANCE_SEC, SLIPPAGE_BPS_PER_SIDE,
)
import mst_config as config

# 240 = the frozen 4h baseline. Longer holds are included because the
# shorter ones came out monotonically worse -- the fixed round-trip cost
# is amortized over a larger gross move as the hold grows, so the obvious
# follow-up question is whether the trend continues past 4h. Note these
# go beyond the 4h horizon the LPL hypothesis was validated on, so they
# are exploratory, not a validated extension.
HOLD_MINUTES = [15, 30, 60, 120, 240, 480, 720, 1440]
TOL_MS = ENTRY_EXIT_TOLERANCE_SEC * 1000


def simulate_hold(signals: pd.DataFrame, price_history: dict, sorted_ts: list,
                  hold_min: int) -> list:
    trades = []
    position_open_until = None
    hold_ms = hold_min * 60_000
    for _, row in signals.iterrows():
        state_ts = row["timestamp"]
        if position_open_until is not None and state_ts < position_open_until:
            continue
        entry_ms = int(state_ts.timestamp() * 1000)
        entry_price = lookup_price(price_history, sorted_ts, entry_ms, TOL_MS)
        exit_price = lookup_price(price_history, sorted_ts, entry_ms + hold_ms, TOL_MS)
        if entry_price is None or exit_price is None:
            continue
        gross = (exit_price - entry_price) / entry_price
        net = gross - 2 * config.TAKER_FEE - 2 * (SLIPPAGE_BPS_PER_SIDE / 10000)
        trades.append({"net_return": net, "gross_return": gross})
        position_open_until = state_ts + pd.Timedelta(minutes=hold_min)
    return trades


def _stats(trades: list) -> dict:
    if not trades:
        return {"n": 0}
    net = np.array([t["net_return"] for t in trades])
    gross = np.array([t["gross_return"] for t in trades])
    wins = net > 0
    gw, gl = net[wins].sum(), -net[~wins].sum()
    eq = np.cumprod(1 + net)
    peak = np.maximum.accumulate(eq)
    return {"n": len(net), "win_rate": wins.mean(), "gross_median": np.median(gross),
            "median": np.median(net), "mean": net.mean(), "p05": np.quantile(net, 0.05),
            "profit_factor": gw / gl if gl > 0 else float("inf"),
            "final_equity": eq[-1], "max_dd": ((eq - peak) / peak).min()}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/discovery_v19_shorter_horizon.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    lpl_q = apply_quintile(disc["local_price_location"], lpl_edges)
    vol_q = apply_quintile(disc["volatility_atr_norm"], vol_edges)
    signals = disc[apply_decision_rule(lpl_q, vol_q) == "long_candidate"].sort_values("timestamp")
    print(f"long_candidate signals: {len(signals):,}")

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    round_trip_cost = 2 * config.TAKER_FEE + 2 * (SLIPPAGE_BPS_PER_SIDE / 10000)
    lines = [
        "## Hold length vs. realized outcome (Option A, same signals)\n",
        f"Round-trip cost is fixed at **{round_trip_cost*100:.4f}%** "
        "(fees + the stated 5bps/side slippage assumption) regardless of "
        "hold length, so a shorter hold must produce proportionally more "
        "gross move to break even. `Gross median` is shown alongside the "
        "net figures to make that trade-off visible.\n",
        "Trade count changes by design: a shorter hold frees the position "
        "sooner, so more signals become trades (Option A). These are "
        "therefore different trade sequences, not subsets — the same "
        "caveat discovery_v16 raised.\n",
        "| Hold | n trades | Win rate | Gross median | Net median | Mean | P05 | Profit factor | Final equity | Max DD |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for hold in HOLD_MINUTES:
        print(f"  simulating hold={hold}m...")
        s = _stats(simulate_hold(signals, price_history, sorted_ts, hold))
        label = f"{hold}m" + (" (frozen baseline)" if hold == 240 else "")
        lines.append(
            f"| {label} | {s['n']:,} | {s['win_rate']*100:.1f}% | {s['gross_median']*100:+.4f}% | "
            f"{s['median']*100:+.4f}% | {s['mean']*100:+.4f}% | {s['p05']*100:+.2f}% | "
            f"{s['profit_factor']:.3f} | {s['final_equity']:.4f} | {s['max_dd']*100:.2f}% |")

    header = (
        "# Discovery v19 — is 4h the right hold length?\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "`decision_rule_v1`'s 4h target was frozen in Phase B because "
        "that was the horizon the LPL hypothesis was validated on, and "
        "has never been revisited. Same Option A logic, same signals, "
        "same fee/slippage assumptions; only hold length varies. Purely "
        "descriptive; does not change decision_rule_v1. Discovery only "
        "(2020-2025); 2026 untouched.\n\n"
        "---\n\n"
    )
    full = header + "\n".join(lines) + "\n"

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
