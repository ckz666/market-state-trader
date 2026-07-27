"""
Discovery v17 — volume, the one field present in every kline row and
every stored candidate that discovery_v1-v16 never tested.

`market_state.ohlcv.volume` is stored for all 57,565 candidates but
appears nowhere in discovery_report.py's DIMENSIONS list, so it has
never been through the univariate/stability pipeline.

IMPORTANT — raw volume is NOT usable directly. BTC volume in 2020 and
2025 differ by orders of magnitude, so a raw-volume quintile split would
mostly be a proxy for "which year is this", not a market-state feature.
This computes three normalized variants instead, all using only data up
to and including the state candle (no look-ahead):

  volume_rel_24h  = vol_t / mean(vol over the previous 24 1h candles)
  volume_rel_7d   = vol_t / mean(vol over the previous 168 1h candles)
  volume_trend_24h= mean(last 6 candles) / mean(previous 24) -- is
                    activity rising or falling into this moment?

Sections:
  A. Univariate: each variant, quintile-binned, at 15m/1h/4h.
  B. Year stability for whichever variant shows the widest 4h spread.
  C. Interaction with volatility and with LPL -- the two dimensions that
     mattered for every previous factor. Volume and volatility are
     expected to be correlated, so the correlation is reported to make
     any redundancy visible (same check discovery_v11 applied to the
     15m/1m candidates).

Purely descriptive; does not change decision_rule_v1 or propose a rule.
Discovery period only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v17_volume.py
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

MIN_CELL_N = 30
HORIZONS = ["15m", "1h", "4h"]
Q_LABELS = ["Q1", "Q2", "Q3", "Q4", "Q5"]
VOLUME_VARIANTS = ["volume_rel_24h", "volume_rel_7d", "volume_trend_24h"]


def build_volume_features(df: pd.DataFrame, hourly_csv: str) -> pd.DataFrame:
    """All windows are TRAILING and exclude nothing after the state candle."""
    h = pd.read_csv(hourly_csv)
    h["timestamp"] = pd.to_datetime(h["timestamp"].astype("int64"), unit="ms", utc=True)
    h = h.sort_values("timestamp").set_index("timestamp")
    vol = h["volume"]

    # shift(1) so the trailing mean EXCLUDES the current candle -- the ratio
    # then compares this candle's volume against what came strictly before it.
    mean_24 = vol.shift(1).rolling(24, min_periods=24).mean()
    mean_168 = vol.shift(1).rolling(168, min_periods=168).mean()
    recent_6 = vol.rolling(6, min_periods=6).mean()
    prior_24 = vol.shift(6).rolling(24, min_periods=24).mean()

    feats = pd.DataFrame({
        "volume_rel_24h": vol / mean_24,
        "volume_rel_7d": vol / mean_168,
        "volume_trend_24h": recent_6 / prior_24,
    })
    # zero-volume windows (exchange outages / very early illiquid data) produce
    # inf here; drop them rather than letting them land in the top quintile
    feats = feats.replace([np.inf, -np.inf], np.nan)
    # the state candle at timestamp T is the 1h candle that CLOSED at T,
    # i.e. the one indexed (opened) at T-1h
    feats.index = feats.index + pd.Timedelta(hours=1)
    return df.join(feats, on="timestamp")


def section_univariate(df: pd.DataFrame) -> tuple[str, dict]:
    lines = ["## A. Univariate — normalized volume variants\n"]
    spreads = {}
    for field in VOLUME_VARIANTS:
        sub = df.dropna(subset=[field]).copy()
        edges = fit_quintile_edges(sub[field])
        sub["q"] = apply_quintile(sub[field], edges)
        lines.append(f"\n### {field}  (n={len(sub):,})\n")
        lines.append("| Quintile | " + " | ".join(f"{h} win% / median" for h in HORIZONS) + " |")
        lines.append("|---|" + "---|" * len(HORIZONS))
        med = {}
        for q in Q_LABELS:
            cells = []
            for h in HORIZONS:
                s = sub.loc[sub["q"] == q, f"fwd_{h}"].dropna()
                if len(s) < MIN_CELL_N:
                    cells.append("n too few")
                    continue
                cells.append(f"{(s>0).mean()*100:.1f}% / {s.median()*100:+.4f}%")
                if h == "4h":
                    med[q] = s.median()
            lines.append(f"| {q} | " + " | ".join(cells) + " |")
        if "Q1" in med and "Q5" in med:
            spreads[field] = med["Q5"] - med["Q1"]
            lines.append(f"\n4h Q5-Q1 median spread: **{spreads[field]*100:+.4f}%**\n")
    return "\n".join(lines) + "\n", spreads


def section_stability(df: pd.DataFrame, field: str) -> str:
    sub = df.dropna(subset=[field]).copy()
    edges = fit_quintile_edges(sub[field])
    sub["q"] = apply_quintile(sub[field], edges)
    lines = [
        f"## B. Year stability — `{field}` (widest 4h spread from section A)\n",
        "Frozen quintile edges (fit on the full Discovery period) applied per year.\n",
        "| Year | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread (Q5-Q1) |",
        "|---|---|---|---|---|---|",
    ]
    signs = []
    for year in sorted(sub["year"].unique()):
        yr = sub[sub["year"] == year]
        q1 = yr.loc[yr["q"] == "Q1", "fwd_4h"].dropna()
        q5 = yr.loc[yr["q"] == "Q5", "fwd_4h"].dropna()
        if len(q1) < MIN_CELL_N or len(q5) < MIN_CELL_N:
            lines.append(f"| {year} | {len(q1)} | n too few | {len(q5)} | n too few | - |")
            continue
        spread = q5.median() - q1.median()
        signs.append(spread > 0)
        lines.append(f"| {year} | {len(q1):,} | {q1.median()*100:+.4f}% | {len(q5):,} | "
                     f"{q5.median()*100:+.4f}% | {spread*100:+.4f}% |")
    if signs:
        lines.append(f"\nSign consistency: {sum(signs)}/{len(signs)} years\n")
    return "\n".join(lines) + "\n"


def section_interaction(df: pd.DataFrame, field: str) -> str:
    sub = df.dropna(subset=[field, "volatility_atr_norm", "local_price_location"]).copy()
    corr_vol = sub[field].corr(sub["volatility_atr_norm"])
    corr_lpl = sub[field].corr(sub["local_price_location"])
    edges = fit_quintile_edges(sub[field])
    sub["vq"] = apply_quintile(sub[field], edges)

    lines = [
        f"## C. Interaction — `{field}`\n",
        f"Correlation with `volatility_atr_norm`: **{corr_vol:+.3f}**; "
        f"with `local_price_location` (LPL): **{corr_lpl:+.3f}**. High "
        "correlation with volatility would mean this is largely a "
        "re-measurement of a factor already in use.\n",
        "\n**LPL=Q1 vs Q5 (4h median), split by volume quintile — does volume amplify the LPL edge?**\n",
        "| Volume quintile | n (LPL Q1) | LPL Q1 median | n (LPL Q5) | LPL Q5 median | Spread |",
        "|---|---|---|---|---|---|",
    ]
    for q in Q_LABELS:
        m = sub["vq"] == q
        q1 = sub.loc[m & (sub["lpl_q"] == "Q1"), "fwd_4h"].dropna()
        q5 = sub.loc[m & (sub["lpl_q"] == "Q5"), "fwd_4h"].dropna()
        if len(q1) < MIN_CELL_N or len(q5) < MIN_CELL_N:
            lines.append(f"| {q} | {len(q1)} | n too few | {len(q5)} | n too few | - |")
            continue
        lines.append(f"| {q} | {len(q1):,} | {q1.median()*100:+.4f}% | {len(q5):,} | "
                     f"{q5.median()*100:+.4f}% | {(q1.median()-q5.median())*100:+.4f}% |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--hourly-csv", default="data/backfill_cache/BTC_USDT_1h.csv")
    p.add_argument("--out", default="data/reports/discovery_v17_volume.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = dr.load_candidates([args.historical])
    print("Building normalized volume features...")
    df = build_volume_features(df, args.hourly_csv)

    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()  # Discovery only

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    disc["lpl_q"] = apply_quintile(disc["local_price_location"], lpl_edges)
    print(f"Discovery n={len(disc):,}, with volume features: "
          f"{disc['volume_rel_24h'].notna().sum():,}")

    md_a, spreads = section_univariate(disc)
    widest = max(spreads, key=lambda k: abs(spreads[k])) if spreads else VOLUME_VARIANTS[0]
    body = md_a + "\n---\n\n" + section_stability(disc, widest) + "\n---\n\n" + section_interaction(disc, widest)

    header = (
        "# Discovery v17 — volume (never tested in discovery_v1-v16)\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "`volume` is stored for every candidate but appears in no "
        "dimension of discovery_report.py. Raw volume is non-stationary "
        "across 2020-2025 (a raw quintile split would largely encode "
        "*which year* a sample came from), so three trailing-window "
        "normalized variants are used instead, none of which look past "
        "the state candle. Purely descriptive; does not change "
        "decision_rule_v1. Discovery only (2020-2025); 2026 untouched. "
        f"Cells with n < {MIN_CELL_N} are marked instead of reported.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
