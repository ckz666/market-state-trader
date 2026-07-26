# Market State Trader

A research tool, not a trading strategy. It observes BTC/USDT across four
timeframes, compiles a structured multi-timeframe "market state" once per
closed 1h candle, classifies that state into one of five discrete regimes,
and logs it together with its *exact* forward returns (15m/30m/1h/4h) so
that later analysis can ask: **which state dimensions actually predict
what happens next?**

It also runs a paper-trading loop on top of the same classification (no
real orders, no real capital), mostly to have a second, execution-facing
view of the same signal — but the primary deliverable right now is the
labeled dataset, not the paper P&L.

```
1m / 15m / 1h / 4h OHLCV  (Bitget, via ccxt)
            ↓
     abgeschlossene Candles   (time-gated, never the still-forming one)
            ↓
        MarketState           (observation/compiler.py)
            ↓
   1 Candidate pro 1h-Candle  (storage/logger.py, deduped, restart-safe)
            ↓
  state_price (candle close)  +  execution_price (live price at decision time)
            ↓
15m / 30m / 1h / 4h Forward Returns   (measured at the exact target time
                                        from a rolling 1m price buffer)
            ↓
       Analyse-Datensatz  (data/candidates.json)
```

## Architecture

| Layer | File | Role |
|---|---|---|
| Exchange | `exchange_client.py` | Thin async ccxt wrapper (Bitget USDT-M perpetuals) |
| Observation | `observation/compiler.py`, `observation/models.py` | Compiles the multi-TF `MarketState` — trend/momentum/volatility/price-location/exhaustion (1h), structure (4h), impulse (15m), microstructure (1m). No scores, no trading logic. |
| Indicators | `indicators/*.py` | RSI/MACD/ADX/BB/ATR/squeeze/cycle-strength/vol-regime feature computation used by the compiler |
| Context | `context/classifier.py` | Rule-based classification of a `MarketState` into `continuation` \| `mean_reversion` \| `extended` \| `compressed` \| `transition` |
| Strategy | `strategy/decision.py` | Per-context rule → `TradingDecision` (open/close/hold). Confidence is passed straight through from the context classifier, not independently computed. |
| Paper trading | `paper/engine.py` | Simulated position/PnL/SL-TP tracking, no real orders |
| Storage | `storage/logger.py` | Persists one `Candidate` per closed 1h candle + its forward returns |
| Web | `web/app.py`, `web/templates/index.html` | FastAPI + WebSocket live dashboard: candlestick chart, market-state panel, context/decision, portfolio, event log |
| Orchestration | `main.py` | The async loop tying it all together |

## Timing model

This was the source of most of the correctness bugs found during review —
worth understanding if you touch this code:

```
1h-Candle:    07:00–08:00   (OHLCV index = candle OPEN, i.e. 07:00)
state_ts:     08:00         (candle CLOSE — this is what gets stored)
state_price:  close @ 08:00

Forward-return targets, measured at the EXACT timestamp, not "whatever
price is live when the bot happens to check":
15m → 08:15
30m → 08:30
1h  → 09:00
4h  → 12:00
```

- **Evaluation is gated to once per closed 1h candle**, using a dedup
  marker restored from the most recently persisted candidate on startup —
  a restart mid-hour does not re-log the candle that was already
  processed.
- **`state_price` vs `execution_price`** are deliberately separate fields
  on `Candidate`: `state_price` (the 1h candle's close) is what forward
  returns are measured against, for a clean state → outcome analysis.
  `execution_price` (the live price when the decision was made) is what
  paper trades actually use — it can differ by cents to dollars depending
  on when in the cycle the bot happened to run.
- **Outcomes are measured from a rolling 1m price buffer**
  (`MarketStateTrader.price_history`, ~5h of 1m closes), looked up at the
  *exact* target timestamp within a 2-minute tolerance. If no 1m close is
  close enough (e.g. the bot was offline through that exact minute), the
  outcome stays `None` — pending — rather than being filled with a later,
  wrong price. A `WARN` log line fires once when a target time freshly
  passes with no matching data, not repeatedly for the same permanently-
  stuck gap.
- All timestamps are UTC throughout (`timezone.utc` / pandas `tz='UTC'`),
  including the fallback default in `compile()` for callers that omit
  `state_ts` (the live path always supplies one).

## Storage & disk usage

`data/candidates.json` — one entry per closed 1h candle (~24/day), full
`market_state` + forward returns + timestamps:

- **~2.7 KB per candidate** (indent=2 JSON) → **~64 KB/day**, **~23 MB/year**
  at a steady 1h cadence.
- Capped at `CandidateLogger.MAX_CANDIDATES = 50_000` (~5.7 years of
  hourly candidates, ~129 MB worst case) — both the in-memory list and the
  persisted file share this single cap. *(An earlier version of this file
  wrote only the newest 2000 candidates to disk on every save regardless
  of the in-memory cap — ~83 days of runway before older data silently
  disappeared. Fixed; if you lower `MAX_CANDIDATES` again, make sure
  `_save()` isn't reintroducing a second, smaller cap.)*

`data/state.json` — paper-trading balance/position/trade history, capped
at 200 trades (~200 bytes each) → a few tens of KB, effectively constant
size regardless of runtime.

Equity-curve points (`PaperTrader.equity_history`) are recorded every
cycle but capped at 500 in-memory entries and **not persisted to disk** —
zero disk cost, resets on restart (only used for the live UI, not for
analysis).

`journalctl -u market-state-trader` output is governed by systemd-journald's
own retention policy (`/etc/systemd/journald.conf`), not by this app.

**Bottom line: disk usage is not a practical constraint** — even multiple
years of continuous collection stays under ~150 MB total.

## Running it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

`.env` (not committed, see `.gitignore`):
```
BITGET_API_KEY=...
BITGET_SECRET=...
BITGET_PASSPHRASE=...
```

### As a systemd service (recommended — survives reboots/crashes)

Installed at `/etc/systemd/system/market-state-trader.service`:

```ini
[Unit]
Description=Market State Trader Web UI + Paper Trading Loop
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/projekte/market-state-trader
ExecStart=/root/projekte/market-state-trader/.venv/bin/uvicorn web.app:app --host 0.0.0.0 --port 8081
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
systemctl status market-state-trader     # is it up?
journalctl -u market-state-trader -f     # live logs
systemctl restart market-state-trader    # apply a code change (picks up
                                          # Python edits; templates/index.html
                                          # is read fresh on every request,
                                          # no restart needed for UI-only edits)
```

Starting the web server does **not** start the collection loop by itself —
either click ▶ Start in the UI, or:

```bash
curl -X POST localhost:8081/api/start                 # default 60s cycle
curl -X POST localhost:8081/api/start -d '{"interval":30}' -H 'Content-Type: application/json'
curl -X POST localhost:8081/api/stop
curl localhost:8081/api/status                         # full current state/context/decision/portfolio
curl localhost:8081/api/log?limit=30                    # recent event log
curl localhost:8081/api/candidates?limit=50             # recent candidates + summary stats
curl localhost:8081/api/analysis                        # per-context win-rate/expectancy (analysis/report.py)
```

## Backfill: months of history in minutes

`scripts/backfill.py` reconstructs historical candidates instead of waiting
for the live collector hour by hour — it reuses the exact same
`compile_state()` / `classify()` / `decide()` code path, iterating past 1h
candle-close timestamps instead of real time, with the same bounded
trailing window (`WINDOW = {1m:120, 15m:96, 1h:200, 4h:50}`) a live cycle
would have seen. Forward returns are measured immediately against the
already-known historical 1m price series.

```bash
.venv/bin/python scripts/backfill.py --start 2025-01-01 --end 2026-07-26
.venv/bin/python scripts/backfill.py --days 180                   # last 180 days, ending now
.venv/bin/python scripts/backfill.py --start 2025-01-01 --dry-run  # fetch/cache only, no compute
```

**This is a backfill, not a backtest** — no position sequencing, no PnL,
`execution_price == state_price` for every backfilled candidate (there's
no live tick to record in the past). `decision`/`direction` are computed
for schema completeness only, always assuming no open position. It answers
"what did the state look like, and what happened next?", not "would a
strategy have made money?".

Writes to its own file, **`data/historical_candidates.json`**, never to
the live collector's `data/candidates.json` — safe to run while the live
systemd service keeps writing that file concurrently. Combine both files
for analysis; dedupe by `timestamp` first if their date ranges overlap.
Per-timeframe OHLCV is cached to CSV under `data/backfill_cache/` so
re-running with a wider range doesn't re-fetch already-covered history.
1m history depth on Bitget goes back at least to January 2025 (tested);
the true earliest boundary for this symbol wasn't determined further back.

## Web UI

Dark dashboard at `http://<host>:8081`: live BTC/USDT candlestick chart
(hover for an OHLC crosshair readout, switchable 1m/15m/1h/4h), the full
`MarketState` breakdown, current context classification with rationale,
trading decision, paper portfolio/position, trade history, and a live
event log. Every card header carries a hover tooltip ("?") explaining
what the numbers mean and where they come from — most useful on the
Market State panel (BB %B anchoring, ADX trending threshold, etc.).

## Status: data-collection phase

The classifier, decision rules, and BB thresholds are frozen as-is on
purpose. The point right now is accumulating a clean, correctly-labeled
dataset — not tuning trading rules against it. The next real step is
**analysis**: which combinations of state dimensions (trend × momentum ×
volatility regime × BB position × 4h structure × exhaustion) actually
separate winners from losers in the forward-return data, before any new
strategy logic gets written.

`indicators/ml_signal.py`'s `get_indicators()`/`build_features()` are live
(used by the compiler); an unused ML ensemble train/predict pipeline that
used to live in the same file was removed as dead code — nothing in this
repo currently trains or serves a model.
