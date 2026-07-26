"""
Phase D execution-consequences v1 -- what happens AFTER a trade is
classified into a recovery state (S1/S2/S3), on the real decision_rule_v1
Discovery trade set. Still purely descriptive: no exit rule, no partial
reduction, no parameter optimization. Per the project discussion: State 3
is empirically worse (phase_d_recovery_state_v1.py: P(winner) 24/13/5% at
1h/2h/3h) but "worse" is not automatically "exit" -- this script looks at
the actual trade-off between remaining upside and remaining downside
before any management-action hypothesis is written.

Same frozen state definition as phase_d_recovery_state_v1.py (Def 1
recovery, deep threshold -0.75% -- midpoint of the frozen -0.5%/-1.0%
band, not re-fit here), same population (decision_rule_v1's actual
Discovery trades, LPL==Q1 & Vol==Q5), same checkpoints (1h/2h/3h).

Three sections:
  A. Per state, per checkpoint: outcome distribution AND how much further
     the price moved after that checkpoint (remaining MAE/MFE, i.e. the
     running-extremes-from-entry delta between the checkpoint and the 4h
     close -- a lower bound on "how much more could still happen", not a
     fresh from-t price recomputation).
  B. State 3 deep dive: split S3 trades at each checkpoint into eventual
     winners vs. eventual losers, so the size of the "still relevant"
     minority is visible, not just its existence.
  C. Recovery transitions: of trades in S3 at an early checkpoint, what
     fraction have recovered (by the same Def 1 threshold) by a later
     checkpoint, and what's their eventual win rate?

Discovery period only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/phase_d_execution_consequences_v1.py
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
from phase_c_trade_path_analysis_v2 import build_trade_frame
from phase_c_trade_path_analysis_v4 import MIN_CELL_N
from phase_d_recovery_state_v1 import DEEP_THRESHOLD, classify, TIME_ROWS

STATE_LABELS = ["1: never deep", "2: deep, recovered", "3: deep, still impaired"]
LATER_CHECKPOINTS = {"1h": ["2h", "3h", "4h"], "2h": ["3h", "4h"], "3h": ["4h"]}


def _cell_stats(sub: pd.Series):
    n = len(sub)
    if n < MIN_CELL_N:
        return n, None
    return n, {
        "wr": (sub > 0).mean(),
        "median": sub.median(),
        "mean": sub.mean(),
        "p05": sub.quantile(0.05),
    }


def section_a(trade_df: pd.DataFrame) -> str:
    lines = [
        "## A. Outcome and remaining path, by state and checkpoint\n",
        "'Remaining MAE/MFE' = mae_4h - mae_t / mfe_4h - mfe_t: how much "
        "FURTHER the running extremes (from entry) moved between "
        "checkpoint t and the 4h close. Not a fresh from-t recomputation "
        "-- a lower bound on how much more happened after t, in the same "
        "entry-relative units used throughout Phase C/D.\n",
        "| Time | State | n | P(Winner) | Median return | Mean return | P05 | Median remaining MAE | Median remaining MFE |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t_label in TIME_ROWS:
        mae_col, mfe_col = f"mae_{t_label}", f"mfe_{t_label}"
        if trade_df.empty or mae_col not in trade_df.columns:
            continue
        state = classify(trade_df, t_label)
        for label in STATE_LABELS:
            mask = state == label
            n, stats = _cell_stats(trade_df.loc[mask, "net_return"])
            if stats is None:
                lines.append(f"| {t_label} | {label} | {n} | n too few | - | - | - | - | - |")
                continue
            sub = trade_df.loc[mask]
            rem_mae = (sub["mae_4h"] - sub[mae_col]).median()
            rem_mfe = (sub["mfe_4h"] - sub[mfe_col]).median()
            lines.append(
                f"| {t_label} | {label} | {n} | {stats['wr']*100:.1f}% | "
                f"{stats['median']*100:+.4f}% | {stats['mean']*100:+.4f}% | "
                f"{stats['p05']*100:+.2f}% | {rem_mae*100:+.4f}% | {rem_mfe*100:+.4f}% |"
            )
    return "\n".join(lines) + "\n"


def section_b(trade_df: pd.DataFrame) -> str:
    lines = [
        "## B. State 3 deep dive: eventual winners vs. losers\n",
        "Among trades classified as State 3 (deep, still impaired) at "
        "each checkpoint: how big is the eventual-winner minority, and "
        "how does its return compare to the eventual-loser majority?\n",
        "| Time | Outcome | n | % of State 3 | Median return | Mean return | P05 |",
        "|---|---|---|---|---|---|---|",
    ]
    for t_label in TIME_ROWS:
        mae_col = f"mae_{t_label}"
        if trade_df.empty or mae_col not in trade_df.columns:
            continue
        state = classify(trade_df, t_label)
        s3 = trade_df.loc[state == "3: deep, still impaired"]
        n_s3 = len(s3)
        if n_s3 == 0:
            continue
        for outcome_label, mask in [("eventual winner", s3["net_return"] > 0),
                                     ("eventual loser", s3["net_return"] <= 0)]:
            sub = s3.loc[mask, "net_return"]
            n = len(sub)
            if n < MIN_CELL_N:
                lines.append(f"| {t_label} | {outcome_label} | {n} | {n/n_s3*100:.1f}% | n too few | - | - |")
                continue
            lines.append(
                f"| {t_label} | {outcome_label} | {n} | {n/n_s3*100:.1f}% | "
                f"{sub.median()*100:+.4f}% | {sub.mean()*100:+.4f}% | {sub.quantile(0.05)*100:+.2f}% |"
            )
    return "\n".join(lines) + "\n"


def section_c(trade_df: pd.DataFrame) -> str:
    lines = [
        "## C. Recovery transitions out of State 3\n",
        "Of trades in State 3 at an early checkpoint, what fraction have "
        "recovered (Def 1: DD_current back above the deep threshold) by "
        "a later checkpoint -- and what's the eventual win rate of the "
        "still-impaired remainder at that later point?\n",
        "| From (State 3 @) | To checkpoint | n (State 3 @ from) | Recovered by 'to' | Still impaired at 'to' |",
        "|---|---|---|---|---|",
    ]
    for from_t in ["1h", "2h", "3h"]:
        mae_from = f"mae_{from_t}"
        if trade_df.empty or mae_from not in trade_df.columns:
            continue
        state_from = classify(trade_df, from_t)
        s3 = trade_df.loc[state_from == "3: deep, still impaired"]
        n_s3 = len(s3)
        if n_s3 == 0:
            continue
        for to_t in LATER_CHECKPOINTS[from_t]:
            ret_to = f"ret_{to_t}"
            if ret_to not in s3.columns:
                continue
            recovered_mask = s3[ret_to] > DEEP_THRESHOLD
            n_rec, stats_rec = _cell_stats(s3.loc[recovered_mask, "net_return"])
            n_imp, stats_imp = _cell_stats(s3.loc[~recovered_mask, "net_return"])
            rec_cell = f"n={n_rec}" if stats_rec is None else f"{stats_rec['wr']*100:.0f}% winrate (n={n_rec})"
            imp_cell = f"n={n_imp}" if stats_imp is None else f"{stats_imp['wr']*100:.0f}% winrate (n={n_imp})"
            lines.append(f"| {from_t} | {to_t} | {n_s3} | {rec_cell} | {imp_cell} |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_d_execution_consequences_v1.md")
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
    trade_df = build_trade_frame(trades, price_history, sorted_ts)

    body = section_a(trade_df) + "\n---\n\n" + section_b(trade_df) + "\n---\n\n" + section_c(trade_df)

    header = (
        "# Phase D execution-consequences v1 -- what follows a recovery-state classification\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Still not a position-management rule. Same frozen state "
        "definition and population as phase_d_recovery_state_v1.py "
        "(Def 1 recovery, deep threshold {:.2f}%, decision_rule_v1's "
        "actual Discovery trades). Looks at the trade-off between "
        "remaining upside and remaining downside per state, rather than "
        "just P(winner), before any exit/partial-reduction hypothesis is "
        "written. Cells with n < {} are marked instead of reported. 2026 "
        "untouched.\n\n"
        "---\n\n".format(DEEP_THRESHOLD * 100, MIN_CELL_N)
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
