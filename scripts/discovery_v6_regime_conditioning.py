"""
Discovery v6 — regime conditioning of the frozen LPL x Volatility edge.

Per the project discussion: rather than adding a new feature/dimension,
this tests whether the ALREADY-VALIDATED LPL x Volatility hypothesis
(hypothesis_validation.py, decision_rule_v1.py) is uniform across market
regimes that were already collected in every candidate but never used in
Discovery v1-v5 (`context_4h.regime`, `context_4h.structure_trend`) --
zero new data collection, exact same frozen LPL/quintile parameters,
same discipline as discovery_v5's own follow-up cuts.

Purely descriptive. Does NOT change decision_rule_v1, does NOT propose a
new rule. Discovery period only (2020-2025); 2026 untouched (consistent
with this project's fit-freeze-then-OOS discipline -- this is a NEW
sub-hypothesis, so it gets its own eventual OOS step later, not bundled
into this descriptive pass).

Two cuts, both restricted to Volatility=Q5 (decision_rule_v1's actual
traded regime -- so this speaks directly to the rule that's actually in
use, not just a diagnostic on the widened population):
  A. LPL=Q1 vs LPL=Q5, 4h forward return, split by context_4h.regime
     ("trending" | "ranging" | "transitioning").
  B. Same, split by context_4h.structure_trend ("uptrend" | "downtrend" |
     "sideways" | "expanding" | "contracting").
  C. Time-stability (sign-consistency per year) of the regime cut that
     shows the widest spread in A, matching discovery_v5's own
     stability-check convention.

Usage:
    .venv/bin/python scripts/discovery_v6_regime_conditioning.py
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


def _cell(sub: pd.Series):
    n = len(sub)
    if n < MIN_CELL_N:
        return None, f"n={n}"
    return n, f"n={n}, median {sub.median()*100:+.4f}%, mean {sub.mean()*100:+.4f}%, win {((sub>0).mean())*100:.1f}%"


def section_cut(df: pd.DataFrame, group_col: str, group_label: str) -> tuple[str, dict]:
    """Returns (markdown, {group_value: spread}) for later stability check."""
    lines = [
        f"## LPL=Q1 vs LPL=Q5 (4h return), split by `{group_col}` (Vol=Q5 only)\n",
        f"| {group_label} | n (Q1) | LPL=Q1 | n (Q5) | LPL=Q5 | Spread (Q1 - Q5 median) |",
        "|---|---|---|---|---|---|",
    ]
    spreads = {}
    vol_q5 = df[df["vol_q"] == "Q5"]
    for val in sorted(vol_q5[group_col].dropna().unique()):
        sub = vol_q5[vol_q5[group_col] == val]
        q1 = sub[sub["lpl_q"] == "Q1"][HORIZON]
        q5 = sub[sub["lpl_q"] == "Q5"][HORIZON]
        n1, cell1 = _cell(q1)
        n5, cell5 = _cell(q5)
        spread_str = "n/a"
        if n1 and n5:
            spread = q1.median() - q5.median()
            spreads[val] = spread
            spread_str = f"{spread*100:+.4f}%"
        lines.append(f"| {val} | {n1 or len(q1)} | {cell1} | {n5 or len(q5)} | {cell5} | {spread_str} |")
    return "\n".join(lines) + "\n", spreads


def section_stability(df: pd.DataFrame, group_col: str, group_val, direction: str) -> str:
    lines = [
        f"## Time stability: `{group_col} == {group_val!r}`, LPL=Q1 vs Q5, Vol=Q5, 4h\n",
        f"Widest spread from the cut above ({direction}). Per-year check, same "
        "convention as discovery_v5 SS5 -- an effect that flips sign across "
        "years is not a finding.\n",
        "| Year | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread |",
        "|---|---|---|---|---|---|",
    ]
    sub_all = df[(df["vol_q"] == "Q5") & (df[group_col] == group_val)]
    signs = []
    for year in sorted(sub_all["year"].unique()):
        yr = sub_all[sub_all["year"] == year]
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


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/reports/discovery_v6_regime_conditioning.md")
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

    body = "\n---\n\n".join([
        f"n Discovery candidates: {len(disc):,}. `regime_4h` value counts: "
        f"{disc['regime_4h'].value_counts().to_dict()}. `structure_trend_4h` "
        f"value counts: {disc['structure_trend_4h'].value_counts().to_dict()}.\n",
    ])

    md_a, spreads_a = section_cut(disc, "regime_4h", "Regime")
    md_b, spreads_b = section_cut(disc, "structure_trend_4h", "Structure trend")

    body += "\n---\n\n" + md_a + "\n---\n\n" + md_b

    if spreads_a:
        widest_col, widest_val = "regime_4h", max(spreads_a, key=lambda k: abs(spreads_a[k]))
        direction = "widest spread in section A"
        body += "\n---\n\n" + section_stability(disc, widest_col, widest_val, direction)

    header = (
        "# Discovery v6 — regime conditioning of the frozen LPL x Volatility edge\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Purely descriptive; does not change decision_rule_v1 or propose "
        "a new rule. Tests whether the already-validated LPL x Volatility "
        "edge (restricted to Vol=Q5, decision_rule_v1's actual traded "
        "regime) is uniform across `context_4h.regime` / "
        "`context_4h.structure_trend` -- fields already collected in "
        "every candidate but never used in discovery_v1-v5. Same frozen "
        "LPL/quintile-edge parameters as hypothesis_validation.py "
        "(fit on 2020-2025 only). Discovery only; 2026 untouched -- this "
        "is a new sub-hypothesis and would get its own OOS step later if "
        "it survives this descriptive pass. Cells with n < {} are marked "
        "instead of reported.\n\n"
        "---\n\n".format(MIN_CELL_N)
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
