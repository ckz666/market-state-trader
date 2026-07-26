"""
Phase D discovery v1 — Recovery-State (Class D') definition exploration.

Still NOT a position-management rule. Per phase_d_path_state_hypothesis.md
SS10/11: Class D' was chosen on structural grounds (DD_current != MAE_so_far,
established in phase_c_trade_path_analysis_v4.py). This script's only job is
to look at the empirical stability of the resulting 3-state split across a
range of "deep drawdown" thresholds and a few candidate "recovered"
definitions -- not to pick a single best threshold. Discovery period only
(2020-2025); 2026 is untouched here, exactly as in every prior phase.

Section A: for a range of deep-drawdown thresholds and pre-terminal time
checkpoints, split trades into three states and report whether
P(winner | State 1) > P(winner | State 2) > P(winner | State 3) holds --
across the range, not just at one threshold. The 4h (terminal) checkpoint
is deliberately excluded: DD_current at t=4h is ~= the final return, so a
"recovered by 4h" state there is close to a restatement of "closed a
winner" (the same degeneracy flagged in v4's table A, SS on the 4h row).

Section B: at one representative threshold/time, compares three concrete
"recovered" definitions against each other (back above the threshold /
recovered by a fixed margin from its own low / recovered to a small
absolute residual), to see whether the recovered-vs-impaired split is
sensitive to which definition is used.

Usage:
    .venv/bin/python scripts/phase_d_recovery_state_discovery_v1.py
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
from phase_c_baseline_v1 import load_1m_price_series
from phase_c_trade_path_analysis_v4 import build_vol_trade_dfs, Q_LABELS, MIN_CELL_N

DEEP_THRESHOLDS = [-0.0025, -0.005, -0.0075, -0.01, -0.0125, -0.015, -0.02, -0.025, -0.03]
TIME_ROWS = ["15m", "30m", "1h", "2h", "3h"]  # pre-terminal only -- see module docstring

# Section B: recovery-definition variants, tested at one representative
# (threshold, time) pair per volatility quintile.
SECTION_B_THRESHOLD = -0.01
SECTION_B_TIMES = ["1h", "2h"]
RECOVERY_MARGIN_X = [0.0025, 0.005]  # for Definition 2
RESIDUAL_ABS = [-0.0025, -0.005]  # for Definition 3


def _cell(mask, df):
    n = int(mask.sum())
    if n < MIN_CELL_N:
        return n, None, None
    wr = (df.loc[mask, "net_return"] > 0).mean()
    med = df.loc[mask, "net_return"].median()
    return n, wr, med


def _fmt(n, wr):
    return f"n={n}" if wr is None else f"{wr*100:.0f}% (n={n})"


def classify_states(df: pd.DataFrame, t_label: str, threshold: float):
    """Definition 1 recovery ('back above the deep threshold'). Returns
    (state1, state2, state3) each as (n, win_rate_or_None, median_or_None)."""
    mae_col, ret_col = f"mae_{t_label}", f"ret_{t_label}"
    if df.empty or mae_col not in df.columns:
        return None
    deep = df[mae_col] <= threshold
    state1 = _cell(~deep, df)
    state2 = _cell(deep & (df[ret_col] > threshold), df)
    state3 = _cell(deep & (df[ret_col] <= threshold), df)
    return state1, state2, state3


def section_a(vol_trade_dfs: dict) -> str:
    lines = [
        "## A. Recovery-state stability across deep-drawdown thresholds\n",
        "Definition 1 recovery ('DD_current back above the deep threshold "
        "it dropped below'). For each volatility quintile, pre-terminal "
        "time checkpoint, and candidate deep-drawdown threshold: State 1 "
        "= never reached that depth by t, State 2 = reached it but has "
        "since recovered (by this definition), State 3 = reached it and "
        "is still there at t. 'Ordering' flags whether "
        "P(winner|S1) > P(winner|S2) > P(winner|S3) holds where all three "
        "cells clear the n >= {} floor -- looking for a stable RANGE, not "
        "a single optimal threshold.\n".format(MIN_CELL_N),
    ]
    for vq in Q_LABELS:
        df = vol_trade_dfs[vq]
        lines.append(f"\n### Volatility {vq}\n")
        lines.append("| Time | Deep <= | State 1: never deep | State 2: deep->recovered | State 3: deep->still impaired | Ordering S1>S2>S3 |")
        lines.append("|---|---|---|---|---|---|")
        for t_label in TIME_ROWS:
            for th in DEEP_THRESHOLDS:
                res = classify_states(df, t_label, th)
                if res is None:
                    continue
                (n1, wr1, _), (n2, wr2, _), (n3, wr3, _) = res
                if wr1 is None and wr2 is None and wr3 is None:
                    continue
                ordering = "n/a"
                if wr1 is not None and wr2 is not None and wr3 is not None:
                    ordering = "yes" if wr1 > wr2 > wr3 else "no"
                lines.append(
                    f"| {t_label} | {th*100:.2f}% | {_fmt(n1, wr1)} | {_fmt(n2, wr2)} | "
                    f"{_fmt(n3, wr3)} | {ordering} |"
                )
    return "\n".join(lines) + "\n"


def section_b(vol_trade_dfs: dict) -> str:
    lines = [
        "## B. Recovery-definition sensitivity\n",
        f"Fixed at deep-threshold <= {SECTION_B_THRESHOLD*100:.1f}%, "
        f"times {', '.join(SECTION_B_TIMES)}. Among trades that reached "
        "this deep threshold by time t, how does the recovered/impaired "
        "split (and each side's win rate) change depending on which "
        "'recovered' definition is used?\n\n"
        "- **Def 1** -- `DD_current > threshold` (no longer as deep as "
        "the threshold itself).\n"
        "- **Def 2 (margin X)** -- `DD_current >= MAE_so_far(t) + X` "
        "(recovered by at least X from the trade's own low point, "
        "regardless of the fixed threshold).\n"
        "- **Def 3 (residual)** -- `DD_current >= residual` (back to "
        "within a small absolute distance of breakeven, a stricter bar "
        "than Def 1/2).\n",
    ]
    for vq in Q_LABELS:
        df = vol_trade_dfs[vq]
        lines.append(f"\n### Volatility {vq}\n")
        lines.append("| Time | Definition | n deep (total) | Recovered | Impaired |")
        lines.append("|---|---|---|---|---|")
        for t_label in SECTION_B_TIMES:
            mae_col, ret_col = f"mae_{t_label}", f"ret_{t_label}"
            if df.empty or mae_col not in df.columns:
                continue
            deep_mask = df[mae_col] <= SECTION_B_THRESHOLD
            n_deep = int(deep_mask.sum())
            if n_deep == 0:
                continue
            deep_df = df.loc[deep_mask]

            def emit(label, recovered_mask_local):
                rec = _cell(recovered_mask_local, deep_df)
                imp = _cell(~recovered_mask_local, deep_df)
                lines.append(f"| {t_label} | {label} | {n_deep} | {_fmt(*rec[:2])} | {_fmt(*imp[:2])} |")

            emit("Def 1: back above threshold", deep_df[ret_col] > SECTION_B_THRESHOLD)
            for x in RECOVERY_MARGIN_X:
                emit(f"Def 2: margin +{x*100:.2f}% from own low",
                     deep_df[ret_col] >= deep_df[mae_col] + x)
            for r in RESIDUAL_ABS:
                emit(f"Def 3: residual <= {r*100:.2f}% of breakeven",
                     deep_df[ret_col] >= r)
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_d_recovery_state_discovery_v1.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()  # Discovery only -- 2026 untouched, per SS7

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    disc_lpl_q = apply_quintile(disc["local_price_location"], lpl_edges)
    disc_vol_q = apply_quintile(disc["volatility_atr_norm"], vol_edges)

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    print("\n=== Discovery (2020-2025, in-sample) ===")
    vol_trade_dfs = build_vol_trade_dfs(disc, disc_lpl_q, disc_vol_q, price_history, sorted_ts)

    body = section_a(vol_trade_dfs) + "\n---\n\n" + section_b(vol_trade_dfs)

    header = (
        "# Phase D discovery v1 — Recovery-state (Class D') definition exploration\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Still not a position-management rule. Discovery only (2020-2025) "
        "-- per phase_d_path_state_hypothesis.md SS7, mechanic definition "
        "work stays on Discovery data; 2026 is untouched here. Same "
        "widened LPL==Q1-across-all-volatility-quintiles diagnostic "
        "population as phase_c_trade_path_analysis_v3/v4 (decision_rule_v1 "
        "itself only fires at Volatility==Q5). Cells with n < {} are "
        "marked instead of reported, per the same discipline used "
        "throughout this project.\n\n"
        "Goal is NOT to find the single best deep-drawdown threshold. It "
        "is to see whether a RANGE of plausible thresholds/definitions "
        "shows the same qualitative structure (P(winner) falling from "
        "State 1 to State 2 to State 3) -- a stable range is a much "
        "stronger result than one threshold that happens to separate best.\n\n"
        "---\n\n".format(MIN_CELL_N)
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
