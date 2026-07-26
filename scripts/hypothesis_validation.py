"""
Hypothesis Validation — freezes the Discovery v1-v5 hypothesis exactly,
then tests it on genuinely unseen data. Per the project discussion: the
discovery phase is done; this is the point to stop searching the
historical data for a "better" state and instead check whether what was
already found survives contact with data none of the discovery decisions
were based on.

FROZEN HYPOTHESIS:
  Input:  Local Price Location (LPL) = avg(zscore(bb_position),
          zscore(vwap_distance)) x Volatility Level (volatility_atr_norm)
  Output: forward return distribution at 15m / 30m / 1h / 4h
  Claim:  LOW LPL -> systematically better forward-return distribution,
          HIGH LPL -> systematically worse. The magnitude of that
          difference scales continuously with volatility level (no
          threshold, no breakdown at the extreme — v5's finding), driven
          by volatility LEVEL not its recent rate of change.

METHOD — this is the part that matters: every parameter of the
transformation (z-score mean/std for LPL, quintile bin edges for both LPL
and volatility) is fit ONLY on the discovery period (2020-01-01 through
2025-12-31) and then applied AS-IS, frozen, to the validation period
(2026-01-01 onward). The validation period is never used to choose or
adjust anything — re-fitting bin edges on it would silently leak
information back into the "test" and defeat the point.

Usage:
    .venv/bin/python scripts/hypothesis_validation.py
    .venv/bin/python scripts/hypothesis_validation.py --cutoff 2026-01-01
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
import mst_config as config

Q_LABELS = ["Q1", "Q2", "Q3", "Q4", "Q5"]
MIN_CELL_N = 30  # lower than discovery's 100 — the validation period is much smaller by design


# ── Frozen transformation, fit ONLY on the discovery period ────────────

def fit_params(disc: pd.DataFrame) -> dict:
    return {
        "bb_mean": disc["bb_position"].mean(), "bb_std": disc["bb_position"].std(),
        "vwap_mean": disc["vwap_distance"].mean(), "vwap_std": disc["vwap_distance"].std(),
    }


def apply_lpl(df: pd.DataFrame, params: dict) -> pd.Series:
    bb_z = (df["bb_position"] - params["bb_mean"]) / params["bb_std"]
    vwap_z = (df["vwap_distance"] - params["vwap_mean"]) / params["vwap_std"]
    return (bb_z + vwap_z) / 2


def fit_quintile_edges(s: pd.Series) -> np.ndarray:
    _, edges = pd.qcut(s, 5, retbins=True, duplicates="drop")
    edges = edges.copy()
    edges[0], edges[-1] = -np.inf, np.inf  # frozen boundary: values beyond the
    # discovery period's observed range still fall in the extreme bin, rather
    # than becoming NaN — the validation period WILL contain values outside
    # what discovery saw, and dropping them would bias the test.
    return edges


def apply_quintile(s: pd.Series, edges: np.ndarray) -> pd.Series:
    return pd.cut(s, bins=edges, labels=Q_LABELS[:len(edges)-1], include_lowest=True).astype(str).where(s.notna())


# ── Reporting ────────────────────────────────────────────────────────────

def spread_table(df: pd.DataFrame, lpl_q: pd.Series, vol_q: pd.Series, horizon: str) -> list:
    """Same shape as discovery_v5's section 1 table: per volatility
    quintile, LPL=Q1 median, LPL=Q5 median, spread."""
    fwd = df[f"fwd_{horizon}"]
    rows = []
    for vq in Q_LABELS:
        m1 = (vol_q == vq) & (lpl_q == "Q1")
        m5 = (vol_q == vq) & (lpl_q == "Q5")
        s1, s5 = horizon_stats(fwd[m1]), horizon_stats(fwd[m5])
        if not s1 or not s5:
            continue
        rows.append({"vol_q": vq, "n1": s1["n"], "med1": s1["median"],
                      "n5": s5["n"], "med5": s5["median"], "spread": s5["median"] - s1["median"]})
    return rows


def format_spread_table(rows: list) -> str:
    out = ["| Volatility | n (Q1) | LPL=Q1 median | n (Q5) | LPL=Q5 median | Spread (Q5-Q1) |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['vol_q']} | {r['n1']:,} | {r['med1']*100:+.4f}% | {r['n5']:,} | "
                    f"{r['med5']*100:+.4f}% | {r['spread']*100:+.4f}% |")
    return "\n".join(out) + "\n"


def section_1(disc: pd.DataFrame, val: pd.DataFrame, disc_lpl_q, disc_vol_q, val_lpl_q, val_vol_q) -> str:
    lines = ["## 1. Discovery vs. Validation — LPL spread by volatility quintile\n",
             "Same table as discovery_v5 section 1, computed separately on "
             "each period using the frozen quintile edges. If the "
             "hypothesis is real (not overfit to the discovery period), "
             "the validation column should show the same sign and a "
             "similar growing-with-volatility pattern, even if the exact "
             "magnitudes differ.\n"]
    for h in HORIZONS:
        lines.append(f"### {h}\n")
        lines.append("**Discovery (2020-2025, in-sample):**\n")
        lines.append(format_spread_table(spread_table(disc, disc_lpl_q, disc_vol_q, h)))
        lines.append("**Validation (2026, out-of-sample, frozen bins):**\n")
        lines.append(format_spread_table(spread_table(val, val_lpl_q, val_vol_q, h)))
    return "\n".join(lines) + "\n"


def section_2(val: pd.DataFrame, val_lpl_q, val_vol_q) -> str:
    lines = ["## 2. Validation period — full outcome distribution, extreme cells (4h)\n",
             "Same check as discovery_v5 section 3, on validation data only.\n"]
    fwd = val["fwd_4h"]
    cells = [("LPL=Q1 (lowest) + Volatility=Q5 (highest)", (val_lpl_q == "Q1") & (val_vol_q == "Q5")),
             ("LPL=Q5 (highest) + Volatility=Q5 (highest)", (val_lpl_q == "Q5") & (val_vol_q == "Q5"))]
    lines.append("| Cell | n | Mean | Median | Win Rate | Std | P05 | P25 | P75 | P95 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for label, mask in cells:
        s = horizon_stats(fwd[mask])
        if not s:
            lines.append(f"| {label} | insufficient data | | | | | | | | |")
            continue
        flag = " ⚠ n<MIN_CELL_N" if s["n"] < MIN_CELL_N else ""
        lines.append(f"| {label}{flag} | {s['n']:,} | {s['mean']*100:+.4f}% | {s['median']*100:+.4f}% | "
                      f"{s['win_rate']*100:.1f}% | {s['std']*100:.3f}% | {s['p05']*100:+.2f}% | "
                      f"{s['p25']*100:+.2f}% | {s['p75']*100:+.2f}% | {s['p95']*100:+.2f}% |")
    return "\n".join(lines) + "\n"


def section_3(disc: pd.DataFrame, val: pd.DataFrame, disc_lpl_q, disc_vol_q, val_lpl_q, val_vol_q) -> str:
    lines = ["## 3. Verdict\n"]
    d_rows = spread_table(disc, disc_lpl_q, disc_vol_q, "4h")
    v_rows = spread_table(val, val_lpl_q, val_vol_q, "4h")
    d_by_q = {r["vol_q"]: r["spread"] for r in d_rows}
    v_by_q = {r["vol_q"]: r["spread"] for r in v_rows}

    lines.append("| Volatility | Discovery spread (4h) | Validation spread (4h) | Same sign? |")
    lines.append("|---|---|---|---|")
    same_sign_count, total = 0, 0
    for vq in Q_LABELS:
        d, v = d_by_q.get(vq), v_by_q.get(vq)
        if d is None or v is None:
            continue
        total += 1
        same = (d > 0) == (v > 0)
        same_sign_count += same
        lines.append(f"| {vq} | {d*100:+.4f}% | {v*100:+.4f}% | {'yes' if same else 'NO'} |")

    lines.append(f"\n**{same_sign_count}/{total} volatility quintiles: validation spread has the same "
                 f"sign as discovery.**\n")

    d_monotonic = all(d_by_q[Q_LABELS[i]] <= d_by_q[Q_LABELS[i-1]] for i in range(1, 5) if Q_LABELS[i] in d_by_q and Q_LABELS[i-1] in d_by_q)
    v_available = [vq for vq in Q_LABELS if vq in v_by_q]
    v_monotonic = all(v_by_q[v_available[i]] <= v_by_q[v_available[i-1]] for i in range(1, len(v_available)))

    lines.append(f"Discovery spread monotonically grows (more negative) with volatility: {d_monotonic}\n")
    lines.append(f"Validation spread monotonically grows (more negative) with volatility: {v_monotonic} "
                 f"(n is much smaller out-of-sample — {sum(r['n1']+r['n5'] for r in v_rows):,} samples "
                 f"total vs. discovery's {sum(r['n1']+r['n5'] for r in d_rows):,} — so some noise in the "
                 f"exact ordering is expected even if the hypothesis holds)\n")

    if same_sign_count == total:
        lines.append("**The core directional claim survives out-of-sample validation on 2026 data that "
                     "played no part in defining Local Price Location, its quintile boundaries, or the "
                     "volatility quintile boundaries.**\n")
    else:
        lines.append("**The direction did NOT hold in every volatility quintile out-of-sample — treat "
                     "the hypothesis as partially, not fully, confirmed.**\n")

    return "\n".join(lines) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01", help="ISO date splitting discovery (before) from validation (on/after)")
    p.add_argument("--historical", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "reports", "hypothesis_validation.md"))
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    print(f"Loaded {len(df):,} candidates, {df['timestamp'].min()} -> {df['timestamp'].max()}")

    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()
    val = df[df["timestamp"] >= cutoff].copy()
    print(f"Discovery (train) period: {len(disc):,} samples, {disc['timestamp'].min()} -> {disc['timestamp'].max()}")
    print(f"Validation (test) period: {len(val):,} samples, {val['timestamp'].min()} -> {val['timestamp'].max()}")

    # Fit everything on discovery only.
    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    val["local_price_location"] = apply_lpl(val, params)  # frozen params applied to validation

    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])

    disc_lpl_q = apply_quintile(disc["local_price_location"], lpl_edges)
    disc_vol_q = apply_quintile(disc["volatility_atr_norm"], vol_edges)
    val_lpl_q = apply_quintile(val["local_price_location"], lpl_edges)  # frozen edges applied to validation
    val_vol_q = apply_quintile(val["volatility_atr_norm"], vol_edges)

    print("Validation LPL quintile counts:", val_lpl_q.value_counts().to_dict())
    print("Validation volatility quintile counts:", val_vol_q.value_counts().to_dict())

    print("Section 1: discovery vs validation spread tables...")
    md1 = section_1(disc, val, disc_lpl_q, disc_vol_q, val_lpl_q, val_vol_q)
    print("Section 2: validation full outcome distribution...")
    md2 = section_2(val, val_lpl_q, val_vol_q)
    print("Section 3: verdict...")
    md3 = section_3(disc, val, disc_lpl_q, disc_vol_q, val_lpl_q, val_vol_q)

    header = (
        f"# Hypothesis Validation — frozen LPL x Volatility, tested out-of-sample\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        f"Discovery (train) period: {disc['timestamp'].min()} -> {disc['timestamp'].max()} "
        f"({len(disc):,} samples).\n\n"
        f"Validation (test) period: {val['timestamp'].min()} -> {val['timestamp'].max()} "
        f"({len(val):,} samples) — never used to fit LPL's z-score parameters or either "
        f"dimension's quintile bin edges.\n\n---\n\n"
    )
    full = header + md1 + "\n---\n\n" + md2 + "\n---\n\n" + md3

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
