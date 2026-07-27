"""
Hypothesis Validation — micro_return_5m. Freezes the discovery_v10-v12
finding exactly, then tests it on genuinely unseen data, same discipline
as hypothesis_validation.py (the original LPL validation).

FROZEN HYPOTHESIS:
  Input:  micro_return_5m (1m microstructure: price change over the last
          5 minutes before the state candle)
  Output: forward return distribution at 15m / 1h / 4h
  Claim:  LOW (very negative) micro_return_5m -> systematically better
          forward-return distribution; HIGH (very positive) -> worse.
          Short-horizon mean reversion, found independent of the
          existing LPL factor (r=0.127, discovery_v11) and 6/6-year
          stable at all three horizons (discovery_v12).

METHOD: quintile bin edges are fit ONLY on the discovery period
(2020-01-01 through 2025-12-31) and applied AS-IS, frozen, to the
validation period (2026-01-01 onward) — same discipline as
hypothesis_validation.py. The validation period is never used to choose
or adjust anything.

Usage:
    .venv/bin/python scripts/hypothesis_validation_micro_return_5m.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import discovery_report as dr
from discovery_report import horizon_stats
from hypothesis_validation import fit_quintile_edges, apply_quintile, Q_LABELS

MIN_CELL_N = 30  # matches hypothesis_validation.py's validation threshold
HORIZONS = ["15m", "1h", "4h"]
NEW_DIMENSIONS = [("micro_return_5m", ("micro_1m", "return_5m"), False)]


def q1_q5_row(df: pd.DataFrame, q_col: str, horizon: str) -> dict:
    fwd = df[f"fwd_{horizon}"]
    s1 = horizon_stats(fwd[df[q_col] == "Q1"])
    s5 = horizon_stats(fwd[df[q_col] == "Q5"])
    if not s1 or not s5:
        return {}
    return {"n1": s1["n"], "wr1": s1["win_rate"], "med1": s1["median"],
            "n5": s5["n"], "wr5": s5["win_rate"], "med5": s5["median"],
            "spread": s1["median"] - s5["median"]}


def section_1(disc: pd.DataFrame, val: pd.DataFrame) -> str:
    lines = [
        "## 1. Discovery vs. Validation — Q1 (very negative) vs Q5 (very positive) micro_return_5m\n",
        "Frozen quintile edges (fit on Discovery only) applied unchanged "
        "to both periods.\n",
        "| Horizon | Period | n (Q1) | Q1 win% | Q1 median | n (Q5) | Q5 win% | Q5 median | Spread (Q1-Q5) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for h in HORIZONS:
        for label, d in [("Discovery", disc), ("Validation", val)]:
            r = q1_q5_row(d, "ret5m_q", h)
            if not r:
                lines.append(f"| {h} | {label} | insufficient data | | | | | | |")
                continue
            flag = " (n<MIN_CELL_N)" if (label == "Validation" and (r["n1"] < MIN_CELL_N or r["n5"] < MIN_CELL_N)) else ""
            lines.append(
                f"| {h} | {label}{flag} | {r['n1']} | {r['wr1']*100:.1f}% | {r['med1']*100:+.4f}% | "
                f"{r['n5']} | {r['wr5']*100:.1f}% | {r['med5']*100:+.4f}% | {r['spread']*100:+.4f}% |"
            )
    return "\n".join(lines) + "\n"


def section_verdict(disc: pd.DataFrame, val: pd.DataFrame) -> str:
    lines = ["## 2. Verdict\n", "| Horizon | Discovery spread | Validation spread | Same sign? |", "|---|---|---|---|"]
    same_count, total = 0, 0
    for h in HORIZONS:
        d, v = q1_q5_row(disc, "ret5m_q", h), q1_q5_row(val, "ret5m_q", h)
        if not d or not v:
            continue
        total += 1
        same = (d["spread"] > 0) == (v["spread"] > 0)
        same_count += same
        lines.append(f"| {h} | {d['spread']*100:+.4f}% | {v['spread']*100:+.4f}% | {'yes' if same else 'NO'} |")
    lines.append(f"\n**{same_count}/{total} horizons held the same sign out-of-sample.**\n")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/reports/hypothesis_validation_micro_return_5m.md")
    args = p.parse_args()

    print("Loading candidates...")
    dr.DIMENSIONS = dr.DIMENSIONS + NEW_DIMENSIONS
    df = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()
    val = df[df["timestamp"] >= cutoff].copy()
    disc = disc.dropna(subset=["micro_return_5m"]).copy()
    val = val.dropna(subset=["micro_return_5m"]).copy()
    print(f"Discovery n={len(disc):,}, Validation n={len(val):,}")

    edges = fit_quintile_edges(disc["micro_return_5m"])  # fit ONLY on Discovery
    disc["ret5m_q"] = apply_quintile(disc["micro_return_5m"], edges)
    val["ret5m_q"] = apply_quintile(val["micro_return_5m"], edges)  # frozen, applied as-is

    body = section_1(disc, val) + "\n---\n\n" + section_verdict(disc, val)

    header = (
        "# Hypothesis Validation — micro_return_5m\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Freezes discovery_v10-v12's micro_return_5m finding and tests it "
        "OOS, same discipline as hypothesis_validation.py's original LPL "
        "validation. Quintile edges fit ONLY on 2020-2025, applied "
        "unchanged to 2026. Does not change decision_rule_v1 or propose "
        "a rule -- purely tests whether the Discovery-period finding "
        "survives contact with unseen data.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
