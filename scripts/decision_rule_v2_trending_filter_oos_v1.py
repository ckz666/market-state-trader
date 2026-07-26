"""
decision_rule_v2 trending-filter OOS v1 -- the single, unmodified 2026
validation run for the frozen trending-regime filter, per
data/reports/decision_rule_v2_trending_filter_hypothesis.md (pre-
registered and committed BEFORE this script was run).

Frozen, not re-decided here: decision_rule_v1's existing signals,
restricted to regime_4h=='trending' at entry. No new fitted parameter.
LPL/volatility quintile edges fit on 2020-2025 only, applied unchanged
to 2026 (same discipline as hypothesis_validation.py throughout this
project). No tuning permitted in this run.

Usage:
    .venv/bin/python scripts/decision_rule_v2_trending_filter_oos_v1.py
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

MIN_CELL_N = 15


def _stats(net: np.ndarray) -> dict:
    n = len(net)
    if n == 0:
        return {"n": 0}
    wins = net > 0
    gross_wins = net[wins].sum()
    gross_losses = -net[~wins].sum()
    pf = gross_wins / gross_losses if gross_losses > 0 else float("inf")
    return {
        "n": n, "win_rate": wins.mean(), "mean": net.mean(), "median": np.median(net),
        "p05": np.quantile(net, 0.05) if n >= 20 else float("nan"), "profit_factor": pf,
    }


def _fmt(s: dict) -> str:
    if s["n"] == 0:
        return "n=0"
    flag = " (n < 15, directional only)" if s["n"] < MIN_CELL_N else ""
    return (f"n={s['n']}{flag}, win {s['win_rate']*100:.1f}%, mean {s['mean']*100:+.4f}%, "
            f"median {s['median']*100:+.4f}%, P05 {s['p05']*100:+.2f}%, PF {s['profit_factor']:.3f}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/decision_rule_v2_trending_filter_oos_v1.md")
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

    regime_by_ts = val.set_index("timestamp")["regime_4h"]
    trade_df = pd.DataFrame([{
        "net_return": t["net_return"],
        "regime_4h": regime_by_ts.get(t["entry_ts"]),
    } for t in trades])

    baseline = _stats(trade_df["net_return"].to_numpy())
    trending = _stats(trade_df.loc[trade_df["regime_4h"] == "trending", "net_return"].to_numpy())
    non_trending = _stats(trade_df.loc[trade_df["regime_4h"] != "trending", "net_return"].to_numpy())

    body = (
        "## Baseline (unfiltered decision_rule_v1) vs. trending-filtered, 2026 OOS\n\n"
        "| Population | Stats |\n|---|---|\n"
        f"| All decision_rule_v1 trades (baseline) | {_fmt(baseline)} |\n"
        f"| ...restricted to regime_4h == trending | {_fmt(trending)} |\n"
        f"| ...restricted to regime_4h != trending | {_fmt(non_trending)} |\n"
    )

    header = (
        "# decision_rule_v2 trending-filter OOS v1 -- 2026 validation\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Single, unmodified OOS run per "
        "decision_rule_v2_trending_filter_hypothesis.md (pre-registered "
        "BEFORE this script was run). No tuning of any kind performed "
        "here. LPL/volatility quintile edges fit on 2020-2025 only, "
        "applied unchanged to 2026.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
