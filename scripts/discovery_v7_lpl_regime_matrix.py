"""
Discovery v7 — full LPL quintile x regime_4h outcome matrix.

Direct follow-up to discovery_v6: that script showed the LPL=Q1 vs Q5
spread (at Vol=Q5, decision_rule_v1's actual traded regime) grows
monotonically from ranging (+0.073%) to transitioning (+0.217%) to
trending (+0.432%), with no sign flip anywhere. This only compared the
two extreme quintiles per regime -- it doesn't yet show WHERE the
widening spread comes from. Per the project discussion, three candidate
explanations:

  A. Q1 gets better in trending regimes (Q5 roughly flat across regimes)
  B. Q5 gets worse in trending regimes (Q1 roughly flat across regimes)
  C. A genuine LPL x regime interaction -- neither extreme alone explains
     it, and/or the effect is non-monotone across LPL quintiles within
     a regime (not just a Q1-vs-Q5 story)

This script reports the full 5 (LPL quintile) x 3 (regime) matrix, at
Vol=Q5, 4h horizon, so the shape can be read directly rather than
inferred from the two-quintile spread alone. Purely descriptive; does
not change decision_rule_v1 or propose a new rule. Same frozen LPL/
quintile-edge parameters as hypothesis_validation.py / discovery_v6.
Discovery only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v7_lpl_regime_matrix.py
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

MIN_CELL_N = 15
HORIZON = "fwd_4h"
REGIMES = ["ranging", "transitioning", "trending"]
LPL_QUINTILES = ["Q1", "Q2", "Q3", "Q4", "Q5"]


def _cell(sub: pd.Series) -> str:
    n = len(sub)
    if n < MIN_CELL_N:
        return f"n={n} (too few)"
    wins = sub > 0
    gross_wins = sub[wins].sum()
    gross_losses = -sub[~wins].sum()
    pf = gross_wins / gross_losses if gross_losses > 0 else float("inf")
    # NOTE: no literal "|" allowed here -- this string is embedded directly
    # inside a markdown table cell, and "|" would silently split columns.
    return (
        f"n={n}, win {wins.mean()*100:.1f}%, mean {sub.mean()*100:+.4f}%, "
        f"median {sub.median()*100:+.4f}%, P05 {sub.quantile(0.05)*100:+.2f}%, PF {pf:.2f}"
    )


def section_matrix(df: pd.DataFrame) -> str:
    vol_q5 = df[df["vol_q"] == "Q5"]
    lines = [
        "## Full LPL quintile x regime_4h matrix (Vol=Q5, 4h forward return)\n",
        "| LPL | " + " | ".join(REGIMES) + " |",
        "|---|" + "---|" * len(REGIMES),
    ]
    medians = {r: {} for r in REGIMES}
    for lpl_q in LPL_QUINTILES:
        row = [lpl_q]
        for regime in REGIMES:
            sub = vol_q5[(vol_q5["lpl_q"] == lpl_q) & (vol_q5["regime_4h"] == regime)][HORIZON]
            row.append(_cell(sub))
            if len(sub) >= MIN_CELL_N:
                medians[regime][lpl_q] = sub.median()
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n", medians


def section_hypothesis_check(medians: dict) -> str:
    lines = [
        "## Which hypothesis does the shape support?\n",
        "Median 4h return by LPL quintile, per regime (from the matrix above):\n",
        "| Regime | " + " | ".join(LPL_QUINTILES) + " |",
        "|---|" + "---|" * len(LPL_QUINTILES),
    ]
    for regime in REGIMES:
        row = [regime]
        for lpl_q in LPL_QUINTILES:
            v = medians[regime].get(lpl_q)
            row.append(f"{v*100:+.4f}%" if v is not None else "n/a")
        lines.append("| " + " | ".join(row) + " |")

    q1_by_regime = {r: medians[r].get("Q1") for r in REGIMES}
    q5_by_regime = {r: medians[r].get("Q5") for r in REGIMES}
    if all(v is not None for v in q1_by_regime.values()) and all(v is not None for v in q5_by_regime.values()):
        q1_range = q1_by_regime["trending"] - q1_by_regime["ranging"]
        q5_range = q5_by_regime["trending"] - q5_by_regime["ranging"]
        lines.append("")
        lines.append(f"Q1 movement (trending - ranging): {q1_range*100:+.4f}%")
        lines.append(f"Q5 movement (trending - ranging): {q5_range*100:+.4f}%")
        lines.append("")
        if abs(q1_range) > abs(q5_range) * 1.5:
            verdict = "Hypothesis A dominant: Q1 improves much more than Q5 degrades as regime shifts toward trending."
        elif abs(q5_range) > abs(q1_range) * 1.5:
            verdict = "Hypothesis B dominant: Q5 degrades much more than Q1 improves as regime shifts toward trending."
        else:
            verdict = "Neither extreme dominates alone -- both move by comparable amounts (consistent with a genuine interaction, Hypothesis C)."
        lines.append(f"**{verdict}**")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/reports/discovery_v7_lpl_regime_matrix.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()  # Discovery only

    params = fit_params(disc)  # frozen procedure, reused unchanged
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    disc["lpl_q"] = apply_quintile(disc["local_price_location"], lpl_edges)
    disc["vol_q"] = apply_quintile(disc["volatility_atr_norm"], vol_edges)

    md_matrix, medians = section_matrix(disc)
    md_verdict = section_hypothesis_check(medians)

    body = md_matrix + "\n---\n\n" + md_verdict

    header = (
        "# Discovery v7 — full LPL quintile x regime_4h outcome matrix\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Direct follow-up to discovery_v6: decomposes the LPL=Q1 vs Q5 "
        "spread (which widened monotonically ranging -> transitioning -> "
        "trending) into the full quintile matrix, to see whether Q1 "
        "improves, Q5 degrades, or there's a genuine interaction/"
        "non-monotone shape. Vol=Q5 only (decision_rule_v1's actual "
        "traded regime). Purely descriptive; does not change "
        "decision_rule_v1. Same frozen LPL/quintile-edge parameters as "
        "hypothesis_validation.py / discovery_v6. Discovery only; 2026 "
        f"untouched. Cells with n < {MIN_CELL_N} are marked instead of "
        "reported.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
