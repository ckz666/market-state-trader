"""
Phase C baseline v1 — the simplest possible honest execution test of the
frozen decision rule. Per the project discussion: does the answer
                            "avoid_long"
already tell us it is short signal? Explicitly NO — avoid_long here means
only "don't go long in this state," never used as a short entry. Only
long_candidate produces a trade in this version.

Position logic — Option A (per the project discussion, the only sound
choice for a real backtest): a signal opens a position; further signals
while that position is open are ignored (not stacked, not treated as
independent trades) — otherwise overlapping 4h windows from
closely-spaced signals would double/triple-count the same market move.

    long_candidate signal (state_ts)
            v
    no position currently open?
            v (yes)
    ENTER long at the first realistic 1m price at/after state_ts
            v
    hold exactly 4h (matches the horizon the hypothesis was frozen on —
    NOT optimizing entry+exit+state simultaneously)
            v
    EXIT at the realistic 1m price at/after state_ts+4h
            v
    apply fees (mst_config.TAKER_FEE, round trip) and an ASSUMED slippage
    (see SLIPPAGE_BPS below — no historical order-book data exists for
    this range, so this is a stated assumption, not a measurement)

Explicitly NOT included in this version (deliberately deferred):
  - stop-loss / take-profit (would require optimizing an exit rule)
  - position sizing (every trade is unit-sized, PnL reported as % return)
  - short trades from avoid_long
  - any re-fitting of LPL/volatility quintile edges — reuses
    hypothesis_validation.py's exact frozen (2020-2025-only) parameters
  - walk-forward re-calibration

Usage:
    .venv/bin/python scripts/phase_c_baseline_v1.py
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
import mst_config as config

HOLD_HOURS = 4
ENTRY_EXIT_TOLERANCE_SEC = 120  # matches storage/logger.py's outcome-matching tolerance
# No historical order-book/trade-tape data exists for this range, so this
# is a stated, conservative ASSUMPTION, not a measurement from real fills —
# flagged as such in every output. 5bps/side is a deliberately unaggressive
# guess for a liquid BTC/USDT perpetual; Phase C v2+ could replace this with
# something measured (e.g. from exchange_client.py's estimate_execution())
# if live order-book data starts getting collected.
SLIPPAGE_BPS_PER_SIDE = 5


def load_1m_price_series(cache_path: str) -> dict:
    df = pd.read_csv(cache_path)
    return dict(zip(df["timestamp"].astype(np.int64), df["close"].astype(float)))


def lookup_price(price_history: dict, sorted_ts: list, target_ms: int, tolerance_ms: int):
    idx = bisect.bisect_left(sorted_ts, target_ms)
    if idx >= len(sorted_ts) or sorted_ts[idx] - target_ms > tolerance_ms:
        return None
    return price_history[sorted_ts[idx]]


def simulate(signals: pd.DataFrame, price_history: dict, sorted_ts: list) -> tuple[list, int]:
    """Option A position logic: sequential, non-overlapping. Returns
    (trades, n_skipped_overlap_or_gap)."""
    trades = []
    skipped = 0
    position_open_until = None
    tol_ms = ENTRY_EXIT_TOLERANCE_SEC * 1000
    hold_ms = HOLD_HOURS * 3600 * 1000

    for _, row in signals.iterrows():
        state_ts = row["timestamp"]
        if position_open_until is not None and state_ts < position_open_until:
            skipped += 1
            continue  # a prior trade is still open — ignore this signal (Option A)

        entry_ms = int(state_ts.timestamp() * 1000)
        exit_ms = entry_ms + hold_ms
        entry_price = lookup_price(price_history, sorted_ts, entry_ms, tol_ms)
        exit_price = lookup_price(price_history, sorted_ts, exit_ms, tol_ms)
        if entry_price is None or exit_price is None:
            skipped += 1
            continue  # data gap at entry or exit — cannot execute this trade honestly

        gross_return = (exit_price - entry_price) / entry_price
        fee_cost = 2 * config.TAKER_FEE  # round trip
        slippage_cost = 2 * (SLIPPAGE_BPS_PER_SIDE / 10000)  # round trip
        net_return = gross_return - fee_cost - slippage_cost

        trades.append({
            "entry_ts": state_ts, "exit_ts": state_ts + pd.Timedelta(hours=HOLD_HOURS),
            "entry_price": entry_price, "exit_price": exit_price,
            "gross_return": gross_return, "fee_cost": fee_cost,
            "slippage_cost": slippage_cost, "net_return": net_return,
        })
        position_open_until = state_ts + pd.Timedelta(hours=HOLD_HOURS)

    return trades, skipped


def compute_stats(trades: list) -> dict:
    if not trades:
        return {}
    net = np.array([t["net_return"] for t in trades])
    gross = np.array([t["gross_return"] for t in trades])
    wins = net > 0
    equity = np.cumprod(1 + net)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_dd = drawdown.min()

    gross_wins = net[wins].sum()
    gross_losses = -net[~wins].sum()
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")

    return {
        "n_trades": len(trades),
        "win_rate": wins.mean(),
        "gross_return_mean": gross.mean(),
        "total_fees": sum(t["fee_cost"] for t in trades),
        "total_slippage": sum(t["slippage_cost"] for t in trades),
        "net_return_mean": net.mean(),
        "net_return_median": np.median(net),
        "profit_factor": profit_factor,
        "final_equity": equity[-1],
        "max_drawdown": max_dd,
    }


def format_report(period_name: str, n_signals: int, skipped: int, stats: dict) -> str:
    lines = [f"### {period_name}\n"]
    lines.append(f"- n_signals (long_candidate fired): {n_signals:,}")
    lines.append(f"- n_trades actually executed (Option A: non-overlapping, gaps excluded): "
                 f"{stats.get('n_trades', 0):,}")
    lines.append(f"- signals skipped (overlapping position or data gap at entry/exit): {skipped:,}\n")
    if not stats:
        lines.append("No trades executed in this period.\n")
        return "\n".join(lines) + "\n"
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Win rate | {stats['win_rate']*100:.1f}% |")
    lines.append(f"| Mean gross return/trade | {stats['gross_return_mean']*100:+.4f}% |")
    lines.append(f"| Total fees (sum) | {stats['total_fees']*100:.4f}% of notional, summed |")
    lines.append(f"| Total slippage (assumed, sum) | {stats['total_slippage']*100:.4f}% of notional, summed |")
    lines.append(f"| Mean net return/trade | {stats['net_return_mean']*100:+.4f}% |")
    lines.append(f"| Median net return/trade | {stats['net_return_median']*100:+.4f}% |")
    lines.append(f"| Profit factor (gross wins / gross losses) | {stats['profit_factor']:.2f} |")
    lines.append(f"| Final compounded equity (100% of capital re-bet every trade, starting at 1.0) | "
                 f"{stats['final_equity']:.4f} |")
    lines.append(f"| Max drawdown (of that same 100%-of-capital equity curve) | {stats['max_drawdown']*100:.2f}% |")
    lines.append(f"\n**Caveat on the last two rows:** this equity curve assumes every trade risks the "
                 f"ENTIRE account with no position sizing at all — nobody would actually trade this way. "
                 f"It's included only to show the qualitative shape of compounding risk (does the tail "
                 f"risk from the median>mean gap above compound badly?), not as a projection of real "
                 f"capital growth. Position sizing is explicitly out of scope for this baseline.\n")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--price-cache", default=os.path.join(config.DATA_DIR, "backfill_cache", "BTC_USDT_1m.csv"))
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "reports", "phase_c_baseline_v1.md"))
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
    print(f"Loaded {len(price_history):,} 1m closes.")

    results = {}
    for name, cand_df, decision in [("Discovery (2020-2025, in-sample)", disc, disc_decision),
                                     ("Validation (2026, out-of-sample)", val, val_decision)]:
        signals = cand_df[decision == "long_candidate"].sort_values("timestamp")
        trades, skipped = simulate(signals, price_history, sorted_ts)
        stats = compute_stats(trades)
        results[name] = (len(signals), skipped, stats)
        print(f"{name}: {len(signals)} signals -> {stats.get('n_trades', 0)} trades, "
              f"win_rate={stats.get('win_rate', float('nan'))*100:.1f}%, "
              f"net_mean={stats.get('net_return_mean', float('nan'))*100:+.4f}%")

    header = (
        "# Phase C baseline v1 — minimal honest execution test (long_candidate only)\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Entry: first real 1m close at/after the signal's state timestamp. "
        f"Exit: first real 1m close at/after entry+{HOLD_HOURS}h (fixed — "
        "not optimized). Fees: mst_config.TAKER_FEE, round trip. Slippage: "
        f"a STATED ASSUMPTION of {SLIPPAGE_BPS_PER_SIDE}bps/side (no "
        "historical order-book data exists to measure this from — not a "
        "real fill), round trip. Position logic: Option A — a signal opens "
        "a trade only if no prior trade from this rule is still open; "
        "overlapping signals are skipped, not stacked. avoid_long is NOT "
        "traded as a short in this version — it remains a long-avoidance "
        "signal only. No stop-loss/take-profit, no position sizing, no "
        "re-fitting of any state parameters.\n\n---\n\n"
    )
    body = "## Results\n\n"
    for name, (n_signals, skipped, stats) in results.items():
        body += format_report(name, n_signals, skipped, stats) + "\n"

    full = header + body
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
