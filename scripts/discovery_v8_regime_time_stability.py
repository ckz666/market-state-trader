"""
Discovery v8 — time stability of the LPL x regime_4h matrix (discovery_v7).

Direct follow-up per the project discussion: discovery_v6 only checked
per-year stability for the "trending" regime (the widest LPL=Q1 vs Q5
spread). discovery_v7 then found two things that still need a stability
check of their own:

  1. The Q1 vs Q5 spread's regime-conditioning (ranging < transitioning
     < trending) -- is this ordering stable per year in ALL THREE
     regimes, not just trending?
  2. discovery_v7's more surprising finding: within "ranging", the LPL
     quintile ordering is NOT monotone (Q4's median beat Q1's) -- is
     that a stable structural feature of the ranging regime, or a
     one-or-two-year artifact?

Purely descriptive; does not change decision_rule_v1 or propose a rule.
Same frozen LPL/quintile-edge parameters as hypothesis_validation.py /
discovery_v6/v7. Vol=Q5 only (decision_rule_v1's actual traded regime).
Discovery only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v8_regime_time_stability.py
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

MIN_CELL_N = 15
HORIZON = "fwd_4h"
REGIMES = ["ranging", "transitioning", "trending"]
LPL_QUINTILES = ["Q1", "Q2", "Q3", "Q4", "Q5"]


def section_q1_q5_stability(df: pd.DataFrame) -> str:
    lines = [
        "## A. Per-regime, per-year: LPL=Q1 vs Q5 spread (Vol=Q5, 4h)\n",
        "Extends discovery_v6's stability check (which only covered "
        "'trending') to all three regimes -- is the ranging < "
        "transitioning < trending ordering of the spread itself stable "
        "per year, or driven by a subset of years?\n",
    ]
    vol_q5 = df[df["vol_q"] == "Q5"]
    for regime in REGIMES:
        lines.append(f"\n### {regime}\n")
        lines.append("| Year | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread |")
        lines.append("|---|---|---|---|---|---|")
        sub_regime = vol_q5[vol_q5["regime_4h"] == regime]
        signs = []
        for year in sorted(sub_regime["year"].unique()):
            yr = sub_regime[sub_regime["year"] == year]
            q1 = yr[yr["lpl_q"] == "Q1"][HORIZON]
            q5 = yr[yr["lpl_q"] == "Q5"][HORIZON]
            if len(q1) < MIN_CELL_N or len(q5) < MIN_CELL_N:
                lines.append(f"| {year} | {len(q1)} | n too few | {len(q5)} | n too few | - |")
                continue
            spread = q1.median() - q5.median()
            signs.append(spread > 0)
            lines.append(f"| {year} | {len(q1)} | {q1.median()*100:+.4f}% | {len(q5)} | {q5.median()*100:+.4f}% | {spread*100:+.4f}% |")
        if signs:
            lines.append(f"\nSign consistency: {sum(signs)}/{len(signs)} years positive (Q1 > Q5 median)\n")
    return "\n".join(lines) + "\n"


def section_ranging_shape_stability(df: pd.DataFrame) -> str:
    lines = [
        "## B. Is 'ranging' regime's non-monotone LPL shape stable per year?\n",
        "discovery_v7 found Q4's median return beating Q1's within "
        "'ranging' (Vol=Q5, pooled 2020-2025). Full Q1-Q5 median row per "
        "year, to see whether Q4 > Q1 is a recurring feature or a "
        "one/two-year artifact.\n",
        "| Year | Q1 | Q2 | Q3 | Q4 | Q5 | Q4 > Q1? |",
        "|---|---|---|---|---|---|---|",
    ]
    ranging = df[(df["vol_q"] == "Q5") & (df["regime_4h"] == "ranging")]
    flags = []
    for year in sorted(ranging["year"].unique()):
        yr = ranging[ranging["year"] == year]
        medians = {}
        ns = {}
        for lpl_q in LPL_QUINTILES:
            sub = yr[yr["lpl_q"] == lpl_q][HORIZON]
            ns[lpl_q] = len(sub)
            medians[lpl_q] = sub.median() if len(sub) >= MIN_CELL_N else None
        if medians["Q1"] is None or medians["Q4"] is None:
            row = [str(year)] + ["n too few" if medians[q] is None else f"{medians[q]*100:+.4f}%" for q in LPL_QUINTILES] + ["n/a"]
        else:
            q4_beats_q1 = medians["Q4"] > medians["Q1"]
            flags.append(q4_beats_q1)
            row = [str(year)] + [f"{medians[q]*100:+.4f}%" if medians[q] is not None else "n too few" for q in LPL_QUINTILES] + ["yes" if q4_beats_q1 else "no"]
        lines.append("| " + " | ".join(row) + " |")
    if flags:
        lines.append(f"\nQ4 > Q1 in {sum(flags)}/{len(flags)} years with sufficient n.\n")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/reports/discovery_v8_regime_time_stability.md")
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

    body = section_q1_q5_stability(disc) + "\n---\n\n" + section_ranging_shape_stability(disc)

    header = (
        "# Discovery v8 — time stability of the LPL x regime_4h matrix\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Follow-up to discovery_v6/v7. Section A extends discovery_v6's "
        "per-year stability check (previously only done for 'trending') "
        "to all three regimes. Section B checks whether discovery_v7's "
        "surprising 'ranging' non-monotonicity (Q4 beating Q1) is a "
        "stable per-year feature or a pooled-period artifact. Purely "
        "descriptive; does not change decision_rule_v1. Same frozen LPL/"
        "quintile-edge parameters as hypothesis_validation.py. Vol=Q5 "
        "only. Discovery only; 2026 untouched. Cells with n < "
        f"{MIN_CELL_N} are marked instead of reported.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
