"""
Discovery Analysis Report v2 — redundancy and independent information
content of the "local price location" dimensions that v1 flagged as the
strongest, most time-stable effects: bb_position, range_position_20,
range_position_50, vwap_distance.

v1's open question: are these four independent information sources, or do
they mostly measure the same latent variable (something like "where is
price relative to its own recent local structure")?

  1. Correlation matrix — Pearson (linear) and Spearman (monotonic) among
     the four core dimensions, plus trend_ema_cross_norm/momentum_rsi
     (v1's next-strongest effects) for context.
  2. Latent factor (PCA) — if one principal component explains most of the
     variance among the four, that's direct evidence for a single latent
     "local price location" factor rather than four separate signals.
  3. Redundancy: incremental R² — raw-sample-level (not decile-aggregated
     like v1's shape classification, which inflates apparent correlation
     by averaging out noise) OLS R² of forward_return_4h/1h on each
     dimension alone, then on growing combinations, to see whether adding
     more of these dimensions actually buys additional explanatory power
     or just restates what's already there.
  4. Residual analysis — for each of the four, the part NOT explained by
     the other three (an OLS residual), re-run through the exact same
     median-binned decile / shape / year-stability machinery v1 used. If a
     residual still shows a real, time-stable effect, that dimension
     carries independent information beyond the other three; if not, it's
     redundant with them.

Usage:
    .venv/bin/python scripts/discovery_v2.py
    .venv/bin/python scripts/discovery_v2.py --include-live
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from discovery_report import (
    load_candidates, horizon_stats, bin_dimension, dimension_table,
    format_dim_table, classify_shape, top_bottom_bin_spread_by_year,
    HORIZONS, N_BINS,
)
import mst_config as config

CORE_DIMS = ["bb_position", "range_position_20", "range_position_50", "vwap_distance"]
CONTEXT_DIMS = ["trend_ema_cross_norm", "momentum_rsi"]
ALL_DIMS = CORE_DIMS + CONTEXT_DIMS


# ── 1. Correlation matrix ───────────────────────────────────────────────

def section_1(df: pd.DataFrame) -> str:
    lines = ["## 1. Correlation matrix\n",
             "Pairwise correlation among the state dimensions themselves "
             "(not vs. forward return) — do they move together (redundant) "
             "or independently?\n"]
    sub = df[ALL_DIMS].dropna()
    lines.append(f"n = {len(sub):,}\n")

    lines.append("**Pearson (linear):**\n")
    pearson = sub.corr(method="pearson")
    lines.append(_corr_table(pearson))

    lines.append("\n**Spearman (monotonic — more appropriate given v1's "
                  "linear/monotonic-but-not-necessarily-straight-line shapes):**\n")
    spearman = sub.corr(method="spearman")
    lines.append(_corr_table(spearman))

    return "\n".join(lines) + "\n"


def _corr_table(corr: pd.DataFrame) -> str:
    cols = list(corr.columns)
    out = ["| | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for r in cols:
        vals = " | ".join(f"{corr.loc[r, c]:+.3f}" for c in cols)
        out.append(f"| **{r}** | {vals} |")
    return "\n".join(out) + "\n"


# ── 2. PCA / latent factor ──────────────────────────────────────────────

def pca(df: pd.DataFrame, cols: list) -> tuple:
    sub = df[cols].dropna()
    X = sub.values
    mu, sigma = X.mean(axis=0), X.std(axis=0)
    Xs = (X - mu) / sigma
    cov = np.cov(Xs, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals, eigvecs = eigvals[order], eigvecs[:, order]
    explained = eigvals / eigvals.sum()
    return explained, eigvecs, len(sub)


def section_2(df: pd.DataFrame) -> str:
    lines = ["## 2. Latent factor (PCA)\n",
             "Principal-component decomposition of the four core dimensions "
             "(standardized). If PC1 alone explains most of the variance, "
             "that's direct evidence they're mostly one latent \"local "
             "price location\" factor, not four independent signals.\n"]
    explained, eigvecs, n = pca(df, CORE_DIMS)
    lines.append(f"n = {n:,}\n")
    lines.append("| Component | Explained variance | Cumulative |")
    lines.append("|---|---|---|")
    cum = 0.0
    for i, ev in enumerate(explained):
        cum += ev
        lines.append(f"| PC{i+1} | {ev*100:.1f}% | {cum*100:.1f}% |")

    lines.append("\n**PC1 loadings** (how much each dimension contributes, "
                  "sign-normalized so bb_position loads positive):\n")
    pc1 = eigvecs[:, 0]
    if pc1[CORE_DIMS.index("bb_position")] < 0:
        pc1 = -pc1
    lines.append("| Dimension | PC1 loading |")
    lines.append("|---|---|")
    for dim, loading in zip(CORE_DIMS, pc1):
        lines.append(f"| {dim} | {loading:+.3f} |")

    verdict = ("PC1 explains a large majority of the variance — strong "
                "evidence for a single shared latent factor."
                if explained[0] > 0.7 else
                "PC1 explains a moderate majority — a dominant shared "
                "factor, but with meaningful independent variance left over."
                if explained[0] > 0.5 else
                "PC1 does not dominate — these look like more than one "
                "independent information source.")
    lines.append(f"\n**Verdict:** {verdict}\n")
    return "\n".join(lines) + "\n"


# ── 3. Redundancy: incremental R² ───────────────────────────────────────

def ols_r2(df: pd.DataFrame, x_cols: list, y_col: str):
    sub = df[x_cols + [y_col]].dropna()
    if len(sub) < 200:
        return None
    X = np.column_stack([np.ones(len(sub))] + [sub[c].values for c in x_cols])
    y = sub[y_col].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    y_pred = X @ beta
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return r2, len(sub)


def section_3(df: pd.DataFrame) -> str:
    lines = ["## 3. Redundancy: incremental R²\n",
             "Raw-sample-level OLS R² (NOT decile-aggregated like v1's "
             "shape classification, which inflates apparent correlation by "
             "averaging out noise — these numbers will look small; that's "
             "normal for single-sample return prediction and expected. "
             "What matters here is the RELATIVE, incremental change as "
             "dimensions are added, not the absolute size).\n"]

    standalone = [
        (["bb_position"], "bb_position"),
        (["range_position_20"], "range_position_20"),
        (["range_position_50"], "range_position_50"),
        (["vwap_distance"], "vwap_distance"),
    ]
    # Each step's cols is the previous step's cols + one more dimension, so
    # the delta is a genuine "what did adding THIS dimension buy us" figure
    # — not a comparison against an unrelated baseline.
    chain = [
        (["bb_position"], "bb_position alone"),
        (["bb_position", "range_position_20"], "+ range_position_20"),
        (["bb_position", "range_position_20", "vwap_distance"], "+ vwap_distance"),
        (CORE_DIMS, "+ range_position_50 (= all four)"),
    ]

    for horizon in ["1h", "4h"]:
        lines.append(f"### Horizon: {horizon}\n")

        lines.append("**Standalone (each dimension alone, for reference):**\n")
        lines.append("| Dimension | n | R² |")
        lines.append("|---|---|---|")
        for cols, label in standalone:
            result = ols_r2(df, cols, f"fwd_{horizon}")
            if result is None:
                continue
            r2, n = result
            lines.append(f"| {label} | {n:,} | {r2:.5f} |")

        lines.append("\n**Incremental chain (each row adds one dimension to the row above):**\n")
        lines.append("| Combination | n | R² | Δ from adding this dimension |")
        lines.append("|---|---|---|---|")
        prev_r2 = None
        for cols, label in chain:
            result = ols_r2(df, cols, f"fwd_{horizon}")
            if result is None:
                continue
            r2, n = result
            delta_str = f"{r2 - prev_r2:+.5f}" if prev_r2 is not None else "—"
            lines.append(f"| {label} | {n:,} | {r2:.5f} | {delta_str} |")
            prev_r2 = r2
        lines.append("")
    return "\n".join(lines) + "\n"


# ── 4. Residual analysis ────────────────────────────────────────────────

def ols_residual(df: pd.DataFrame, x_col: str, control_cols: list) -> pd.Series:
    sub = df[[x_col] + control_cols].dropna()
    X = np.column_stack([np.ones(len(sub))] + [sub[c].values for c in control_cols])
    y = sub[x_col].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return pd.Series(resid, index=sub.index)


def section_4(df: pd.DataFrame) -> str:
    lines = ["## 4. Residual analysis — independent information content\n",
             "For each core dimension, the residual after regressing it on "
             "the OTHER three (\"the part of X not explained by the "
             "others\"), run through the same median-binned decile / "
             "shape / year-stability check v1 used on the raw dimensions. "
             "A residual that still shows a real, time-stable effect means "
             "that dimension carries information the other three don't; a "
             "flat/unstable residual means it's redundant with them.\n"]

    for target in CORE_DIMS:
        controls = [c for c in CORE_DIMS if c != target]
        resid = ols_residual(df, target, controls)
        col_name = f"resid_{target}"
        work = df.copy()
        work[col_name] = np.nan
        work.loc[resid.index, col_name] = resid.values

        rows_4h = dimension_table(work, col_name, False, "4h")
        if len(rows_4h) < 3:
            lines.append(f"### {target} | resid after {', '.join(controls)}\n\nInsufficient bins, skipped.\n")
            continue
        medians = [r["median"] for r in rows_4h]
        spread = max(medians) - min(medians)
        shape = classify_shape(medians)

        by_year = top_bottom_bin_spread_by_year(work, col_name, False, "4h")
        signs = [1 if v["spread"] > 0 else -1 for v in by_year.values()]
        consistent = sum(1 for s in signs if s == signs[0]) if signs else 0
        stability = f"{consistent}/{len(signs)} years same sign" if signs else "n/a"

        # Compare to the RAW (non-residualized) dimension's own spread/shape
        # for a direct before/after picture.
        raw_rows = dimension_table(df, target, False, "4h")
        raw_medians = [r["median"] for r in raw_rows]
        raw_spread = max(raw_medians) - min(raw_medians)

        lines.append(f"### {target} | residual after controlling for {', '.join(controls)}\n")
        lines.append(f"- Raw dimension 4h median spread: {raw_spread*100:+.4f}%")
        lines.append(f"- **Residual** 4h median spread: {spread*100:+.4f}% "
                      f"({spread/raw_spread*100:.0f}% of raw, if raw != 0)")
        lines.append(f"- Residual shape: {shape}")
        lines.append(f"- Residual time stability: {stability}\n")
        lines.append(format_dim_table(f"{target} residual", rows_4h, "4h"))

    return "\n".join(lines) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--include-live", action="store_true")
    p.add_argument("--historical", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "reports", "discovery_v2.md"))
    args = p.parse_args()

    paths = [args.historical]
    if args.include_live:
        paths.append(config.CANDIDATES_FILE)

    print("Loading candidates...")
    df = load_candidates(paths)
    print(f"Loaded {len(df):,} candidates, {df['timestamp'].min()} -> {df['timestamp'].max()}")

    print("Section 1: correlation matrix...")
    md1 = section_1(df)
    print("Section 2: PCA / latent factor...")
    md2 = section_2(df)
    print("Section 3: redundancy (incremental R²)...")
    md3 = section_3(df)
    print("Section 4: residual analysis...")
    md4 = section_4(df)

    header = (
        f"# Discovery Analysis Report v2 — redundancy and independent information\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()} from {', '.join(paths)}.\n\n"
        f"Follow-up to v1's headline finding: bb_position, range_position_20, "
        f"range_position_50, and vwap_distance all showed a strong, "
        f"time-stable relationship to forward returns. Open question: are "
        f"these four independent information sources, or do they mostly "
        f"measure the same latent \"local price location\" variable?\n\n---\n\n"
    )
    full = header + md1 + "\n---\n\n" + md2 + "\n---\n\n" + md3 + "\n---\n\n" + md4

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
