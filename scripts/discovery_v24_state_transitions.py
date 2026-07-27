"""
Discovery v24 — state transitions: does the ORIGIN of the current market
state carry information the current state alone does not?

`context` (the 5-regime classifier: continuation / mean_reversion /
extended / compressed / transition) is stored for all 57,565 candidates
and was tested by discovery_v1 as a STATIC categorical dimension only.
Transitions between states have never been examined. 22.1% of candidates
involve a state change, giving 25 distinct transitions.

THE CENTRAL QUESTION, per the project discussion — not "which transition
predicts returns" (that invites picking the best of 25 x 3 horizons = 75
cells) but the model-comparison question:

    Model A:  current_context                  -> forward return
    Model B:  previous_context x current_context -> forward return

    Does B carry information beyond A?

Sections:
  A. Full transition matrix with forward-return stats per cell.
  B. The model comparison: within each current_context, how much do
     outcomes vary by origin? If origin is uninformative, all origins
     leading into the same current state should look alike.
  C. PERMUTATION TEST. With 25 transitions and small off-diagonal cells,
     *some* spread appears by chance. `previous_context` is shuffled
     (breaking any real link to the outcome while preserving both
     marginal distributions and all cell sizes) and the section-B spread
     statistic is recomputed 200 times. The observed value is reported
     against that null distribution. Without this the section-B numbers
     are uninterpretable.

Purely descriptive; does not change decision_rule_v1 and proposes no
rule. Discovery only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v24_state_transitions.py
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

MIN_CELL_N = 100  # transitions are candidate-level (n=52k), so a strict floor
HORIZONS = ["15m", "1h", "4h"]
N_PERMUTATIONS = 200
RNG_SEED = 20260727


def spread_statistic(df: pd.DataFrame, horizon: str, prev_col: str = "prev_context") -> float:
    """Mean, across current states, of the (max - min) median forward
    return over origins with enough samples. Higher = origin matters more."""
    spreads = []
    for cur, g in df.groupby("context"):
        meds = []
        for _, gg in g.groupby(prev_col):
            s = gg[f"fwd_{horizon}"].dropna()
            if len(s) >= MIN_CELL_N:
                meds.append(s.median())
        if len(meds) >= 2:
            spreads.append(max(meds) - min(meds))
    return float(np.mean(spreads)) if spreads else float("nan")


def section_matrix(df: pd.DataFrame, horizon: str) -> str:
    states = sorted(df["context"].dropna().unique())
    lines = [f"**Median {horizon} forward return — rows: previous state, columns: current state**\n",
             "| from \\ to | " + " | ".join(states) + " |",
             "|---|" + "---|" * len(states)]
    for prev in states:
        row = [prev]
        for cur in states:
            s = df.loc[(df["prev_context"] == prev) & (df["context"] == cur), f"fwd_{horizon}"].dropna()
            row.append(f"n={len(s)}" if len(s) < MIN_CELL_N
                       else f"{s.median()*100:+.4f}% (n={len(s):,})")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def section_model_comparison(df: pd.DataFrame) -> str:
    lines = [
        "## B. Model A vs. Model B — does origin add information?\n",
        "For each current state: the median forward return of the state "
        "overall (Model A), and the range across the origins leading into "
        "it (Model B). A wide range means the same current state behaves "
        "differently depending on where it came from.\n",
    ]
    for horizon in HORIZONS:
        lines.append(f"\n**Horizon {horizon}**\n")
        lines.append("| Current state | n total | Model A median | Best origin | Worst origin | Range |")
        lines.append("|---|---|---|---|---|---|")
        for cur, g in df.groupby("context"):
            overall = g[f"fwd_{horizon}"].dropna()
            rows = []
            for prev, gg in g.groupby("prev_context"):
                s = gg[f"fwd_{horizon}"].dropna()
                if len(s) >= MIN_CELL_N:
                    rows.append((s.median(), prev, len(s)))
            if len(rows) < 2:
                lines.append(f"| {cur} | {len(overall):,} | {overall.median()*100:+.4f}% | (too few origins) | | |")
                continue
            rows.sort(reverse=True)
            best, worst = rows[0], rows[-1]
            lines.append(
                f"| {cur} | {len(overall):,} | {overall.median()*100:+.4f}% | "
                f"{best[1]} {best[0]*100:+.4f}% (n={best[2]:,}) | "
                f"{worst[1]} {worst[0]*100:+.4f}% (n={worst[2]:,}) | "
                f"**{(best[0]-worst[0])*100:.4f}pp** |")
    return "\n".join(lines) + "\n"


def section_permutation(df: pd.DataFrame) -> str:
    rng = np.random.default_rng(RNG_SEED)
    lines = [
        "## C. Permutation test — is that spread more than chance?\n",
        f"`previous_context` is shuffled {N_PERMUTATIONS} times (destroying "
        "any real origin-outcome link while preserving both marginal "
        "distributions). The section-B spread statistic — mean across "
        "current states of (best origin median − worst origin median) — is "
        "recomputed each time. If the observed value sits inside the null "
        "distribution, the apparent structure in sections A/B is what 25 "
        "transitions produce by chance.\n",
        "| Horizon | Observed spread | Null mean | Null 95th pct | Percentile of observed | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    work = df.copy()
    for horizon in HORIZONS:
        observed = spread_statistic(work, horizon)
        null = []
        for _ in range(N_PERMUTATIONS):
            work["_shuf"] = rng.permutation(work["prev_context"].values)
            null.append(spread_statistic(work, horizon, prev_col="_shuf"))
        null = np.array([x for x in null if not np.isnan(x)])
        pct = (null < observed).mean() * 100
        verdict = ("**exceeds chance (>95th pct)**" if pct > 95
                   else "within chance" if pct > 5 else "below chance")
        lines.append(
            f"| {horizon} | {observed*100:.4f}pp | {null.mean()*100:.4f}pp | "
            f"{np.quantile(null, 0.95)*100:.4f}pp | {pct:.1f} | {verdict} |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/reports/discovery_v24_state_transitions.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = dr.load_candidates([args.historical]).sort_values("timestamp").reset_index(drop=True)

    # previous state = the state one hour earlier; only valid where the
    # preceding candidate really is the adjacent hour (no data gap)
    df["prev_context"] = df["context"].shift(1)
    gap_ok = df["timestamp"].diff() == pd.Timedelta(hours=1)
    df.loc[~gap_ok, "prev_context"] = np.nan

    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[(df["timestamp"] < cutoff) & df["prev_context"].notna()].copy()
    changed = (disc["context"] != disc["prev_context"]).mean()
    print(f"Discovery candidates with a valid previous state: {len(disc):,} "
          f"({changed*100:.1f}% involve a state change)")

    body = "## A. Transition matrix\n\n"
    for horizon in HORIZONS:
        body += section_matrix(disc, horizon) + "\n"
    body += "\n---\n\n" + section_model_comparison(disc)
    print("Running permutation test...")
    body += "\n---\n\n" + section_permutation(disc)

    header = (
        "# Discovery v24 — state transitions: does origin matter?\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "> **CORRECTION — read `discovery_v25_transition_overlap_check.md` "
        "alongside this report.** Section C's permutation test treats rows "
        "as exchangeable, which is valid at 15m and 1h but NOT at 4h: "
        "consecutive hourly candidates have 75% overlapping 4h forward "
        "windows, making the 4h null too narrow. Re-tested on four "
        "disjoint non-overlapping subsamples, the 4h result does not hold "
        "(percentiles 49.5 / 83.5 / 93.5 / 85.0, none above 95). **The "
        "surviving claim is 15m only** — and that is the smallest of the "
        "three effects. The 4h numbers below are left unchanged as the "
        "record of what the uncorrected test produced.\n\n"
        "`context` was tested by discovery_v1 as a static categorical "
        "dimension; its transitions never were. The question here is not "
        "\"which transition predicts returns\" (25 transitions x 3 "
        "horizons = 75 cells invites cherry-picking) but whether "
        "`previous_context x current_context` carries information beyond "
        "`current_context` alone — with a permutation test to say what "
        "counts as more than chance. Purely descriptive; proposes no "
        f"rule. Discovery only (2020-2025); 2026 untouched. Cells below "
        f"n={MIN_CELL_N} are marked instead of reported.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
