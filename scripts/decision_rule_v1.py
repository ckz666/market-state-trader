"""
Decision Rule v1 — Phase B (Decision Design), strictly separated from
Phase C (Trading Validation: fees, slippage, stops, position sizing,
walk-forward). This translates the validated Phase A hypothesis into a
named decision, and checks how often it fires and what its raw forward-
return distribution looks like — it does NOT compute PnL, does NOT apply
fees/slippage, does NOT size positions, and does NOT define an exit rule
beyond the fixed 4h horizon the hypothesis was validated on. That's
deliberate: the point right now is confirming the rule as specified
produces the exact state population already validated, and measuring its
signal frequency — not optimizing it into a strategy.

FROZEN RULE (no thresholds tuned on 2026 — reuses hypothesis_validation.py's
exact frozen z-score parameters and quintile bin edges, fit only on the
2020-2025 discovery period):

    LPL = avg(zscore(bb_position), zscore(vwap_distance))
    LPL quintile, Volatility quintile: frozen 5-quantile edges from discovery

    IF   LPL == Q1 (lowest quintile)  AND Volatility == Q5 (highest quintile):
         decision = "long_candidate"
    ELIF LPL == Q5 (highest quintile) AND Volatility == Q5 (highest quintile):
         decision = "avoid_long"   (candidate for short / at minimum: do not go long)
    ELSE:
         decision = "no_signal"

Target horizon: 4h — where the OOS test showed the most consistent
confirmation (per the project discussion, 15m is explicitly excluded as
"not yet robust" in the highest-volatility quintile). Only the two most
extreme, most-tested cells get a decision; every other state is
deliberately "no_signal" rather than extrapolating the hypothesis to
combinations that were not specifically OOS-validated.

Usage:
    .venv/bin/python scripts/decision_rule_v1.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from discovery_report import load_candidates, horizon_stats, HORIZONS
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges, apply_quintile
import mst_config as config

TARGET_HORIZON = "4h"


def apply_decision_rule(lpl_q: pd.Series, vol_q: pd.Series) -> pd.Series:
    decision = pd.Series("no_signal", index=lpl_q.index)
    decision[(lpl_q == "Q1") & (vol_q == "Q5")] = "long_candidate"
    decision[(lpl_q == "Q5") & (vol_q == "Q5")] = "avoid_long"
    return decision


def report_period(df: pd.DataFrame, decision: pd.Series, period_name: str) -> str:
    lines = [f"### {period_name} (n={len(df):,})\n"]
    total = len(df)
    lines.append("| Decision | Count | % of period | Signals/day (approx) |")
    lines.append("|---|---|---|---|")
    days = (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 86400
    for label in ["long_candidate", "avoid_long", "no_signal"]:
        n = (decision == label).sum()
        per_day = n / days if days > 0 else 0
        lines.append(f"| {label} | {n:,} | {n/total*100:.1f}% | {per_day:.3f} |")

    lines.append(f"\n**Realized {TARGET_HORIZON} forward-return distribution per decision:**\n")
    lines.append("| Decision | n | Mean | Median | Win Rate | Std | P05 | P95 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    fwd = df[f"fwd_{TARGET_HORIZON}"]
    for label in ["long_candidate", "avoid_long"]:
        mask = decision == label
        s = horizon_stats(fwd[mask])
        if not s:
            lines.append(f"| {label} | 0 | - | - | - | - | - | - |")
            continue
        lines.append(f"| {label} | {s['n']:,} | {s['mean']*100:+.4f}% | {s['median']*100:+.4f}% | "
                      f"{s['win_rate']*100:.1f}% | {s['std']*100:.3f}% | {s['p05']*100:+.2f}% | {s['p95']*100:+.2f}% |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "reports", "decision_rule_v1.md"))
    args = p.parse_args()

    print("Loading candidates...")
    df = load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()
    val = df[df["timestamp"] >= cutoff].copy()
    print(f"Discovery: {len(disc):,} | Validation: {len(val):,}")

    # Exactly the frozen parameters from hypothesis_validation.py — fit on
    # discovery only, applied as-is to both periods (validation genuinely
    # untouched; discovery reported too, for direct comparison).
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

    print("Discovery decision counts:", disc_decision.value_counts().to_dict())
    print("Validation decision counts:", val_decision.value_counts().to_dict())

    md_disc = report_period(disc, disc_decision, "Discovery (2020-2025, in-sample)")
    md_val = report_period(val, val_decision, "Validation (2026, out-of-sample)")

    header = (
        "# Decision Rule v1 — signal frequency and raw realized distribution\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "**Phase B (Decision Design) only** — NOT a backtest. No fees, no "
        "slippage, no position sizing, no stop-loss/take-profit, no "
        "walk-forward. This measures exactly two things: how often the "
        "frozen rule fires, and what the raw realized forward-return "
        "distribution of its signals looks like, in both the discovery "
        "period (for reference) and the untouched validation period. Phase "
        "C (Trading Validation) is a deliberately separate, later step.\n\n"
        "**Rule** (frozen, no thresholds tuned on 2026 — see module "
        "docstring for the exact frozen parameters):\n\n"
        "```\n"
        "IF   LPL == Q1 (lowest quintile)  AND Volatility == Q5 (highest): "
        "long_candidate\n"
        "ELIF LPL == Q5 (highest quintile) AND Volatility == Q5 (highest): "
        "avoid_long\n"
        "ELSE: no_signal\n"
        "```\n\n"
        f"Target horizon: {TARGET_HORIZON}.\n\n---\n\n"
    )
    full = header + "## Signal frequency and realized outcomes\n\n" + md_disc + "\n" + md_val

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
