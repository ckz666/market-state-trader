"""
Discovery Analysis Report v4 — Local Price Location x orthogonal state
groups (Volatility, Exhaustion, Structure), tested pairwise, not combined.

v3's conclusion: bb_position and vwap_distance combine mostly additively
(a moderate, not dramatic, interaction) and both agreeing corners (both
low, both high) show 7/7-year sign-consistent effects — the strongest,
most robust finding of the whole discovery process so far.

This asks the next question, per the project discussion: does something
OTHER than local price location change what that effect means? Not:

    Local Price x Volatility x Exhaustion x Structure  (sparse, multiple
    testing, uninterpretable)

But three separate pairwise tests:

    v4A: Local Price Location x Volatility  (state_1h.volatility.atr_norm)
    v4B: Local Price Location x Exhaustion  (state_1h.exhaustion.cycle_strength)
    v4C: Local Price Location x Structure   (context_4h.structure_trend, categorical)

Local Price Location itself is defined as simply as v3's finding allows:
the average of bb_position and vwap_distance, each standardized (z-score)
first so they contribute roughly equally despite different raw scales —
NOT a fitted/weighted score, just the plain average of the two dimensions
v2/v3 showed carry the shared "local price location" signal.

Same methodology as v3 throughout: MIN_CELL_N guard before any
additive-vs-interaction decomposition or year-stability check (a v3
lesson — don't let sparse cells manufacture a fake interaction).

Usage:
    .venv/bin/python scripts/discovery_v4.py
    .venv/bin/python scripts/discovery_v4.py --include-live
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

MIN_CELL_N = 100
BIN_LABELS = ["low", "mid", "high"]


# ── Local Price Location ────────────────────────────────────────────────

def add_local_price_location(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    bb_z = (df["bb_position"] - df["bb_position"].mean()) / df["bb_position"].std()
    vwap_z = (df["vwap_distance"] - df["vwap_distance"].mean()) / df["vwap_distance"].std()
    df["local_price_location"] = (bb_z + vwap_z) / 2
    return df


def tertile_bin(s: pd.Series) -> pd.Series:
    binned = pd.qcut(s, 3, labels=BIN_LABELS, duplicates="drop")
    return binned.astype(str).where(s.notna())


# ── Generic 2D grid + additive/interaction + stability (shared by A/B/C) ──

def build_grid(df: pd.DataFrame, horizon: str, row_bin: pd.Series, col_bin: pd.Series,
                row_labels: list, col_labels: list) -> pd.DataFrame:
    fwd = df[f"fwd_{horizon}"]
    rows = []
    for r in row_labels:
        for c in col_labels:
            mask = (row_bin == r) & (col_bin == c)
            s = horizon_stats(fwd[mask])
            if s:
                rows.append({"row": r, "col": c, **s})
    return pd.DataFrame(rows)


def format_grid_table(grid: pd.DataFrame, horizon: str, row_labels: list, col_labels: list,
                       row_name: str, col_name: str) -> str:
    out = [f"**{horizon}**\n"]
    out.append(f"| {row_name} | {col_name} | n | Mean | Median | Win Rate | Std |")
    out.append("|---|---|---|---|---|---|---|")
    for r in row_labels:
        for c in col_labels:
            row = grid[(grid["row"] == r) & (grid["col"] == c)]
            if row.empty:
                continue
            v = row.iloc[0]
            out.append(f"| {r} | {c} | {v['n']:,.0f} | {v['mean']*100:+.4f}% | "
                        f"{v['median']*100:+.4f}% | {v['win_rate']*100:.1f}% | {v['std']*100:.3f}% |")
    return "\n".join(out) + "\n"


def additive_decomposition(grid: pd.DataFrame, row_labels: list, col_labels: list, metric: str = "median"):
    pivot = grid.pivot(index="row", columns="col", values=metric).reindex(index=row_labels, columns=col_labels)
    n_pivot = grid.pivot(index="row", columns="col", values="n").reindex(index=row_labels, columns=col_labels)
    reliable = pivot.where(n_pivot >= MIN_CELL_N)

    grand = np.nanmean(reliable.values)
    row_effects = reliable.mean(axis=1, skipna=True) - grand
    col_effects = reliable.mean(axis=0, skipna=True) - grand
    predicted = pd.DataFrame({c: grand + row_effects + col_effects[c] for c in col_labels}, index=row_labels)
    residual = reliable - predicted
    return grand, row_effects, col_effects, reliable, predicted, residual, n_pivot


def format_matrix(m: pd.DataFrame, row_labels: list, col_labels: list, n_pivot: pd.DataFrame = None,
                   fmt="{:+.4f}%", scale=100) -> str:
    out = ["| \\ | " + " | ".join(col_labels) + " |", "|---|" + "---|" * len(col_labels)]
    for r in row_labels:
        cells = []
        for c in col_labels:
            v = m.loc[r, c]
            if pd.isna(v):
                n = int(n_pivot.loc[r, c]) if n_pivot is not None else "?"
                cells.append(f"n/a (n={n})")
            else:
                cells.append(fmt.format(v * scale))
        out.append(f"| **{r}** | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def cell_stats_by_year(df: pd.DataFrame, row_bin: pd.Series, col_bin: pd.Series, r, c, horizon: str):
    fwd = df[f"fwd_{horizon}"]
    mask = (row_bin == r) & (col_bin == c)
    out = {}
    for yr in sorted(df["year"].unique()):
        m = mask & (df["year"] == yr)
        s = horizon_stats(fwd[m])
        if s and s["n"] >= 20:
            out[yr] = s
    return out


def run_pairwise_analysis(df: pd.DataFrame, row_col: str, row_labels: list, row_bin: pd.Series,
                           col_col: str, col_labels: list, col_bin: pd.Series,
                           title: str, row_name: str, col_name: str) -> str:
    lines = [f"## {title}\n"]

    total_n = row_bin.notna().sum()
    counts = pd.crosstab(row_bin, col_bin).reindex(index=row_labels, columns=col_labels)
    lines.append(f"Cell sample sizes (n={total_n:,} total, MIN_CELL_N={MIN_CELL_N}):\n")
    lines.append(format_matrix(counts, row_labels, col_labels, fmt="{:.0f}", scale=1))

    lines.append("\n### 2D grid (all horizons)\n")
    grids = {}
    for h in HORIZONS:
        grid = build_grid(df, h, row_bin, col_bin, row_labels, col_labels)
        grids[h] = grid
        lines.append(format_grid_table(grid, h, row_labels, col_labels, row_name, col_name))

    lines.append("\n### Additive vs. interaction (4h, median)\n")
    grand, row_eff, col_eff, actual, predicted, residual, n_pivot = additive_decomposition(
        grids["4h"], row_labels, col_labels)
    lines.append(f"Grand median (reliable cells only): {grand*100:+.4f}%\n")
    lines.append(f"**{row_name} effects:**\n")
    lines.append(f"| {row_name} | effect |\n|---|---|")
    for r in row_labels:
        v = row_eff[r]
        lines.append(f"| {r} | {v*100:+.4f}% |" if pd.notna(v) else f"| {r} | n/a |")
    lines.append(f"\n**{col_name} effects:**\n")
    lines.append(f"| {col_name} | effect |\n|---|---|")
    for c in col_labels:
        v = col_eff[c]
        lines.append(f"| {c} | {v*100:+.4f}% |" if pd.notna(v) else f"| {c} | n/a |")
    lines.append("\n**Actual median:**\n")
    lines.append(format_matrix(actual, row_labels, col_labels, n_pivot))
    lines.append("\n**Predicted (additive model):**\n")
    lines.append(format_matrix(predicted, row_labels, col_labels, n_pivot))
    lines.append("\n**Residual (interaction signal):**\n")
    lines.append(format_matrix(residual, row_labels, col_labels, n_pivot))

    resid_vals = residual.values[~np.isnan(residual.values)]
    if len(resid_vals) > 0:
        row_spread = row_eff.max() - row_eff.min()
        col_spread = col_eff.max() - col_eff.min()
        max_resid = np.abs(resid_vals).max()
        max_idx = np.unravel_index(np.nanargmax(np.abs(residual.values)), residual.shape)
        max_cell = (row_labels[max_idx[0]], col_labels[max_idx[1]])
        verdict = (f"{len(resid_vals)} reliable cells. Largest residual {residual.loc[max_cell[0],max_cell[1]]*100:+.4f}% "
                   f"at {row_name}={max_cell[0]}/{col_name}={max_cell[1]}. Row spread {row_spread*100:.4f}%, "
                   f"col spread {col_spread*100:.4f}%. ")
        ratio = max_resid / max(row_spread, col_spread) if max(row_spread, col_spread) > 0 else 0
        if ratio < 0.25:
            verdict += f"Residual/spread ratio {ratio*100:.0f}% — mostly ADDITIVE."
        else:
            verdict += f"Residual/spread ratio {ratio*100:.0f}% — a real interaction, {col_name} changes what {row_name} means."
        lines.append(f"\n**Verdict:** {verdict}\n")
    else:
        lines.append("\n**Verdict:** not enough reliable cells.\n")

    lines.append("\n### Time stability (4h) of reliable cells\n")
    for r in row_labels:
        for c in col_labels:
            if pd.isna(n_pivot.loc[r, c]) or n_pivot.loc[r, c] < MIN_CELL_N:
                continue
            by_year = cell_stats_by_year(df, row_bin, col_bin, r, c, "4h")
            if not by_year:
                continue
            medians = [s["median"] for s in by_year.values()]
            signs = [1 if m > 0 else -1 for m in medians]
            consistent = sum(1 for s in signs if s == signs[0])
            lines.append(f"- **{row_name}={r}, {col_name}={c}**: {consistent}/{len(signs)} years same sign "
                          f"(aggregate median {np.median(medians)*100:+.4f}%)")
    lines.append("")

    return "\n".join(lines) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--include-live", action="store_true")
    p.add_argument("--historical", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "reports", "discovery_v4.md"))
    args = p.parse_args()

    paths = [args.historical]
    if args.include_live:
        paths.append(config.CANDIDATES_FILE)

    print("Loading candidates...")
    df = load_candidates(paths)
    df = add_local_price_location(df)
    print(f"Loaded {len(df):,} candidates, {df['timestamp'].min()} -> {df['timestamp'].max()}")

    lpl_bin = tertile_bin(df["local_price_location"])
    print("local_price_location tertile counts:", lpl_bin.value_counts().to_dict())

    print("v4A: Local Price Location x Volatility...")
    vol_bin = tertile_bin(df["volatility_atr_norm"])
    md_a = run_pairwise_analysis(df, "local_price_location", BIN_LABELS, lpl_bin,
                                  "volatility_atr_norm", BIN_LABELS, vol_bin,
                                  "v4A. Local Price Location x Volatility (ATR norm)",
                                  "LPL", "Volatility")

    print("v4B: Local Price Location x Exhaustion...")
    exh_bin = tertile_bin(df["exhaustion_cycle_strength"])
    md_b = run_pairwise_analysis(df, "local_price_location", BIN_LABELS, lpl_bin,
                                  "exhaustion_cycle_strength", BIN_LABELS, exh_bin,
                                  "v4B. Local Price Location x Exhaustion (cycle strength)",
                                  "LPL", "Exhaustion")

    print("v4C: Local Price Location x Structure...")
    struct_labels = sorted(df["structure_trend_4h"].dropna().unique().tolist())
    struct_bin = df["structure_trend_4h"].astype(str).where(df["structure_trend_4h"].notna())
    md_c = run_pairwise_analysis(df, "local_price_location", BIN_LABELS, lpl_bin,
                                  "structure_trend_4h", struct_labels, struct_bin,
                                  "v4C. Local Price Location x Structure (4h trend)",
                                  "LPL", "Structure")

    header = (
        f"# Discovery Analysis Report v4 — Local Price Location x orthogonal state groups\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()} from {', '.join(paths)}.\n\n"
        f"local_price_location = average of z-scored bb_position and "
        f"z-scored vwap_distance (v2/v3 showed these two carry the shared "
        f"\"local price location\" signal; plain average, not a fitted "
        f"score). Three separate pairwise tests, not one combined "
        f"4-way grid (sparse data + multiple testing) — v4A vs. Volatility, "
        f"v4B vs. Exhaustion, v4C vs. Structure, asking which of these "
        f"changes what Local Price Location means the most.\n\n---\n\n"
    )
    full = header + md_a + "\n---\n\n" + md_b + "\n---\n\n" + md_c

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
