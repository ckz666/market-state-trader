"""
Discovery v11 — are the new 15m/1m candidates from discovery_v10 (which
each showed a clean, monotone, LPL-like contrarian pattern) independent
information, or just a faster/noisier copy of the already-frozen LPL
factor?

Per the project discussion: this mirrors the correlation/PCA check
discovery_v2 originally ran on bb_position vs. vwap_distance before
combining them into LPL. Two steps:

  A. Correlation matrix + PCA (cheap, linear-redundancy check) between
     `local_price_location` (frozen LPL) and four v10 candidates:
     `short_term_rsi_15m`, `short_term_range_position_20_15m`,
     `micro_return_5m`, and `short_term_direction_15m` (numerically
     encoded bearish=-1/neutral=0/bullish=+1).
  B. Conditional incremental test (the real question): for each
     candidate, a LPL-quintile x candidate-quintile(Q1 vs Q5 only) cross-
     tab at Vol=Q5 (decision_rule_v1's traded regime), 4h horizon. If the
     candidate still separates outcomes WITHIN every LPL quintile, it
     carries information beyond LPL. If the spread collapses once LPL is
     held fixed, it was just a correlated proxy.

Purely descriptive; does not change decision_rule_v1 or propose a rule.
Same frozen LPL/quintile-edge parameters as hypothesis_validation.py.
Discovery only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v11_15m_lpl_correlation.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import discovery_report as dr
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile

MIN_CELL_N = 15
CANDIDATE_FIELDS = ["short_term_rsi_15m", "short_term_range_position_20_15m", "micro_return_5m"]
NEW_DIMENSIONS = [
    ("short_term_rsi_15m",              ("short_term_15m", "rsi"), False),
    ("short_term_range_position_20_15m", ("short_term_15m", "range_position_20"), False),
    ("micro_return_5m",                  ("micro_1m", "return_5m"), False),
    ("short_term_direction_15m",         ("short_term_15m", "direction"), True),
]


def section_correlation(df: pd.DataFrame) -> str:
    cols = ["local_price_location"] + CANDIDATE_FIELDS + ["short_term_direction_15m_enc"]
    corr = df[cols].corr(method="pearson")
    lines = [
        "## A. Correlation matrix (Pearson) with frozen LPL\n",
        "`short_term_direction_15m_enc`: bearish=-1, neutral=0, bullish=+1.\n",
        "| | " + " | ".join(cols) + " |",
        "|---|" + "---|" * len(cols),
    ]
    for c1 in cols:
        row = [c1] + [f"{corr.loc[c1, c2]:+.3f}" for c2 in cols]
        lines.append("| " + " | ".join(row) + " |")

    # simple PCA on the standardized continuous set (LPL + 3 continuous candidates)
    cont_cols = ["local_price_location"] + CANDIDATE_FIELDS
    z = (df[cont_cols] - df[cont_cols].mean()) / df[cont_cols].std()
    cov = np.cov(z.values, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals, eigvecs = eigvals[order], eigvecs[:, order]
    explained = eigvals / eigvals.sum()
    lines.append("\n**PCA on standardized [LPL, " + ", ".join(CANDIDATE_FIELDS) + "]:**\n")
    lines.append(f"- PC1 explains {explained[0]*100:.1f}% of variance (loadings: " +
                 ", ".join(f"{c}={eigvecs[i,0]:+.3f}" for i, c in enumerate(cont_cols)) + ")")
    lines.append(f"- PC2 explains {explained[1]*100:.1f}% of variance (loadings: " +
                 ", ".join(f"{c}={eigvecs[i,1]:+.3f}" for i, c in enumerate(cont_cols)) + ")")
    lines.append(
        "\nIf PC1 alone explained the large majority of variance with all "
        "loadings the same sign, these fields would mostly be measuring "
        "the same thing (as bb_position/vwap_distance did before "
        "collapsing into LPL). If variance is spread across multiple "
        "components, they carry more independent information.\n"
    )
    return "\n".join(lines) + "\n"


def section_incremental(df: pd.DataFrame) -> str:
    lines = ["## B. Conditional incremental test: LPL quintile x candidate (Q1 vs Q5), Vol=Q5, 4h\n"]
    vol_q5 = df[df["vol_q"] == "Q5"]
    for field in CANDIDATE_FIELDS + ["short_term_direction_15m"]:
        lines.append(f"\n### {field}\n")
        if field == "short_term_direction_15m":
            cand_q = vol_q5[field]
            low_label, high_label = "bearish", "bullish"
        else:
            try:
                cand_binned, cand_edges = pd.qcut(vol_q5[field], 5, labels=False, retbins=True, duplicates="drop")
            except ValueError:
                lines.append("(could not quintile this field -- too few unique values)\n")
                continue
            cand_q = cand_binned.map({0: "Q1", 4: "Q5"})
            low_label, high_label = "Q1", "Q5"
        lines.append(f"| LPL | n ({low_label}) | {low_label} median | n ({high_label}) | {high_label} median | Spread |")
        lines.append("|---|---|---|---|---|---|")
        for lpl_q in ["Q1", "Q2", "Q3", "Q4", "Q5"]:
            sub = vol_q5[vol_q5["lpl_q"] == lpl_q]
            low = sub.loc[cand_q.reindex(sub.index) == low_label, "fwd_4h"]
            high = sub.loc[cand_q.reindex(sub.index) == high_label, "fwd_4h"]
            n_low, n_high = len(low), len(high)
            if n_low < MIN_CELL_N or n_high < MIN_CELL_N:
                lines.append(f"| {lpl_q} | {n_low} | n too few | {n_high} | n too few | - |")
                continue
            spread = low.median() - high.median()
            lines.append(
                f"| {lpl_q} | {n_low} | {low.median()*100:+.4f}% | {n_high} | {high.median()*100:+.4f}% | {spread*100:+.4f}% |"
            )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/reports/discovery_v11_15m_lpl_correlation.md")
    args = p.parse_args()

    print("Loading candidates (extended dimension set)...")
    dr.DIMENSIONS = dr.DIMENSIONS + NEW_DIMENSIONS
    df_all = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df_all[df_all["timestamp"] < cutoff].copy()  # Discovery only

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    disc["lpl_q"] = apply_quintile(disc["local_price_location"], lpl_edges)
    disc["vol_q"] = apply_quintile(disc["volatility_atr_norm"], vol_edges)

    dir_map = {"bearish": -1, "neutral": 0, "bullish": 1}
    disc["short_term_direction_15m_enc"] = disc["short_term_direction_15m"].map(dir_map)

    needed = ["local_price_location"] + CANDIDATE_FIELDS + ["short_term_direction_15m_enc"]
    disc_clean = disc.dropna(subset=needed).copy()
    print(f"n candidates with all fields present: {len(disc_clean):,}")

    body = section_correlation(disc_clean) + "\n---\n\n" + section_incremental(disc_clean)

    header = (
        "# Discovery v11 — do the new 15m/1m candidates add information beyond LPL?\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Purely descriptive; does not change decision_rule_v1. Mirrors "
        "discovery_v2's original bb_position/vwap_distance correlation "
        "check, applied to discovery_v10's standout 15m/1m candidates "
        "(`short_term_rsi_15m`, `short_term_range_position_20_15m`, "
        "`micro_return_5m`, `short_term_direction_15m`). Same frozen "
        "LPL/quintile-edge parameters as hypothesis_validation.py. "
        "Discovery only; 2026 untouched. Cells with n < "
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
