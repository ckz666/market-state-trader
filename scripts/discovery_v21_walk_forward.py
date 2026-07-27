"""
Discovery v21 — walk-forward validation of the 24h-hold candidate
(decision_rule_v4), instead of the project's single train/test split.

WHAT THIS IS: expanding-origin walk-forward. For each test year Y from
2021 to 2025, every transform parameter (LPL z-score mean/std, LPL and
volatility quintile edges) is fit on 2020..Y-1 ONLY and applied frozen
to year Y. Both the 4h baseline and the 24h candidate are simulated on
year Y. This yields 5 quasi-independent tests instead of one.

WHAT THIS IS NOT, stated plainly because it matters:

  1. **Not out-of-sample.** Every year 2020-2025 has been examined many
     times over discovery_v1-v20. Parameters are re-fit honestly per
     fold, but the *decision to test a 24h hold at all* came from having
     already looked at this data (discovery_v19). Walk-forward cannot
     undo that.
  2. **It does not replace the 2026 validation.** 2026 remains the only
     genuinely unseen period, and decision_rule_v4's n=16 result there
     stands as the real OOS evidence.
  3. **It raises multiple-testing exposure**, not lowers it: this is an
     additional test of a hypothesis that has already been tested.

What it CAN do: show whether the 24h-over-4h advantage is consistent
across market regimes (2021 bull, 2022 bear, 2023 quiet, 2024-25 mixed)
or whether it is carried by one or two periods. That is a real question
the single 2020-2025/2026 split cannot answer.

Purely descriptive; does not change decision_rule_v1.

Usage:
    .venv/bin/python scripts/discovery_v21_walk_forward.py
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

TEST_YEARS = [2021, 2022, 2023, 2024, 2025]
BASELINE_HOLD = 240
CANDIDATE_HOLD = 1440
MIN_N = 15


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/discovery_v21_walk_forward.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = dr.load_candidates([args.historical])
    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    rows = []
    for test_year in TEST_YEARS:
        train = df[df["year"] < test_year].copy()
        test = df[df["year"] == test_year].copy()
        if train.empty or test.empty:
            continue

        # every parameter fit on the TRAINING slice only
        params = fit_params(train)
        train["local_price_location"] = apply_lpl(train, params)
        test["local_price_location"] = apply_lpl(test, params)
        lpl_edges = fit_quintile_edges(train["local_price_location"])
        vol_edges = fit_quintile_edges(train["volatility_atr_norm"])
        test_lpl_q = apply_quintile(test["local_price_location"], lpl_edges)
        test_vol_q = apply_quintile(test["volatility_atr_norm"], vol_edges)
        signals = test[apply_decision_rule(test_lpl_q, test_vol_q) == "long_candidate"].sort_values("timestamp")

        s_base = _stats(simulate_hold(signals, price_history, sorted_ts, BASELINE_HOLD))
        s_cand = _stats(simulate_hold(signals, price_history, sorted_ts, CANDIDATE_HOLD))
        rows.append({"year": test_year, "train_n": len(train), "base": s_base, "cand": s_cand})
        print(f"  {test_year}: train={len(train):,} rows, "
              f"4h n={s_base.get('n',0)}, 24h n={s_cand.get('n',0)}")

    lines = [
        "## A. Per-fold results (parameters fit on prior years only)\n",
        "| Test year | Train rows | Hold | n | Win rate | Net median | Mean | Profit factor |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        for label, s in [("4h", r["base"]), ("24h", r["cand"])]:
            if s["n"] == 0:
                lines.append(f"| {r['year']} | {r['train_n']:,} | {label} | 0 | - | - | - | - |")
                continue
            flag = " ⚠" if s["n"] < MIN_N else ""
            lines.append(
                f"| {r['year']} | {r['train_n']:,} | {label} | {s['n']}{flag} | "
                f"{s['win_rate']*100:.1f}% | {s['median']*100:+.4f}% | "
                f"{s['mean']*100:+.4f}% | {s['profit_factor']:.3f} |")
    lines.append("\n⚠ = fewer than 15 trades in that fold; treat as directional only.\n")

    lines.append("\n## B. Does 24h beat 4h, fold by fold?\n")
    lines.append("| Test year | Win rate | Net median | Profit factor | All three? |")
    lines.append("|---|---|---|---|---|")
    counts = {"win_rate": 0, "median": 0, "profit_factor": 0}
    evaluable = 0
    all_three = 0
    for r in rows:
        b, c = r["base"], r["cand"]
        if b["n"] == 0 or c["n"] == 0:
            continue
        evaluable += 1
        marks = {}
        for k in counts:
            better = c[k] > b[k]
            counts[k] += better
            marks[k] = "yes" if better else "no"
        three = all(m == "yes" for m in marks.values())
        all_three += three
        note = " (n<15)" if c["n"] < MIN_N else ""
        lines.append(f"| {r['year']}{note} | {marks['win_rate']} | {marks['median']} | "
                     f"{marks['profit_factor']} | {'**yes**' if three else 'no'} |")
    lines.append(
        f"\n**Folds where 24h beat 4h:** win rate {counts['win_rate']}/{evaluable}, "
        f"net median {counts['median']}/{evaluable}, profit factor "
        f"{counts['profit_factor']}/{evaluable}. All three simultaneously: "
        f"{all_three}/{evaluable}.\n")

    header = (
        "# Discovery v21 — walk-forward validation of the 24h hold\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "**Read the caveats before the numbers.** This is expanding-origin "
        "walk-forward: for each test year, all transform parameters are "
        "fit on prior years only and applied frozen. But this is NOT "
        "out-of-sample — every year 2020-2025 has been examined repeatedly "
        "across discovery_v1-v20, and the idea of testing a 24h hold came "
        "from having already looked at this data (discovery_v19). It does "
        "not replace the 2026 validation (decision_rule_v4's n=16 result "
        "remains the only genuine OOS evidence), and it *increases* "
        "multiple-testing exposure rather than reducing it. What it can "
        "legitimately show is whether the 24h advantage is consistent "
        "across regimes or carried by one or two periods.\n\n"
        "---\n\n"
    )
    full = header + "\n".join(lines) + "\n"

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
