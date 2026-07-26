"""
Backfill — reconstructs historical MarketState candidates over a past date
range, using the exact same compile/classify/decide code path the live
collector (main.py) uses, plus exact-target-time forward returns computed
from already-known historical 1m data (no waiting).

    "Wie sah der Market State zu diesem Zeitpunkt aus und was passierte
    danach?" — NOT a backtest. No position sequencing, no PnL, no
    entry/exit simulation. execution_price == state_price for every
    backfilled candidate (there is no live tick to record in the past);
    decision/direction are computed for schema completeness only, always
    assuming no open position. See README.md.

Writes to its own file (default data/historical_candidates.json), never to
the live collector's data/candidates.json — safe to run while the live
service is running.

Usage:
    .venv/bin/python scripts/backfill.py --start 2025-01-01 --end 2026-07-26
    .venv/bin/python scripts/backfill.py --days 180                # last 180 days, ending now
    .venv/bin/python scripts/backfill.py --start 2025-01-01 --dry-run  # fetch/cache only, no compute
"""
import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from exchange_client import ExchangeClient
from observation.compiler import compile as compile_state
from context import classify
from strategy import decide
from storage import CandidateLogger, Candidate
import mst_config as config

# Mirrors main.py's live fetch_ohlcv(..., limit=N) exactly — every backfilled
# candidate sees the SAME bounded trailing window a live cycle would have
# seen, not the full cumulative history (which would both diverge from live
# behavior and make get_indicators()'s pattern-scan O(n^2) over the backfill).
WINDOW = {"1m": 120, "15m": 96, "1h": 200, "4h": 50}
TF_MS = {"1m": 60_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000}

# How much history to fetch before --start so the first backfilled candle's
# bounded window (above) is already fully populated with real data, matching
# what a live cycle would have had — not partially short/NaN-warming-up.
LEAD_IN = {
    "1m": timedelta(minutes=WINDOW["1m"]) + timedelta(hours=1),
    "15m": timedelta(minutes=15 * WINDOW["15m"]) + timedelta(hours=2),
    "1h": timedelta(hours=WINDOW["1h"]) + timedelta(days=1),
    "4h": timedelta(hours=4 * WINDOW["4h"]) + timedelta(days=2),
}


def _cache_path(cache_dir: str, symbol: str, tf: str) -> str:
    tag = symbol.replace("/", "_").replace(":", "_")
    return os.path.join(cache_dir, f"{tag}_{tf}.csv")


def _write_cache_csv(path: str, rows: list):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp")
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)  # atomic — a crash mid-write can't corrupt the cache


async def fetch_with_cache(client: ExchangeClient, symbol: str, tf: str,
                            since_ms: int, until_ms: int, cache_dir: str, use_cache: bool) -> list:
    path = _cache_path(cache_dir, symbol, tf)
    existing_rows: list = []
    resume_since = since_ms

    if use_cache and os.path.exists(path):
        cached = pd.read_csv(path)
        if not cached.empty:
            cmin, cmax = int(cached["timestamp"].min()), int(cached["timestamp"].max())
            if cmin <= since_ms and cmax >= until_ms - TF_MS[tf]:
                rows = cached[(cached["timestamp"] >= since_ms) & (cached["timestamp"] < until_ms)]
                print(f"  {tf}: {len(rows)} candles from cache ({path})")
                return rows.values.tolist()
            if cmin <= since_ms:
                # Partial cache from an earlier/interrupted run that starts
                # early enough — resume fetching from where it left off
                # instead of re-fetching the whole range from scratch.
                existing_rows = cached[cached["timestamp"] < until_ms].values.tolist()
                resume_since = cmax + TF_MS[tf]
                print(f"  {tf}: resuming from cached checkpoint ({len(existing_rows)} candles "
                      f"already cached up to {datetime.fromtimestamp(cmax/1000, tz=timezone.utc)})")

    start_dt = datetime.fromtimestamp(resume_since / 1000, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(until_ms / 1000, tz=timezone.utc)
    expected = max(1, (until_ms - resume_since) // TF_MS[tf])
    print(f"  {tf}: fetching from exchange, {start_dt} -> {end_dt} (~{expected:,} candles)...")
    t0 = time.monotonic()
    last_print = [0.0]

    def progress(batches, last_ts):
        now = time.monotonic()
        if now - last_print[0] >= 5:
            # Time-based, not batch-count-based — batch size varies (Bitget's
            # historical endpoint caps at 200/call, not the requested limit).
            pct = min(100, (last_ts - resume_since) / max(1, until_ms - resume_since) * 100)
            when = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc)
            elapsed = now - t0
            eta_s = elapsed / max(pct, 0.01) * (100 - pct)
            print(f"    ...{tf}: ~{pct:4.1f}% ({batches} batches, up to {when}, "
                  f"ETA ~{eta_s/60:.0f}min)")
            last_print[0] = now

    async def checkpoint(fetched_so_far: list):
        # Runs every ~100 batches (~1min at Bitget's observed pace) and once
        # more at the end — persists progress incrementally instead of only
        # ever holding it in this process's memory for the whole run.
        _write_cache_csv(path, existing_rows + fetched_so_far)

    data = await client.fetch_ohlcv_range(symbol, tf, resume_since, until_ms,
                                           progress_cb=progress, checkpoint_cb=checkpoint)
    print(f"  {tf}: got {len(data)} new candles in {time.monotonic()-t0:.1f}s")

    combined = existing_rows + data
    _write_cache_csv(path, combined)
    return [r for r in combined if since_ms <= r[0] < until_ms]


def to_df(data: list) -> pd.DataFrame:
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)
    return df[~df.index.duplicated(keep="last")]


async def run(start_dt: datetime, end_dt: datetime, symbol: str, out_path: str,
              cache_dir: str, use_cache: bool, dry_run: bool):
    fetch_start = {tf: int((start_dt - LEAD_IN[tf]).timestamp() * 1000) for tf in WINDOW}
    fetch_end = {tf: int(end_dt.timestamp() * 1000) for tf in WINDOW}
    # 1m needs to reach past the last candle's 4h forward-return target too.
    fetch_end["1m"] = int((end_dt + timedelta(hours=4, minutes=5)).timestamp() * 1000)

    print(f"Backfilling {symbol} from {start_dt} to {end_dt}")
    async with ExchangeClient() as client:
        raw = {}
        for tf in ["1m", "15m", "1h", "4h"]:
            raw[tf] = await fetch_with_cache(client, symbol, tf, fetch_start[tf], fetch_end[tf],
                                              cache_dir, use_cache)

    if dry_run:
        print("Dry run — fetched/cached only, no candidates computed.")
        return

    df_1m, df_15m, df_1h, df_4h = (to_df(raw[tf]) for tf in ["1m", "15m", "1h", "4h"])
    price_history = {int(r[0]): float(r[4]) for r in raw["1m"]}
    if price_history:
        lo = datetime.fromtimestamp(min(price_history) / 1000, tz=timezone.utc)
        hi = datetime.fromtimestamp(max(price_history) / 1000, tz=timezone.utc)
        print(f"price_history: {len(price_history)} 1m closes ({lo} -> {hi})")
    else:
        print("price_history: empty")

    logger = CandidateLogger(file_path=out_path)
    existing_ts = {c.timestamp for c in logger.candidates}
    print(f"{out_path}: {len(logger.candidates)} existing candidates (will be skipped, not duplicated)")

    hours = pd.date_range(start_dt.replace(minute=0, second=0, microsecond=0), end_dt, freq="1h")
    # Indicators like ADX (window=14) crash outright on too-short input rather
    # than returning NaN. Live never hits this (main.py always fetches a full
    # window from an exchange with years of prior history) — but the very
    # first hours after --start, if --start is at/near the true beginning of
    # available exchange history, genuinely can't have a full lead-in yet.
    # Matches the >30 threshold compiler.py already uses for its 4h guard.
    MIN_BARS = 30

    added, skipped_existing, skipped_gap, skipped_error = 0, 0, 0, 0
    t0 = time.monotonic()

    for state_ts in hours:
        if state_ts.isoformat() in existing_ts:
            skipped_existing += 1
            continue

        closed_1h = df_1h[df_1h.index + pd.Timedelta(hours=1) <= state_ts].tail(WINDOW["1h"])
        if len(closed_1h) < MIN_BARS:
            skipped_gap += 1
            continue
        last_closed_open = closed_1h.index[-1]
        if last_closed_open + pd.Timedelta(hours=1) != state_ts:
            skipped_gap += 1  # no 1h candle actually closed exactly at this hour (exchange data gap)
            continue

        closed_4h = df_4h[df_4h.index + pd.Timedelta(hours=4) <= state_ts].tail(WINDOW["4h"])
        closed_15m = df_15m[df_15m.index + pd.Timedelta(minutes=15) <= state_ts].tail(WINDOW["15m"])
        closed_1m = df_1m[df_1m.index + pd.Timedelta(minutes=1) <= state_ts].tail(WINDOW["1m"])

        try:
            state = compile_state(closed_1h, closed_4h, df_15m=closed_15m, df_1m=closed_1m, state_ts=state_ts)
            context = classify(state)
            atr_pct = state.state_1h.volatility.atr_norm
            decision = decide(context, atr_pct, has_open_position=False, position_side=None)
        except Exception as e:
            skipped_error += 1
            print(f"  ! skipped {state_ts}: {e}")
            continue

        direction = "none"
        if decision.action.startswith("open_"):
            direction = "long" if "long" in decision.action else "short"
        elif context.direction_bias in ("long", "bullish") and decision.action != "hold":
            direction = "long"
        elif context.direction_bias in ("short", "bearish") and decision.action != "hold":
            direction = "short"

        logger.candidates.append(Candidate(
            timestamp=state.timestamp.isoformat(),
            direction=direction,
            state_price=state.ohlcv["close"],
            execution_price=state.ohlcv["close"],  # no live tick in the past — see module docstring
            context=context.name, context_confidence=context.confidence,
            decision=decision.action, decision_reason=decision.reason,
            market_state=state.to_dict(),
            source="backfill",
        ))
        added += 1

        if added % 500 == 0:
            elapsed = time.monotonic() - t0
            print(f"  ...{added} candidates so far ({state_ts}), {elapsed:.0f}s elapsed")
            logger._save()  # periodic checkpoint so a crash doesn't lose everything

    print(f"Computed {added} new candidates ({skipped_existing} already present, "
          f"{skipped_gap} skipped for data gaps, {skipped_error} skipped on error)")

    if added:
        print("Measuring exact forward returns from historical 1m data...")
        outcomes = logger.update_outcomes(price_history)
        filled_counts = {}
        for f in outcomes["filled"]:
            filled_counts[f["window"]] = filled_counts.get(f["window"], 0) + 1
        print(f"  outcomes filled: {filled_counts} "
              f"({outcomes['fresh_misses']} fresh misses — see WARN semantics in storage/logger.py)")
        logger._save()

    print(f"Done. {out_path}: {len(logger.candidates)} total candidates.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", help="ISO date, e.g. 2025-01-01 (UTC)")
    p.add_argument("--end", help="ISO date, e.g. 2026-07-26 (UTC). Default: now.")
    p.add_argument("--days", type=int, help="Alternative to --start: backfill the last N days ending at --end/now.")
    p.add_argument("--symbol", default=config.SYMBOL)
    p.add_argument("--out", default=os.path.join(config.DATA_DIR, "historical_candidates.json"))
    p.add_argument("--cache-dir", default=os.path.join(config.DATA_DIR, "backfill_cache"))
    p.add_argument("--no-cache", action="store_true", help="Ignore/overwrite any cached OHLCV, refetch everything.")
    p.add_argument("--dry-run", action="store_true", help="Only fetch/cache OHLCV, skip candidate computation.")
    args = p.parse_args()

    end_dt = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc) if args.end else datetime.now(timezone.utc)
    if args.start:
        start_dt = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    elif args.days:
        start_dt = end_dt - timedelta(days=args.days)
    else:
        p.error("either --start or --days is required")

    if start_dt >= end_dt:
        p.error(f"--start ({start_dt}) must be before --end ({end_dt})")

    asyncio.run(run(start_dt, end_dt, args.symbol, args.out, args.cache_dir,
                     use_cache=not args.no_cache, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
