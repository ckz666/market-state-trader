"""
Discovery v26 — re-run the project's key results WITH funding costs.

Every simulation in v1-v25 ignored funding, because the data did not
exist (verified absent from both the stored state and the raw cache).
`backfill_funding.py` has now supplied 7,119 8-hourly intervals back to
2020-01, so the two results most exposed to funding can finally be
evaluated honestly:

  1. **The 24h hold (decision_rule_v4)** — the project's only candidate
     with profit factor above 1. A 24h position crosses ~3 funding
     intervals; a 4h position crosses 0 or 1. Funding therefore
     penalises the longer hold specifically, and the entire
     "longer is better" finding could be an artifact of ignoring it.
  2. **The short side (discovery_v20)** — shorts RECEIVE funding when
     the rate is positive, which it overwhelmingly is (mean +0.004% to
     +0.028% per 8h depending on year). v20 concluded the short side
     loses; funding works in its favour and might change that.

Funding convention: a long pays `rate` at each interval crossed while
the position is open; a short receives it. Applied per interval actually
crossed, not annualised or averaged.

Caveat carried from backfill_funding.md: the rates are **Binance**, the
prices are **Bitget**. Measured proxy error is 0.284 bps per 8h interval
(correlation +0.80 over the 10 overlapping intervals Bitget exposes).
Small relative to funding levels, not zero.

Discovery only (2020-2025); the 2026 OOS figures for the 24h candidate
are recomputed here too, since funding changes them.

Usage:
    .venv/bin/python scripts/discovery_v26_funding_adjusted.py
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
TOL_MS = ENTRY_EXIT_TOLERANCE_SEC * 1000


def load_funding(path: str) -> np.ndarray:
    f = pd.read_csv(path).sort_values("timestamp_ms")
    return f["timestamp_ms"].to_numpy(), f["funding_rate"].to_numpy()


def funding_cost(entry_ms: int, exit_ms: int, f_ts: np.ndarray, f_rate: np.ndarray) -> float:
    """Sum of funding rates for intervals strictly inside (entry, exit].
    Positive = cost to a long, benefit to a short."""
    lo = np.searchsorted(f_ts, entry_ms, side="right")
    hi = np.searchsorted(f_ts, exit_ms, side="right")
    return float(f_rate[lo:hi].sum()) if hi > lo else 0.0


def simulate(signals, price_history, sorted_ts, hold_min, f_ts, f_rate, short=False):
    trades = []
    position_open_until = None
    hold_ms = hold_min * 60_000
    for _, row in signals.iterrows():
        ts = row["timestamp"]
        if position_open_until is not None and ts < position_open_until:
            continue
        entry_ms = int(ts.timestamp() * 1000)
        exit_ms = entry_ms + hold_ms
        ep = lookup_price(price_history, sorted_ts, entry_ms, TOL_MS)
        xp = lookup_price(price_history, sorted_ts, exit_ms, TOL_MS)
        if ep is None or xp is None:
            continue
        move = (xp - ep) / ep
        gross = -move if short else move
        costs = 2 * config.TAKER_FEE + 2 * (SLIPPAGE_BPS_PER_SIDE / 10000)
        fund = funding_cost(entry_ms, exit_ms, f_ts, f_rate)
        fund_effect = +fund if short else -fund  # long pays, short receives
        trades.append({"net_excl_funding": gross - costs,
                       "net_incl_funding": gross - costs + fund_effect,
                       "funding": fund_effect})
        position_open_until = ts + pd.Timedelta(minutes=hold_min)
    return pd.DataFrame(trades)


def _stats(net: np.ndarray) -> dict:
    if len(net) == 0:
        return {"n": 0}
    wins = net > 0
    gw, gl = net[wins].sum(), -net[~wins].sum()
    eq = np.cumprod(1 + net)
    return {"n": len(net), "win_rate": wins.mean(), "median": np.median(net),
            "mean": net.mean(), "profit_factor": gw / gl if gl > 0 else float("inf"),
            "equity": eq[-1]}


def row(label, s):
    if s["n"] == 0:
        return f"| {label} | 0 | - | - | - | - | - |\n"
    return (f"| {label} | {s['n']:,} | {s['win_rate']*100:.1f}% | {s['median']*100:+.4f}% | "
            f"{s['mean']*100:+.4f}% | {s['profit_factor']:.3f} | {s['equity']:.4f} |\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--funding", default="data/backfill_cache/BTCUSDT_funding.csv")
    p.add_argument("--out", default="data/reports/discovery_v26_funding_adjusted.md")
    args = p.parse_args()

    print("Loading...")
    df = dr.load_candidates([args.historical])
    f_ts, f_rate = load_funding(args.funding)
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc, val = df[df["timestamp"] < cutoff].copy(), df[df["timestamp"] >= cutoff].copy()

    params = fit_params(disc)
    for d in (disc, val):
        d["local_price_location"] = apply_lpl(d, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])

    def signals_for(d, label):
        dec = apply_decision_rule(apply_quintile(d["local_price_location"], lpl_edges),
                                  apply_quintile(d["volatility_atr_norm"], vol_edges))
        return d[dec == label].sort_values("timestamp")

    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    hdr = "| Config | n | Win rate | Median | Mean | PF | Equity |\n|---|---|---|---|---|---|---|\n"
    body = "## 1. The 24h candidate, with and without funding (Discovery)\n\n" + hdr
    for hold in HOLDS:
        print(f"  discovery hold={hold}m...")
        t = simulate(signals_for(disc, "long_candidate"), price_history, sorted_ts, hold, f_ts, f_rate)
        body += row(f"{hold}m — excl. funding (as published)", _stats(t["net_excl_funding"].to_numpy()))
        body += row(f"**{hold}m — incl. funding**", _stats(t["net_incl_funding"].to_numpy()))
        body += (f"| ↳ mean funding per trade | | | | {t['funding'].mean()*100:+.4f}% | | |\n")

    body += "\n---\n\n## 2. The 24h candidate on 2026 OOS, with funding\n\n" + hdr
    for hold in HOLDS:
        print(f"  OOS hold={hold}m...")
        t = simulate(signals_for(val, "long_candidate"), price_history, sorted_ts, hold, f_ts, f_rate)
        body += row(f"{hold}m — excl. funding (as published)", _stats(t["net_excl_funding"].to_numpy()))
        body += row(f"**{hold}m — incl. funding**", _stats(t["net_incl_funding"].to_numpy()))

    body += ("\n---\n\n## 3. The short side, which RECEIVES funding (Discovery)\n\n"
             "discovery_v20 concluded the short side loses at every hold. "
             "Funding is overwhelmingly positive, so a short receives it — "
             "the one cost component that works in the short's favour.\n\n" + hdr)
    for hold in HOLDS:
        print(f"  short hold={hold}m...")
        t = simulate(signals_for(disc, "avoid_long"), price_history, sorted_ts, hold, f_ts, f_rate, short=True)
        body += row(f"{hold}m short — excl. funding (as published)", _stats(t["net_excl_funding"].to_numpy()))
        body += row(f"**{hold}m short — incl. funding**", _stats(t["net_incl_funding"].to_numpy()))
        body += (f"| ↳ mean funding received per trade | | | | {t['funding'].mean()*100:+.4f}% | | |\n")

    header = (
        "# Discovery v26 — key results re-run WITH funding costs\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Every simulation in v1-v25 ignored funding because the data did "
        "not exist. It now does (7,119 8-hourly intervals from 2020-01). "
        "A long pays the rate at each interval it holds through; a short "
        "receives it. **Source caveat:** rates are Binance, prices are "
        "Bitget — measured proxy error 0.284 bps per 8h interval "
        "(see funding_backfill.md). Discovery 2020-2025 plus the 2026 OOS "
        "figures for the 24h candidate, since funding changes those too.\n\n"
        "---\n\n"
    )
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(header + body)
    print(f"\nWrote report to {args.out}")


if __name__ == "__main__":
    main()
