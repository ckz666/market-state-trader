"""
Phase 2: State Analysis Pipeline — loads candidates, computes per-context
and per-dimension statistics, and generates a readable report.

Usage:
    from analysis import full_report
    full_report("data/candidates.json")
"""
import json
import os
from collections import defaultdict


def load_candidates(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return data.get("candidates", [])


def _get_outcome(c, key, old_key):
    """Return outcome value — new key first, fall back to old key for backward compat."""
    val = c.get(key)
    if val is not None:
        return val
    return c.get(old_key)


def _extract_nested(d, *keys, default=None):
    for key in keys:
        if not isinstance(d, dict): return default
        d = d.get(key)
        if d is None: return default
    return d


# Numeric dimensions to analyze (dot-path → label)
NUMERIC_DIMS = {
    "candle.body_ratio":            "Candle: Body Ratio",
    "candle.upper_wick_ratio":      "Candle: Upper Wick",
    "candle.lower_wick_ratio":      "Candle: Lower Wick",
    "candle.close_location":        "Candle: Close Location",
    "candle.range_expansion":       "Candle: Range Expansion",
    "trend.strength":               "Trend: Strength",
    "trend.adx":                    "Trend: ADX",
    "momentum.strength":            "Momentum: Strength",
    "momentum.rsi":                 "Momentum: RSI",
    "volatility.prob_storm":        "Volatility: P(Storm)",
    "volatility.atr_norm":          "Volatility: ATR norm",
    "price_location.range_position_20": "Location: Range 20",
    "price_location.bb_position":   "Location: BB Position",
    "exhaustion.cycle_strength":    "Exhaustion: Cycle Strength",
    "exhaustion.trend_momentum_divergence": "Exhaustion: T-M Divergence",
}


def full_report(json_path: str, outcome_horizon: str = "4h"):
    """Print a complete analysis report."""
    candidates = load_candidates(json_path)
    if not candidates:
        print("No candidates found.")
        return

    # Filter to candidates with market_state and outcome
    outcome_key = f"forward_return_{outcome_horizon}"
    # Backward compat: also check old 'outcome_' prefix
    old_outcome_key = f"outcome_{outcome_horizon}"
    ms_cands = [c for c in candidates if c.get("market_state") and (c.get(outcome_key) is not None or c.get(old_outcome_key) is not None)]

    total = len(candidates)
    with_outcome = len(ms_cands)
    winners = sum(1 for c in ms_cands if _get_outcome(c, outcome_key, old_outcome_key) > 0)
    losers = sum(1 for c in ms_cands if _get_outcome(c, outcome_key, old_outcome_key) < 0)

    print("=" * 72)
    print("  MARKET STATE ANALYSIS REPORT")
    print("=" * 72)
    print(f"\n  DATA OVERVIEW")
    print(f"  {'─' * 50}")
    print(f"  Total candidates:           {total:>6d}")
    print(f"  With {outcome_horizon} outcome:       {with_outcome:>6d}")
    print(f"  Winners:                    {winners:>6d}  ({winners/with_outcome*100:.1f}%)" if with_outcome else "")
    print(f"  Losers:                     {losers:>6d}  ({losers/with_outcome*100:.1f}%)" if with_outcome else "")
    if with_outcome:
        mean = sum(_get_outcome(c, outcome_key, old_outcome_key) for c in ms_cands) / with_outcome
        print(f"  Overall expectancy:         {mean*100:>+.4f}%")

    # ── Context performance ──
    print(f"\n\n  CONTEXT PERFORMANCE ({outcome_horizon})")
    print(f"  {'─' * 50}")
    ctx_groups = defaultdict(list)
    for c in ms_cands:
        ctx = c.get("context", "unknown")
        ctx_groups[ctx].append(_get_outcome(c, outcome_key, old_outcome_key))

    for ctx in ["continuation", "mean_reversion", "extended", "compressed", "transition"]:
        vals = ctx_groups.get(ctx, [])
        if vals:
            w = sum(1 for v in vals if v > 0)
            m = sum(vals) / len(vals)
            print(f"  {ctx:<20s}  n={len(vals):>4d}  WR={w/len(vals)*100:5.1f}%  E={m*100:+7.4f}%")
        else:
            print(f"  {ctx:<20s}  n=   0")

    # ── Top discriminators ──
    if with_outcome >= 10:
        print(f"\n\n  TOP DISCRIMINATORS (winner vs loser separation)")
        print(f"  {'─' * 50}")
        discriminators = []
        for dim_path, label in NUMERIC_DIMS.items():
            keys = dim_path.split(".")
            w_vals = []
            l_vals = []
            for c in ms_cands:
                v = _extract_nested(c.get("market_state"), *keys)
                if v is None: continue
                if _get_outcome(c, outcome_key, old_outcome_key) > 0: w_vals.append(v)
                elif _get_outcome(c, outcome_key, old_outcome_key) < 0: l_vals.append(v)
            if len(w_vals) >= 5 and len(l_vals) >= 5:
                wm = sum(w_vals) / len(w_vals)
                lm = sum(l_vals) / len(l_vals)
                sep = abs(wm - lm)
                discriminators.append((label, dim_path, sep, wm, lm, len(w_vals) + len(l_vals)))

        discriminators.sort(key=lambda x: -x[2])
        for i, (label, _, sep, wm, lm, n) in enumerate(discriminators[:10]):
            print(f"  {i+1:>2d}. {label:<35s}  sep={sep:8.4f}  W={wm:.3f}  L={lm:.3f}  n={n}")

    # ── Direction breakdown ──
    print(f"\n\n  DIRECTION BREAKDOWN")
    print(f"  {'─' * 50}")
    for direction in ["long", "short"]:
        subset = [c for c in ms_cands if c.get("direction") == direction]
        if subset:
            w = sum(1 for c in subset if _get_outcome(c, outcome_key, old_outcome_key) > 0)
            m = sum(_get_outcome(c, outcome_key, old_outcome_key) for c in subset) / len(subset)
            print(f"  {direction:<10s}  n={len(subset):>4d}  WR={w/len(subset)*100:5.1f}%  E={m*100:+7.4f}%")

    # ── Context × Direction ──
    print(f"\n\n  CONTEXT × DIRECTION")
    print(f"  {'─' * 50}")
    for ctx in ["continuation", "mean_reversion", "extended", "compressed", "transition"]:
        for direction in ["long", "short"]:
            subset = [c for c in ms_cands if c.get("context") == ctx and c.get("direction") == direction]
            if len(subset) >= 3:
                w = sum(1 for c in subset if _get_outcome(c, outcome_key, old_outcome_key) > 0)
                m = sum(_get_outcome(c, outcome_key, old_outcome_key) for c in subset) / len(subset)
                print(f"  {ctx:<20s} {direction:<6s}  n={len(subset):>4d}  WR={w/len(subset)*100:5.1f}%  E={m*100:+7.4f}%")

    print(f"\n{'=' * 72}")
    print(f"  END OF REPORT")
    print(f"{'=' * 72}")


def context_summary(json_path: str) -> dict:
    """Return per-context statistics as a dict (for API)."""
    cands = load_candidates(json_path)
    result = {}
    for horizon in ["15m", "30m", "1h", "4h"]:
        ok = f"forward_return_{horizon}"
        old_ok = f"outcome_{horizon}"
        ctx_stats = defaultdict(lambda: {"total": 0, "wins": 0, "sum": 0.0})
        for c in cands:
            val = _get_outcome(c, ok, old_ok)
            if c.get("market_state") and val is not None:
                ctx = c.get("context", "unknown")
                ctx_stats[ctx]["total"] += 1
                if val > 0: ctx_stats[ctx]["wins"] += 1
                ctx_stats[ctx]["sum"] += val
        result[horizon] = {}
        for ctx, s in ctx_stats.items():
            result[horizon][ctx] = {
                "n": s["total"],
                "win_rate": round(s["wins"] / s["total"], 4) if s["total"] else None,
                "expectancy": round(s["sum"] / s["total"], 6) if s["total"] else None,
            }
    return result
