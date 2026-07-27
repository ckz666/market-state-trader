"""
Discovery v10 — the 15m/1m dimensions never tested in discovery_v1, plus
a proper year-stability check for `short_term_direction_15m` (which WAS
tested in v1 but never went through v1's own Section D/E pipeline,
because that pipeline only runs on continuous, decile-binned dimensions
-- categorical fields like direction are silently skipped there).

Per the project discussion: discovery_v1's DIMENSIONS list covered only
2 of the 8 collected `short_term_15m` fields (direction,
momentum_aligned) and 4 of the 9 collected `micro_1m` fields (body_ratio,
close_location, upper/lower wick ratio) -- the 1m candle-geometry ones,
which turned out to be flat/no-signal. Never tested at all:
  15m: rsi, macd_norm, upper_rejection, lower_rejection,
       range_position_20, candle_direction
  1m:  volatility_1m, return_5m, immediate_reversal, candle_direction

This script extends discovery_report.py's DIMENSIONS list (in-process,
not editing the frozen v1 file) with those fields and runs the exact
same binning/stats machinery, at 15m/1h/4h horizons (per the user's
request to specifically check win rate at 15m and 1h). It also adds a
year-by-year stability check for `short_term_direction_15m` (categorical
analogue of v1 Section E, which only covers continuous dimensions).

Purely descriptive; does not change decision_rule_v1 or propose a rule.
Discovery period only (2020-2025); 2026 untouched, consistent with every
script since discovery_v6 (v1 itself pooled through 2026, before this
project's later fit/freeze/OOS discipline was established).

Usage:
    .venv/bin/python scripts/discovery_v10_15m_1m_dimensions.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import discovery_report as dr

MIN_CELL_N = 15
CHECK_HORIZONS = ["15m", "1h", "4h"]

NEW_DIMENSIONS = [
    # 15m — short_term_15m fields never in v1's DIMENSIONS
    ("short_term_rsi_15m",              ("short_term_15m", "rsi"), False),
    ("short_term_macd_norm_15m",        ("short_term_15m", "macd_norm"), False),
    ("short_term_upper_rejection_15m",  ("short_term_15m", "upper_rejection"), False),
    ("short_term_lower_rejection_15m",  ("short_term_15m", "lower_rejection"), False),
    ("short_term_range_position_20_15m", ("short_term_15m", "range_position_20"), False),
    ("short_term_candle_direction_15m", ("short_term_15m", "candle_direction"), True),
    # 1m — micro_1m fields never in v1's DIMENSIONS
    ("micro_volatility_1m",      ("micro_1m", "volatility_1m"), False),
    ("micro_return_5m",          ("micro_1m", "return_5m"), False),
    ("micro_immediate_reversal", ("micro_1m", "immediate_reversal"), True),
    ("micro_candle_direction",   ("micro_1m", "candle_direction"), True),
]


def section_new_dimensions(df: pd.DataFrame) -> str:
    lines = ["## A. Never-tested 15m/1m dimensions -- univariate, 15m/1h/4h horizons\n"]
    for label, _, categorical in NEW_DIMENSIONS:
        lines.append(f"\n### {label}\n")
        any_rows = False
        for horizon in CHECK_HORIZONS:
            rows = dr.dimension_table(df, label, categorical, horizon)
            rows = [r for r in rows if r["n"] >= MIN_CELL_N]
            if not rows:
                continue
            any_rows = True
            lines.append(f"**{label} — {horizon}**\n")
            lines.append("| Bin | n | Win Rate | Median | Mean | P05 |")
            lines.append("|---|---|---|---|---|---|")
            for r in rows:
                lines.append(
                    f"| {r['bin']} | {r['n']:,} | {r['win_rate']*100:.1f}% | "
                    f"{r['median']*100:+.4f}% | {r['mean']*100:+.4f}% | {r['p05']*100:+.2f}% |"
                )
            lines.append("")
        if not any_rows:
            lines.append(f"(no cells with n >= {MIN_CELL_N} -- field likely missing/constant in this data)\n")
    return "\n".join(lines) + "\n"


def section_short_term_direction_stability(df: pd.DataFrame) -> str:
    lines = [
        "## B. Year stability of `short_term_direction_15m` (categorical analogue of v1 Section E)\n",
        "v1 found a real-looking pattern here (bearish 15m momentum -> "
        "higher win rate/positive median; bullish -> lower win rate/"
        "negative median, consistent across all 4 horizons) but it never "
        "went through v1's own per-year stability check, since that "
        "pipeline only handles continuous dimensions. This does the "
        "categorical equivalent, at 15m and 1h horizons.\n",
    ]
    for horizon in ["15m", "1h"]:
        lines.append(f"\n### Horizon: {horizon}\n")
        lines.append("| Year | bearish n | bearish win% | bearish median | bullish n | bullish win% | bullish median |")
        lines.append("|---|---|---|---|---|---|---|")
        fwd = df[f"fwd_{horizon}"]
        signs = []
        for year in sorted(df["year"].unique()):
            yr_mask = df["year"] == year
            bear = fwd[yr_mask & (df["short_term_direction_15m"] == "bearish")]
            bull = fwd[yr_mask & (df["short_term_direction_15m"] == "bullish")]
            if len(bear) < MIN_CELL_N or len(bull) < MIN_CELL_N:
                lines.append(f"| {year} | {len(bear)} | n too few | - | {len(bull)} | n too few | - |")
                continue
            bear_wr, bear_med = (bear > 0).mean(), bear.median()
            bull_wr, bull_med = (bull > 0).mean(), bull.median()
            signs.append(bear_med > bull_med)
            lines.append(
                f"| {year} | {len(bear)} | {bear_wr*100:.1f}% | {bear_med*100:+.4f}% | "
                f"{len(bull)} | {bull_wr*100:.1f}% | {bull_med*100:+.4f}% |"
            )
        if signs:
            lines.append(f"\nSign consistency (bearish median > bullish median): {sum(signs)}/{len(signs)} years\n")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/reports/discovery_v10_15m_1m_dimensions.md")
    args = p.parse_args()

    print("Loading candidates (extended dimension set)...")
    dr.DIMENSIONS = dr.DIMENSIONS + NEW_DIMENSIONS
    df_all = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df_all[df_all["timestamp"] < cutoff].copy()  # Discovery only -- 2026 untouched
    print(f"Discovery candidates: {len(disc):,}")

    body = section_new_dimensions(disc) + "\n---\n\n" + section_short_term_direction_stability(disc)

    header = (
        "# Discovery v10 — never-tested 15m/1m dimensions, and short_term_direction_15m stability\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Purely descriptive; does not change decision_rule_v1 or propose "
        "a rule. Extends discovery_v1's DIMENSIONS list (in-process, not "
        "editing the frozen v1 script) with 15m/1m fields that were "
        "collected but never tested, and adds a categorical year-"
        "stability check for `short_term_direction_15m` (v1's own Section "
        "D/E pipeline only handles continuous dimensions, so this field's "
        "real-looking pattern was never stability-checked). Discovery "
        "period only (2020-2025); 2026 untouched. Cells with n < "
        f"{MIN_CELL_N} are omitted.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
