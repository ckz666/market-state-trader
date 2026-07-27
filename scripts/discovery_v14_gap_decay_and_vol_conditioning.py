"""
Discovery v14 — two follow-ups to discovery_v13, run together because
they answer complementary questions about the same effect.

A. GAP DECAY. v13 showed the mean-reversion effect survives a 1-minute
   gap (so it is not purely the shared-P_t artifact). But how does it
   behave as the gap widens? Compute the same 5-minute window ending
   g minutes before the state candle, for g = 0 (original), 1, 2, 3, 5,
   10, 15:

       gap_g = (P_t-g - P_t-g-5) / P_t-g-5

   A smooth monotone decay is what a genuine short-horizon
   mean-reversion effect should look like (the older the signal, the
   less of it is left by entry time). An abrupt collapse right after
   g=1 would instead suggest the surviving part at g=1 is still
   contaminated (e.g. by autocorrelated noise spanning a couple of
   bars), not real economics.

B. VOLATILITY CONDITIONING. LPL only became a usable edge once
   conditioned on volatility level (discovery_v4/v5 -> decision_rule_v1
   trades LPL==Q1 & Vol==Q5). The direct analogue for this factor has
   never been tested: does `micro_return_5m`'s spread widen with
   volatility the way LPL's does? Two conditioning variables are
   checked separately, since they measure different things:
     - `volatility_atr_norm` (1h ATR level -- the SAME variable LPL is
       conditioned on, so this asks whether both factors want the same
       regime)
     - `micro_volatility_1m` (1m realized vol -- the timeframe-matched
       analogue, weak on its own in discovery_v10)

Purely descriptive; does not change decision_rule_v1 or propose a rule.
Discovery period only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v14_gap_decay_and_vol_conditioning.py
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
from phase_c_baseline_v1 import load_1m_price_series
from hypothesis_validation import fit_quintile_edges, apply_quintile

MIN_CELL_N = 30
HORIZONS = ["15m", "1h", "4h"]
GAPS = [0, 1, 2, 3, 5, 10, 15]
Q_LABELS = ["Q1", "Q2", "Q3", "Q4", "Q5"]
NEW_DIMENSIONS = [
    ("micro_return_5m",   ("micro_1m", "return_5m"), False),
    ("micro_volatility_1m", ("micro_1m", "volatility_1m"), False),
]


def compute_gapped(df: pd.DataFrame, price_history: dict, gap: int) -> pd.Series:
    """(P_t-gap - P_t-gap-5) / P_t-gap-5. price_history is keyed by candle
    OPEN time, so the candle closing at X opens at X-1min: P_t == ph[t-1min]."""
    out = []
    for ts in df["timestamp"]:
        ms = int(ts.timestamp() * 1000)
        p_end = price_history.get(ms - (1 + gap) * 60_000)
        p_start = price_history.get(ms - (6 + gap) * 60_000)
        out.append(np.nan if (p_end is None or p_start is None or p_start == 0)
                   else (p_end - p_start) / p_start)
    return pd.Series(out, index=df.index)


def section_gap_decay(df: pd.DataFrame, price_history: dict) -> str:
    lines = [
        "## A. Gap decay — how fast does the effect fade as the signal ages?\n",
        "Q1-vs-Q5 median spread for the same 5-minute window ending `gap` "
        "minutes before the state candle. gap=0 is the original "
        "`micro_return_5m` (shares P_t with the outcome); every gap >= 1 "
        "shares no price point with it.\n",
        "| Gap (min) | " + " | ".join(HORIZONS) + " |",
        "|---|" + "---|" * len(HORIZONS),
    ]
    for gap in GAPS:
        col = f"gap_{gap}"
        df[col] = compute_gapped(df, price_history, gap)
        sub = df.dropna(subset=[col])
        edges = fit_quintile_edges(sub[col])
        q = apply_quintile(sub[col], edges)
        cells = []
        for h in HORIZONS:
            fwd = sub[f"fwd_{h}"]
            q1, q5 = fwd[q == "Q1"].dropna(), fwd[q == "Q5"].dropna()
            if len(q1) < MIN_CELL_N or len(q5) < MIN_CELL_N:
                cells.append("n too few")
                continue
            cells.append(f"{(q1.median()-q5.median())*100:+.4f}%")
        label = f"{gap} (original)" if gap == 0 else str(gap)
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append(
        "\nA smooth monotone decline is consistent with a real, decaying "
        "short-horizon effect. A cliff right after gap=0 would instead "
        "point to the shared-price artifact still dominating.\n"
    )
    return "\n".join(lines) + "\n"


def section_vol_conditioning(df: pd.DataFrame, vol_col: str, title: str, note: str) -> str:
    lines = [f"## {title}\n", note + "\n"]
    sub = df.dropna(subset=["micro_return_5m", vol_col]).copy()
    ret_edges = fit_quintile_edges(sub["micro_return_5m"])
    vol_edges = fit_quintile_edges(sub[vol_col])
    sub["ret_q"] = apply_quintile(sub["micro_return_5m"], ret_edges)
    sub["vol_q"] = apply_quintile(sub[vol_col], vol_edges)
    for h in HORIZONS:
        lines.append(f"\n**Horizon {h}**\n")
        lines.append("| Volatility | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread (Q1-Q5) |")
        lines.append("|---|---|---|---|---|---|")
        fwd = sub[f"fwd_{h}"]
        for vq in Q_LABELS:
            m = sub["vol_q"] == vq
            q1 = fwd[m & (sub["ret_q"] == "Q1")].dropna()
            q5 = fwd[m & (sub["ret_q"] == "Q5")].dropna()
            if len(q1) < MIN_CELL_N or len(q5) < MIN_CELL_N:
                lines.append(f"| {vq} | {len(q1)} | n too few | {len(q5)} | n too few | - |")
                continue
            lines.append(
                f"| {vq} | {len(q1):,} | {q1.median()*100:+.4f}% | {len(q5):,} | "
                f"{q5.median()*100:+.4f}% | {(q1.median()-q5.median())*100:+.4f}% |"
            )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/discovery_v14_gap_decay_and_vol_conditioning.md")
    args = p.parse_args()

    print("Loading candidates...")
    dr.DIMENSIONS = dr.DIMENSIONS + NEW_DIMENSIONS
    df_all = dr.load_candidates([args.historical])
    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)

    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df_all[df_all["timestamp"] < cutoff].copy()  # Discovery only
    print(f"Discovery n={len(disc):,}")

    body = (
        section_gap_decay(disc, price_history) +
        "\n---\n\n" +
        section_vol_conditioning(
            disc, "volatility_atr_norm",
            "B1. Conditioned on `volatility_atr_norm` (1h ATR — the same variable LPL uses)",
            "If `micro_return_5m`'s spread widens with volatility the way "
            "LPL's does, both factors want the same high-volatility regime "
            "— which would matter for whether they can be combined or "
            "compete for the same trades.",
        ) +
        "\n---\n\n" +
        section_vol_conditioning(
            disc, "micro_volatility_1m",
            "B2. Conditioned on `micro_volatility_1m` (1m realized vol — timeframe-matched)",
            "The timeframe-matched analogue. Weak on its own in "
            "discovery_v10, but LPL's volatility conditioning was also "
            "only visible as an interaction, not a standalone effect.",
        )
    )

    header = (
        "# Discovery v14 — gap decay and volatility conditioning of micro_return_5m\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Two follow-ups to discovery_v13: (A) how the effect decays as "
        "the signal window is moved further from the entry price, and "
        "(B) whether it strengthens with volatility the way LPL does. "
        "Purely descriptive; does not change decision_rule_v1. Discovery "
        f"only (2020-2025); 2026 untouched. Cells with n < {MIN_CELL_N} "
        "are marked instead of reported.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
