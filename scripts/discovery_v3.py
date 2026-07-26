"""
Discovery Analysis Report v3 — bb_position x vwap_distance as a 2D state
map, not a combined score.

v2's conclusion: bb_position and vwap_distance together capture most of
the "local price location" latent factor's information (the incremental-R²
chain jumped 15x when vwap_distance was added to bb_position, while the
two range_position_* dimensions added almost nothing). Open question this
answers: do the two combine PURELY ADDITIVELY (so a one-dimensional
"local price score" would lose nothing), or is there a genuine
INTERACTION — does "bb high + vwap high" mean something different from
what you'd predict just from "bb high" and "vwap high" separately?

  1. 2D grid — bb_position x vwap_distance tertiles (low/mid/high), full
     distribution per cell (n, mean, median, win rate, std) for every
     horizon (15m/30m/1h/4h).
  2. Additive-vs-interaction test — classic two-way decomposition at 4h:
     predicted_cell = grand_median + row_effect + col_effect. A residual
     far from zero means the combination isn't just "sum of its parts."
  3. Time stability of the most informative cells (corners + the
     high/low vs. low/high "mixed" cells) across 2020-2026.

Usage:
    .venv/bin/python scripts/discovery_v3.py
    .venv/bin/python scripts/discovery_v3.py --include-live
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

BIN_LABELS = ["low", "mid", "high"]


# ── Binning ──────────────────────────────────────────────────────────────

def tertile_bin(s: pd.Series) -> pd.Series:
    binned = pd.qcut(s, 3, labels=BIN_LABELS, duplicates="drop")
    return binned.astype(str).where(s.notna())


def build_grid(df: pd.DataFrame, horizon: str, bb_bin: pd.Series, vwap_bin: pd.Series) -> pd.DataFrame:
    fwd = df[f"fwd_{horizon}"]
    rows = []
    for bb in BIN_LABELS:
        for vw in BIN_LABELS:
            mask = (bb_bin == bb) & (vwap_bin == vw)
            s = horizon_stats(fwd[mask])
            if s:
                rows.append({"bb": bb, "vwap": vw, **s})
    return pd.DataFrame(rows)


# ── Section 1: grid tables ──────────────────────────────────────────────

def format_grid_table(grid: pd.DataFrame, horizon: str) -> str:
    out = [f"**{horizon}**\n"]
    out.append("| bb_position | vwap_distance | n | Mean | Median | Win Rate | Std |")
    out.append("|---|---|---|---|---|---|---|")
    for bb in BIN_LABELS:
        for vw in BIN_LABELS:
            row = grid[(grid["bb"] == bb) & (grid["vwap"] == vw)]
            if row.empty:
                continue
            r = row.iloc[0]
            out.append(f"| {bb} | {vw} | {r['n']:,.0f} | {r['mean']*100:+.4f}% | "
                        f"{r['median']*100:+.4f}% | {r['win_rate']*100:.1f}% | {r['std']*100:.3f}% |")
    return "\n".join(out) + "\n"


def section_1(df: pd.DataFrame, bb_bin: pd.Series, vwap_bin: pd.Series) -> tuple[str, dict]:
    lines = ["## 1. 2D grid: bb_position x vwap_distance\n",
             "Tertiles (low/mid/high, ~1/3 of samples each) on both axes, "
             "full distribution per cell, every horizon.\n"]
    grids = {}
    for h in HORIZONS:
        grid = build_grid(df, h, bb_bin, vwap_bin)
        grids[h] = grid
        lines.append(format_grid_table(grid, h))
    return "\n".join(lines) + "\n", grids


# ── Section 2: additive vs. interaction ─────────────────────────────────

# bb_position and vwap_distance are strongly correlated (Spearman 0.90, per
# v2) — their tertile cross-tab is NOT close to balanced: 3 of 9 cells
# (low/low, mid/mid, high/high) hold ~77% of all samples, while the two
# "disagreeing" corners (bb=low & vwap=high, bb=high & vwap=low) have only
# ~11-16 samples each. Those two cells are statistically meaningless on
# their own but, unguarded, dominate a two-way decomposition's residuals —
# excluded from row/col effects and the interaction verdict below.
MIN_CELL_N = 100


def additive_decomposition(grid: pd.DataFrame, metric: str = "median"):
    """Classic unweighted two-way decomposition: predicted_cell = grand +
    row_effect + col_effect, computed only from cells with n >= MIN_CELL_N
    (see module note). Returns (grand, row_effects, col_effects, actual,
    predicted, residual, n_pivot) all indexed by BIN_LABELS; low-n cells in
    actual/residual are NaN."""
    pivot = grid.pivot(index="bb", columns="vwap", values=metric).reindex(index=BIN_LABELS, columns=BIN_LABELS)
    n_pivot = grid.pivot(index="bb", columns="vwap", values="n").reindex(index=BIN_LABELS, columns=BIN_LABELS)
    reliable = pivot.where(n_pivot >= MIN_CELL_N)

    grand = np.nanmean(reliable.values)
    row_effects = reliable.mean(axis=1, skipna=True) - grand
    col_effects = reliable.mean(axis=0, skipna=True) - grand
    predicted = pd.DataFrame(
        {c: grand + row_effects + col_effects[c] for c in BIN_LABELS}, index=BIN_LABELS)
    residual = reliable - predicted
    return grand, row_effects, col_effects, reliable, predicted, residual, n_pivot


def format_matrix(m: pd.DataFrame, n_pivot: pd.DataFrame = None, fmt="{:+.4f}%", scale=100) -> str:
    out = ["| bb \\ vwap | " + " | ".join(BIN_LABELS) + " |", "|---|" + "---|" * len(BIN_LABELS)]
    for bb in BIN_LABELS:
        cells = []
        for c in BIN_LABELS:
            v = m.loc[bb, c]
            if pd.isna(v):
                n = int(n_pivot.loc[bb, c]) if n_pivot is not None else "?"
                cells.append(f"n/a (n={n}, too few)")
            else:
                cells.append(fmt.format(v * scale))
        out.append(f"| **{bb}** | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def section_2(grids: dict) -> str:
    lines = ["## 2. Additive vs. interaction (4h, median)\n",
             "predicted_cell = grand_median + row_effect + col_effect "
             "(what you'd expect if bb_position and vwap_distance acted "
             "purely independently/additively). residual = actual - "
             "predicted: far from zero means the specific COMBINATION "
             "carries information beyond each dimension's separate "
             "marginal effect.\n",
             f"**Caveat:** cells with n < {MIN_CELL_N} are excluded from "
             "this decomposition and marked n/a below — bb_position and "
             "vwap_distance are correlated enough (Spearman 0.90) that the "
             "two \"disagreeing\" corners (bb low + vwap high, bb high + "
             "vwap low) have only ~11-16 samples in this dataset and would "
             "otherwise dominate the residuals with noise, not signal.\n"]
    grid = grids["4h"]
    grand, row_eff, col_eff, actual, predicted, residual, n_pivot = additive_decomposition(grid, "median")

    lines.append(f"Grand median (reliable cells only): {grand*100:+.4f}%\n")
    lines.append("**Row effects (bb_position, averaged over vwap):**\n")
    lines.append("| bb_position | effect |")
    lines.append("|---|---|")
    for bb in BIN_LABELS:
        lines.append(f"| {bb} | {row_eff[bb]*100:+.4f}% |")

    lines.append("\n**Column effects (vwap_distance, averaged over bb):**\n")
    lines.append("| vwap_distance | effect |")
    lines.append("|---|---|")
    for vw in BIN_LABELS:
        lines.append(f"| {vw} | {col_eff[vw]*100:+.4f}% |")

    lines.append(f"\n**Cell sample sizes** (n < {MIN_CELL_N} excluded above):\n")
    lines.append(format_matrix(n_pivot, fmt="{:.0f}", scale=1))
    lines.append("\n**Actual median return per cell:**\n")
    lines.append(format_matrix(actual, n_pivot))
    lines.append("\n**Predicted (additive model):**\n")
    lines.append(format_matrix(predicted, n_pivot))
    lines.append("\n**Residual (actual − predicted — the interaction signal):**\n")
    lines.append(format_matrix(residual, n_pivot))

    resid_vals = residual.values[~np.isnan(residual.values)]
    row_spread = row_eff.max() - row_eff.min()
    col_spread = col_eff.max() - col_eff.min()
    if len(resid_vals) == 0:
        lines.append("\n**Verdict:** Not enough reliable cells to assess.\n")
        return "\n".join(lines) + "\n"

    max_resid = np.abs(resid_vals).max()
    max_idx = np.unravel_index(np.nanargmax(np.abs(residual.values)), residual.shape)
    max_cell = (BIN_LABELS[max_idx[0]], BIN_LABELS[max_idx[1]])
    verdict = (
        f"Among the {len(resid_vals)} reliable (n>={MIN_CELL_N}) cells, largest residual: "
        f"{residual.loc[max_cell[0], max_cell[1]]*100:+.4f}% at bb={max_cell[0]}/vwap={max_cell[1]}. "
        f"Row (bb) spread: {row_spread*100:.4f}%, column (vwap) spread: {col_spread*100:.4f}%. "
    )
    if max_resid < 0.25 * max(row_spread, col_spread):
        verdict += "Residuals are small relative to the main effects — the two dimensions look mostly ADDITIVE."
    else:
        verdict += "Residuals are large relative to the main effects — there IS a genuine interaction, not just additive."
    verdict += (f" (Note: the two low-n corner cells — bb=low/vwap=high, bb=high/vwap=low — are excluded "
                f"from this verdict entirely; they cannot be assessed reliably with only ~11-16 samples.)")
    lines.append(f"\n**Verdict:** {verdict}\n")

    return "\n".join(lines) + "\n"


# ── Section 3: time stability of key cells ──────────────────────────────

def cell_stats_by_year(df: pd.DataFrame, bb_bin: pd.Series, vwap_bin: pd.Series, bb: str, vw: str, horizon: str):
    fwd = df[f"fwd_{horizon}"]
    mask = (bb_bin == bb) & (vwap_bin == vw)
    out = {}
    for yr in sorted(df["year"].unique()):
        m = mask & (df["year"] == yr)
        s = horizon_stats(fwd[m])
        if s and s["n"] >= 20:
            out[yr] = s
    return out


def section_3(df: pd.DataFrame, bb_bin: pd.Series, vwap_bin: pd.Series) -> str:
    lines = ["## 3. Time stability of the key cells (4h)\n",
             "Corners (both dimensions agree) and mixed cells (dimensions "
             "disagree) — if bb and vwap ever point in different "
             "directions, the mixed cells are where that would show up.\n"]
    cells = [("low", "low", "both low"), ("high", "high", "both high"),
             ("high", "low", "bb high, vwap low"), ("low", "high", "bb low, vwap high")]
    for bb, vw, label in cells:
        by_year = cell_stats_by_year(df, bb_bin, vwap_bin, bb, vw, "4h")
        if not by_year:
            lines.append(f"### {label} (bb={bb}, vwap={vw})\n")
            lines.append("Skipped — this cell has too few total samples for any year to reach "
                         "n>=20 (see Section 2's caveat: bb_position and vwap_distance are "
                         "correlated enough that this \"disagreeing\" combination is rare).\n")
            continue
        medians = [s["median"] for s in by_year.values()]
        signs = [1 if m > 0 else -1 for m in medians]
        consistent = sum(1 for s in signs if s == signs[0])
        lines.append(f"### {label} (bb={bb}, vwap={vw})\n")
        lines.append(f"Sign consistency: {consistent}/{len(signs)} years\n")
        lines.append("| Year | n | Median | Win Rate |")
        lines.append("|---|---|---|---|")
        for yr, s in sorted(by_year.items()):
            lines.append(f"| {yr} | {s['n']:,} | {s['median']*100:+.4f}% | {s['win_rate']*100:.1f}% |")
        lines.append("")
    return "\n".join(lines) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--include-live", action="store_true")
    p.add_argument("--historical", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "reports", "discovery_v3.md"))
    args = p.parse_args()

    paths = [args.historical]
    if args.include_live:
        paths.append(config.CANDIDATES_FILE)

    print("Loading candidates...")
    df = load_candidates(paths)
    print(f"Loaded {len(df):,} candidates, {df['timestamp'].min()} -> {df['timestamp'].max()}")

    bb_bin = tertile_bin(df["bb_position"])
    vwap_bin = tertile_bin(df["vwap_distance"])
    print("bb_position tertile counts:", bb_bin.value_counts().to_dict())
    print("vwap_distance tertile counts:", vwap_bin.value_counts().to_dict())

    print("Section 1: 2D grid...")
    md1, grids = section_1(df, bb_bin, vwap_bin)
    print("Section 2: additive vs. interaction...")
    md2 = section_2(grids)
    print("Section 3: time stability of key cells...")
    md3 = section_3(df, bb_bin, vwap_bin)

    header = (
        f"# Discovery Analysis Report v3 — bb_position x vwap_distance as a 2D state map\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()} from {', '.join(paths)}.\n\n"
        f"Follow-up to v2: bb_position and vwap_distance together capture "
        f"most of the \"local price location\" latent factor's information. "
        f"This tests whether they combine additively or interact.\n\n---\n\n"
    )
    full = header + md1 + "\n---\n\n" + md2 + "\n---\n\n" + md3

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
