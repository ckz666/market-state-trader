"""
Discovery v16 — why did decision_rule_v3's trade-level and
candidate-level OOS results disagree?

The 2026 OOS run (decision_rule_v3_micro_return_filter_oos_v1.py) found:
  - trade level (Option A de-duplicated, n=24): filter improves every
    primary metric (win 54.2% vs 51.3%, median +0.377% vs +0.179%,
    PF 1.565 vs 0.868)
  - candidate level (all signals, n=45): filter mildly HURTS
    (win 57.8% vs 59.3%, median identical, PF 0.965 vs 1.122)

Two competing explanations, indistinguishable at n=24/45:
  (i) SMALL-SAMPLE NOISE — with 24 trades, a handful drive everything,
      and the disagreement is luck.
  (ii) SYSTEMATIC MECHANISM — Option A de-duplication doesn't just
      reduce trade count, it changes WHICH signals become trades (the
      first signal of a cluster wins; later ones are skipped while a
      position is open). If micro_return_5m==Q1 signals sit at
      systematically different positions within signal clusters than
      other signals, the filter interacts with de-duplication itself,
      independent of any predictive content.

This script tests both on the Discovery period, where the same two views
have 1,064 trades and 3,276 candidates instead of 24 and 45.

  A. Reproduce both views on Discovery. If the same directional
     disagreement appears there at 40x the sample, explanation (ii) is
     supported; if both views agree on Discovery, (i) is more likely and
     the 2026 discrepancy was noise.
  B. Direct test of the proposed mechanism: does Option A de-duplication
     retain filtered signals at a different rate than unfiltered ones,
     and do filtered signals sit at different positions within signal
     clusters?

Purely diagnostic; does not change decision_rule_v1 and does not
re-tune anything. Discovery only (2020-2025); 2026 numbers are quoted
from the already-published OOS report for comparison, not recomputed
or re-analyzed here.

Usage:
    .venv/bin/python scripts/discovery_v16_trade_vs_candidate_discrepancy.py
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
from phase_c_baseline_v1 import load_1m_price_series, simulate

NEW_DIMENSIONS = [("micro_return_5m", ("micro_1m", "return_5m"), False)]


def _stats(net: np.ndarray) -> dict:
    n = len(net)
    if n == 0:
        return {"n": 0}
    wins = net > 0
    gw, gl = net[wins].sum(), -net[~wins].sum()
    return {"n": n, "win_rate": wins.mean(), "mean": net.mean(),
            "median": np.median(net), "profit_factor": gw / gl if gl > 0 else float("inf")}


def _fmt(s: dict) -> str:
    if s["n"] == 0:
        return "n=0"
    return (f"n={s['n']:,}, win {s['win_rate']*100:.1f}%, mean {s['mean']*100:+.4f}%, "
            f"median {s['median']*100:+.4f}%, PF {s['profit_factor']:.3f}")


def section_a(disc, sig_mask, price_history, sorted_ts) -> tuple[str, dict]:
    cand_all = disc.loc[sig_mask, "fwd_4h"].dropna()
    cand_filt = disc.loc[sig_mask & (disc["ret5m_q"] == "Q1"), "fwd_4h"].dropna()

    trades_all, _ = simulate(disc[sig_mask].sort_values("timestamp"), price_history, sorted_ts)
    trades_filt, _ = simulate(
        disc[sig_mask & (disc["ret5m_q"] == "Q1")].sort_values("timestamp"), price_history, sorted_ts)
    net_all = np.array([t["net_return"] for t in trades_all])
    net_filt = np.array([t["net_return"] for t in trades_filt])

    s_ta, s_tf = _stats(net_all), _stats(net_filt)
    s_ca, s_cf = _stats(cand_all.to_numpy()), _stats(cand_filt.to_numpy())

    lines = [
        "## A. Both views on Discovery (2020-2025) — 40x the OOS sample\n",
        "| View | Population | Stats |",
        "|---|---|---|",
        f"| Trade level (Option A, fees) | Baseline | {_fmt(s_ta)} |",
        f"| Trade level (Option A, fees) | + micro_return_5m==Q1 | {_fmt(s_tf)} |",
        f"| Candidate level (raw signals) | Baseline | {_fmt(s_ca)} |",
        f"| Candidate level (raw signals) | + micro_return_5m==Q1 | {_fmt(s_cf)} |",
        "",
        "**Direction of the filter's effect, per view:**\n",
        "| Metric | Trade level | Candidate level | Agree? |",
        "|---|---|---|---|",
    ]
    for key, label in [("win_rate", "Win rate"), ("median", "Median"), ("profit_factor", "Profit factor")]:
        t_delta = s_tf[key] - s_ta[key]
        c_delta = s_cf[key] - s_ca[key]
        agree = "yes" if (t_delta > 0) == (c_delta > 0) else "**NO**"
        fmt = (lambda v: f"{v*100:+.4f}pp") if key != "profit_factor" else (lambda v: f"{v:+.3f}")
        lines.append(f"| {label} | {fmt(t_delta)} | {fmt(c_delta)} | {agree} |")

    return "\n".join(lines) + "\n", {
        "trade_all": s_ta, "trade_filt": s_tf, "cand_all": s_ca, "cand_filt": s_cf,
        "n_trades_all": len(trades_all), "n_trades_filt": len(trades_filt),
        "n_cand_all": len(cand_all), "n_cand_filt": len(cand_filt),
    }


def section_b(disc, sig_mask, res) -> str:
    """Does the filter interact with Option A de-duplication itself?"""
    sigs = disc[sig_mask].sort_values("timestamp").copy()
    # position within a "cluster" of consecutive hourly signals: a new cluster
    # starts whenever the gap to the previous signal exceeds the 4h hold
    gaps = sigs["timestamp"].diff()
    new_cluster = (gaps.isna()) | (gaps > pd.Timedelta(hours=4))
    sigs["cluster_id"] = new_cluster.cumsum()
    sigs["pos_in_cluster"] = sigs.groupby("cluster_id").cumcount()
    sigs["is_filtered"] = sigs["ret5m_q"] == "Q1"

    retention_all = res["n_trades_all"] / res["n_cand_all"]
    retention_filt = res["n_trades_filt"] / res["n_cand_filt"]

    lines = [
        "## B. Does the filter interact with Option A de-duplication itself?\n",
        "Option A keeps the FIRST signal of a cluster and skips the rest "
        "while that position is open. If filtered signals sit at "
        "systematically different positions within clusters, the filter "
        "changes *which* signals survive de-duplication, not just how "
        "many — a mechanism that would produce a trade-vs-candidate "
        "discrepancy with no predictive content involved.\n",
        "**Signal-to-trade retention rate:**\n",
        "| Population | Candidates | Trades | Retention |",
        "|---|---|---|---|",
        f"| Baseline | {res['n_cand_all']:,} | {res['n_trades_all']:,} | {retention_all*100:.1f}% |",
        f"| Filtered (ret5m==Q1) | {res['n_cand_filt']:,} | {res['n_trades_filt']:,} | {retention_filt*100:.1f}% |",
        "",
        "**Position within signal cluster (0 = first signal, which Option A always takes):**\n",
        "| Population | n | Mean position | Median position | % at position 0 |",
        "|---|---|---|---|---|",
    ]
    for label, mask in [("All signals", pd.Series(True, index=sigs.index)),
                        ("Filtered (ret5m==Q1)", sigs["is_filtered"]),
                        ("Non-filtered", ~sigs["is_filtered"])]:
        sub = sigs[mask]
        lines.append(
            f"| {label} | {len(sub):,} | {sub['pos_in_cluster'].mean():.2f} | "
            f"{sub['pos_in_cluster'].median():.1f} | {(sub['pos_in_cluster']==0).mean()*100:.1f}% |"
        )
    lines.append(
        "\nIf the filtered population sits disproportionately at position "
        "0, it is over-represented among exactly the signals Option A "
        "would have taken anyway — meaning the filter's apparent "
        "trade-level benefit partly reflects cluster timing rather than "
        "signal quality.\n"
    )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--price-cache", default="data/backfill_cache/BTC_USDT_1m.csv")
    p.add_argument("--out", default="data/reports/discovery_v16_trade_vs_candidate_discrepancy.md")
    args = p.parse_args()

    print("Loading candidates...")
    dr.DIMENSIONS = dr.DIMENSIONS + NEW_DIMENSIONS
    df = dr.load_candidates([args.historical])
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    disc = df[df["timestamp"] < cutoff].copy()  # Discovery only

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])
    ret_edges = fit_quintile_edges(disc["micro_return_5m"].dropna())
    lpl_q = apply_quintile(disc["local_price_location"], lpl_edges)
    vol_q = apply_quintile(disc["volatility_atr_norm"], vol_edges)
    disc["ret5m_q"] = apply_quintile(disc["micro_return_5m"], ret_edges)
    sig_mask = apply_decision_rule(lpl_q, vol_q) == "long_candidate"

    print(f"Loading 1m price series from {args.price_cache}...")
    price_history = load_1m_price_series(args.price_cache)
    sorted_ts = sorted(price_history.keys())

    md_a, res = section_a(disc, sig_mask, price_history, sorted_ts)
    md_b = section_b(disc, sig_mask, res)

    reference = (
        "\n---\n\n## Reference: the 2026 OOS numbers this is explaining\n\n"
        "Quoted unchanged from `decision_rule_v3_micro_return_filter_oos_v1.md` "
        "(not recomputed here).\n\n"
        "| View | Baseline | Filtered |\n|---|---|---|\n"
        "| Trade level | n=39, win 51.3%, median +0.1787%, PF 0.868 | n=24, win 54.2%, median +0.3772%, PF 1.565 |\n"
        "| Candidate level | n=113, win 59.3%, median +0.3110%, PF 1.122 | n=45, win 57.8%, median +0.3110%, PF 0.965 |\n"
    )

    header = (
        "# Discovery v16 — explaining decision_rule_v3's trade-vs-candidate OOS discrepancy\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "The 2026 OOS run disagreed between its trade-level (n=24, filter "
        "looks strong) and candidate-level (n=45, filter looks mildly "
        "harmful) views. This reproduces both views on Discovery, where "
        "they have ~1,000 trades and ~3,000 candidates, to distinguish "
        "small-sample noise from a systematic Option-A-de-duplication "
        "mechanism. Purely diagnostic; does not change decision_rule_v1 "
        "and re-tunes nothing. Discovery only (2020-2025).\n\n"
        "---\n\n"
    )
    full = header + md_a + "\n---\n\n" + md_b + reference

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(full)
    print(f"\nWrote report to {args.out} ({len(full):,} chars)")


if __name__ == "__main__":
    main()
