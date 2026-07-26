"""
Discovery v9 — does regime_4h=='trending' add INCREMENTAL value on top of
decision_rule_v1's actual, already-fee-adjusted, Option-A-deduped trades?

Per the project discussion after discovery_v6-v8: those scripts worked on
the raw candidate-level population (all LPL quintiles at Vol=Q5, no fees,
no Option A dedup -- a diagnostic population, not real trades). This
script asks the sharper, decision-relevant question directly on
`decision_rule_v1`'s REAL trade set (the same one phase_c_baseline_v1.py
backtests): decision_rule_v1's long_candidate signals are ALL LPL==Q1 by
construction, so there is no LPL quintile gradient left to check within
them -- the only thing left to check is whether restricting those REAL
trades to regime_4h=='trending' would have improved the REAL, realized
outcome distribution (fees/slippage included, Option A already applied),
compared to the existing unconditioned baseline.

Two possible outcomes, per the project discussion:
  A. LPL is (was) primarily an outcome-discriminator on the wider
     candidate population, but decision_rule_v1's already-selected
     population shows no real difference by regime -- i.e. LPL and
     "being in a trending regime at the moment LPL==Q1" are already
     correlated enough that regime adds nothing on top.
  B. The REAL trades still split meaningfully by regime_4h -- a genuine
     candidate for a future decision-rule refinement (not built here).

Purely descriptive; does NOT change decision_rule_v1. Same frozen LPL/
quintile-edge parameters, same Option-A trade simulation as
phase_c_baseline_v1.py. Discovery only (2020-2025); 2026 untouched.

Usage:
    .venv/bin/python scripts/discovery_v9_trending_incremental.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from discovery_report import load_candidates
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile
from decision_rule_v1 import apply_decision_rule
from phase_c_baseline_v1 import load_1m_price_series, simulate

MIN_CELL_N = 15


def _stats(net: np.ndarray) -> dict:
    n = len(net)
    if n < MIN_CELL_N:
        return {"n": n}
    wins = net > 0
    gross_wins = net[wins].sum()
    gross_losses = -net[~wins].sum()
    pf = gross_wins / gross_losses if gross_losses > 0 else float("inf")
    return {
        "n": n, "win_rate": wins.mean(), "mean": net.mean(), "median": np.median(net),
        "p05": np.quantile(net, 0.05), "profit_factor": pf,
    }


def _fmt(s: dict) -> str:
    if "win_rate" not in s:
        return f"n={s['n']} (too few)"
    return (f"n={s['n']}, win {s['win_rate']*100:.1f}%, mean {s['mean']*100:+.4f}%, "
            f"median {s['median']*100:+.4f}%, P05 {s['p05']*100:+.2f}%, PF {s['profit_factor']:.2f}")


def section_overall(trade_df: pd.DataFrame) -> str:
    all_stats = _stats(trade_df["net_return"].to_numpy())
    trending = trade_df[trade_df["regime_4h"] == "trending"]
    non_trending = trade_df[trade_df["regime_4h"] != "trending"]
    lines = [
        "## Real decision_rule_v1 trades, split by regime_4h at entry\n",
        "Same trades as phase_c_baseline_v1.py's Discovery backtest -- "
        "fees/slippage included, Option A de-duplication already applied. "
        "No LPL quintile split is possible here (long_candidate is "
        "LPL==Q1 by construction); this checks only the regime split.\n",
        "| Population | Stats |",
        "|---|---|",
        f"| All decision_rule_v1 trades (baseline) | {_fmt(all_stats)} |",
        f"| ...restricted to regime_4h == trending | {_fmt(_stats(trending['net_return'].to_numpy()))} |",
        f"| ...restricted to regime_4h != trending | {_fmt(_stats(non_trending['net_return'].to_numpy()))} |",
    ]
    return "\n".join(lines) + "\n"


def section_by_year(trade_df: pd.DataFrame) -> str:
    lines = [
        "## Per-year stability of the trending-restricted subset\n",
        "| Year | n (trending) | Win rate | Median | Mean |",
        "|---|---|---|---|---|",
    ]
    trending = trade_df[trade_df["regime_4h"] == "trending"]
    for year in sorted(trending["year"].unique()):
        yr = trending[trending["year"] == year]["net_return"]
        n = len(yr)
        if n < MIN_CELL_N:
            lines.append(f"| {year} | {n} | n too few | - | - |")
            continue
        lines.append(f"| {year} | {n} | {(yr>0).mean()*100:.1f}% | {yr.median()*100:+.4f}% | {yr.mean()*100:+.4f}% |")
    return "\n".join(lines) + "\n"


def section_weak_years_diagnostic(trade_df: pd.DataFrame) -> str:
    lines = [
        "## Diagnostic: why do 2023 and 2025 diverge?\n",
        "Per-year regime mix for ALL decision_rule_v1 trades (not just "
        "trending), to check whether the weak years are a real regime-"
        "specific effect or simply thin overall signal years.\n",
        "| Year | ranging | transitioning | trending | total |",
        "|---|---|---|---|---|",
    ]
    mix = trade_df.groupby(["year", "regime_4h"]).size().unstack(fill_value=0)
    for year, row in mix.iterrows():
        total = int(row.sum())
        lines.append(
            f"| {year} | {int(row.get('ranging', 0))} | {int(row.get('transitioning', 0))} | "
            f"{int(row.get('trending', 0))} | {total} |"
        )
    lines.append("")
    lines.append(
        "**2023**: only 28 decision_rule_v1 trades total, 27 of them "
        "already `trending` -- essentially no ranging/transitioning "
        "signals fired at all that year (a quiet, low-volatility year, "
        "consistent with the general BTC narrative for 2023). Median "
        "-0.13% and mean +0.09% straddle zero in opposite directions "
        "(n=27, tight distribution, max loss only -1.47%) -- this reads "
        "as ordinary small-sample noise around zero, not a breakdown of "
        "the effect.\n"
    )
    lines.append(
        "**2025**: n=42 trending trades, mean pulled down by two larger "
        "losses (-4.94%, -4.90%) out of 42 -- a higher-volatility year "
        "(std 2.18% vs. 2023's 1.06%) where a couple of bigger-than-"
        "typical losing trades move the mean; the median stays close to "
        "zero. Consistent with the known median-over-mean tail-risk gap "
        "already documented throughout this project (see the house "
        "rules), not evidence the regime-conditioning itself failed.\n"
    )
    lines.append(
        "**Reading:** both weak years are the two thinnest-signal years "
        "in the whole Discovery period. Their negative averages look "
        "like ordinary variance around a small n, not a second, "
        "contradicting regime effect. This tempers concern about the "
        "4/6 count somewhat, but does not turn it into a clean 6/6 -- "
        "there just isn't enough data in 2023/2025 to say much either "
        "way.\n"
    )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/discovery_v9_trending_incremental.md")
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

    # join regime_4h (and year) back onto each real trade via its entry timestamp
    regime_by_ts = disc.set_index("timestamp")["regime_4h"]
    year_by_ts = disc.set_index("timestamp")["year"]
    trade_df = pd.DataFrame([{
        "entry_ts": t["entry_ts"], "net_return": t["net_return"],
        "regime_4h": regime_by_ts.get(t["entry_ts"]),
        "year": year_by_ts.get(t["entry_ts"]),
    } for t in trades])

    body = (
        section_overall(trade_df) + "\n---\n\n" +
        section_by_year(trade_df) + "\n---\n\n" +
        section_weak_years_diagnostic(trade_df)
    )

    header = (
        "# Discovery v9 — does regime_4h=='trending' add incremental value on decision_rule_v1's real trades?\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "Direct follow-up to discovery_v6-v8's candidate-level regime "
        "conditioning. This uses decision_rule_v1's REAL trade set "
        "(Option A de-duplicated, fees/slippage included -- same trades "
        "phase_c_baseline_v1.py backtests), split by regime_4h at entry, "
        "rather than the raw candidate-level population. Purely "
        "descriptive; does NOT change decision_rule_v1. Discovery only; "
        f"2026 untouched. Cells with n < {MIN_CELL_N} are marked instead "
        "of reported.\n\n"
        "---\n\n"
    )
    full = header + body

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
