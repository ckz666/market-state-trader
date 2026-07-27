"""
Export the frozen LPL / volatility transform parameters to JSON so live
code can apply them without ever re-fitting.

This matters more than it looks. Every OOS result in this project rests
on fitting these on 2020-2025 ONLY and applying them unchanged. If the
live shadow recorder called `fit_params()` on whatever data it happened
to have, it would silently re-fit on live data and quietly invalidate
the comparison with every published figure.

Output: data/frozen_params.json

Usage:
    .venv/bin/python scripts/export_frozen_params.py
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from discovery_report import load_candidates
from hypothesis_validation import fit_params, apply_lpl, fit_quintile_edges


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoff", default="2026-01-01")
    p.add_argument("--historical", default="data/historical_candidates.json")
    p.add_argument("--out", default="data/frozen_params.json")
    args = p.parse_args()

    df = load_candidates([args.historical])
    disc = df[df["timestamp"] < pd.Timestamp(args.cutoff, tz="UTC")].copy()
    print(f"Fitting on {len(disc):,} Discovery candidates (< {args.cutoff})")

    params = fit_params(disc)
    disc["local_price_location"] = apply_lpl(disc, params)
    lpl_edges = fit_quintile_edges(disc["local_price_location"])
    vol_edges = fit_quintile_edges(disc["volatility_atr_norm"])

    out = {
        "fitted_on": {"source": args.historical, "cutoff": args.cutoff, "n_rows": int(len(disc))},
        "generated": datetime.now(timezone.utc).isoformat(),
        "lpl": {k: float(v) for k, v in params.items()},
        "lpl_quintile_edges": [float(x) for x in lpl_edges],
        "vol_quintile_edges": [float(x) for x in vol_edges],
        "note": ("Frozen 2020-2025. Live code MUST load these rather than "
                 "re-fitting, or every OOS comparison silently breaks."),
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
