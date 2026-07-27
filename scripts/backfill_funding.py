"""
Backfill historical funding rates — the one cost component this project
has never modelled.

DATA SOURCE PROBLEM, stated up front: all price/kline data in this
project is **Bitget** (via ccxt), but Bitget's funding history is capped
at ~100 records (~33 days) and ignores `since` — verified directly.
Binance publishes complete funding history back to 2020-01 via
data.binance.vision. So the only way to get 6 years of funding is to use
a *different exchange's* rates alongside Bitget prices.

That is an approximation, not a fix. This script therefore does two
things:

  1. Downloads Binance USDⓈ-M BTCUSDT funding (monthly zips, ~825 bytes
     each) for the full backfill range.
  2. **Measures the proxy error** by fetching Bitget's available ~33
     days via ccxt and comparing them directly, so the size of the
     mismatch is a measured number rather than an assumption.

Funding is paid every 8h on both venues. A long position pays when the
rate is positive and receives when negative; a short is the reverse.

Output: data/backfill_cache/BTCUSDT_funding.csv
        (columns: timestamp_ms, funding_rate)

Usage:
    .venv/bin/python scripts/backfill_funding.py
"""
import argparse
import io
import os
import sys
import zipfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import urllib.request

BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT"


def month_range(start: str, end: str):
    cur = pd.Timestamp(start)
    last = pd.Timestamp(end)
    while cur <= last:
        yield cur.strftime("%Y-%m")
        cur += pd.DateOffset(months=1)


def download_month(ym: str) -> pd.DataFrame | None:
    url = f"{BASE}/BTCUSDT-fundingRate-{ym}.zip"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
    except Exception as e:
        print(f"  {ym}: {type(e).__name__} (likely not published)")
        return None
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        name = z.namelist()[0]
        df = pd.read_csv(z.open(name))
    # header names vary slightly across months; normalise positionally
    df.columns = [c.strip().lower() for c in df.columns]
    ts_col = next((c for c in df.columns if "time" in c), df.columns[0])
    rate_col = next((c for c in df.columns if "rate" in c), df.columns[-1])
    out = df[[ts_col, rate_col]].copy()
    out.columns = ["timestamp_ms", "funding_rate"]
    out = out[pd.to_numeric(out["timestamp_ms"], errors="coerce").notna()]
    out["timestamp_ms"] = out["timestamp_ms"].astype("int64")
    out["funding_rate"] = out["funding_rate"].astype(float)
    return out


def measure_proxy_error(binance: pd.DataFrame) -> str:
    """Compare against Bitget's own (short) funding history via ccxt."""
    try:
        import ccxt
        ex = ccxt.bitget()
        rows = ex.fetch_funding_rate_history("BTC/USDT:USDT", limit=100)
    except Exception as e:
        return f"Could not fetch Bitget funding for comparison: {type(e).__name__} {e}\n"
    if not rows:
        return "Bitget returned no funding history; proxy error not measurable.\n"

    bg = pd.DataFrame([{"timestamp_ms": r["timestamp"], "bitget": r["fundingRate"]} for r in rows])
    merged = bg.merge(binance.rename(columns={"funding_rate": "binance"}),
                      on="timestamp_ms", how="inner")
    if merged.empty:
        return ("Bitget and Binance funding timestamps did not overlap in the "
                "fetched window; proxy error not measurable.\n")
    d = merged["binance"] - merged["bitget"]
    per_8h_bps = d.abs().mean() * 10000
    return (
        f"Overlapping funding intervals compared: **{len(merged)}** "
        f"({pd.to_datetime(merged.timestamp_ms.min(), unit='ms')} to "
        f"{pd.to_datetime(merged.timestamp_ms.max(), unit='ms')})\n\n"
        f"- Correlation Binance vs Bitget: **{merged['binance'].corr(merged['bitget']):+.4f}**\n"
        f"- Mean Bitget rate: {merged['bitget'].mean()*100:+.5f}% per 8h\n"
        f"- Mean Binance rate: {merged['binance'].mean()*100:+.5f}% per 8h\n"
        f"- Mean absolute difference: **{per_8h_bps:.3f} bps per 8h interval** "
        f"(= {per_8h_bps*3:.2f} bps/day, {per_8h_bps*3*365/100:.2f}%/year)\n"
        f"- Max absolute difference: {d.abs().max()*10000:.2f} bps\n\n"
        "This is the measured cost of using Binance funding as a stand-in "
        "for Bitget. It is small relative to typical funding levels but "
        "not zero, and it is a real limitation of every funding-adjusted "
        "number downstream.\n"
    )


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", default="2020-01")
    p.add_argument("--end", default="2026-07")
    p.add_argument("--out", default="data/backfill_cache/BTCUSDT_funding.csv")
    p.add_argument("--report", default="data/reports/funding_backfill.md")
    args = p.parse_args()

    print(f"Downloading Binance funding {args.start} .. {args.end}")
    frames = []
    for ym in month_range(args.start, args.end):
        df = download_month(ym)
        if df is not None:
            frames.append(df)
            print(f"  {ym}: {len(df)} intervals")
    if not frames:
        print("No data downloaded.")
        return

    all_df = pd.concat(frames).drop_duplicates("timestamp_ms").sort_values("timestamp_ms")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    all_df.to_csv(args.out, index=False)
    print(f"\nWrote {len(all_df):,} funding intervals to {args.out}")

    print("Measuring Binance-vs-Bitget proxy error...")
    proxy = measure_proxy_error(all_df)

    ts = pd.to_datetime(all_df["timestamp_ms"], unit="ms", utc=True)
    yearly = all_df.assign(year=ts.dt.year).groupby("year")["funding_rate"].agg(["count", "mean", "median"])
    lines = ["## Coverage\n",
             f"- Intervals: **{len(all_df):,}** (8h funding)",
             f"- Range: {ts.min()} to {ts.max()}\n",
             "| Year | Intervals | Mean rate per 8h | Median rate per 8h | Annualized cost to a LONG |",
             "|---|---|---|---|---|"]
    for year, row in yearly.iterrows():
        lines.append(f"| {year} | {int(row['count']):,} | {row['mean']*100:+.5f}% | "
                     f"{row['median']*100:+.5f}% | {row['mean']*3*365*100:+.2f}% |")

    header = (
        "# Funding rate backfill\n\n"
        f"Generated {datetime.now(timezone.utc).isoformat()}.\n\n"
        "**Source mismatch, stated plainly:** every price/kline in this "
        "project comes from **Bitget**, but Bitget's funding history is "
        "capped at ~100 records (~33 days) and ignores `since` (verified "
        "directly via ccxt). Complete history back to 2020 is only "
        "available from **Binance** (data.binance.vision). These figures "
        "therefore pair Binance funding with Bitget prices — an "
        "approximation whose error is measured below rather than "
        "assumed.\n\n"
        "---\n\n"
    )
    body = "\n".join(lines) + "\n\n---\n\n## Proxy error: Binance funding vs. Bitget's own\n\n" + proxy

    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w") as f:
        f.write(header + body)
    print(f"Wrote report to {args.report}")


if __name__ == "__main__":
    main()
