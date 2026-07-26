"""
Phase C trade-path analysis — MAE/MFE and the intra-trade path shape of
the EXACT same trades phase_c_baseline_v1.py already executed (same
signals, same Option A position logic, same entry/exit prices). Per the
project discussion: this is analysis of the existing hypothesis, NOT
optimization — no stop-loss/take-profit is chosen or tested here. The
point is understanding whether the negative mean / profit-factor<1 result
comes from a few extreme tail losses or a broadly negative-skew profile
across most trades, and whether winners/losers are distinguishable early
in the trade — before touching a single exit parameter.

For every executed trade:
  MAE = Maximum Adverse Excursion (the worst intra-trade drawdown vs. entry)
  MFE = Maximum Favorable Excursion (the best intra-trade run-up vs. entry)
  return at each of 15m / 30m / 1h / 2h / 3h / 4h into the trade

Then, split by the trade's actual outcome (winner = net_return > 0, loser
otherwise):
  - average return-at-each-checkpoint, winners vs. losers
  - average/median MAE and MFE, winners vs. losers
  - % of winners that dipped negative (MAE < 0) at some point before
    closing positive
  - % of losers that rose above entry (MFE > 0) at some point before
    closing negative
  - is the negative mean driven by a small number of extreme-MAE trades,
    or is the whole loser population moderately negative? (loser MAE
    distribution, not just its average)

Usage:
    .venv/bin/python scripts/phase_c_trade_path_analysis.py
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
from phase_c_baseline_v1 import load_1m_price_series, lookup_price, simulate
import mst_config as config

CHECKPOINTS = [("15m", 15), ("30m", 30), ("1h", 60), ("2h", 120), ("3h", 180), ("4h", 240)]


def compute_path_metrics(entry_ts, entry_price: float, exit_ts, price_history: dict, sorted_ts: list):
    entry_ms = int(entry_ts.timestamp() * 1000)
    exit_ms = int(exit_ts.timestamp() * 1000)
    lo = bisect.bisect_left(sorted_ts, entry_ms)
    hi = bisect.bisect_right(sorted_ts, exit_ms)
    path_ts = sorted_ts[lo:hi]
    if len(path_ts) < 2:
        return None
    path_returns = [(price_history[t] - entry_price) / entry_price for t in path_ts]
    mae, mfe = min(path_returns), max(path_returns)

    checkpoints = {}
    for label, minutes in CHECKPOINTS:
        target_ms = entry_ms + minutes * 60_000
        price = lookup_price(price_history, sorted_ts, target_ms, 120_000)
        if price is not None:
            checkpoints[label] = (price - entry_price) / entry_price
    return {"mae": mae, "mfe": mfe, "checkpoints": checkpoints}


def analyze_trades(trades: list, price_history: dict, sorted_ts: list) -> pd.DataFrame:
    rows = []
    for t in trades:
        m = compute_path_metrics(t["entry_ts"], t["entry_price"], t["exit_ts"], price_history, sorted_ts)
        if m is None:
            continue
        row = {"net_return": t["net_return"], "mae": m["mae"], "mfe": m["mfe"]}
        row.update({f"cp_{label}": m["checkpoints"].get(label) for label, _ in CHECKPOINTS})
        rows.append(row)
    return pd.DataFrame(rows)


def format_report(period_name: str, df: pd.DataFrame) -> str:
    lines = [f"### {period_name} (n={len(df):,} trades with full path data)\n"]
    if df.empty:
        lines.append("No trades with sufficient path data.\n")
        return "\n".join(lines) + "\n"

    winners = df[df["net_return"] > 0]
    losers = df[df["net_return"] <= 0]
    lines.append(f"Winners: {len(winners):,} ({len(winners)/len(df)*100:.1f}%). "
                 f"Losers: {len(losers):,} ({len(losers)/len(df)*100:.1f}%).\n")

    lines.append("**Average return at each checkpoint, winners vs. losers:**\n")
    lines.append("| Checkpoint | Winners (mean) | Losers (mean) |")
    lines.append("|---|---|---|")
    for label, _ in CHECKPOINTS:
        col = f"cp_{label}"
        w = winners[col].mean() if col in winners and winners[col].notna().any() else float("nan")
        l = losers[col].mean() if col in losers and losers[col].notna().any() else float("nan")
        lines.append(f"| {label} | {w*100:+.4f}% | {l*100:+.4f}% |")

    lines.append("\n**MAE / MFE, winners vs. losers:**\n")
    lines.append("| Group | Mean MAE | Median MAE | Mean MFE | Median MFE |")
    lines.append("|---|---|---|---|---|")
    for name, g in [("Winners", winners), ("Losers", losers)]:
        if g.empty:
            continue
        lines.append(f"| {name} | {g['mae'].mean()*100:+.4f}% | {g['mae'].median()*100:+.4f}% | "
                      f"{g['mfe'].mean()*100:+.4f}% | {g['mfe'].median()*100:+.4f}% |")

    winners_dipped = (winners["mae"] < 0).mean() if len(winners) else float("nan")
    losers_rose = (losers["mfe"] > 0).mean() if len(losers) else float("nan")
    lines.append(f"\n- Winners that dipped negative at some point before closing positive "
                 f"(MAE < 0): {winners_dipped*100:.1f}%")
    lines.append(f"- Losers that rose above entry at some point before closing negative "
                 f"(MFE > 0): {losers_rose*100:.1f}%\n")

    lines.append("**Loser MAE distribution** (is the negative mean driven by a few extreme "
                 "tail trades, or broadly negative across most losers?):\n")
    lines.append("| Percentile | MAE |")
    lines.append("|---|---|")
    if len(losers):
        for pct in [10, 25, 50, 75, 90]:
            lines.append(f"| P{pct} | {losers['mae'].quantile(pct/100)*100:+.4f}% |")
        tail_share = (losers["mae"] < losers["mae"].quantile(0.10)).sum()
        lines.append(f"\nWorst 10% of losers by MAE: {tail_share} trades, mean MAE "
                     f"{losers[losers['mae'] <= losers['mae'].quantile(0.10)]['mae'].mean()*100:.4f}% "
                     f"vs. the other 90% of losers' mean MAE "
                     f"{losers[losers['mae'] > losers['mae'].quantile(0.10)]['mae'].mean()*100:.4f}%\n")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--price-cache", default=os.path.join(config.DATA_DIR, "backfill_cache", "BTC_USDT_1m.csv"))
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "reports", "phase_c_trade_path_analysis.md"))
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
        print(f"{name}: {len(trades)} trades, computing path metrics...")
        path_df = analyze_trades(trades, price_history, sorted_ts)
        body += format_report(name, path_df) + "\n"

    header = (
        "# Phase C trade-path analysis — MAE/MFE, not optimization\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Same exact trades as phase_c_baseline_v1.py (same signals, same "
        "Option A logic, same entry/exit). This is analysis of the "
        "existing hypothesis's trade paths — no stop-loss, take-profit, "
        "or exit timing is chosen or tested here. The question is only: "
        "does the negative mean / profit-factor<1 result come from a few "
        "extreme tail losses, or a broadly negative-skew profile across "
        "most trades — and are winners/losers distinguishable early?\n\n---\n\n"
    )
    full = header + "## Results\n\n" + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
