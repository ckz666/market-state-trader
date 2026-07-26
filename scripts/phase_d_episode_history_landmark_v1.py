"""
Phase D episode-history landmark v1 -- does `episode_count_so_far(t)`
(a properly live-observable version of phase_d_episode_reentry_v1.py's
whole-hold episode count) carry information about the eventual outcome?

Per the project discussion: phase_d_episode_reentry_v1.py showed episode
count/re-entry matters a great deal (81.6% -> 26.2% win rate across 0 to
4+ total episodes; 78.6% vs. 28.8% for no-re-entry vs. re-entry among
recovered-episode-1 trades) -- but that count is only fully known at the
4h close, the same hindsight problem phase_d_recovery_window_v1.py fixed
for "never recovered by close". This script reconstructs the same
information using ONLY the price path observable up to a given checkpoint
t (never looking past t), for t in {1h, 2h, 3h}:

    episode_count_so_far(t) = number of deep episodes that have already
        STARTED AND ENDED (recovered) strictly within (entry, t] -- an
        episode still open exactly at t is not counted here.
    currently_deep(t) = is the trade below the deep threshold AT t.

Two tables:
  A. P(winner | episode_count_so_far(t), t) -- the direct live-observable
     analogue of phase_d_episode_reentry_v1.py's section A.
  B. P(winner | path-state, t) -- a 6-way state combining episode count
     and current status (stable / in episode 1 / recovered-no-reentry /
     in episode 2 / recovered-2+ / in episode 3+), approximating the
     "transition" table from the project discussion using a checkpoint
     snapshot (a full transition-event table is a further step, not
     built here).

Still purely descriptive. No `w`, no Action Class, no exit rule is
chosen here. Same frozen deep threshold (Def 1, -0.75%) and population
(decision_rule_v1's actual Discovery trades) as the rest of Phase D.
Discovery only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/phase_d_episode_history_landmark_v1.py
"""
import argparse
import bisect
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from discovery_report import load_candidates
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile
from decision_rule_v1 import apply_decision_rule
from phase_c_baseline_v1 import load_1m_price_series, simulate
from phase_c_trade_path_analysis_v4 import MIN_CELL_N
from phase_d_recovery_state_v1 import DEEP_THRESHOLD

CHECKPOINT_MINUTES = [("1h", 60), ("2h", 120), ("3h", 180)]
EPISODE_COUNT_BUCKETS = [0, 1, 2, 3]  # last bucket is "3+"


def episode_state_at(entry_ts, entry_price: float, price_history: dict, sorted_ts: list, t_minutes: int):
    """Uses ONLY the price path from entry up to t_minutes -- never looks
    past it. Returns None if there isn't enough path data at t."""
    entry_ms = int(entry_ts.timestamp() * 1000)
    lo = bisect.bisect_left(sorted_ts, entry_ms)
    hi = bisect.bisect_right(sorted_ts, entry_ms + t_minutes * 60_000)
    path_ts = sorted_ts[lo:hi]
    if len(path_ts) < 2:
        return None

    completed = 0
    was_below = False
    for ts in path_ts:
        ret = (price_history[ts] - entry_price) / entry_price
        below_now = ret <= DEEP_THRESHOLD
        if was_below and not below_now:
            completed += 1
        was_below = below_now

    return {"episode_count_so_far": completed, "currently_deep": was_below}


def path_state_label(episode_count_so_far: int, currently_deep: bool) -> str:
    if episode_count_so_far == 0:
        return "in episode 1 (ongoing)" if currently_deep else "0: stable, never deep"
    if episode_count_so_far == 1:
        return "in episode 2 / re-entry (ongoing)" if currently_deep else "recovered after 1 episode, no re-entry"
    return "in episode 3+ (ongoing)" if currently_deep else "recovered after 2+ episodes"


def build_landmark_frame(trades: list, price_history: dict, sorted_ts: list) -> pd.DataFrame:
    rows = []
    for t in trades:
        row = {"net_return": t["net_return"]}
        for label, minutes in CHECKPOINT_MINUTES:
            st = episode_state_at(t["entry_ts"], t["entry_price"], price_history, sorted_ts, minutes)
            if st is None:
                continue
            row[f"episode_count_{label}"] = st["episode_count_so_far"]
            row[f"currently_deep_{label}"] = st["currently_deep"]
        rows.append(row)
    return pd.DataFrame(rows)


def _cell(sub: pd.Series):
    n = len(sub)
    if n < MIN_CELL_N:
        return f"n={n}"
    return f"{(sub > 0).mean()*100:.1f}% (n={n})"


def section_a(df: pd.DataFrame) -> str:
    lines = [
        "## A. P(winner | episode_count_so_far(t), t) -- live-observable\n",
        "Live-observable analogue of phase_d_episode_reentry_v1.py's "
        "section A: episodes counted only up to t, not over the whole "
        "hold.\n",
        "| t | 0 episodes | 1 episode | 2 episodes | 3+ episodes |",
        "|---|---|---|---|---|",
    ]
    for label, _ in CHECKPOINT_MINUTES:
        col = f"episode_count_{label}"
        if col not in df.columns:
            continue
        row_cells = []
        for n_ep in EPISODE_COUNT_BUCKETS:
            if n_ep == EPISODE_COUNT_BUCKETS[-1]:
                mask = df[col] >= n_ep
            else:
                mask = df[col] == n_ep
            row_cells.append(_cell(df.loc[mask, "net_return"]))
        lines.append(f"| {label} | " + " | ".join(row_cells) + " |")
    return "\n".join(lines) + "\n"


def section_b(df: pd.DataFrame) -> str:
    lines = [
        "## B. P(winner | path-state, t) -- checkpoint snapshot of history + current status\n",
        "Combines episode_count_so_far(t) with whether the trade is "
        "CURRENTLY deep at t into one of six path-states.\n",
        "| t | Path-state | n | P(Winner) |",
        "|---|---|---|---|",
    ]
    state_order = [
        "0: stable, never deep",
        "in episode 1 (ongoing)",
        "recovered after 1 episode, no re-entry",
        "in episode 2 / re-entry (ongoing)",
        "recovered after 2+ episodes",
        "in episode 3+ (ongoing)",
    ]
    for label, _ in CHECKPOINT_MINUTES:
        ep_col, deep_col = f"episode_count_{label}", f"currently_deep_{label}"
        if ep_col not in df.columns:
            continue
        states = df.apply(lambda r: path_state_label(r[ep_col], r[deep_col]), axis=1)
        for state in state_order:
            mask = states == state
            n = int(mask.sum())
            if n == 0:
                continue
            lines.append(f"| {label} | {state} | {n} | {_cell(df.loc[mask, 'net_return'])} |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_d_episode_history_landmark_v1.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()  # Discovery only

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    disc_lpl_q = apply_quintile(disc["local_price_location"], lpl_edges)
    disc_vol_q = apply_quintile(disc["volatility_atr_norm"], vol_edges)
    disc_decision = apply_decision_rule(disc_lpl_q, disc_vol_q)

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    signals = disc[disc_decision == "long_candidate"].sort_values("timestamp")
    trades, _ = simulate(signals, price_history, sorted_ts)
    print(f"decision_rule_v1 Discovery trades: {len(trades)}")
    landmark_df = build_landmark_frame(trades, price_history, sorted_ts)

    body = section_a(landmark_df) + "\n---\n\n" + section_b(landmark_df)

    header = (
        "# Phase D episode-history landmark v1 -- live-observable episode_count_so_far(t)\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Still not a position-management rule; no `w` or Action Class is "
        "chosen here. Fixes phase_d_episode_reentry_v1.py's hindsight "
        "problem (whole-hold episode count) by reconstructing "
        "`episode_count_so_far(t)` using only the path observable up to "
        "t. Same frozen deep threshold (Def 1, "
        f"{DEEP_THRESHOLD*100:.2f}%) and population (decision_rule_v1's "
        f"actual Discovery trades) as the rest of Phase D. Cells with "
        f"n < {MIN_CELL_N} are marked instead of reported. 2026 untouched.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
