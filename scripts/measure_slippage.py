"""
Measure the slippage assumption against Bitget's actual order book.

Every simulation in this project applies `SLIPPAGE_BPS_PER_SIDE = 5` — a
**stated assumption**, never measured, and flagged as such in
phase_c_baseline_v1.py's own comments. It matters more than usual here:
the project's measured edge is roughly the same size as its round-trip
cost, so this single number moves every conclusion.

WHY BITGET AND NOT BINANCE: all prices in this project are Bitget.
Binance `aggTrades`/`bookTicker` bulk history is freely available and
would give years of data, but Binance is materially more liquid than
Bitget, so Binance-derived slippage would *understate* what this
strategy would actually pay. Measuring the wrong venue precisely is
worse than measuring the right one roughly.

WHAT THIS CAN AND CANNOT DO: Bitget exposes only the *current* order
book via ccxt — there is no historical book data. So this samples the
live book repeatedly and computes the slippage a market order of a given
notional would incur by walking the book. That is a real measurement on
the correct venue, but it is a **present-day snapshot**, not the
2020-2025 conditions the backtests cover. Liquidity in 2020-2022 was
almost certainly worse.

Slippage here = volume-weighted fill price vs. mid price, in bps, which
is what a market order actually pays (half-spread plus depth walk).

Usage:
    .venv/bin/python scripts/measure_slippage.py
    .venv/bin/python scripts/measure_slippage.py --samples 20 --interval 15
"""
import argparse
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from phase_c_baseline_v1 import SLIPPAGE_BPS_PER_SIDE

NOTIONALS = [1_000, 5_000, 10_000, 50_000, 100_000]  # USDT


def walk_book(levels, notional_usdt, mid):
    """VWAP fill price for a market order of `notional_usdt`, walking the
    book. Returns slippage in bps vs mid, or None if the book is too thin."""
    remaining = notional_usdt
    cost = qty = 0.0
    for price, size in levels:
        lvl_notional = price * size
        take = min(remaining, lvl_notional)
        q = take / price
        cost += q * price
        qty += q
        remaining -= take
        if remaining <= 0:
            break
    if remaining > 0 or qty == 0:
        return None  # book exhausted
    vwap = cost / qty
    return abs(vwap - mid) / mid * 10000


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--symbol", default="BTC/USDT:USDT")
    p.add_argument("--samples", type=int, default=12)
    p.add_argument("--interval", type=int, default=10, help="seconds between samples")
    p.add_argument("--out", default="data/reports/slippage_measurement.md")
    args = p.parse_args()

    import ccxt
    ex = ccxt.bitget()

    print(f"Sampling Bitget order book for {args.symbol}: "
          f"{args.samples} samples, {args.interval}s apart...")
    rows = []
    spreads = []
    for i in range(args.samples):
        try:
            ob = ex.fetch_order_book(args.symbol, limit=200)
        except Exception as e:
            print(f"  sample {i}: {type(e).__name__}")
            time.sleep(args.interval)
            continue
        bids, asks = ob["bids"], ob["asks"]
        if not bids or not asks:
            continue
        mid = (bids[0][0] + asks[0][0]) / 2
        spreads.append((asks[0][0] - bids[0][0]) / mid * 10000)
        for notional in NOTIONALS:
            buy = walk_book(asks, notional, mid)
            sell = walk_book(bids, notional, mid)
            rows.append({"notional": notional, "buy_bps": buy, "sell_bps": sell})
        print(f"  sample {i+1}/{args.samples}: mid={mid:.1f}, "
              f"spread={spreads[-1]:.2f}bps")
        if i < args.samples - 1:
            time.sleep(args.interval)

    if not rows:
        print("No book data collected.")
        return

    df = pd.DataFrame(rows)
    lines = [
        f"Samples collected: **{len(spreads)}** | "
        f"Top-of-book spread: mean **{np.mean(spreads):.2f} bps**, "
        f"median {np.median(spreads):.2f}, max {np.max(spreads):.2f}\n",
        "## Slippage by order size (one side, market order)\n",
        "| Notional | Buy slippage (bps) | Sell slippage (bps) | Mean both sides | vs. 5 bps assumption |",
        "|---|---|---|---|---|",
    ]
    for notional in NOTIONALS:
        sub = df[df["notional"] == notional]
        b, s = sub["buy_bps"].dropna(), sub["sell_bps"].dropna()
        if b.empty or s.empty:
            lines.append(f"| ${notional:,} | book too thin | book too thin | - | - |")
            continue
        both = float(np.mean([b.mean(), s.mean()]))
        delta = both - SLIPPAGE_BPS_PER_SIDE
        verdict = (f"**{delta:+.2f} bps** — assumption too "
                   f"{'optimistic' if delta > 0 else 'pessimistic'}")
        lines.append(f"| ${notional:,} | {b.mean():.2f} | {s.mean():.2f} | "
                     f"**{both:.2f}** | {verdict} |")

    lines.append(
        "\n## What this changes\n\n"
        f"The project applies {SLIPPAGE_BPS_PER_SIDE} bps per side, i.e. "
        f"{2*SLIPPAGE_BPS_PER_SIDE} bps round trip, inside a total "
        "round-trip cost of 22 bps (the rest being taker fees). Since the "
        "measured 4h net median is only about +4.7 bps per trade, a few "
        "bps of error either way is decisive at that hold; the 24h "
        "candidate (net median ~+50 bps) has far more headroom.\n"
    )

    header = (
        "# Slippage measurement — Bitget order book\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        f"`SLIPPAGE_BPS_PER_SIDE = {SLIPPAGE_BPS_PER_SIDE}` has been a "
        "stated assumption since Phase C, never measured. This walks "
        "Bitget's live order book — the venue all prices in this project "
        "come from — to price a market order of various sizes.\n\n"
        "**Two limitations, stated rather than buried:** (1) Bitget "
        "exposes only the current book, so this is a present-day "
        "snapshot, not the 2020-2025 conditions the backtests cover; "
        "liquidity was very likely worse in 2020-2022. (2) Sample window "
        "is minutes, so it does not capture stressed markets, which is "
        "exactly when this strategy's high-volatility entries fire.\n\n"
        "---\n\n"
    )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(header + "\n".join(lines) + "\n")
    print(f"\nWrote report to {args.out}")


# ── Sensitivity appendix ────────────────────────────────────────────────
# Added after the measurement showed slippage is ~60x smaller than assumed.
# Re-runs the two headline configurations across a range of slippage values
# so the reader can see how much the assumption alone was costing.

def sensitivity(slippage_values=(0.2, 1.0, 2.0, 5.0, 10.0)):
    import discovery_report as dr
    from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile
    from decision_rule_v1 import apply_decision_rule
    from phase_c_baseline_v1 import load_1m_price_series, lookup_price, ENTRY_EXIT_TOLERANCE_SEC
    import mst_config as config

    df = dr.load_candidates(["data/historical_candidates.json"])
    disc = df[df["timestamp"] < pd.Timestamp("2026-01-01", tz="UTC")].copy()
    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_e = fit_quintile_edges(disc["local_price_location"])
    vol_e = fit_quintile_edges(disc["volatility_atr_norm"])
    dec = apply_decision_rule(apply_quintile(disc["local_price_location"], lpl_e),
                              apply_quintile(disc["volatility_atr_norm"], vol_e))
    sigs = disc[dec == "long_candidate"].sort_values("timestamp")
    ph = load_1m_price_series("data/backfill_cache/BTC_USDT_1m.csv")
    sts = sorted(ph.keys())
    tol = ENTRY_EXIT_TOLERANCE_SEC * 1000

    out = {}
    for hold in (240, 1440):
        grosses, open_until = [], None
        for _, r in sigs.iterrows():
            ts = r["timestamp"]
            if open_until is not None and ts < open_until:
                continue
            e_ms = int(ts.timestamp() * 1000)
            ep, xp = lookup_price(ph, sts, e_ms, tol), lookup_price(ph, sts, e_ms + hold*60_000, tol)
            if ep is None or xp is None:
                continue
            grosses.append((xp - ep) / ep)
            open_until = ts + pd.Timedelta(minutes=hold)
        g = np.array(grosses)
        out[hold] = {}
        for sl in slippage_values:
            net = g - 2*config.TAKER_FEE - 2*(sl/10000)
            wins = net > 0
            gw, gl = net[wins].sum(), -net[~wins].sum()
            out[hold][sl] = {"n": len(net), "median": np.median(net), "mean": net.mean(),
                             "pf": gw/gl if gl > 0 else float("inf"),
                             "equity": float(np.prod(1+net))}
    return out


def run_sensitivity():
    print("Running slippage sensitivity...")
    res = sensitivity()
    lines = ["\n---\n\n## Sensitivity: how much was the assumption costing?\n",
             "Same trades, only `SLIPPAGE_BPS_PER_SIDE` varied. The measured "
             "value is ~0.2 bps; the project assumed 5.\n",
             "| Hold | Slippage/side | n | Median | Mean | PF | Equity |",
             "|---|---|---|---|---|---|---|"]
    for hold, per_sl in res.items():
        for sl, s in per_sl.items():
            mark = " ← measured" if sl == 0.2 else (" ← assumed" if sl == 5.0 else "")
            lines.append(f"| {hold}m | {sl} bps{mark} | {s['n']:,} | {s['median']*100:+.4f}% | "
                         f"{s['mean']*100:+.4f}% | {s['pf']:.3f} | {s['equity']:.4f} |")
    with open("data/reports/slippage_measurement.md", "a") as f:
        f.write("\n".join(lines) + "\n")
    print("Appended sensitivity to data/reports/slippage_measurement.md")


if __name__ == "__main__":
    if "--sensitivity" in sys.argv:
        run_sensitivity()
    else:
        main()
