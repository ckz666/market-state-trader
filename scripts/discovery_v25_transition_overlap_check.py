"""
Discovery v25 — is discovery_v24's transition finding an artifact of
overlapping forward-return windows?

THE CONCERN (found while examining v24's unexplained 1h gap):

Candidates are hourly. Forward-return windows therefore overlap by
horizon:
    15m forward: t..t+15m, next candidate t+1h..t+1h15m  -> NO overlap
    1h  forward: t..t+1h,  next t+1h..t+2h               -> NO overlap
    4h  forward: t..t+4h,  next t+1h..t+5h               -> 75% OVERLAP

v24's permutation test shuffles `previous_context` while treating all
rows as exchangeable. That is valid for 15m and 1h, but NOT for 4h:
with 75% window overlap, adjacent 4h observations are largely the same
price move re-measured, so the effective sample is roughly a quarter of
the nominal one. The permutation null is then too narrow and the
apparent significance too generous.

This is the same autocorrelation problem that motivated Option A in
Phase C (a house rule of this project), applied here to the candidate
level rather than the trade level.

Note the pattern this predicts, and which v24 actually showed:
    15m (no overlap):  exceeded chance
    1h  (no overlap):  within chance
    4h  (75% overlap): exceeded chance  <- the suspect one

Test: re-run v24's spread statistic and permutation test on
NON-OVERLAPPING subsamples. For 4h, that means taking every 4th hourly
candidate (4 disjoint offsets, all reported, so the result cannot rest
on one lucky slice). 15m and 1h are re-run unchanged as controls -- if
the method is sound they should reproduce v24.

Purely diagnostic; proposes no rule. Discovery only (2020-2025).

Usage:
    .venv/bin/python scripts/discovery_v25_transition_overlap_check.py
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
from discovery_v24_state_transitions import spread_statistic, MIN_CELL_N

N_PERMUTATIONS = 200
RNG_SEED = 20260727
# horizon -> hours of overlap between consecutive hourly candidates
STRIDE = {"15m": 1, "1h": 1, "4h": 4}


def permutation_result(df: pd.DataFrame, horizon: str, rng) -> dict:
    observed = spread_statistic(df, horizon)
    if np.isnan(observed):
        return {"observed": float("nan"), "n": len(df)}
    work = df.copy()
    null = []
    for _ in range(N_PERMUTATIONS):
        work["_shuf"] = rng.permutation(work["prev_context"].values)
        v = spread_statistic(work, horizon, prev_col="_shuf")
        if not np.isnan(v):
            null.append(v)
    null = np.array(null)
    return {"observed": observed, "n": len(df), "null_mean": null.mean(),
            "null_p95": np.quantile(null, 0.95), "pct": (null < observed).mean() * 100}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/reports/discovery_v25_transition_overlap_check.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = dr.load_candidates([args.historical]).sort_values("timestamp").reset_index(drop=True)
    df["prev_context"] = df["context"].shift(1)
    gap_ok = df["timestamp"].diff() == pd.Timedelta(hours=1)
    df.loc[~gap_ok, "prev_context"] = np.nan
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[(df["timestamp"] < cutoff) & df["prev_context"].notna()].copy().reset_index(drop=True)
    print(f"Discovery candidates: {len(disc):,}")

    rng = np.random.default_rng(RNG_SEED)
    lines = [
        "## Non-overlapping re-test of discovery_v24's permutation result\n",
        "15m and 1h have no window overlap between consecutive hourly "
        "candidates and are re-run unchanged as method controls. 4h "
        "overlaps 75%, so it is re-run on each of the 4 disjoint "
        "every-4th-hour subsamples — all four reported, so no single "
        "lucky slice can carry the conclusion.\n",
        "| Horizon | Subsample | n | Observed | Null mean | Null 95th | Pct | Verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for horizon in ["15m", "1h", "4h"]:
        stride = STRIDE[horizon]
        for offset in range(stride):
            sub = disc.iloc[offset::stride].copy() if stride > 1 else disc
            label = "full (no overlap)" if stride == 1 else f"offset {offset}/4"
            r = permutation_result(sub, horizon, rng)
            if np.isnan(r["observed"]):
                lines.append(f"| {horizon} | {label} | {r['n']:,} | insufficient cells | | | | |")
                continue
            verdict = ("**exceeds chance**" if r["pct"] > 95
                       else "within chance" if r["pct"] > 5 else "below chance")
            lines.append(
                f"| {horizon} | {label} | {r['n']:,} | {r['observed']*100:.4f}pp | "
                f"{r['null_mean']*100:.4f}pp | {r['null_p95']*100:.4f}pp | "
                f"{r['pct']:.1f} | {verdict} |")
            print(f"  {horizon} {label}: pct={r['pct']:.1f}")

    lines.append(
        "\n**How to read this:** if 4h exceeds chance on all four disjoint "
        "subsamples, the v24 finding survives the overlap correction. If "
        "it exceeds on none or only some, v24's 4h result was inflated by "
        "re-measuring the same price moves, and the honest summary of the "
        "transition work becomes 15m-only — a much weaker claim, since 1h "
        "already sat within chance.\n"
    )

    header = (
        "# Discovery v25 — overlap check on the state-transition finding\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "discovery_v24 reported that transition origin exceeds chance at "
        "15m and 4h but not 1h. Consecutive hourly candidates have "
        "**75% overlapping 4h forward windows** (none at 15m/1h), so v24's "
        "permutation test — which treats rows as exchangeable — has a "
        "null that is too narrow at 4h specifically. That is the same "
        "autocorrelation problem Option A was introduced to handle in "
        "Phase C. This re-tests on non-overlapping subsamples. Purely "
        "diagnostic. Discovery only (2020-2025).\n\n"
        "---\n\n"
    )
    full = header + "\n".join(lines) + "\n"

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
