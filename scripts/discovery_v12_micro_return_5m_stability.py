"""
Discovery v12 — time stability of `micro_return_5m`, the one v10/v11
candidate that looked genuinely independent of LPL (r=0.127, its own PCA
component, incremental spread persisting across LPL quintiles).

Same convention as discovery_v1 Section E / discovery_v5/v6/v8: fit
quintile edges ONCE on the full Discovery period, apply those SAME frozen
edges per year, and check whether the Q1-vs-Q5 (most negative vs. most
positive 5m return) spread holds sign consistently year by year -- an
effect that only shows up pooled, or flips sign across years, is not a
finding.

Checked at 15m, 1h, and 4h horizons (per the user's request to look at
win rate specifically at 15m/1h, not just the 4h horizon used
throughout Phase A-D). Purely descriptive; does not change
decision_rule_v1 or propose a rule. Discovery period only (2020-2025);
2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v12_micro_return_5m_stability.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import discovery_report as dr
from hypothesis_validation import fit_quintile_edges, apply_quintile

MIN_CELL_N = 15
HORIZONS = ["15m", "1h", "4h"]
NEW_DIMENSIONS = [("micro_return_5m", ("micro_1m", "return_5m"), False)]


def section_pooled(df: pd.DataFrame) -> str:
    lines = [
        "## A. Pooled Q1-Q5 spread, all three horizons (frozen quintile edges)\n",
        "| Horizon | n (Q1) | Q1 win% | Q1 median | n (Q5) | Q5 win% | Q5 median | Spread |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for h in HORIZONS:
        fwd = df[f"fwd_{h}"]
        q1 = fwd[df["ret5m_q"] == "Q1"]
        q5 = fwd[df["ret5m_q"] == "Q5"]
        lines.append(
            f"| {h} | {len(q1)} | {(q1>0).mean()*100:.1f}% | {q1.median()*100:+.4f}% | "
            f"{len(q5)} | {(q5>0).mean()*100:.1f}% | {q5.median()*100:+.4f}% | {(q1.median()-q5.median())*100:+.4f}% |"
        )
    return "\n".join(lines) + "\n"


def section_yearly(df: pd.DataFrame) -> str:
    lines = ["## B. Per-year stability (SAME frozen quintile edges applied to each year)\n"]
    for h in HORIZONS:
        lines.append(f"\n### Horizon: {h}\n")
        lines.append("| Year | n (Q1) | Q1 win% | Q1 median | n (Q5) | Q5 win% | Q5 median | Spread |")
        lines.append("|---|---|---|---|---|---|---|---|")
        fwd = df[f"fwd_{h}"]
        signs = []
        for year in sorted(df["year"].unique()):
            yr_mask = df["year"] == year
            q1 = fwd[yr_mask & (df["ret5m_q"] == "Q1")]
            q5 = fwd[yr_mask & (df["ret5m_q"] == "Q5")]
            if len(q1) < MIN_CELL_N or len(q5) < MIN_CELL_N:
                lines.append(f"| {year} | {len(q1)} | n too few | - | {len(q5)} | n too few | - | - |")
                continue
            spread = q1.median() - q5.median()
            signs.append(spread > 0)
            lines.append(
                f"| {year} | {len(q1)} | {(q1>0).mean()*100:.1f}% | {q1.median()*100:+.4f}% | "
                f"{len(q5)} | {(q5>0).mean()*100:.1f}% | {q5.median()*100:+.4f}% | {spread*100:+.4f}% |"
            )
        if signs:
            lines.append(f"\nSign consistency: {sum(signs)}/{len(signs)} years positive (Q1 > Q5 median)\n")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/reports/discovery_v12_micro_return_5m_stability.md")
    args = p.parse_args()

    print("Loading candidates...")
    dr.DIMENSIONS = dr.DIMENSIONS + NEW_DIMENSIONS
    df_all = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df_all[df_all["timestamp"] < cutoff].copy()  # Discovery only
    disc = disc.dropna(subset=["micro_return_5m"]).copy()
    print(f"n candidates: {len(disc):,}")

    edges = fit_quintile_edges(disc["micro_return_5m"])  # fit ONCE on full Discovery period
    disc["ret5m_q"] = apply_quintile(disc["micro_return_5m"], edges)

    body = section_pooled(disc) + "\n---\n\n" + section_yearly(disc)

    header = (
        "# Discovery v12 — time stability of micro_return_5m\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Purely descriptive; does not change decision_rule_v1. Same "
        "convention as discovery_v1 Section E / discovery_v5/v6/v8: "
        "quintile edges fit ONCE on the full Discovery period, applied "
        "unchanged per year. Discovery only (2020-2025); 2026 untouched. "
        f"Cells with n < {MIN_CELL_N} are marked instead of reported.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
