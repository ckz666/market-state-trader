"""
decision_rule_v4 (24h hold) OOS v1 -- the single, unmodified 2026
validation run, per
data/reports/decision_rule_v4_hold_length_hypothesis.md (pre-registered
and committed BEFORE this script was written).

Frozen: decision_rule_v1's entry unchanged, hold = 1440 minutes instead
of 240. Option A logic, fees, and the stated 5bps/side slippage
assumption unchanged. All quintile edges fit ONLY on 2020-2025. No
tuning, and no testing of other hold lengths, in this run.

Usage:
    .venv/bin/python scripts/decision_rule_v4_hold_length_oos_v1.py
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
from phase_c_baseline_v1 import load_1m_price_series
from discovery_v19_shorter_horizon import simulate_hold, _stats

BASELINE_HOLD = 240
CANDIDATE_HOLD = 1440
MIN_N = 15  # pre-registered: below this, directional only

# Discovery figures quoted from discovery_v19 / the pre-registration, for
# the required Discovery-vs-OOS direction comparison. Not recomputed here.
DISC = {
    BASELINE_HOLD: {"n": 1064, "win_rate": 0.514, "median": 0.000473, "profit_factor": 0.853},
    CANDIDATE_HOLD: {"n": 365, "win_rate": 0.564, "median": 0.005179, "profit_factor": 1.255},
}


def _fmt(s: dict) -> str:
    if s["n"] == 0:
        return "n=0"
    flag = f" **(n<{MIN_N}, directional only)**" if s["n"] < MIN_N else ""
    return (f"n={s['n']}{flag}, win {s['win_rate']*100:.1f}%, median {s['median']*100:+.4f}%, "
            f"mean {s['mean']*100:+.4f}%, P05 {s['p05']*100:+.2f}%, PF {s['profit_factor']:.3f}, "
            f"maxDD {s['max_dd']*100:.2f}%")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/decision_rule_v4_hold_length_oos_v1.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()
    val = df[df["timestamp"] >= cutoff].copy()

    params = fit_params(disc)  # fit ONLY on Discovery
    for d in (disc, val):
        d["local_price_location"] = apply_lpl(d, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    val_lpl_q = apply_quintile(val["local_price_location"], lpl_edges)
    val_vol_q = apply_quintile(val["volatility_atr_norm"], vol_edges)
    signals = val[apply_decision_rule(val_lpl_q, val_vol_q) == "long_candidate"].sort_values("timestamp")
    print(f"2026 long_candidate signals: {len(signals):,}")

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    results = {}
    for hold in (BASELINE_HOLD, CANDIDATE_HOLD):
        results[hold] = _stats(simulate_hold(signals, price_history, sorted_ts, hold))
        print(f"  hold={hold}m -> {results[hold]['n']} trades")

    lines = [
        "## 1. 2026 OOS — baseline 4h vs. candidate 24h\n",
        "| Hold | Stats |", "|---|---|",
        f"| 240m (baseline) | {_fmt(results[BASELINE_HOLD])} |",
        f"| 1440m (candidate) | {_fmt(results[CANDIDATE_HOLD])} |",
        "",
        "---\n",
        "## 2. Pre-registered Discovery-vs-OOS direction check\n",
        "Per the pre-registration: because different hold lengths produce "
        "different trade sequences (not subsets), the decisive question is "
        "whether each primary metric moves the SAME direction in both "
        "periods — the failure mode that sank decision_rule_v3.\n",
        "| Metric | Discovery (4h -> 24h) | OOS (4h -> 24h) | Same direction? |",
        "|---|---|---|---|",
    ]
    for key, label, pct in [("win_rate", "Win rate", True), ("median", "Net median", True),
                            ("profit_factor", "Profit factor", False)]:
        d_delta = DISC[CANDIDATE_HOLD][key] - DISC[BASELINE_HOLD][key]
        o_delta = results[CANDIDATE_HOLD][key] - results[BASELINE_HOLD][key]
        agree = "yes" if (d_delta > 0) == (o_delta > 0) else "**NO**"
        f = (lambda v: f"{v*100:+.4f}pp") if pct else (lambda v: f"{v:+.3f}")
        lines.append(f"| {label} | {f(d_delta)} | {f(o_delta)} | {agree} |")

    header = (
        "# decision_rule_v4 (24h hold) — 2026 OOS validation\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Single, unmodified OOS run per "
        "decision_rule_v4_hold_length_hypothesis.md (pre-registered "
        "BEFORE this script was written). Entry unchanged; only hold "
        "length differs. All quintile edges fit ONLY on 2020-2025. No "
        "tuning, and no other hold lengths tested here.\n\n"
        "---\n\n"
    )
    full = header + "\n".join(lines) + "\n"

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
