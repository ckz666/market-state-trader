"""
Phase C trade-path analysis v3 — drawdown x time, drawdown x volatility,
and time-to-first-recovery. Still purely descriptive, per the project
discussion: no exit rule is chosen here.

  A. Drawdown x Time: v2's P(winner | drawdown reached) collapsed across
     the whole 4h hold into one number per threshold. This asks the same
     question separately AT each checkpoint (15m/30m/1h/2h/3h/4h) — is
     -1% after 15 minutes the same signal as -1% after 3 hours?

  B. Drawdown x Volatility — IMPORTANT SCOPE NOTE: decision_rule_v1 only
     ever fires at Volatility==Q5 (its frozen rule requires LPL==Q1 AND
     Volatility==Q5), so every executed long_candidate trade already
     shares the same volatility bucket — there is no within-rule
     variation to compare. This section therefore widens the population
     to LPL==Q1 at EVERY volatility quintile (Q1-Q5), each simulated as
     its own independent Option-A trade sequence, purely as a diagnostic
     — NOT a change to decision_rule_v1 or a proposal to trade these
     other volatility levels. Answers: does -1% mean something different
     at low vs. high entry volatility?

  C. Time to first positive MFE: how long, typically, until a trade's
     running price first exceeds entry? Compared winners vs. losers — if
     winners reliably go green early and losers don't, that's an
     additional, independent early signal beyond drawdown depth alone.

Usage:
    .venv/bin/python scripts/phase_c_trade_path_analysis_v3.py
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
from phase_c_baseline_v1 import load_1m_price_series, lookup_price, simulate
from phase_c_trade_path_analysis_v2 import CHECKPOINTS, build_trade_frame

DRAWDOWN_THRESHOLDS = [-0.0025, -0.005, -0.01, -0.015, -0.02]
Q_LABELS = ["Q1", "Q2", "Q3", "Q4", "Q5"]


# ── A. Drawdown x Time ───────────────────────────────────────────────────

def section_a(trade_df: pd.DataFrame) -> str:
    lines = ["## A. Drawdown x Time — P(eventual winner)\n",
             "For each checkpoint, among only the trades whose RUNNING "
             "MAE (from entry up to that checkpoint, not the whole trade) "
             "has reached at least this much adverse excursion, what "
             "fraction still closed as a winner? Rows = drawdown depth, "
             "columns = how long into the trade.\n"]
    header = "| Drawdown | " + " | ".join(label for label, _ in CHECKPOINTS) + " |"
    lines.append(header)
    lines.append("|---|" + "---|" * len(CHECKPOINTS))
    for th in DRAWDOWN_THRESHOLDS:
        row = [f"<= {th*100:.2f}%"]
        for label, _ in CHECKPOINTS:
            col = f"mae_{label}"
            if col not in trade_df.columns:
                row.append("n/a")
                continue
            mask = trade_df[col] <= th
            n = mask.sum()
            if n < 10:
                row.append(f"n={n} (too few)")
                continue
            wr = (trade_df.loc[mask, "net_return"] > 0).mean()
            row.append(f"{wr*100:.0f}% (n={n})")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


# ── B. Drawdown x Volatility (widened LPL==Q1 population) ──────────────

def section_b(cand_df: pd.DataFrame, lpl_q: pd.Series, vol_q: pd.Series,
              price_history: dict, sorted_ts: list) -> str:
    lines = ["## B. Drawdown x Volatility (diagnostic — widened population, "
             "not a change to decision_rule_v1)\n",
             "decision_rule_v1 only fires at Volatility==Q5, so its actual "
             "trades have no volatility variation to compare. This uses "
             "LPL==Q1 at every volatility quintile instead, each an "
             "independent Option-A trade sequence, purely to see whether "
             "the drawdown-recovery relationship changes with entry "
             "volatility. Not a proposal to trade these other quintiles.\n"]
    header = "| Drawdown | " + " | ".join(f"Vol={vq}" for vq in Q_LABELS) + " |"
    lines.append(header)
    lines.append("|---|" + "---|" * len(Q_LABELS))

    vol_trade_dfs = {}
    for vq in Q_LABELS:
        mask = (lpl_q == "Q1") & (vol_q == vq)
        signals = cand_df[mask].sort_values("timestamp")
        trades, _ = simulate(signals, price_history, sorted_ts)
        vol_trade_dfs[vq] = build_trade_frame(trades, price_history, sorted_ts)
        print(f"  LPL=Q1 & Vol={vq}: {len(signals)} signals -> {len(trades)} trades")

    baseline_row = ["(baseline win rate)"]
    for vq in Q_LABELS:
        df = vol_trade_dfs[vq]
        wr = (df["net_return"] > 0).mean() if len(df) else float("nan")
        baseline_row.append(f"{wr*100:.0f}% (n={len(df)})" if len(df) else "n/a")
    lines.append("| " + " | ".join(baseline_row) + " |")

    for th in DRAWDOWN_THRESHOLDS:
        row = [f"<= {th*100:.2f}%"]
        for vq in Q_LABELS:
            df = vol_trade_dfs[vq]
            if df.empty or "final_mae" not in df.columns:
                row.append("n/a")
                continue
            mask = df["final_mae"] <= th
            n = mask.sum()
            if n < 10:
                row.append(f"n={n} (too few)")
                continue
            wr = (df.loc[mask, "net_return"] > 0).mean()
            row.append(f"{wr*100:.0f}% (n={n})")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


# ── C. Time to first positive MFE ───────────────────────────────────────

def time_to_first_positive(entry_ts, entry_price: float, exit_ts, price_history: dict, sorted_ts: list):
    entry_ms = int(entry_ts.timestamp() * 1000)
    exit_ms = int(exit_ts.timestamp() * 1000)
    lo = bisect.bisect_left(sorted_ts, entry_ms)
    hi = bisect.bisect_right(sorted_ts, exit_ms)
    for t in sorted_ts[lo:hi]:
        if price_history[t] > entry_price:
            return (t - entry_ms) / 60000.0  # minutes
    return None  # never went positive


def section_c(trades: list, price_history: dict, sorted_ts: list, net_returns: list) -> str:
    lines = ["## C. Time to first positive MFE\n",
             "How long, typically, until a trade's running price first "
             "exceeds entry (i.e. unrealized PnL first turns positive, "
             "before fees)? Winners vs. losers.\n"]
    times = []
    for t, net_ret in zip(trades, net_returns):
        mins = time_to_first_positive(t["entry_ts"], t["entry_price"], t["exit_ts"], price_history, sorted_ts)
        times.append({"minutes_to_positive": mins, "net_return": net_ret})
    df = pd.DataFrame(times)
    winners, losers = df[df["net_return"] > 0], df[df["net_return"] <= 0]

    lines.append("| Group | n | Never went positive | Median time-to-positive (of those that did) |")
    lines.append("|---|---|---|---|")
    for name, g in [("Winners", winners), ("Losers", losers)]:
        never = g["minutes_to_positive"].isna().sum()
        went_positive = g.dropna(subset=["minutes_to_positive"])
        median_t = went_positive["minutes_to_positive"].median() if len(went_positive) else float("nan")
        lines.append(f"| {name} | {len(g):,} | {never:,} ({never/len(g)*100:.1f}%) | "
                      f"{median_t:.0f} min |" if len(g) else f"| {name} | 0 | - | - |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/phase_c_trade_path_analysis_v3.md")
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

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    body = ""
    for name, cand_df, lpl_q, vol_q in [("Discovery (2020-2025, in-sample)", disc, disc_lpl_q, disc_vol_q),
                                          ("Validation (2026, out-of-sample)", val, val_lpl_q, val_vol_q)]:
        print(f"\n=== {name} ===")
        body += f"# {name}\n\n"

        signal_mask = (lpl_q == "Q1") & (vol_q == "Q5")
        signals = cand_df[signal_mask].sort_values("timestamp")
        trades, _ = simulate(signals, price_history, sorted_ts)
        print(f"long_candidate: {len(trades)} trades")

        trade_df = build_trade_frame(trades, price_history, sorted_ts)
        body += section_a(trade_df) + "\n"

        print("Section B: widened LPL=Q1 population across volatility quintiles...")
        body += section_b(cand_df, lpl_q, vol_q, price_history, sorted_ts) + "\n"

        print("Section C: time to first positive MFE...")
        body += section_c(trades, price_history, sorted_ts, [t["net_return"] for t in trades]) + "\n"

        body += "---\n\n"

    header = (
        "# Phase C trade-path analysis v3 — drawdown x time x volatility, time-to-recovery\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Still purely descriptive — no exit rule is chosen or tested here. "
        "Section B widens the population beyond decision_rule_v1's actual "
        "signals for diagnostic purposes only (see its note).\n\n---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
