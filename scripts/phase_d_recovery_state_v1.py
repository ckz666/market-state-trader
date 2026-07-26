"""
Phase D v1 — Recovery-state (Class D'), frozen definition applied to the
actual decision_rule_v1 trade set.

Still NOT a position-management rule -- confirmatory descriptive step only.
Applies the definition frozen in phase_d_path_state_hypothesis.md SS11
(not re-scanned, not re-fit here):

    - Recovery = Def 1 (DD_current(t) > deep_threshold)
    - Deep threshold = -0.75% (midpoint of the frozen -0.5%/-1.0% band --
      any value in that band is equally valid per SS11; the midpoint is
      used only as a concrete number to report with, not a fitted choice)
    - Checkpoints: 1h, 2h, 3h (15m/30m and the terminal 4h excluded, see
      SS11)
    - Volatility Q5 only -- decision_rule_v1's actual, real trade set
      (LPL==Q1 & Vol==Q5), not the widened diagnostic population used to
      derive the definition. Q1-Q4 are out of scope: decision_rule_v1
      never trades them, and Q1 was explicitly left unsupported in SS11.

Discovery period only (2020-2025). 2026 stays untouched until an actual
execution-mechanic hypothesis exists (SS12 point 2) -- this script does
not validate anything, it confirms the frozen state definition still
produces a sane 3-way split on the real trade set before that next step.

Usage:
    .venv/bin/python scripts/phase_d_recovery_state_v1.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from discovery_report import load_candidates
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile
from decision_rule_v1 import apply_decision_rule
from phase_c_baseline_v1 import load_1m_price_series, simulate
from phase_c_trade_path_analysis_v2 import build_trade_frame
from phase_c_trade_path_analysis_v4 import MIN_CELL_N

DEEP_THRESHOLD = -0.0075  # midpoint of the frozen -0.5%/-1.0% band, see module docstring
TIME_ROWS = ["1h", "2h", "3h"]


def classify(df: pd.DataFrame, t_label: str) -> pd.Series:
    mae_col, ret_col = f"mae_{t_label}", f"ret_{t_label}"
    deep = df[mae_col] <= DEEP_THRESHOLD
    state = pd.Series("1: never deep", index=df.index)
    state[deep & (df[ret_col] > DEEP_THRESHOLD)] = "2: deep, recovered"
    state[deep & (df[ret_col] <= DEEP_THRESHOLD)] = "3: deep, still impaired"
    return state


def section(trade_df: pd.DataFrame) -> str:
    lines = [
        "| Time | State | n | P(Winner) | Median net return | Mean net return | P05 |",
        "|---|---|---|---|---|---|---|",
    ]
    for t_label in TIME_ROWS:
        mae_col = f"mae_{t_label}"
        if trade_df.empty or mae_col not in trade_df.columns:
            continue
        state = classify(trade_df, t_label)
        for label in ["1: never deep", "2: deep, recovered", "3: deep, still impaired"]:
            mask = state == label
            n = int(mask.sum())
            if n < MIN_CELL_N:
                lines.append(f"| {t_label} | {label} | {n} | n too few | - | - | - |")
                continue
            sub = trade_df.loc[mask, "net_return"]
            wr = (sub > 0).mean()
            lines.append(
                f"| {t_label} | {label} | {n} | {wr*100:.1f}% | {sub.median()*100:+.4f}% | "
                f"{sub.mean()*100:+.4f}% | {sub.quantile(0.05)*100:+.2f}% |"
            )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_d_recovery_state_v1.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()  # Discovery only, per module docstring

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
    trade_df = build_trade_frame(trades, price_history, sorted_ts)

    body = section(trade_df)

    header = (
        "# Phase D v1 — Recovery-state (Class D'), frozen definition on the real trade set\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Confirmatory descriptive step, not a position-management rule. "
        "Applies the definition frozen in phase_d_path_state_hypothesis.md "
        "SS11 -- Def 1 recovery, deep threshold {:.2f}% (midpoint of the "
        "frozen -0.5%/-1.0% band, not re-fit here), checkpoints 1h/2h/3h -- "
        "to `decision_rule_v1`'s actual Discovery (2020-2025) trades "
        "(LPL==Q1 & Vol==Q5), not the widened diagnostic population used "
        "to derive the definition. 2026 untouched (SS12: an execution-"
        "mechanic hypothesis has to exist before validation is looked at "
        "again). Cells with n < {} are marked instead of reported.\n\n"
        "---\n\n".format(DEEP_THRESHOLD * 100, MIN_CELL_N)
    )
    full = header + "## Outcome distribution by recovery state\n\n" + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
