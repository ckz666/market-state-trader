"""
Discovery v22 — concurrent positions: Option A discards 89% of signals
at a 24h hold. Are the discarded ones any good?

Option A (frozen since Phase C) ignores every signal that arrives while
a position is open. At the 4h hold that consumed 3,276 signals -> 1,064
trades (32% retained). At the 24h hold that discovery_v19/v4 favour, it
is 3,276 -> 365 (11% retained) — nearly nine in ten signals discarded.
That is a large amount of discarded opportunity, and whether it *should*
be discarded has never been tested.

Two questions, kept separate because they need different evidence:

  A. QUALITY OF DISCARDED SIGNALS. Simulate K concurrent slots. A signal
     takes the lowest free slot. Report per-slot trade statistics: slot 1
     is exactly what Option A takes today; slots 2+ are what it throws
     away. If slot 2+ trades are markedly worse, Option A is doing real
     work; if they are comparable, it is discarding usable signal.
     This needs no capital-allocation assumptions and is the primary
     result.

  B. PORTFOLIO EFFECT. An approximate equity curve under equal 1/K
     allocation per slot, compounded in exit order. This is an
     approximation (it ignores the fact that capital is idle when fewer
     than K slots are filled, which flatters higher K) and is labelled as
     such — it is included for scale, not as a precise backtest.

Run at both the frozen 4h hold and the 24h candidate, since the amount
of discarded signal differs so much between them.

Purely descriptive; does not change decision_rule_v1. Discovery only
(2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v22_concurrent_positions.py
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
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile
from decision_rule_v1 import apply_decision_rule
from phase_c_baseline_v1 import (
    load_1m_price_series, lookup_price, ENTRY_EXIT_TOLERANCE_SEC, SLIPPAGE_BPS_PER_SIDE,
)
import mst_config as config

HOLDS = [240, 1440]
SLOT_COUNTS = [1, 2, 3, 5, 999]  # 999 = effectively unlimited
TOL_MS = ENTRY_EXIT_TOLERANCE_SEC * 1000
MIN_N = 15


def simulate_slots(signals: pd.DataFrame, price_history: dict, sorted_ts: list,
                   hold_min: int, n_slots: int) -> list:
    """K concurrent slots; a signal takes the lowest-indexed free slot.
    slot_idx 0 reproduces Option A exactly."""
    trades = []
    free_at = [pd.Timestamp.min.tz_localize("UTC")] * min(n_slots, 10_000)
    hold_ms = hold_min * 60_000
    for _, row in signals.iterrows():
        ts = row["timestamp"]
        slot = next((i for i, t in enumerate(free_at) if ts >= t), None)
        if slot is None:
            continue
        entry_ms = int(ts.timestamp() * 1000)
        entry_price = lookup_price(price_history, sorted_ts, entry_ms, TOL_MS)
        exit_price = lookup_price(price_history, sorted_ts, entry_ms + hold_ms, TOL_MS)
        if entry_price is None or exit_price is None:
            continue
        gross = (exit_price - entry_price) / entry_price
        net = gross - 2 * config.TAKER_FEE - 2 * (SLIPPAGE_BPS_PER_SIDE / 10000)
        exit_ts = ts + pd.Timedelta(minutes=hold_min)
        trades.append({"net_return": net, "slot": slot, "exit_ts": exit_ts})
        free_at[slot] = exit_ts
    return trades


def _stats(net: np.ndarray) -> dict:
    if len(net) == 0:
        return {"n": 0}
    wins = net > 0
    gw, gl = net[wins].sum(), -net[~wins].sum()
    return {"n": len(net), "win_rate": wins.mean(), "median": np.median(net),
            "mean": net.mean(), "profit_factor": gw / gl if gl > 0 else float("inf")}


def _fmt(s: dict) -> str:
    if s["n"] == 0:
        return "n=0"
    flag = " ⚠" if s["n"] < MIN_N else ""
    return (f"n={s['n']:,}{flag}, win {s['win_rate']*100:.1f}%, median {s['median']*100:+.4f}%, "
            f"mean {s['mean']*100:+.4f}%, PF {s['profit_factor']:.3f}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/discovery_v22_concurrent_positions.md")
    args = p.parse_args()

    print("Loading candidates...")
    df = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    lpl_q = apply_quintile(disc["local_price_location"], lpl_edges)
    vol_q = apply_quintile(disc["volatility_atr_norm"], vol_edges)
    signals = disc[apply_decision_rule(lpl_q, vol_q) == "long_candidate"].sort_values("timestamp")
    print(f"long_candidate signals: {len(signals):,}")

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    body = ""
    for hold in HOLDS:
        print(f"\n=== hold={hold}m ===")
        body += f"\n## Hold {hold}m\n\n### A. Per-slot trade quality (unlimited slots)\n\n"
        body += ("Slot 0 is exactly what Option A takes today; slots 1+ are "
                 "the signals it discards. No capital assumptions involved.\n\n")
        trades = simulate_slots(signals, price_history, sorted_ts, hold, 999)
        tdf = pd.DataFrame(trades)
        body += "| Slot | Stats |\n|---|---|\n"
        for slot in sorted(tdf["slot"].unique())[:6]:
            sub = tdf.loc[tdf["slot"] == slot, "net_return"].to_numpy()
            label = "0 (= Option A)" if slot == 0 else str(slot)
            body += f"| {label} | {_fmt(_stats(sub))} |\n"
        rest = tdf.loc[tdf["slot"] >= 6, "net_return"].to_numpy()
        if len(rest):
            body += f"| 6+ | {_fmt(_stats(rest))} |\n"
        body += f"\nTotal trades with unlimited slots: **{len(tdf):,}** of {len(signals):,} signals.\n"

        body += "\n### B. Portfolio approximation by slot count\n\n"
        body += ("Equity assumes equal 1/K allocation per slot, compounded in "
                 "exit order. **Approximation:** it ignores capital sitting "
                 "idle when fewer than K slots are filled, which flatters "
                 "higher K. Included for scale, not as a precise backtest.\n\n")
        body += "| Slots (K) | n trades | Win rate | Median | Mean | PF | Approx. equity |\n|---|---|---|---|---|---|---|\n"
        for k in SLOT_COUNTS:
            tr = simulate_slots(signals, price_history, sorted_ts, hold, k)
            if not tr:
                continue
            net = np.array([t["net_return"] for t in tr])
            s = _stats(net)
            ordered = pd.DataFrame(tr).sort_values("exit_ts")["net_return"].to_numpy()
            equity = float(np.prod(1 + ordered / min(k, 20)))
            label = "1 (= Option A)" if k == 1 else ("unlimited" if k == 999 else str(k))
            body += (f"| {label} | {s['n']:,} | {s['win_rate']*100:.1f}% | {s['median']*100:+.4f}% | "
                     f"{s['mean']*100:+.4f}% | {s['profit_factor']:.3f} | {equity:.4f} |\n")

    header = (
        "# Discovery v22 — concurrent positions\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Option A discards every signal arriving while a position is open "
        "— 68% of signals at the 4h hold, 89% at the 24h candidate. "
        "Whether those discarded signals are worth taking has never been "
        "tested. Section A answers that directly (per-slot trade quality, "
        "no capital assumptions); section B gives an approximate "
        "portfolio view. Purely descriptive; does not change "
        "decision_rule_v1. Discovery only (2020-2025); 2026 untouched. "
        f"⚠ marks fewer than {MIN_N} trades.\n\n"
        "---\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
