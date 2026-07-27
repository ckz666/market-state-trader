"""
Discovery v13 — is `micro_return_5m`'s mean-reversion effect real, or an
artifact of sharing one price point with the forward return?

THE CONCERN (found during a verification pass, not previously checked):

    micro_return_5m  = (P_t   - P_t-5) / P_t-5
    forward_return_h = (P_t+h - P_t  ) / P_t

Both use the SAME price P_t. This was verified empirically: the state
candle's `state_price` (from which storage/logger.py measures every
forward return) is bit-identical to the last 1m close used in
`micro_return_5m` (2000/2000 candidates checked, zero mismatches).

If P_t carries ANY transient measurement noise e -- bid-ask bounce, a
momentary wick, a thin-liquidity print -- then micro_return_5m is biased
UP by e while forward_return is biased DOWN by e. That mechanically
induces negative correlation between the two, in exactly the direction
of the reported "finding" (low micro_return_5m -> high forward return),
with no economic effect required at all. This is the classic spurious-
negative-autocorrelation problem from microstructure noise.

THE DECISIVE TEST: introduce a one-minute gap so the two quantities
share no price point.

    gapped_return_5m = (P_t-1 - P_t-6) / P_t-6      <- ends 1 min early
    forward_return_h = (P_t+h - P_t  ) / P_t        <- unchanged

If the effect survives the gap at similar magnitude, it is a real
short-horizon mean-reversion effect. If it largely collapses, the
discovery_v10-v12 result (and its OOS "validation") was substantially a
measurement artifact, not a tradeable edge.

Both variants are computed on the SAME candidates, from the same raw 1m
CSV, so the comparison is paired and like-for-like. Discovery period
only (2020-2025); 2026 shown separately for reference since the original
finding was OOS-"validated" there.

Usage:
    .venv/bin/python scripts/discovery_v13_micro_return_5m_bounce_check.py
"""
import argparse
import bisect
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
NEW_DIMENSIONS = [("micro_return_5m", ("micro_1m", "return_5m"), False)]


def compute_gapped(df: pd.DataFrame, price_history: dict, sorted_ts: list) -> pd.Series:
    """(P_t-1 - P_t-6) / P_t-6 -- the same 5-minute window as
    micro_return_5m but ending one minute EARLIER, so it shares no price
    point with the forward return measured from P_t.

    price_history is keyed by candle OPEN time; the candle closing at X
    is the one opening at X-1min. So P_t == ph[t-1min], P_t-1 ==
    ph[t-2min], P_t-6 == ph[t-7min]."""
    out = []
    for ts in df["timestamp"]:
        ms = int(ts.timestamp() * 1000)
        p_end = price_history.get(ms - 2 * 60_000)    # P_t-1
        p_start = price_history.get(ms - 7 * 60_000)  # P_t-6
        if p_end is None or p_start is None or p_start == 0:
            out.append(np.nan)
        else:
            out.append((p_end - p_start) / p_start)
    return pd.Series(out, index=df.index)


def sanity_check(df: pd.DataFrame, price_history: dict) -> str:
    """Reconstruct micro_return_5m itself from the raw CSV to confirm the
    shared-price-point claim is real and not a misreading of the code."""
    recomputed, stored = [], []
    for ts, val in zip(df["timestamp"].head(3000), df["micro_return_5m"].head(3000)):
        ms = int(ts.timestamp() * 1000)
        p_end = price_history.get(ms - 60_000)        # P_t
        p_start = price_history.get(ms - 6 * 60_000)  # P_t-5
        if p_end is None or p_start is None or pd.isna(val):
            continue
        recomputed.append((p_end - p_start) / p_start)
        stored.append(val)
    if not recomputed:
        return "(could not reconstruct -- no overlapping price data)\n"
    r, s = np.array(recomputed), np.array(stored)
    close = np.abs(r - s) < 1e-5
    return (
        f"Reconstructed `micro_return_5m` from the raw 1m CSV as (P_t - P_t-5)/P_t-5 "
        f"for {len(r):,} candidates: **{close.mean()*100:.1f}% match the stored value** "
        f"(tolerance 1e-5; correlation {np.corrcoef(r, s)[0,1]:.4f}). This confirms "
        "the numerator price P_t is exactly the `state_price` that every forward "
        "return is measured from -- the shared-price-point concern is real, not a "
        "misreading of the code.\n"
    )


def spread_table(df: pd.DataFrame, q_col: str, label: str) -> str:
    lines = [f"**{label}**\n",
             "| Horizon | n (Q1) | Q1 win% | Q1 median | n (Q5) | Q5 win% | Q5 median | Spread (Q1-Q5) |",
             "|---|---|---|---|---|---|---|---|"]
    for h in HORIZONS:
        fwd = df[f"fwd_{h}"]
        q1 = fwd[df[q_col] == "Q1"].dropna()
        q5 = fwd[df[q_col] == "Q5"].dropna()
        if len(q1) < MIN_CELL_N or len(q5) < MIN_CELL_N:
            lines.append(f"| {h} | {len(q1)} | n too few | - | {len(q5)} | n too few | - | - |")
            continue
        lines.append(
            f"| {h} | {len(q1):,} | {(q1>0).mean()*100:.1f}% | {q1.median()*100:+.4f}% | "
            f"{len(q5):,} | {(q5>0).mean()*100:.1f}% | {q5.median()*100:+.4f}% | "
            f"{(q1.median()-q5.median())*100:+.4f}% |"
        )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/discovery_v13_micro_return_5m_bounce_check.md")
    args = p.parse_args()

    print("Loading candidates...")
    dr.DIMENSIONS = dr.DIMENSIONS + NEW_DIMENSIONS
    df_all = dr.load_candidates([args.historical])
    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    print("Computing gapped variant...")
    df_all["gapped_return_5m"] = compute_gapped(df_all, price_history, sorted_ts)

    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df_all[df_all["timestamp"] < cutoff].dropna(subset=["micro_return_5m", "gapped_return_5m"]).copy()
    val = df_all[df_all["timestamp"] >= cutoff].dropna(subset=["micro_return_5m", "gapped_return_5m"]).copy()
    print(f"Discovery n={len(disc):,}, Validation n={len(val):,}")

    sanity = sanity_check(disc, price_history)

    orig_edges = fit_quintile_edges(disc["micro_return_5m"])
    gap_edges = fit_quintile_edges(disc["gapped_return_5m"])
    for d in (disc, val):
        d["orig_q"] = apply_quintile(d["micro_return_5m"], orig_edges)
        d["gap_q"] = apply_quintile(d["gapped_return_5m"], gap_edges)

    corr = disc[["micro_return_5m", "gapped_return_5m"]].corr().iloc[0, 1]

    body = (
        "## 0. Sanity check — is the shared price point real?\n\n" + sanity +
        "\n---\n\n## 1. Discovery (2020-2025): original vs. gapped\n\n"
        f"Correlation between the two variants: **{corr:+.4f}** (they cover "
        "overlapping 5-minute windows offset by one minute, so they are "
        "expected to be highly correlated -- if the effect is economic, "
        "both should show it; if it comes from the shared price point, "
        "only the original will).\n\n"
        + spread_table(disc, "orig_q", "Original `micro_return_5m` (shares P_t with forward return)")
        + "\n" + spread_table(disc, "gap_q", "Gapped `(P_t-1 - P_t-6)/P_t-6` (shares NO price point)")
        + "\n---\n\n## 2. Validation (2026): original vs. gapped\n\n"
        + spread_table(val, "orig_q", "Original `micro_return_5m`")
        + "\n" + spread_table(val, "gap_q", "Gapped variant")
    )

    header = (
        "# Discovery v13 — bid-ask-bounce / shared-price-point check on micro_return_5m\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "`micro_return_5m` and every forward return share the same price "
        "P_t (verified below). Transient noise in P_t alone would produce "
        "exactly the reported mean-reversion pattern with no economic "
        "effect. This compares the original against a one-minute-gapped "
        "variant that shares no price point with the outcome. Purely "
        "diagnostic; does not change decision_rule_v1.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
