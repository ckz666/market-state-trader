"""
Phase D time-in-state-3 v1 -- does duration IN the impaired state (not
just being in it) predict the eventual outcome? Per the project
discussion: phase_d_execution_consequences_v1.py showed P(winner|S3)
decays with elapsed checkpoint time (24.4% @1h -> 4.6% @3h) and so does
the recovery-transition rate. This script tests the more precise
hypothesis directly: `duration_in_state_3`, measured on the 1-minute
price path (not the 15m/30m/1h/2h/3h/4h checkpoint grid used so far), as
its own variable -- per phase_d_path_state_hypothesis.md SS13/14.

Still purely descriptive. No action (exit/reduction/anything) is chosen
here. Same frozen deep threshold (Def 1, -0.75%, midpoint of the frozen
-0.5%/-1.0% band) and population (decision_rule_v1's actual Discovery
trades, LPL==Q1 & Vol==Q5) as phase_d_recovery_state_v1.py.

For every trade whose running MAE reaches the deep threshold at some
point within its 4h hold:
    t_enter  = the first minute the running return (from entry) crosses
               AT OR BELOW the deep threshold (well-defined and unique,
               since running MAE is monotonically non-increasing).
    t_recover = the first minute AFTER t_enter that the return crosses
               back ABOVE the deep threshold (Def 1), if this happens
               before the 4h close.
    duration_in_state_3 = t_recover - t_enter, in minutes.

Trades where no such t_recover exists before the 4h close are a separate,
CENSORED group ("never recovered within the hold") -- not merged into the
duration buckets, since "never recovered" is not on the same scale as
"recovered slowly." Only the FIRST deep episode per trade is measured;
a trade that recovers and later re-enters the deep threshold a second
time is not re-measured here (out of scope, noted as a limitation).

Usage:
    .venv/bin/python scripts/phase_d_time_in_state3_v1.py
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

HOLD_MINUTES = 240
DURATION_BUCKETS = [(0, 15, "<15m"), (15, 30, "15-30m"), (30, 60, "30-60m"),
                     (60, 120, "60-120m"), (120, 240, "120-240m")]


def first_episode(entry_ts, entry_price: float, price_history: dict, sorted_ts: list):
    """Returns None if the trade never reaches the deep threshold within
    its 4h hold. Otherwise a dict with t_enter_min (minutes from entry),
    duration_min (minutes from t_enter to recovery or to the 4h close),
    and censored (True if it never recovers within the hold)."""
    entry_ms = int(entry_ts.timestamp() * 1000)
    lo = bisect.bisect_left(sorted_ts, entry_ms)
    hi = bisect.bisect_right(sorted_ts, entry_ms + HOLD_MINUTES * 60_000)
    path_ts = sorted_ts[lo:hi]
    if len(path_ts) < 2:
        return None

    t_enter_ms = None
    t_recover_ms = None
    for ts in path_ts:
        ret = (price_history[ts] - entry_price) / entry_price
        if t_enter_ms is None:
            if ret <= DEEP_THRESHOLD:
                t_enter_ms = ts
        else:
            if ret > DEEP_THRESHOLD:
                t_recover_ms = ts
                break

    if t_enter_ms is None:
        return None  # never entered the deep state at all

    if t_recover_ms is not None:
        return {
            "t_enter_min": (t_enter_ms - entry_ms) / 60_000,
            "duration_min": (t_recover_ms - t_enter_ms) / 60_000,
            "censored": False,
        }
    return {
        "t_enter_min": (t_enter_ms - entry_ms) / 60_000,
        "duration_min": (path_ts[-1] - t_enter_ms) / 60_000,
        "censored": True,
    }


def build_episode_frame(trades: list, price_history: dict, sorted_ts: list) -> pd.DataFrame:
    rows = []
    for t in trades:
        ep = first_episode(t["entry_ts"], t["entry_price"], price_history, sorted_ts)
        if ep is None:
            continue
        rows.append({**ep, "net_return": t["net_return"]})
    return pd.DataFrame(rows)


def _cell(sub: pd.Series):
    n = len(sub)
    if n < MIN_CELL_N:
        return f"n={n}"
    wr = (sub > 0).mean()
    return f"{wr*100:.1f}% (n={n}), median {sub.median()*100:+.4f}%, mean {sub.mean()*100:+.4f}%, P05 {sub.quantile(0.05)*100:+.2f}%"


def section(df: pd.DataFrame) -> str:
    lines = [
        f"n trades ever reaching the deep threshold within the 4h hold: {len(df)}\n",
        "| Group | n | P(Winner), median/mean/P05 |",
        "|---|---|---|",
    ]
    recovered = df[~df["censored"]]
    censored = df[df["censored"]]
    for lo, hi, label in DURATION_BUCKETS:
        mask = (recovered["duration_min"] >= lo) & (recovered["duration_min"] < hi)
        sub = recovered.loc[mask, "net_return"]
        lines.append(f"| recovered, duration {label} | {len(sub)} | {_cell(sub)} |")
    lines.append(f"| **never recovered within 4h (censored)** | {len(censored)} | {_cell(censored['net_return'])} |")
    return "\n".join(lines) + "\n"


def section_t_enter(df: pd.DataFrame) -> str:
    """Secondary check: does WHEN the trade first goes deep (t_enter_min)
    confound the duration effect? E.g. trades entering the deep state
    very late have less remaining time to recover by construction."""
    lines = [
        "Secondary check: trades that first reach the deep threshold "
        "LATE in the hold have mechanically less remaining time to "
        "recover, which could confound the duration bucketing above if "
        "late-entering trades cluster into 'never recovered.' Split by "
        "when the deep episode started:\n",
        "| First reached deep threshold at | n | Never recovered within hold | P(Winner) overall |",
        "|---|---|---|---|",
    ]
    t_buckets = [(0, 60, "0-1h"), (60, 120, "1-2h"), (120, 180, "2-3h"), (180, 240, "3-4h")]
    for lo, hi, label in t_buckets:
        mask = (df["t_enter_min"] >= lo) & (df["t_enter_min"] < hi)
        sub = df.loc[mask]
        n = len(sub)
        if n == 0:
            continue
        n_censored = int(sub["censored"].sum())
        overall = _cell(sub["net_return"])
        lines.append(f"| {label} | {n} | {n_censored} ({n_censored/n*100:.0f}%) | {overall} |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_d_time_in_state3_v1.md")
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

    body = (
        "## Duration-in-state-3 vs. eventual outcome\n\n" + section(episode_df) +
        "\n---\n\n## When the deep episode starts (confound check)\n\n" + section_t_enter(episode_df)
    )

    header = (
        "# Phase D time-in-state-3 v1 -- duration in the impaired state vs. eventual outcome\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Still not a position-management rule. Measures `duration_in_"
        "state_3` from the 1-minute price path (finer than the checkpoint "
        "grid used in phase_c/phase_d v1-v4): minutes from the first "
        "crossing at/below the deep threshold ({:.2f}%, Def 1, same as "
        "phase_d_recovery_state_v1.py) to the first subsequent crossing "
        "back above it, for decision_rule_v1's actual Discovery trades. "
        "Trades that never recover within the 4h hold are reported as a "
        "separate censored group, not folded into the duration buckets. "
        "Only the first deep episode per trade is measured (re-entries "
        "after a recovery are out of scope here). Cells with n < {} are "
        "marked instead of reported. 2026 untouched.\n\n"
        "---\n\n".format(DEEP_THRESHOLD * 100, MIN_CELL_N)
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
