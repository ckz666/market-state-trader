"""
Discovery v20 — the short side: `avoid_long` has never been traded.

`decision_rule_v1` emits `avoid_long` for LPL==Q5 & Vol==Q5, and that
label has been explicitly non-tradeable since Phase B: "never used as a
short entry" (phase_c_baseline_v1.py's module docstring). The reasoning
at the time was that "don't go long here" is a weaker claim than "go
short here", and mixing the two would have muddied the long-side test.

That deferral was never revisited, even though discovery_v5 found
LPL==Q5 & Vol==Q5 held a negative 4h median in **7/7 years**. This tests
it directly, for the first time.

Sections:
  A. Short trades from `avoid_long`, at each hold length from
     discovery_v19 (the long side's best hold turned out to be far
     longer than the frozen 4h, so the short side should not be assumed
     to share the 4h horizon either).
  B. The asymmetry that matters for a perpetual-futures short: funding
     is NOT in this dataset (verified absent from both the stored state
     and the raw cache), so a real short would pay or receive funding
     that this simulation cannot model. Fees and the stated 5bps/side
     slippage are applied identically to both sides, but the funding gap
     is a genuine, unquantified bias — reported, not silently ignored.
  C. Year-by-year stability of the short side at its best hold, since a
     short that only worked during 2022's downtrend would be a
     directional bet on that period rather than an edge.

Purely descriptive; does not change decision_rule_v1 and does not
propose trading shorts. Discovery only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v20_short_side.py
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

HOLD_MINUTES = [240, 480, 1440]
TOL_MS = ENTRY_EXIT_TOLERANCE_SEC * 1000
MIN_CELL_N = 30


def simulate_side(signals: pd.DataFrame, price_history: dict, sorted_ts: list,
                  hold_min: int, short: bool) -> list:
    """Option A. For a short, the gross return is inverted; costs are
    identical (and funding, which a real perpetual short would pay or
    receive, is NOT modelled -- see the report's section B)."""
    trades = []
    position_open_until = None
    hold_ms = hold_min * 60_000
    for _, row in signals.iterrows():
        state_ts = row["timestamp"]
        if position_open_until is not None and state_ts < position_open_until:
            continue
        entry_ms = int(state_ts.timestamp() * 1000)
        entry_price = lookup_price(price_history, sorted_ts, entry_ms, TOL_MS)
        exit_price = lookup_price(price_history, sorted_ts, entry_ms + hold_ms, TOL_MS)
        if entry_price is None or exit_price is None:
            continue
        move = (exit_price - entry_price) / entry_price
        gross = -move if short else move
        net = gross - 2 * config.TAKER_FEE - 2 * (SLIPPAGE_BPS_PER_SIDE / 10000)
        trades.append({"net_return": net, "gross_return": gross, "year": row["year"]})
        position_open_until = state_ts + pd.Timedelta(minutes=hold_min)
    return trades


def _stats(trades: list) -> dict:
    if not trades:
        return {"n": 0}
    net = np.array([t["net_return"] for t in trades])
    wins = net > 0
    gw, gl = net[wins].sum(), -net[~wins].sum()
    eq = np.cumprod(1 + net)
    peak = np.maximum.accumulate(eq)
    return {"n": len(net), "win_rate": wins.mean(), "median": np.median(net),
            "mean": net.mean(), "p05": np.quantile(net, 0.05) if len(net) >= 20 else float("nan"),
            "profit_factor": gw / gl if gl > 0 else float("inf"),
            "final_equity": eq[-1], "max_dd": ((eq - peak) / peak).min()}


def _fmt(s: dict) -> str:
    if s["n"] == 0:
        return "n=0"
    p05 = "n/a" if np.isnan(s["p05"]) else f"{s['p05']*100:+.2f}%"
    return (f"n={s['n']:,}, win {s['win_rate']*100:.1f}%, median {s['median']*100:+.4f}%, "
            f"mean {s['mean']*100:+.4f}%, P05 {p05}, PF {s['profit_factor']:.3f}, "
            f"equity {s['final_equity']:.4f}, maxDD {s['max_dd']*100:.2f}%")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/discovery_v20_short_side.md")
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
    decision = apply_decision_rule(lpl_q, vol_q)

    short_sigs = disc[decision == "avoid_long"].sort_values("timestamp")
    long_sigs = disc[decision == "long_candidate"].sort_values("timestamp")
    print(f"avoid_long signals: {len(short_sigs):,}, long_candidate: {len(long_sigs):,}")

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    lines = ["## A. Short trades from `avoid_long`, by hold length\n",
             "The long side is shown at the same hold for reference. Both "
             "pay identical fees and the same stated 5bps/side slippage "
             "assumption.\n",
             "| Hold | Side | Stats |", "|---|---|---|"]
    short_results = {}
    for hold in HOLD_MINUTES:
        print(f"  simulating hold={hold}m...")
        s_short = simulate_side(short_sigs, price_history, sorted_ts, hold, short=True)
        s_long = simulate_side(long_sigs, price_history, sorted_ts, hold, short=False)
        short_results[hold] = s_short
        lines.append(f"| {hold}m | **short (avoid_long)** | {_fmt(_stats(s_short))} |")
        lines.append(f"| {hold}m | long (reference) | {_fmt(_stats(s_long))} |")

    # year stability at the short side's best hold by profit factor
    best_hold = max(short_results, key=lambda h: _stats(short_results[h])["profit_factor"])
    lines_c = [f"## C. Year stability — short side at {best_hold}m (its best hold by profit factor)\n",
               "A short that only worked in one bear year is a directional "
               "bet on that period, not an edge.\n",
               "| Year | n | Win rate | Median | Mean |", "|---|---|---|---|---|"]
    ydf = pd.DataFrame(short_results[best_hold])
    pos_years = []
    for year in sorted(ydf["year"].unique()):
        sub = ydf.loc[ydf["year"] == year, "net_return"]
        if len(sub) < MIN_CELL_N:
            lines_c.append(f"| {year} | {len(sub)} | n too few | - | - |")
            continue
        pos_years.append(sub.median() > 0)
        lines_c.append(f"| {year} | {len(sub):,} | {(sub>0).mean()*100:.1f}% | "
                       f"{sub.median()*100:+.4f}% | {sub.mean()*100:+.4f}% |")
    if pos_years:
        lines_c.append(f"\nYears with positive median: {sum(pos_years)}/{len(pos_years)}\n")

    section_b = (
        "## B. Unmodelled cost: funding\n\n"
        "Verified absent from both the stored candidate state and the raw "
        "backfill cache (which holds OHLCV only): **funding rate is not in "
        "this dataset**. A real perpetual-futures short pays or receives "
        "funding every 8h, and during sustained bull periods a short "
        "typically *pays*. The simulation above therefore **overstates** "
        "short-side returns by an unknown amount that grows with hold "
        "length — the 1440m rows are the most affected. `exchange_client.py` "
        "can fetch funding history, but Bitget caps it at roughly 100 "
        "records (~33 days), so backfilling it to 2020 is not possible; "
        "only prospective collection would fix this.\n\n"
        "This is a hard limit on how far the short-side numbers can be "
        "trusted, not a rounding detail.\n"
    )

    header = (
        "# Discovery v20 — the short side (`avoid_long`), tested for the first time\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "`avoid_long` (LPL==Q5 & Vol==Q5) has been explicitly "
        "non-tradeable since Phase B and was never revisited, despite "
        "discovery_v5 finding a negative 4h median in 7/7 years. Purely "
        "descriptive; does not change decision_rule_v1 and does not "
        "propose trading shorts. Discovery only (2020-2025); 2026 "
        "untouched.\n\n"
        "---\n\n"
    )
    full = header + "\n".join(lines) + "\n\n---\n\n" + section_b + "\n---\n\n" + "\n".join(lines_c) + "\n"

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
