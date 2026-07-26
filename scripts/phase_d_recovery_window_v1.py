"""
Phase D recovery-window v1 -- landmark analysis: does the ABSENCE of
recovery by an observation time t (measured relative to when the deep
episode started, t0) carry live-observable information about the eventual
outcome? Per the project discussion: phase_d_time_in_state3_v1.py found
that "never recovered BY THE 4h CLOSE" predicts 0% winners -- but that
fact is only knowable in hindsight, at the close itself, so it cannot be
used as a live signal. The methodologically correct question is a
landmark one:

    P(winner | deep episode started at t0, not yet recovered at t0 + w)

using ONLY information available at t0+w (never peeking past it), for a
range of window widths w. This is still purely descriptive -- no action
is chosen. Same frozen deep threshold (Def 1, -0.75%) and population
(decision_rule_v1's actual Discovery trades) as the rest of Phase D.

Two sections:
  A. Unconditional landmark test: among trades whose deep episode leaves
     enough runway to even observe window w before the 4h close, split
     into "recovered by t0+w" vs. "not yet recovered by t0+w" and report
     P(winner) for each.
  B. Runway-controlled version of A: because a trade that hasn't
     recovered by t0+w mechanically has less time left before the 4h
     close than one that has, section A's effect could just be a runway
     proxy. Section B splits each window's "not yet recovered" group by
     how much runway is actually still left after t0+w, to check whether
     "still not recovered" carries information beyond runway alone.

Usage:
    .venv/bin/python scripts/phase_d_recovery_window_v1.py
"""
import argparse
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
from phase_d_time_in_state3_v1 import HOLD_MINUTES, build_episode_frame

WINDOWS = [15, 30, 60, 90, 120]
RUNWAY_SPLIT = 60  # minutes; "ample" vs. "tight" remaining runway after t0+w


def _cell(sub: pd.Series):
    n = len(sub)
    if n < MIN_CELL_N:
        return f"n={n}"
    return f"{(sub > 0).mean()*100:.1f}% (n={n})"


def section_a(df: pd.DataFrame) -> str:
    lines = [
        "## A. Landmark test: no recovery by t0+w vs. recovered by t0+w\n",
        "Only trades whose deep episode starts early enough that t0+w "
        "still falls within the 4h hold are eligible for a given w (a "
        "trade with no runway left to observe w is excluded from that "
        "row, not counted as 'not recovered'). 'Not yet recovered' uses "
        "only information available at t0+w -- unlike the prior script's "
        "'never recovered by close' cut, this is a live-observable split.\n",
        "| Window w | n eligible | Recovered by t0+w | Not yet recovered by t0+w |",
        "|---|---|---|---|",
    ]
    for w in WINDOWS:
        eligible = df[df["t_enter_min"] <= (HOLD_MINUTES - w)]
        if eligible.empty:
            continue
        recovered = eligible[(~eligible["censored"]) & (eligible["duration_min"] <= w)]
        not_recovered = eligible[eligible["censored"] | (eligible["duration_min"] > w)]
        lines.append(
            f"| {w}m | {len(eligible)} | {_cell(recovered['net_return'])} | "
            f"{_cell(not_recovered['net_return'])} |"
        )
    return "\n".join(lines) + "\n"


def section_b(df: pd.DataFrame) -> str:
    lines = [
        "## B. Runway-controlled: is 'not yet recovered' just a runway proxy?\n",
        f"Within each window's 'not yet recovered by t0+w' group, split by "
        f"how much runway remains after t0+w (>= {RUNWAY_SPLIT}m left vs. "
        f"< {RUNWAY_SPLIT}m left before the 4h close). If the win rate "
        "still drops within the 'ample runway left' rows too, 'not yet "
        "recovered' carries information beyond just having less time -- "
        "if it only drops in the 'tight runway' rows, the effect may "
        "just be the runway confound already seen in the t_enter split.\n",
        "| Window w | Runway left after t0+w | n | P(Winner) |",
        "|---|---|---|---|",
    ]
    for w in WINDOWS:
        eligible = df[df["t_enter_min"] <= (HOLD_MINUTES - w)]
        if eligible.empty:
            continue
        not_recovered = eligible[eligible["censored"] | (eligible["duration_min"] > w)]
        if not_recovered.empty:
            continue
        runway_left = HOLD_MINUTES - (not_recovered["t_enter_min"] + w)
        ample = not_recovered[runway_left >= RUNWAY_SPLIT]
        tight = not_recovered[runway_left < RUNWAY_SPLIT]
        lines.append(f"| {w}m | >= {RUNWAY_SPLIT}m ample | {len(ample)} | {_cell(ample['net_return'])} |")
        lines.append(f"| {w}m | < {RUNWAY_SPLIT}m tight | {len(tight)} | {_cell(tight['net_return'])} |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_d_recovery_window_v1.md")
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
    episode_df = build_episode_frame(trades, price_history, sorted_ts)

    body = section_a(episode_df) + "\n---\n\n" + section_b(episode_df)

    header = (
        "# Phase D recovery-window v1 -- landmark test: does absence of recovery predict outcome LIVE\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Still not a position-management rule. Tests "
        "`P(winner | deep episode started at t0, not yet recovered at "
        "t0+w)` using only information available at t0+w (a proper "
        "landmark cut, not the 'never recovered by close' hindsight cut "
        "from phase_d_time_in_state3_v1.py). Same frozen deep threshold "
        f"(Def 1, {DEEP_THRESHOLD*100:.2f}%) and population "
        "(decision_rule_v1's actual Discovery trades) as the rest of "
        f"Phase D. Cells with n < {MIN_CELL_N} are marked instead of "
        "reported. 2026 untouched.\n\n"
        "**Caveat, quantified in phase_d_time_in_state3_v1.md's re-entry "
        "check:** 'recovered by t0+w' here means recovered from the "
        "FIRST deep episode, not 'clear for the rest of the hold' -- "
        "40.0% of first-episode 'recovered' trades (246/615) are back "
        "at/below the deep threshold again by the 4h close. This likely "
        "means the true gap between a genuinely-clear path and a "
        "not-yet-recovered one is understated here, not overstated: the "
        "'recovered' column in section A is diluted by this ~40% "
        "backslide fraction rather than representing a clean population.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
