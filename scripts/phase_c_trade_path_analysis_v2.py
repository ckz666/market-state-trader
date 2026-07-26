"""
Phase C trade-path analysis v2 — time-dependent MAE/MFE and conditional
win probability given drawdown depth. Per the project discussion: still
NOT stop-loss optimization. v1 established that winners and losers
diverge from the first checkpoint (15m) and that losers are broadly (not
just tail-outlier) worse, not just deeper on average. This asks how EARLY
and how RELIABLY that divergence can be read while a trade is still open.

Same exact trades as phase_c_baseline_v1.py / phase_c_trade_path_analysis.py
(same signals, same Option A logic, same entry/exit) — no new trade
selection.

  1. Time-dependent MAE/MFE: not just the final (over the whole 4h hold)
     MAE/MFE from v1, but the RUNNING MAE/MFE up to each checkpoint
     (15m/30m/1h/2h/3h/4h) — winners vs. losers, both periods.
  2. Winner drawdown-depth histogram: v1 found 90.5% of winners dip
     negative at some point — how deep, typically? Bucketed distribution
     of winners' full-trade MAE.
  3. P(eventual winner | trade has drawn down at least X% at some point):
     for a set of drawdown thresholds, the win rate among only the trades
     that ever reached that much adverse excursion. Purely descriptive —
     no threshold is chosen or recommended as a stop here.

Usage:
    .venv/bin/python scripts/phase_c_trade_path_analysis_v2.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bisect
import numpy as np
import pandas as pd

from discovery_report import load_candidates
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile
from decision_rule_v1 import apply_decision_rule
from phase_c_baseline_v1 import load_1m_price_series, simulate
import mst_config as config

CHECKPOINTS = [("15m", 15), ("30m", 30), ("1h", 60), ("2h", 120), ("3h", 180), ("4h", 240)]
DRAWDOWN_THRESHOLDS = [-0.0025, -0.005, -0.01, -0.015, -0.02, -0.03]
MAE_BUCKETS = [(0.0, -0.0025, "0 to -0.25%"), (-0.0025, -0.005, "-0.25% to -0.5%"),
               (-0.005, -0.01, "-0.5% to -1.0%"), (-0.01, -0.02, "-1.0% to -2.0%"),
               (-0.02, -np.inf, "under -2.0%")]


def compute_time_sliced_metrics(entry_ts, entry_price: float, price_history: dict, sorted_ts: list) -> dict:
    """For each checkpoint, the return AT that point and the running
    MAE/MFE from entry up to that point (not the whole 4h trade)."""
    entry_ms = int(entry_ts.timestamp() * 1000)
    lo = bisect.bisect_left(sorted_ts, entry_ms)
    out = {}
    for label, minutes in CHECKPOINTS:
        target_ms = entry_ms + minutes * 60_000
        hi = bisect.bisect_right(sorted_ts, target_ms)
        path_ts = sorted_ts[lo:hi]
        if len(path_ts) < 2:
            continue
        path_returns = [(price_history[t] - entry_price) / entry_price for t in path_ts]
        out[label] = {"return": path_returns[-1], "mae_so_far": min(path_returns), "mfe_so_far": max(path_returns)}
    return out


def build_trade_frame(trades: list, price_history: dict, sorted_ts: list) -> pd.DataFrame:
    rows = []
    for t in trades:
        m = compute_time_sliced_metrics(t["entry_ts"], t["entry_price"], price_history, sorted_ts)
        if "4h" not in m:
            continue
        row = {"net_return": t["net_return"], "final_mae": m["4h"]["mae_so_far"]}
        for label, _ in CHECKPOINTS:
            if label in m:
                row[f"ret_{label}"] = m[label]["return"]
                row[f"mae_{label}"] = m[label]["mae_so_far"]
                row[f"mfe_{label}"] = m[label]["mfe_so_far"]
        rows.append(row)
    return pd.DataFrame(rows)


def section_1(df: pd.DataFrame) -> str:
    lines = ["## 1. Time-dependent MAE/MFE (running, not final)\n",
             "Return, running MAE, and running MFE AT each checkpoint "
             "(i.e. MAE/MFE computed only from entry up to that point, "
             "not over the whole 4h hold) — winners vs. losers.\n"]
    winners, losers = df[df["net_return"] > 0], df[df["net_return"] <= 0]
    lines.append(f"Winners: {len(winners):,}, Losers: {len(losers):,}\n")
    lines.append("| Checkpoint | Ret (W) | Ret (L) | MAE-so-far (W) | MAE-so-far (L) | MFE-so-far (W) | MFE-so-far (L) |")
    lines.append("|---|---|---|---|---|---|---|")
    for label, _ in CHECKPOINTS:
        rw, rl = winners.get(f"ret_{label}"), losers.get(f"ret_{label}")
        maw, mal = winners.get(f"mae_{label}"), losers.get(f"mae_{label}")
        mfw, mfl = winners.get(f"mfe_{label}"), losers.get(f"mfe_{label}")
        if rw is None or rl is None:
            continue
        lines.append(f"| {label} | {rw.mean()*100:+.4f}% | {rl.mean()*100:+.4f}% | "
                      f"{maw.mean()*100:+.4f}% | {mal.mean()*100:+.4f}% | "
                      f"{mfw.mean()*100:+.4f}% | {mfl.mean()*100:+.4f}% |")
    return "\n".join(lines) + "\n"


def section_2(df: pd.DataFrame) -> str:
    lines = ["## 2. Winner drawdown-depth distribution\n",
             "v1 found 90.5%/85.0% of winners dip negative at some point. "
             "How deep, typically?\n"]
    winners = df[df["net_return"] > 0]
    lines.append(f"n winners = {len(winners):,}\n")
    lines.append("| MAE bucket | Count | % of winners |")
    lines.append("|---|---|---|")
    for hi, lo, label in MAE_BUCKETS:
        mask = (winners["final_mae"] <= hi) & (winners["final_mae"] > lo)
        n = mask.sum()
        lines.append(f"| {label} | {n:,} | {n/len(winners)*100:.1f}% |")
    never_dipped = (winners["final_mae"] >= 0).sum()
    lines.append(f"| never dipped (MAE >= 0) | {never_dipped:,} | {never_dipped/len(winners)*100:.1f}% |")
    return "\n".join(lines) + "\n"


def section_3(df: pd.DataFrame) -> str:
    lines = ["## 3. P(eventual winner | trade reached this much drawdown)\n",
             "Purely descriptive — no threshold is chosen or recommended "
             "as a stop. Among only the trades whose full-trade MAE "
             "reached at least this much adverse excursion at some point, "
             "what fraction still closed as a winner?\n"]
    lines.append("| Drawdown reached | n trades that reached it | Win rate among them |")
    lines.append("|---|---|---|")
    baseline_wr = (df["net_return"] > 0).mean()
    lines.append(f"| (baseline, all trades) | {len(df):,} | {baseline_wr*100:.1f}% |")
    for th in DRAWDOWN_THRESHOLDS:
        mask = df["final_mae"] <= th
        n = mask.sum()
        if n == 0:
            continue
        wr = (df.loc[mask, "net_return"] > 0).mean()
        lines.append(f"| <= {th*100:.2f}% | {n:,} | {wr*100:.1f}% |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--price-cache", default=os.path.join(config.DATA_DIR, "backfill_cache", "BTC_USDT_1m.csv"))
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "reports", "phase_c_trade_path_analysis_v2.md"))
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()
    val = df[df["timestamp"] >= cutoff].copy()

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    val["local_price_location"] = apply_lpl(val, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    disc_lpl_q = apply_quintile(disc["local_price_location"], lpl_edges)
    disc_vol_q = apply_quintile(disc["volatility_atr_norm"], vol_edges)
    val_lpl_q = apply_quintile(val["local_price_location"], lpl_edges)
    val_vol_q = apply_quintile(val["volatility_atr_norm"], vol_edges)
    disc_decision = apply_decision_rule(disc_lpl_q, disc_vol_q)
    val_decision = apply_decision_rule(val_lpl_q, val_vol_q)

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    body = ""
    for name, cand_df, decision in [("Discovery (2020-2025, in-sample)", disc, disc_decision),
                                     ("Validation (2026, out-of-sample)", val, val_decision)]:
        signals = cand_df[decision == "long_candidate"].sort_values("timestamp")
        trades, _ = simulate(signals, price_history, sorted_ts)
        print(f"{name}: {len(trades)} trades, computing time-sliced metrics...")
        trade_df = build_trade_frame(trades, price_history, sorted_ts)
        body += f"# {name}\n\n" + section_1(trade_df) + "\n" + section_2(trade_df) + "\n" + section_3(trade_df) + "\n---\n\n"

    header = (
        "# Phase C trade-path analysis v2 — time-dependent MAE/MFE\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Same exact trades as phase_c_baseline_v1.py / "
        "phase_c_trade_path_analysis.py. Still purely descriptive — no "
        "stop-loss, take-profit, or exit rule is chosen or tested here.\n\n---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
