"""
decision_rule_v3 micro_return_5m filter OOS v1 -- the single, unmodified
2026 validation run, per
data/reports/decision_rule_v3_micro_return_filter_hypothesis.md
(pre-registered and committed BEFORE this script was written).

Frozen: decision_rule_v1's existing signals, restricted to
micro_return_5m quintile Q1. All quintile edges (LPL, volatility,
micro_return_5m) fit ONLY on 2020-2025 and applied unchanged to 2026.
No tuning of any kind here.

Reports both views the pre-registration requires:
  - trade level (Option-A-deduplicated, fees/slippage) -- the real
    tradeable result, but pre-declared directional-only if n < 15
  - candidate level (all long_candidate signals) -- higher n, but NOT a
    tradeable sequence (overlapping 4h windows), labeled as such

Usage:
    .venv/bin/python scripts/decision_rule_v3_micro_return_filter_oos_v1.py
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
from phase_c_baseline_v1 import load_1m_price_series, simulate

MIN_N = 15  # pre-registered threshold below which trade-level is directional only
NEW_DIMENSIONS = [("micro_return_5m", ("micro_1m", "return_5m"), False)]


def _stats(net: np.ndarray) -> dict:
    n = len(net)
    if n == 0:
        return {"n": 0}
    wins = net > 0
    gw, gl = net[wins].sum(), -net[~wins].sum()
    return {
        "n": n, "win_rate": wins.mean(), "mean": net.mean(), "median": np.median(net),
        "p05": np.quantile(net, 0.05) if n >= 20 else float("nan"),
        "profit_factor": gw / gl if gl > 0 else float("inf"),
    }


def _fmt(s: dict) -> str:
    if s["n"] == 0:
        return "n=0"
    flag = f" **(n<{MIN_N}, directional only)**" if s["n"] < MIN_N else ""
    p05 = "n/a" if np.isnan(s["p05"]) else f"{s['p05']*100:+.2f}%"
    return (f"n={s['n']}{flag}, win {s['win_rate']*100:.1f}%, mean {s['mean']*100:+.4f}%, "
            f"median {s['median']*100:+.4f}%, P05 {p05}, PF {s['profit_factor']:.3f}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/decision_rule_v3_micro_return_filter_oos_v1.md")
    args = p.parse_args()

    print("Loading candidates...")
    dr.DIMENSIONS = dr.DIMENSIONS + NEW_DIMENSIONS
    df = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()
    val = df[df["timestamp"] >= cutoff].copy()

    params = fit_params(disc)  # fit ONLY on Discovery
    for d in (disc, val):
        d["local_price_location"] = apply_lpl(d, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    ret_edges = fit_quintile_edges(disc["micro_return_5m"].dropna())

    val_lpl_q = apply_quintile(val["local_price_location"], lpl_edges)
    val_vol_q = apply_quintile(val["volatility_atr_norm"], vol_edges)
    val["ret5m_q"] = apply_quintile(val["micro_return_5m"], ret_edges)
    val_decision = apply_decision_rule(val_lpl_q, val_vol_q)

    # ── candidate level (higher n, NOT a tradeable sequence) ──
    sig_mask = val_decision == "long_candidate"
    cand_all = val.loc[sig_mask, "fwd_4h"].dropna()
    cand_filt = val.loc[sig_mask & (val["ret5m_q"] == "Q1"), "fwd_4h"].dropna()

    # ── trade level (Option A, fees/slippage) ──
    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    signals_all = val[sig_mask].sort_values("timestamp")
    trades_all, _ = simulate(signals_all, price_history, sorted_ts)
    signals_filt = val[sig_mask & (val["ret5m_q"] == "Q1")].sort_values("timestamp")
    trades_filt, _ = simulate(signals_filt, price_history, sorted_ts)
    print(f"2026 trades: baseline {len(trades_all)}, filtered {len(trades_filt)}")

    net_all = np.array([t["net_return"] for t in trades_all])
    net_filt = np.array([t["net_return"] for t in trades_filt])

    body = (
        "## 1. Trade level (Option A de-duplicated, fees/slippage) — the real result\n\n"
        "| Population | Stats |\n|---|---|\n"
        f"| Baseline: all decision_rule_v1 trades | {_fmt(_stats(net_all))} |\n"
        f"| Filtered: + micro_return_5m == Q1 | {_fmt(_stats(net_filt))} |\n\n"
        "---\n\n"
        "## 2. Candidate level (all long_candidate signals, NOT a tradeable sequence)\n\n"
        "Higher n, but overlapping 4h windows — reported per the "
        "pre-registration as the higher-sample view only, never as a "
        "tradeable result.\n\n"
        "| Population | Stats |\n|---|---|\n"
        f"| Baseline: all long_candidate signals | {_fmt(_stats(cand_all.to_numpy()))} |\n"
        f"| Filtered: + micro_return_5m == Q1 | {_fmt(_stats(cand_filt.to_numpy()))} |\n"
    )

    header = (
        "# decision_rule_v3 micro_return_5m filter — 2026 OOS validation\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Single, unmodified OOS run per "
        "decision_rule_v3_micro_return_filter_hypothesis.md "
        "(pre-registered BEFORE this script was written). All quintile "
        "edges fit ONLY on 2020-2025, applied unchanged to 2026. No "
        "tuning performed.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
