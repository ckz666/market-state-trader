"""
Discovery v15 — do LPL and micro_return_5m reinforce each other inside
Vol=Q5, or do they compete for the same trades?

Motivation (discovery_v14): both factors' spreads widen with volatility,
and decision_rule_v1 already trades ONLY Vol==Q5. So micro_return_5m
would operate in exactly the same subpopulation LPL already selects --
they may be additive, redundant, or actively conflicting there. This has
never been tested.

Restricted throughout to Vol==Q5 (decision_rule_v1's actual traded
regime), so the answer speaks directly to the rule in use.

  A. Full 5x5 matrix: LPL quintile x micro_return_5m quintile, median
     4h return per cell -- the shape of the interaction, if any.
  B. The decision-relevant comparison: `decision_rule_v1`'s actual entry
     cell (LPL==Q1) split by micro_return_5m quintile. If the
     micro_return gradient survives INSIDE LPL==Q1, it could refine
     entry selection; if it's flat there, the two factors are redundant
     at the point that matters even if both look good marginally.
  C. Same as B at 15m/1h horizons too, since discovery_v12/v14 showed
     this factor's edge is strongest short-horizon and largely gone by
     4h -- decision_rule_v1's 4h target may simply be the wrong horizon
     to harvest it.

Purely descriptive; does not change decision_rule_v1 or propose a rule.
Discovery period only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v15_lpl_x_micro_return_combined.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import discovery_report as dr
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile

MIN_CELL_N = 30
Q_LABELS = ["Q1", "Q2", "Q3", "Q4", "Q5"]
HORIZONS = ["15m", "1h", "4h"]
NEW_DIMENSIONS = [("micro_return_5m", ("micro_1m", "return_5m"), False)]


def section_matrix(df: pd.DataFrame, horizon: str) -> str:
    lines = [
        f"**Median {horizon} return — rows: LPL quintile, columns: micro_return_5m quintile (Vol=Q5)**\n",
        "| LPL \\ ret5m | " + " | ".join(Q_LABELS) + " |",
        "|---|" + "---|" * len(Q_LABELS),
    ]
    fwd = df[f"fwd_{horizon}"]
    for lpl_q in Q_LABELS:
        row = [lpl_q]
        for ret_q in Q_LABELS:
            sub = fwd[(df["lpl_q"] == lpl_q) & (df["ret5m_q"] == ret_q)].dropna()
            row.append(f"n={len(sub)}" if len(sub) < MIN_CELL_N
                       else f"{sub.median()*100:+.4f}% (n={len(sub)})")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def section_within_lpl_q1(df: pd.DataFrame) -> str:
    lines = [
        "## B/C. Inside `decision_rule_v1`'s actual entry cell (LPL==Q1 & Vol==Q5)\n",
        "Does the micro_return_5m gradient survive within the exact "
        "population the live rule already selects? This is the "
        "decision-relevant question -- a factor can look strong "
        "marginally and still add nothing where it would actually be "
        "applied.\n",
    ]
    entry = df[df["lpl_q"] == "Q1"]
    for horizon in HORIZONS:
        lines.append(f"\n**Horizon {horizon}**\n")
        lines.append("| micro_return_5m | n | Win rate | Median | Mean |")
        lines.append("|---|---|---|---|---|")
        fwd = entry[f"fwd_{horizon}"]
        medians = {}
        for ret_q in Q_LABELS:
            sub = fwd[entry["ret5m_q"] == ret_q].dropna()
            if len(sub) < MIN_CELL_N:
                lines.append(f"| {ret_q} | {len(sub)} | n too few | - | - |")
                continue
            medians[ret_q] = sub.median()
            lines.append(
                f"| {ret_q} | {len(sub):,} | {(sub>0).mean()*100:.1f}% | "
                f"{sub.median()*100:+.4f}% | {sub.mean()*100:+.4f}% |"
            )
        if "Q1" in medians and "Q5" in medians:
            lines.append(f"\nQ1-Q5 spread within LPL==Q1: **{(medians['Q1']-medians['Q5'])*100:+.4f}%**\n")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/reports/discovery_v15_lpl_x_micro_return_combined.md")
    args = p.parse_args()

    print("Loading candidates...")
    dr.DIMENSIONS = dr.DIMENSIONS + NEW_DIMENSIONS
    df = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()  # Discovery only

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    ret_edges = fit_quintile_edges(disc["micro_return_5m"].dropna())
    disc["lpl_q"] = apply_quintile(disc["local_price_location"], lpl_edges)
    disc["vol_q"] = apply_quintile(disc["volatility_atr_norm"], vol_edges)
    disc["ret5m_q"] = apply_quintile(disc["micro_return_5m"], ret_edges)

    vol_q5 = disc[(disc["vol_q"] == "Q5")].dropna(subset=["micro_return_5m"]).copy()
    print(f"Vol=Q5 candidates with micro_return_5m: {len(vol_q5):,}")

    body = "## A. Full interaction matrix (Vol=Q5)\n\n"
    for horizon in HORIZONS:
        body += section_matrix(vol_q5, horizon) + "\n"
    body += "\n---\n\n" + section_within_lpl_q1(vol_q5)

    header = (
        "# Discovery v15 — LPL x micro_return_5m inside Vol=Q5\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "discovery_v14 showed both factors strengthen with volatility, "
        "and decision_rule_v1 already trades only Vol==Q5 -- so they "
        "operate in the same subpopulation and may be additive, "
        "redundant, or conflicting there. This tests that directly. "
        "Purely descriptive; does not change decision_rule_v1. Discovery "
        f"only (2020-2025); 2026 untouched. Cells with n < {MIN_CELL_N} "
        "are marked instead of reported.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
