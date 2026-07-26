"""
Phase D episode-reentry v1 -- does re-entering the deep state after
recovering from it carry information beyond having recovered once? Per
the project discussion following phase_d_path_state_hypothesis.md SS18:
the 40% re-entry rate found in the verification pass (SS17) shows
"recovered" is not a terminal state. Before freezing `w` or an Action
Class, this checks two purely descriptive questions on the same frozen
population/threshold as the rest of Phase D:

  A. P(winner) by total number of distinct deep episodes in the trade
     (0, 1, 2, 3, 4+) -- does episode COUNT itself carry information?
  B. Among the 615 Discovery trades that recovered from their FIRST deep
     episode (phase_d_time_in_state3_v1.py's "recovered" population):
     does a trade that goes on to re-enter the deep state (episode 2+)
     have a different eventual win rate than one that never does?

No rule, no `w`, no re-entry-handling decision is made here -- purely
descriptive, to inform that decision. Same frozen deep threshold (Def 1,
-0.75%) and population (decision_rule_v1's actual Discovery trades) as
the rest of Phase D. Discovery only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/phase_d_episode_reentry_v1.py
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
from phase_d_time_in_state3_v1 import HOLD_MINUTES

EPISODE_COUNT_BUCKETS = [0, 1, 2, 3, 4]  # last bucket is "4+"


def detect_episodes(entry_ts, entry_price: float, price_history: dict, sorted_ts: list) -> list:
    """All distinct below-deep-threshold episodes within the 4h hold, in
    chronological order (not just the first, unlike phase_d_time_in_
    state3_v1.first_episode). Each episode: {start_ms, end_ms, censored}
    -- censored=True means still below threshold at the 4h close."""
    entry_ms = int(entry_ts.timestamp() * 1000)
    lo = bisect.bisect_left(sorted_ts, entry_ms)
    hi = bisect.bisect_right(sorted_ts, entry_ms + HOLD_MINUTES * 60_000)
    path_ts = sorted_ts[lo:hi]
    if len(path_ts) < 2:
        return []

    episodes = []
    was_below = False
    cur_start = None
    for ts in path_ts:
        ret = (price_history[ts] - entry_price) / entry_price
        below_now = ret <= DEEP_THRESHOLD
        if below_now and not was_below:
            cur_start = ts
        if not below_now and was_below:
            episodes.append({"start_ms": cur_start, "end_ms": ts, "censored": False})
        was_below = below_now
    if was_below:
        episodes.append({"start_ms": cur_start, "end_ms": path_ts[-1], "censored": True})
    return episodes


def build_episodes_frame(trades: list, price_history: dict, sorted_ts: list) -> pd.DataFrame:
    rows = []
    for t in trades:
        episodes = detect_episodes(t["entry_ts"], t["entry_price"], price_history, sorted_ts)
        rows.append({
            "n_episodes": len(episodes),
            "recovered_first_episode": (len(episodes) >= 1 and not episodes[0]["censored"]),
            "net_return": t["net_return"],
        })
    return pd.DataFrame(rows)


def _cell(sub: pd.Series):
    n = len(sub)
    if n < MIN_CELL_N:
        return f"n={n}"
    return f"{(sub > 0).mean()*100:.1f}% (n={n}), median {sub.median()*100:+.4f}%"


def section_a(df: pd.DataFrame) -> str:
    lines = [
        "## A. P(winner) by total number of distinct deep episodes\n",
        "Does episode COUNT itself (not just whether one ever happened) "
        "carry information about the eventual outcome?\n",
        "| Episodes | n | P(Winner), median |",
        "|---|---|---|",
    ]
    for n_ep in EPISODE_COUNT_BUCKETS:
        if n_ep == EPISODE_COUNT_BUCKETS[-1]:
            mask = df["n_episodes"] >= n_ep
            label = f"{n_ep}+"
        else:
            mask = df["n_episodes"] == n_ep
            label = str(n_ep)
        lines.append(f"| {label} | {mask.sum()} | {_cell(df.loc[mask, 'net_return'])} |")
    return "\n".join(lines) + "\n"


def section_b(df: pd.DataFrame) -> str:
    lines = [
        "## B. Among trades that recovered from episode 1: does re-entry matter?\n",
        "Restricted to the 615 Discovery trades that recovered from "
        "their first deep episode (phase_d_time_in_state3_v1.py's "
        "'recovered' population). Split by whether a second (or later) "
        "deep episode ever happens.\n",
        "| Group | n | P(Winner), median |",
        "|---|---|---|",
    ]
    recovered_ep1 = df[df["recovered_first_episode"]]
    no_reentry = recovered_ep1[recovered_ep1["n_episodes"] == 1]
    reentry = recovered_ep1[recovered_ep1["n_episodes"] >= 2]
    lines.append(f"| no re-entry (exactly 1 episode) | {len(no_reentry)} | {_cell(no_reentry['net_return'])} |")
    lines.append(f"| re-entry (2+ episodes) | {len(reentry)} | {_cell(reentry['net_return'])} |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_d_episode_reentry_v1.md")
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
    episodes_df = build_episodes_frame(trades, price_history, sorted_ts)

    body = section_a(episodes_df) + "\n---\n\n" + section_b(episodes_df)

    header = (
        "# Phase D episode-reentry v1 -- does re-entry carry information beyond first-episode recovery\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Still not a position-management rule; no `w` or Action Class is "
        "chosen here. Same frozen deep threshold (Def 1, "
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
