"""
Phase C trade-path analysis v4 — the 3-way table: Volatility x Time x
Drawdown -> P(eventual winner). Per the project discussion, this is meant
to be the last purely-analytical step before formulating a first position-
management hypothesis (a separate, later, explicitly-labeled hypothesis
to be frozen and OOS-tested on its own — not built here).

Same scope note as v3 section B: decision_rule_v1 only ever fires at
Volatility==Q5, so this uses the widened LPL==Q1 population at every
volatility quintile (independent Option-A trade sequences per quintile)
purely as a diagnostic — not a change to decision_rule_v1.

For each (volatility quintile, time checkpoint, drawdown threshold) cell:
    among trades in that volatility quintile whose RUNNING MAE (from
    entry up to that checkpoint) has reached at least that much adverse
    excursion, what fraction still closed as a winner?

Usage:
    .venv/bin/python scripts/phase_c_trade_path_analysis_v4.py
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
from phase_c_baseline_v1 import load_1m_price_series, simulate
from phase_c_trade_path_analysis_v2 import CHECKPOINTS, build_trade_frame

DRAWDOWN_THRESHOLDS = [-0.005, -0.01, -0.015, -0.02]
TIME_ROWS = ["15m", "1h", "2h", "4h"]  # subset of CHECKPOINTS for a readable table
Q_LABELS = ["Q1", "Q2", "Q3", "Q4", "Q5"]
MIN_CELL_N = 15


def build_vol_trade_dfs(cand_df, lpl_q, vol_q, price_history, sorted_ts) -> dict:
    out = {}
    for vq in Q_LABELS:
        mask = (lpl_q == "Q1") & (vol_q == vq)
        signals = cand_df[mask].sort_values("timestamp")
        trades, _ = simulate(signals, price_history, sorted_ts)
        out[vq] = build_trade_frame(trades, price_history, sorted_ts)
        print(f"  Vol={vq}: {len(signals)} signals -> {len(trades)} trades")
    return out


def section_table(vol_trade_dfs: dict, col_prefix: str) -> str:
    """col_prefix: 'mae' for running MAE-so-far (deepest excursion up to t),
    'ret' for DD_current (unrealized return AT t itself, which may sit above
    MAE-so-far if the trade has partially recovered by t)."""
    lines = []
    lines.append("| Volatility | Time | " + " | ".join(f"<= {th*100:.1f}%" for th in DRAWDOWN_THRESHOLDS) + " |")
    lines.append("|---|---|" + "---|" * len(DRAWDOWN_THRESHOLDS))
    for vq in Q_LABELS:
        df = vol_trade_dfs[vq]
        for t_label in TIME_ROWS:
            col = f"{col_prefix}_{t_label}"
            if df.empty or col not in df.columns:
                row_cells = ["n/a"] * len(DRAWDOWN_THRESHOLDS)
            else:
                row_cells = []
                for th in DRAWDOWN_THRESHOLDS:
                    mask = df[col] <= th
                    n = mask.sum()
                    if n < MIN_CELL_N:
                        row_cells.append(f"n={n}")
                        continue
                    wr = (df.loc[mask, "net_return"] > 0).mean()
                    row_cells.append(f"{wr*100:.0f}% (n={n})")
            lines.append(f"| {vq} | {t_label} | " + " | ".join(row_cells) + " |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_c_trade_path_analysis_v4.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()
    val = df[df["timestamp"] >= cutoff].copy()

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    val["local_price_location"] = apply_lpl(val, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    disc_lpl_q = apply_quintile(disc["local_price_location"], lpl_edges)
    disc_vol_q = apply_quintile(disc["volatility_atr_norm"], vol_edges)
    val_lpl_q = apply_quintile(val["local_price_location"], lpl_edges)
    val_vol_q = apply_quintile(val["volatility_atr_norm"], vol_edges)

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    body = ""
    for name, cand_df, lpl_q, vol_q in [("Discovery (2020-2025, in-sample)", disc, disc_lpl_q, disc_vol_q),
                                          ("Validation (2026, out-of-sample)", val, val_lpl_q, val_vol_q)]:
        print(f"\n=== {name} ===")
        vol_trade_dfs = build_vol_trade_dfs(cand_df, lpl_q, vol_q, price_history, sorted_ts)
        body += f"### {name}\n\n"
        body += "#### A. Current drawdown (unrealized return AT t)\n\n"
        body += section_table(vol_trade_dfs, col_prefix="ret") + "\n"
        body += "#### B. MAE-so-far (deepest excursion reached BY t)\n\n"
        body += section_table(vol_trade_dfs, col_prefix="mae") + "\n"

    header = (
        "# Phase C trade-path analysis v4 — Volatility x Time x Drawdown -> P(winner)\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Last purely-analytical step before formulating a position-"
        "management hypothesis (a separate, later, frozen-and-OOS-tested "
        "step — not built here). LPL==Q1 widened across all volatility "
        "quintiles, per v3's scope note (decision_rule_v1 itself only "
        "fires at Volatility==Q5), as a diagnostic — not a change to "
        "decision_rule_v1.\n\n"
        "Two parallel drawdown definitions, per the project discussion: "
        "**A** is the unrealized return AT checkpoint t (`DD_current`, "
        "which can sit above the deepest point already visited if the "
        "trade has partially recovered by t); **B** is the running "
        "minimum unrealized return from entry up to t (`MAE_so_far`, the "
        "deepest excursion reached at any point up to t regardless of "
        "where the trade sits exactly at t). A trade currently at -0.2% "
        "that dipped to -1.5% earlier appears in B's <= -1.5% row but "
        "not in A's. Cells with n < {} are marked instead of reported, "
        "per the same discipline used throughout this project (v3's "
        "bb_position x vwap_distance sparse-cell lesson).\n\n"
        "**Caveat on A's 4h row:** at the terminal checkpoint, "
        "`DD_current` is essentially the trade's final return (net of "
        "fees), so \"current DD <= threshold at 4h\" is close to a "
        "restatement of \"closed a loser\" rather than an independent "
        "path observation — this is why every Q x 4h cell in table A "
        "reads ~0%. Not a finding; a tautology of the checkpoint "
        "coinciding with the exit. Table B does not have this problem, "
        "since MAE-so-far can differ from the final return at any "
        "checkpoint including the last.\n\n"
        "---\n\n".format(MIN_CELL_N)
    )
    full = header + "## Results\n\n" + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
