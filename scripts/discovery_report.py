"""
Discovery Analysis Report v1 — answers, purely distributionally, no trading
rules and no single-score compression:

    Which concrete market states actually change the distribution of what
    happens in the next 15m / 30m / 1h / 4h — and is that effect real
    (stable across years/regimes) or noise from one BTC phase?

Sections (per project discussion):
  A. Dataset overview — samples, range, gaps, outcome coverage, regime mix
  B. Forward-return baseline per horizon — mean/median/std/win-rate/quantiles
  C. Univariate state-dimension analysis — binned return distributions,
     not just means: n/mean/median/win-rate/std/p25/p75/p05/p95 per bin
  D. Nonlinear pattern detection — linear / threshold / U-shaped, per
     dimension (this is why a linear "bb_position > 1.0" cutoff missed
     what turned out to be a two-sided effect)
  E. Time stability — the strongest effects from C/D, re-measured per year;
     an effect that flips sign or vanishes across years is not a finding
  F. Interactions — State A x State B (x a third dimension), only for the
     candidates that survived D/E

Usage:
    .venv/bin/python scripts/discovery_report.py
    .venv/bin/python scripts/discovery_report.py --include-live
    .venv/bin/python scripts/discovery_report.py --out data/reports/discovery_v1.md
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import mst_config as config

HORIZONS = ["15m", "30m", "1h", "4h"]

# (column label, path into market_state, is_categorical)
DIMENSIONS = [
    ("bb_position",                ("state_1h", "price_location", "bb_position"), False),
    ("range_position_20",          ("state_1h", "price_location", "range_position_20"), False),
    ("range_position_50",          ("state_1h", "price_location", "range_position_50"), False),
    ("vwap_distance",              ("state_1h", "price_location", "vwap_distance"), False),
    ("trend_direction",            ("state_1h", "trend", "direction"), True),
    ("trend_strength",             ("state_1h", "trend", "strength"), False),
    ("trend_adx",                  ("state_1h", "trend", "adx"), False),
    ("trend_ema_cross_norm",       ("state_1h", "trend", "ema_cross_norm"), False),
    ("momentum_direction",         ("state_1h", "momentum", "direction"), True),
    ("momentum_strength",          ("state_1h", "momentum", "strength"), False),
    ("momentum_rsi",               ("state_1h", "momentum", "rsi"), False),
    ("momentum_macd_norm",         ("state_1h", "momentum", "macd_norm"), False),
    ("volatility_regime",          ("state_1h", "volatility", "regime"), True),
    ("volatility_atr_norm",        ("state_1h", "volatility", "atr_norm"), False),
    ("volatility_prob_storm",      ("state_1h", "volatility", "prob_storm"), False),
    ("structure_trend_4h",         ("context_4h", "structure_trend"), True),
    ("regime_4h",                  ("context_4h", "regime"), True),
    ("trend_aligned_4h",           ("context_4h", "trend_aligned"), True),
    ("exhaustion_cycle_strength",  ("state_1h", "exhaustion", "cycle_strength"), False),
    ("exhaustion_divergence",      ("state_1h", "exhaustion", "trend_momentum_divergence"), False),
    ("exhaustion_upper_rejection", ("state_1h", "exhaustion", "upper_rejection"), False),
    ("exhaustion_lower_rejection", ("state_1h", "exhaustion", "lower_rejection"), False),
    ("candle_body_ratio",          ("micro_1m", "body_ratio"), False),
    ("candle_close_location",      ("micro_1m", "close_location"), False),
    ("candle_upper_wick",          ("micro_1m", "upper_wick_ratio"), False),
    ("candle_lower_wick",          ("micro_1m", "lower_wick_ratio"), False),
    ("short_term_direction_15m",   ("short_term_15m", "direction"), True),
    ("short_term_momentum_aligned_15m", ("short_term_15m", "momentum_aligned"), True),
    ("context",                    None, True),  # top-level field, not nested in market_state
]

N_BINS = 10


# ── Loading ──────────────────────────────────────────────────────────────

def _dig(d: dict, path):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def load_candidates(paths: list[str]) -> pd.DataFrame:
    rows = []
    seen_ts = set()
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = json.load(f)
        for c in data.get("candidates", []):
            ts = c["timestamp"]
            if ts in seen_ts:
                continue  # dedupe if historical/live ranges overlap
            seen_ts.add(ts)
            row = {
                "timestamp": ts,
                "context": c.get("context"),
                "context_confidence": c.get("context_confidence"),
                "state_price": c.get("state_price"),
                "source": c.get("source", "live"),
            }
            for horizon in HORIZONS:
                row[f"fwd_{horizon}"] = c.get(f"forward_return_{horizon}")
            ms = c.get("market_state") or {}
            for label, path_tuple, _ in DIMENSIONS:
                if path_tuple is None:
                    continue
                row[label] = _dig(ms, path_tuple)
            rows.append(row)

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df["year"] = df["timestamp"].dt.year
    return df


# ── Section A ────────────────────────────────────────────────────────────

def section_a(df: pd.DataFrame) -> str:
    lines = ["## A. Dataset\n"]
    total = len(df)
    lines.append(f"- Samples: **{total:,}**")
    lines.append(f"- Range: **{df['timestamp'].min()}** to **{df['timestamp'].max()}**")
    by_source = df["source"].value_counts().to_dict()
    lines.append(f"- Source: {by_source}")

    expected = pd.date_range(df["timestamp"].min(), df["timestamp"].max(), freq="1h", tz="UTC")
    missing = len(expected) - df["timestamp"].nunique()
    lines.append(f"- Expected hourly candles in range: {len(expected):,}, missing: {missing:,} "
                 f"({missing/len(expected)*100:.2f}%)")

    lines.append("\n**Outcome coverage:**\n")
    lines.append("| Horizon | n with outcome | % of total |")
    lines.append("|---|---|---|")
    for h in HORIZONS:
        n = df[f"fwd_{h}"].notna().sum()
        lines.append(f"| {h} | {n:,} | {n/total*100:.2f}% |")

    lines.append("\n**Regime (context) distribution:**\n")
    lines.append("| Context | n | % |")
    lines.append("|---|---|---|")
    for ctx, n in df["context"].value_counts().items():
        lines.append(f"| {ctx} | {n:,} | {n/total*100:.1f}% |")

    lines.append("\n**Samples per year:**\n")
    lines.append("| Year | n |")
    lines.append("|---|---|")
    for yr, n in df["year"].value_counts().sort_index().items():
        lines.append(f"| {yr} | {n:,} |")

    return "\n".join(lines) + "\n"


# ── Section B ────────────────────────────────────────────────────────────

def horizon_stats(vals: pd.Series) -> dict:
    v = vals.dropna()
    if len(v) == 0:
        return {}
    return {
        "n": len(v),
        "mean": v.mean(), "median": v.median(), "std": v.std(),
        "win_rate": (v > 0).mean(),
        "p05": v.quantile(0.05), "p25": v.quantile(0.25),
        "p75": v.quantile(0.75), "p95": v.quantile(0.95),
        "min": v.min(), "max": v.max(),
    }


def section_b(df: pd.DataFrame) -> str:
    lines = ["## B. Forward-return baseline\n"]
    lines.append("| Horizon | n | Mean | Median | Std | Win Rate | P05 | P25 | P75 | P95 | Min | Max |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for h in HORIZONS:
        s = horizon_stats(df[f"fwd_{h}"])
        if not s:
            continue
        lines.append(
            f"| {h} | {s['n']:,} | {s['mean']*100:+.4f}% | {s['median']*100:+.4f}% | "
            f"{s['std']*100:.3f}% | {s['win_rate']*100:.1f}% | {s['p05']*100:+.2f}% | "
            f"{s['p25']*100:+.2f}% | {s['p75']*100:+.2f}% | {s['p95']*100:+.2f}% | "
            f"{s['min']*100:+.2f}% | {s['max']*100:+.2f}% |")
    return "\n".join(lines) + "\n"


# ── Binning (shared by C, D, E) ──────────────────────────────────────────

def bin_dimension(df: pd.DataFrame, col: str, categorical: bool, n_bins: int = N_BINS):
    """Returns (bin_labels_ordered, bin_series) — bin_series aligned to df.index."""
    s = df[col]
    if categorical:
        # bool columns print nicer as True/False strings; keep as-is otherwise
        labels = sorted(s.dropna().unique().tolist(), key=str)
        return [str(l) for l in labels], s.astype(str).where(s.notna())
    valid = s.dropna()
    if valid.nunique() < 3:
        return [], None
    try:
        binned, edges = pd.qcut(s, n_bins, labels=False, retbins=True, duplicates="drop")
    except ValueError:
        return [], None
    n_actual = int(np.nanmax(binned)) + 1 if binned.notna().any() else 0
    labels = [f"[{edges[i]:.4g}, {edges[i+1]:.4g})" for i in range(n_actual)]
    return labels, binned


def dimension_table(df: pd.DataFrame, col: str, categorical: bool, horizon: str, n_bins: int = N_BINS):
    """Per-bin stats table for one dimension x one horizon. Returns list of
    dicts: bin, n, mean, median, win_rate, std, p25, p75, p05, p95."""
    labels, binned = bin_dimension(df, col, categorical, n_bins)
    if binned is None:
        return []
    fwd = df[f"fwd_{horizon}"]
    rows = []
    if categorical:
        for label in labels:
            mask = binned == label
            s = horizon_stats(fwd[mask])
            if s:
                rows.append({"bin": label, **s})
    else:
        for i, label in enumerate(labels):
            mask = binned == i
            s = horizon_stats(fwd[mask])
            if s:
                rows.append({"bin": label, **s})
    return rows


# ── Section C ────────────────────────────────────────────────────────────

def format_dim_table(label: str, rows: list, horizon: str) -> str:
    if not rows:
        return ""
    out = [f"**{label} — {horizon}**\n"]
    out.append("| Bin | n | Mean | Median | Win Rate | Std | P25 | P75 | P05 | P95 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        out.append(f"| {r['bin']} | {r['n']:,} | {r['mean']*100:+.4f}% | {r['median']*100:+.4f}% | "
                    f"{r['win_rate']*100:.1f}% | {r['std']*100:.3f}% | {r['p25']*100:+.2f}% | "
                    f"{r['p75']*100:+.2f}% | {r['p05']*100:+.2f}% | {r['p95']*100:+.2f}% |")
    return "\n".join(out) + "\n"


def section_c(df: pd.DataFrame, dims: list) -> tuple[str, dict]:
    """Returns (markdown, all_tables) where all_tables[label][horizon] = rows,
    reused by sections D/E so the binning is only computed once."""
    lines = ["## C. Univariate state-dimension analysis\n",
             "Per dimension, per horizon: how does the forward-return "
             "*distribution* (not just the mean) differ across bins of "
             "this dimension?\n"]
    all_tables = {}
    for label, _, categorical in dims:
        if label not in df.columns:
            continue
        all_tables[label] = {}
        section_lines = []
        for h in HORIZONS:
            rows = dimension_table(df, label, categorical, h)
            all_tables[label][h] = rows
            section_lines.append(format_dim_table(label, rows, h))
        if any(section_lines):
            lines.append(f"### {label}\n")
            lines.extend(section_lines)
    return "\n".join(lines), all_tables


# ── Section D ────────────────────────────────────────────────────────────

def classify_shape(bin_means: list) -> str:
    n = len(bin_means)
    if n < 3:
        return "insufficient bins"
    means = np.array(bin_means, dtype=float)
    if np.std(means) < 1e-10:
        return "flat / no effect"
    x = np.arange(n)
    corr = np.corrcoef(x, means)[0, 1]
    spread = means.max() - means.min()
    mid = means[1:-1]
    mid_mean = mid.mean() if len(mid) else means.mean()
    lo_dev, hi_dev = means[0] - mid_mean, means[-1] - mid_mean
    if abs(corr) > 0.7:
        direction = "increasing" if corr > 0 else "decreasing"
        return f"linear/monotonic ({direction}, r={corr:+.2f})"
    if lo_dev * hi_dev > 0 and abs(lo_dev) > spread * 0.3 and abs(hi_dev) > spread * 0.3:
        shape = "higher" if lo_dev > 0 else "lower"
        return f"U-shaped (both extremes {shape} than middle)"
    if abs(lo_dev) > spread * 0.5 and abs(hi_dev) < spread * 0.25:
        return "threshold (low end diverges)"
    if abs(hi_dev) > spread * 0.5 and abs(lo_dev) < spread * 0.25:
        return "threshold (high end diverges)"
    return f"irregular (r={corr:+.2f}, no clean pattern)"


def section_d(all_tables: dict, dims: list) -> tuple[str, list]:
    """Returns (markdown, ranked_effects) where ranked_effects is a list of
    (label, horizon, median_spread, shape) sorted by |median_spread| at the
    given horizon, continuous dimensions only (shape classification needs
    ordered bins).

    Ranked by MEDIAN spread, not mean spread: a single extreme day (e.g. the
    2020-03 COVID crash) can blow out one bin's *mean* by orders of
    magnitude — seen directly in this dataset (bb_position's [0.412,0.522)
    bin: mean +0.34% vs a median of +0.006%, right in line with neighboring
    bins) — without moving that bin's median or win rate at all. Ranking by
    mean would surface outlier contamination as a "top effect"; the mean
    spread is still shown alongside as a diagnostic (large mean/median
    divergence = suspect a few extreme samples, not a real distributional
    shift).
    """
    ranked = []
    cont_labels = {label for label, _, cat in dims if not cat}
    for label, horizons in all_tables.items():
        if label not in cont_labels:
            continue
        rows = horizons.get("4h", [])
        if len(rows) < 3:
            continue
        means = [r["mean"] for r in rows]
        medians = [r["median"] for r in rows]
        mean_spread = max(means) - min(means)
        median_spread = max(medians) - min(medians)
        shape = classify_shape(medians)
        ranked.append((label, "4h", median_spread, shape, mean_spread))
    ranked.sort(key=lambda x: -abs(x[2]))

    lines = ["## D. Nonlinear pattern detection\n",
             "Shape of the median-return-vs-bin relationship (median, not "
             "mean — see docstring), per continuous dimension, at the 4h "
             "horizon (the horizon with the most time for a real effect to "
             "separate from noise). A large gap between the median-spread "
             "and mean-spread columns flags likely outlier contamination "
             "rather than a genuine distributional shift.\n",
             "| Dimension | Median Spread | Mean Spread | Shape (of medians) |",
             "|---|---|---|---|"]
    for label, h, median_spread, shape, mean_spread in ranked:
        flag = " ⚠ mean≫median" if abs(mean_spread) > abs(median_spread) * 3 and abs(mean_spread) > 0.001 else ""
        lines.append(f"| {label} | {median_spread*100:.4f}% | {mean_spread*100:.4f}%{flag} | {shape} |")
    return "\n".join(lines) + "\n", [(l, h, s, sh) for l, h, s, sh, _ in ranked]


# ── Section E ────────────────────────────────────────────────────────────

def top_bottom_bin_spread_by_year(df: pd.DataFrame, col: str, categorical: bool, horizon: str):
    """For each year, the (top-bin-median - bottom-bin-median) using the SAME
    global bin edges as the full-period table (recomputed per-year would
    make years incomparable if the distribution of the dimension itself
    shifted). Median, not mean — consistent with Section D's ranking, for
    the same outlier-robustness reason (see section_d docstring)."""
    labels, binned = bin_dimension(df, col, categorical, N_BINS)
    if binned is None or len(labels) < 2:
        return {}
    fwd = df[f"fwd_{horizon}"]
    out = {}
    for yr in sorted(df["year"].unique()):
        yr_mask = df["year"] == yr
        bin_medians = {}
        keys = labels if categorical else range(len(labels))
        for key in keys:
            m = yr_mask & (binned == key)
            v = fwd[m].dropna()
            if len(v) >= 20:
                bin_medians[key] = v.median()
        if len(bin_medians) < 2:
            continue
        top_key = max(bin_medians, key=bin_medians.get)
        bot_key = min(bin_medians, key=bin_medians.get)
        out[yr] = {"spread": bin_medians[top_key] - bin_medians[bot_key],
                    "top": labels[top_key] if not categorical else top_key,
                    "bottom": labels[bot_key] if not categorical else bot_key,
                    "n": int((yr_mask).sum())}
    return out


def section_e(df: pd.DataFrame, ranked_effects: list, top_n: int = 15) -> str:
    lines = ["## E. Time stability of the strongest effects\n",
             f"Top {top_n} effects from Section D (by 4h median spread), "
             "re-measured per year using the SAME bin edges as the "
             "full-period table. An effect only counts as real if its sign "
             "is consistent across most years, not just strong in "
             "aggregate.\n"]
    for label, horizon, spread, shape in ranked_effects[:top_n]:
        by_year = top_bottom_bin_spread_by_year(df, label, False, horizon)
        if not by_year:
            continue
        signs = [1 if v["spread"] > 0 else -1 for v in by_year.values()]
        consistent = sum(1 for s in signs if s == signs[0]) if signs else 0
        verdict = f"{consistent}/{len(signs)} years same sign as aggregate"
        lines.append(f"### {label} (aggregate 4h median spread: {spread*100:+.4f}%, shape: {shape})\n")
        lines.append(f"**Stability: {verdict}**\n")
        lines.append("| Year | n | Top-bin median − Bottom-bin median |")
        lines.append("|---|---|---|")
        for yr, v in sorted(by_year.items()):
            lines.append(f"| {yr} | {v['n']:,} | {v['spread']*100:+.4f}% |")
        lines.append("")
    return "\n".join(lines) + "\n"


# ── Section F ────────────────────────────────────────────────────────────

def section_f(df: pd.DataFrame) -> str:
    lines = ["## F. Interactions\n",
             "State A x State B, sliced by a third dimension — only makes "
             "sense once A/B/C individually show something in D/E.\n"]

    def block(title, mask, sub_col, sub_bins, horizon="4h"):
        out = [f"### {title}\n", "| Sub-bin | n | Mean | Median | Win Rate | Std |", "|---|---|---|---|---|---|"]
        fwd = df.loc[mask, f"fwd_{horizon}"]
        sub = df.loc[mask, sub_col]
        any_row = False
        for lo, hi, name in sub_bins:
            m = (sub >= lo) & (sub < hi)
            s = horizon_stats(fwd[m])
            if s and s["n"] >= 20:
                any_row = True
                out.append(f"| {name} | {s['n']:,} | {s['mean']*100:+.4f}% | {s['median']*100:+.4f}% | "
                            f"{s['win_rate']*100:.1f}% | {s['std']*100:.3f}% |")
        return "\n".join(out) + "\n" if any_row else ""

    bb_bins = [(-np.inf, 0.9, "bb < 0.90"), (0.9, 1.0, "0.90 <= bb < 1.00"), (1.0, np.inf, "bb >= 1.00")]

    bullish = (df["trend_direction"] == "bullish") & (df["momentum_direction"] == "bullish")
    r = block("Trend=bullish & Momentum=bullish, by bb_position", bullish, "bb_position", bb_bins)
    if r:
        lines.append(r)

    bearish = (df["trend_direction"] == "bearish") & (df["momentum_direction"] == "bearish")
    r = block("Trend=bearish & Momentum=bearish, by bb_position", bearish, "bb_position", bb_bins)
    if r:
        lines.append(r)

    atr_bins_desc = [
        (-np.inf, df["volatility_atr_norm"].quantile(0.33), "low ATR (bottom third)"),
        (df["volatility_atr_norm"].quantile(0.33), df["volatility_atr_norm"].quantile(0.67), "mid ATR"),
        (df["volatility_atr_norm"].quantile(0.67), np.inf, "high ATR (top third)"),
    ]
    r = block("Trend=bullish & Momentum=bullish, by volatility (ATR norm)", bullish, "volatility_atr_norm",
               atr_bins_desc)
    if r:
        lines.append(r)

    r = block("Trend=bearish & Momentum=bearish, by volatility (ATR norm)", bearish, "volatility_atr_norm",
               atr_bins_desc)
    if r:
        lines.append(r)

    return "\n".join(lines) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--include-live", action="store_true",
                    help="Also merge in data/candidates.json (live-collected candidates)")
    p.add_argument("--historical", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "reports", "discovery_v1.md"))
    args = p.parse_args()

    paths = [args.historical]
    if args.include_live:
        paths.append(config.CANDIDATES_FILE)

    print("Loading candidates...")
    df = load_candidates(paths)
    print(f"Loaded {len(df):,} candidates, {df['timestamp'].min()} -> {df['timestamp'].max()}")

    print("Section A: dataset overview...")
    md_a = section_a(df)
    print("Section B: forward-return baseline...")
    md_b = section_b(df)
    print("Section C: univariate state-dimension analysis...")
    md_c, all_tables = section_c(df, DIMENSIONS)
    print("Section D: nonlinear pattern detection...")
    md_d, ranked = section_d(all_tables, DIMENSIONS)
    print("Section E: time stability...")
    md_e = section_e(df, ranked)
    print("Section F: interactions...")
    md_f = section_f(df)

    header = (
        f"# Discovery Analysis Report v1\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()} from "
        f"{', '.join(paths)}.\n\n"
        f"Purely distributional — no trading rules, no belief-score "
        f"compression. Answers: which state dimensions actually shift the "
        f"forward-return distribution, and does that hold up over time?\n\n"
        f"---\n\n"
    )
    full = header + md_a + "\n---\n\n" + md_b + "\n---\n\n" + md_c + "\n---\n\n" + md_d + \
        "\n---\n\n" + md_e + "\n---\n\n" + md_f

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")

    print("\nTop 10 effects by 4h MEDIAN spread (Section D):")
    for label, h, spread, shape in ranked[:10]:
        print(f"  {label:30s} spread={spread*100:+.4f}%  {shape}")


if __name__ == "__main__":
    main()
