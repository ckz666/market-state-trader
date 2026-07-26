"""
Discovery Analysis Report v5 — deep dive on the strongest finding so far:
Local Price Location (LPL) x Volatility.

v4's finding: high volatility roughly doubles-to-quadruples LPL's effect
size in both directions (residual/spread ratio 30%, a real interaction),
strongest single cell LPL=low+volatility=high -> +0.19% aggregate 4h
median, 7/7 years same sign. Per the project discussion, this deserves a
focused follow-up rather than crossing more dimensions:

  1. Quintile resolution — not just low/mid/high. For each volatility
     quintile, LPL's Q1-vs-Q5 spread, across all 4 horizons: does the
     interaction grow linearly with volatility, kick in past a threshold,
     or break down at the extreme?
  2. Volatility LEVEL vs. volatility CHANGE — is it high ATR itself, or
     ATR that's currently rising, that drives the amplification? Within
     the top volatility quintile only, split by whether ATR rose or
     fell/held over the prior 24h.
  3. Full outcome distribution (not just median) for the two extreme
     cells (LPL low + vol high, LPL high + vol high) — is the median
     shift broad, or a few extreme BTC moves?
  4. Multi-horizon comparison for those same two extreme cells — does the
     effect already show at 15m and hold through 4h, or is it purely a
     4h phenomenon?
  5. Time stability of the extreme cells, year by year (same machinery as
     v3/v4).

Usage:
    .venv/bin/python scripts/discovery_v5.py
    .venv/bin/python scripts/discovery_v5.py --include-live
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from discovery_report import load_candidates, horizon_stats, HORIZONS
from discovery_v4 import add_local_price_location, MIN_CELL_N
import mst_config as config

Q_LABELS = ["Q1", "Q2", "Q3", "Q4", "Q5"]


def quintile_bin(s: pd.Series) -> pd.Series:
    binned = pd.qcut(s, 5, labels=Q_LABELS, duplicates="drop")
    return binned.astype(str).where(s.notna())


# ── 1. Quintile resolution across horizons ──────────────────────────────

def section_1(df: pd.DataFrame, lpl_q: pd.Series, vol_q: pd.Series) -> str:
    lines = ["## 1. LPL x Volatility at quintile resolution, all horizons\n",
             "For each volatility quintile: LPL Q1 (lowest) median return, "
             "LPL Q5 (highest) median return, and the spread between them "
             "— does the LPL effect grow linearly with volatility, "
             "threshold, or reverse at the extreme?\n"]
    for h in HORIZONS:
        fwd = df[f"fwd_{h}"]
        lines.append(f"**{h}**\n")
        lines.append("| Volatility | n (LPL=Q1) | LPL=Q1 median | n (LPL=Q5) | LPL=Q5 median | Spread (Q5-Q1) |")
        lines.append("|---|---|---|---|---|---|")
        for vq in Q_LABELS:
            m1 = (vol_q == vq) & (lpl_q == "Q1")
            m5 = (vol_q == vq) & (lpl_q == "Q5")
            s1, s5 = horizon_stats(fwd[m1]), horizon_stats(fwd[m5])
            if not s1 or not s5:
                continue
            spread = s5["median"] - s1["median"]
            lines.append(f"| {vq} | {s1['n']:,} | {s1['median']*100:+.4f}% | {s5['n']:,} | "
                          f"{s5['median']*100:+.4f}% | {spread*100:+.4f}% |")
        lines.append("")
    return "\n".join(lines) + "\n"


# ── 2. Volatility level vs. change ──────────────────────────────────────

def section_2(df: pd.DataFrame, lpl_q: pd.Series, vol_q: pd.Series) -> str:
    lines = ["## 2. Volatility LEVEL vs. CHANGE\n",
             "Within the highest volatility quintile only (Q5 — where "
             "v4/section 1 show the strongest amplification): does it "
             "matter whether ATR got there by RISING over the prior 24h, "
             "or has just been sitting high? atr_change_24h = atr_norm - "
             "atr_norm 24h ago.\n"]

    atr_change = df["volatility_atr_norm"] - df["volatility_atr_norm"].shift(24)
    # only meaningful where the row 24h ago is the actual prior hour (data
    # has 0 gaps, confirmed in v1, so a plain shift is safe) and both
    # values exist
    valid = atr_change.notna()

    high_vol = vol_q == "Q5"
    rising = valid & high_vol & (atr_change > 0)
    falling = valid & high_vol & (atr_change <= 0)

    lines.append(f"Within volatility=Q5: {rising.sum():,} rows with ATR rising over 24h, "
                 f"{falling.sum():,} rows with ATR flat/falling.\n")

    for h in HORIZONS:
        fwd = df[f"fwd_{h}"]
        lines.append(f"**{h}**\n")
        lines.append("| ATR 24h trend | LPL | n | Median | Win Rate |")
        lines.append("|---|---|---|---|---|")
        for trend_name, trend_mask in [("rising", rising), ("flat/falling", falling)]:
            for lq in ["Q1", "Q5"]:
                m = trend_mask & (lpl_q == lq)
                s = horizon_stats(fwd[m])
                if s and s["n"] >= 20:
                    lines.append(f"| {trend_name} | {lq} | {s['n']:,} | {s['median']*100:+.4f}% | {s['win_rate']*100:.1f}% |")
        lines.append("")

    # explicit spread comparison at 4h
    fwd4h = df["fwd_4h"]
    rows = []
    for trend_name, trend_mask in [("rising", rising), ("flat/falling", falling)]:
        m1 = trend_mask & (lpl_q == "Q1")
        m5 = trend_mask & (lpl_q == "Q5")
        s1, s5 = horizon_stats(fwd4h[m1]), horizon_stats(fwd4h[m5])
        if s1 and s5:
            rows.append((trend_name, s5["median"] - s1["median"], s1["n"], s5["n"]))
    if rows:
        lines.append("**4h LPL spread (Q5-Q1) by ATR trend:**\n")
        lines.append("| ATR 24h trend | Spread | n(Q1) | n(Q5) |")
        lines.append("|---|---|---|---|")
        for name, spread, n1, n5 in rows:
            lines.append(f"| {name} | {spread*100:+.4f}% | {n1:,} | {n5:,} |")
        if len(rows) == 2:
            lines.append(f"\n**Verdict:** {'ATR trend matters — rising and flat/falling ATR produce meaningfully different spreads.' if abs(rows[0][1]-rows[1][1]) > 0.2*max(abs(rows[0][1]),abs(rows[1][1])) else 'ATR trend does not change the spread much — it looks like the LEVEL of volatility that matters, not whether it is currently rising.'}\n")
    return "\n".join(lines) + "\n"


# ── 3. Full outcome distribution for the extreme cells ──────────────────

def section_3(df: pd.DataFrame, lpl_q: pd.Series, vol_q: pd.Series) -> str:
    lines = ["## 3. Full outcome distribution — extreme cells (4h)\n",
             "Is the median shift broad across many samples, or driven by "
             "a handful of extreme BTC moves? Full distribution, not just "
             "the median.\n"]
    fwd = df["fwd_4h"]
    cells = [("LPL=Q1 (lowest) + Volatility=Q5 (highest)", (lpl_q == "Q1") & (vol_q == "Q5")),
             ("LPL=Q5 (highest) + Volatility=Q5 (highest)", (lpl_q == "Q5") & (vol_q == "Q5"))]
    lines.append("| Cell | n | Mean | Median | Win Rate | Std | P05 | P25 | P75 | P95 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for label, mask in cells:
        s = horizon_stats(fwd[mask])
        if not s:
            continue
        lines.append(f"| {label} | {s['n']:,} | {s['mean']*100:+.4f}% | {s['median']*100:+.4f}% | "
                      f"{s['win_rate']*100:.1f}% | {s['std']*100:.3f}% | {s['p05']*100:+.2f}% | "
                      f"{s['p25']*100:+.2f}% | {s['p75']*100:+.2f}% | {s['p95']*100:+.2f}% |")
    lines.append("\nIf mean and median are close and P25/P75 straddle the median symmetrically-ish, "
                 "the shift is broad. A mean far from the median (as v1 found for one bb_position bin) "
                 "would flag outlier-driven contamination instead.\n")
    return "\n".join(lines) + "\n"


# ── 4. Multi-horizon comparison for the extreme cells ───────────────────

def section_4(df: pd.DataFrame, lpl_q: pd.Series, vol_q: pd.Series) -> str:
    lines = ["## 4. Multi-horizon comparison — extreme cells\n",
             "Does the effect already show at 15m and persist through 4h "
             "(a real, early-forming state effect), or does it only "
             "appear at longer horizons (could be something that only "
             "resolves slowly, or noise that coincidentally lines up at 4h)?\n"]
    cells = [("LPL=Q1 + Vol=Q5", (lpl_q == "Q1") & (vol_q == "Q5")),
             ("LPL=Q5 + Vol=Q5", (lpl_q == "Q5") & (vol_q == "Q5"))]
    lines.append("| Cell | Horizon | n | Median | Win Rate |")
    lines.append("|---|---|---|---|---|")
    for label, mask in cells:
        for h in HORIZONS:
            s = horizon_stats(df[f"fwd_{h}"][mask])
            if s:
                lines.append(f"| {label} | {h} | {s['n']:,} | {s['median']*100:+.4f}% | {s['win_rate']*100:.1f}% |")
    lines.append("")
    return "\n".join(lines) + "\n"


# ── 5. Time stability ────────────────────────────────────────────────────

def section_5(df: pd.DataFrame, lpl_q: pd.Series, vol_q: pd.Series) -> str:
    lines = ["## 5. Time stability — extreme cells (4h)\n"]
    cells = [("LPL=Q1 + Vol=Q5", (lpl_q == "Q1") & (vol_q == "Q5")),
             ("LPL=Q5 + Vol=Q5", (lpl_q == "Q5") & (vol_q == "Q5"))]
    fwd = df["fwd_4h"]
    for label, mask in cells:
        lines.append(f"### {label}\n")
        lines.append("| Year | n | Median | Win Rate |")
        lines.append("|---|---|---|---|")
        medians = []
        for yr in sorted(df["year"].unique()):
            m = mask & (df["year"] == yr)
            s = horizon_stats(fwd[m])
            if s and s["n"] >= 20:
                medians.append(s["median"])
                lines.append(f"| {yr} | {s['n']:,} | {s['median']*100:+.4f}% | {s['win_rate']*100:.1f}% |")
        if medians:
            signs = [1 if m > 0 else -1 for m in medians]
            consistent = sum(1 for x in signs if x == signs[0])
            lines.append(f"\nSign consistency: {consistent}/{len(signs)} years\n")
    return "\n".join(lines) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--include-live", action="store_true")
    p.add_argument("--historical", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "reports", "discovery_v5.md"))
    args = p.parse_args()

    paths = [args.historical]
    if args.include_live:
        paths.append(config.CANDIDATES_FILE)

    print("Loading candidates...")
    df = load_candidates(paths)
    df = add_local_price_location(df)
    print(f"Loaded {len(df):,} candidates, {df['timestamp'].min()} -> {df['timestamp'].max()}")

    lpl_q = quintile_bin(df["local_price_location"])
    vol_q = quintile_bin(df["volatility_atr_norm"])
    print("LPL quintile counts:", lpl_q.value_counts().to_dict())
    print("Volatility quintile counts:", vol_q.value_counts().to_dict())

    print("Section 1: quintile resolution across horizons...")
    md1 = section_1(df, lpl_q, vol_q)
    print("Section 2: volatility level vs. change...")
    md2 = section_2(df, lpl_q, vol_q)
    print("Section 3: full outcome distribution for extreme cells...")
    md3 = section_3(df, lpl_q, vol_q)
    print("Section 4: multi-horizon comparison...")
    md4 = section_4(df, lpl_q, vol_q)
    print("Section 5: time stability...")
    md5 = section_5(df, lpl_q, vol_q)

    header = (
        f"# Discovery Analysis Report v5 — Local Price Location x Volatility deep dive\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()} from {', '.join(paths)}.\n\n"
        f"Focused follow-up to v4's strongest finding (LPL x volatility "
        f"interaction, residual/spread ratio 30%). Deliberately not "
        f"crossing more dimensions — per the project discussion, "
        f"understanding this one relationship in depth first.\n\n---\n\n"
    )
    full = header + md1 + "\n---\n\n" + md2 + "\n---\n\n" + md3 + "\n---\n\n" + md4 + "\n---\n\n" + md5

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
