"""
Discovery v23 — position sizing, an entirely untouched dimension.

Every simulation in this project so far has been unit-sized: each trade
risks the same notional, and returns are reported as raw percentages
(phase_c_baseline_v1.py's module docstring lists position sizing under
"explicitly NOT included"). Sizing has therefore never been tested at
all — it is orthogonal to every factor, filter, hold length and exit
rule examined in v1-v22.

Three sizing schemes, all computable from data available at entry time
(no look-ahead), applied to the same trades at both the frozen 4h hold
and the 24h candidate:

  1. UNIT (baseline)          — size 1.0 always. What every prior script did.
  2. INVERSE-VOLATILITY       — size proportional to 1/volatility_atr_norm,
                                normalized to mean 1.0 on the Discovery
                                period. The standard risk-parity idea:
                                equalize risk contribution rather than
                                notional. Note decision_rule_v1 only
                                trades Vol==Q5, so the *within-Q5*
                                spread is what this exploits.
  3. LPL-EXTREMITY            — size proportional to how far below the
                                LPL quintile boundary the signal sits
                                (more extreme = larger), normalized the
                                same way. Tests whether the factor's
                                strength translates into a useful sizing
                                signal rather than just a binary gate.

Scaling factors are capped at [0.25, 4.0] so a single extreme
observation cannot dominate, and every scheme is normalized to mean
size 1.0 so total exposure is comparable across schemes.

Reported: weighted mean return per unit of size, and a compounded equity
curve. Median and win rate are NOT size-dependent in a meaningful way
(a trade's sign doesn't change with its size), so the comparison focuses
on mean, profit factor and equity.

Purely descriptive; does not change decision_rule_v1. Discovery only
(2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v23_position_sizing.py
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
SIZE_CAP = (0.25, 4.0)
TOL_MS = ENTRY_EXIT_TOLERANCE_SEC * 1000


def simulate_with_context(signals: pd.DataFrame, price_history: dict, sorted_ts: list,
                          hold_min: int) -> pd.DataFrame:
    """Option A, unchanged; carries the entry-time context needed for sizing."""
    rows = []
    position_open_until = None
    hold_ms = hold_min * 60_000
    for _, row in signals.iterrows():
        ts = row["timestamp"]
        if position_open_until is not None and ts < position_open_until:
            continue
        entry_ms = int(ts.timestamp() * 1000)
        entry_price = lookup_price(price_history, sorted_ts, entry_ms, TOL_MS)
        exit_price = lookup_price(price_history, sorted_ts, entry_ms + hold_ms, TOL_MS)
        if entry_price is None or exit_price is None:
            continue
        gross = (exit_price - entry_price) / entry_price
        net = gross - 2 * config.TAKER_FEE - 2 * (SLIPPAGE_BPS_PER_SIDE / 10000)
        rows.append({"net_return": net,
                     "atr": row["volatility_atr_norm"],
                     "lpl": row["local_price_location"]})
        position_open_until = ts + pd.Timedelta(minutes=hold_min)
    return pd.DataFrame(rows)


def normalized_size(raw: pd.Series) -> pd.Series:
    s = raw.clip(*SIZE_CAP)
    return s / s.mean()


def _stats(net: np.ndarray, size: np.ndarray) -> dict:
    """Size-weighted. Equity compounds the sized return per trade."""
    sized = net * size
    wins = sized > 0
    gw, gl = sized[wins].sum(), -sized[~wins].sum()
    eq = np.cumprod(1 + sized)
    peak = np.maximum.accumulate(eq)
    return {"n": len(net), "win_rate": wins.mean(), "mean_sized": sized.mean(),
            "median_sized": np.median(sized), "profit_factor": gw / gl if gl > 0 else float("inf"),
            "equity": eq[-1], "max_dd": ((eq - peak) / peak).min(),
            "mean_size": size.mean(), "size_std": size.std()}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/discovery_v23_position_sizing.md")
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
    q1_upper = lpl_edges[1]  # upper boundary of LPL Q1
    print(f"long_candidate signals: {len(signals):,}")

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    body = ""
    for hold in HOLDS:
        print(f"  simulating hold={hold}m...")
        t = simulate_with_context(signals, price_history, sorted_ts, hold)
        net = t["net_return"].to_numpy()

        schemes = {
            "1. Unit (baseline)": pd.Series(1.0, index=t.index),
            "2. Inverse volatility": normalized_size(t["atr"].median() / t["atr"]),
            "3. LPL extremity": normalized_size((q1_upper - t["lpl"]).clip(lower=0) /
                                                (q1_upper - t["lpl"]).clip(lower=0).median()),
        }
        body += (f"\n## Hold {hold}m\n\n"
                 "| Sizing | n | Mean size (sd) | Win rate | Sized mean | Sized median | PF | Equity | Max DD |\n"
                 "|---|---|---|---|---|---|---|---|---|\n")
        for label, size in schemes.items():
            s = _stats(net, size.to_numpy())
            body += (f"| {label} | {s['n']:,} | {s['mean_size']:.2f} ({s['size_std']:.2f}) | "
                     f"{s['win_rate']*100:.1f}% | {s['mean_sized']*100:+.4f}% | "
                     f"{s['median_sized']*100:+.4f}% | {s['profit_factor']:.3f} | "
                     f"{s['equity']:.4f} | {s['max_dd']*100:.2f}% |\n")

    header = (
        "# Discovery v23 — position sizing (never tested)\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Every prior simulation in this project was unit-sized; sizing is "
        "listed under \"explicitly NOT included\" in phase_c_baseline_v1's "
        "docstring and has never been examined. Three schemes, all "
        "computable at entry time with no look-ahead, each normalized to "
        f"mean size 1.0 and capped at {SIZE_CAP} so one extreme "
        "observation cannot dominate. Win rate and the sign of each trade "
        "are unaffected by sizing, so the comparison focuses on mean, "
        "profit factor and compounded equity. Purely descriptive; does "
        "not change decision_rule_v1. Discovery only (2020-2025); 2026 "
        "untouched.\n\n"
        "---\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
