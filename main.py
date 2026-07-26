"""
Market State Trader — main loop. Multi-timeframe parallel collection.

Fetches 1m, 15m, 1h, 4h OHLCV simultaneously.
Compiles MarketState from 1h context with 4h structure.
Evaluates only on new 1h candle close (no duplicates).
Tracks outcomes at 15m/30m/1h/4h using live price updates.
"""

import asyncio
import pandas as pd
from datetime import datetime, timezone

from exchange_client import ExchangeClient
from observation.compiler import compile as compile_state
from context import classify
from strategy import decide
from paper import PaperTrader
from storage import CandidateLogger, Candidate
import mst_config as config


class MarketStateTrader:
    def __init__(self):
        self.paper = PaperTrader()
        self.logger = CandidateLogger()
        self.running = False
        self.cycle_count = 0
        self.live_price = 0.0
        self.last_state = None
        self.last_context = None
        self.last_decision = None
        self.log: list[dict] = []
        # Dedup marker (candle CLOSE / state timestamp) for "evaluate once per
        # closed 1h candle". Restored from the most recent persisted candidate
        # so a restart within the same hour doesn't re-log a duplicate for a
        # candle that was already processed before shutdown.
        self._last_state_ts = self._restore_last_state_ts()
        self.ohlcv_cache: dict = {"1m": [], "15m": [], "1h": [], "4h": []}
        self.price_history: dict[int, float] = {}  # 1m close ts_ms -> price, for exact outcome lookups
        self._last_heartbeat_price = None

    def _restore_last_state_ts(self):
        if not self.logger.candidates:
            return None
        try:
            ts = pd.Timestamp(self.logger.candidates[-1].timestamp)
            return ts.tz_localize('UTC') if ts.tzinfo is None else ts
        except (ValueError, TypeError):
            return None

    def _log(self, level: str, msg: str):
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "level": level, "msg": msg}
        self.log.append(entry)
        self.log = self.log[-200:]
        print(f"[{entry['ts'][11:19]}] [{level}] {msg}")

    async def run_cycle(self, client: ExchangeClient):
        try:
            results = await asyncio.gather(
                client.fetch_ohlcv(config.SYMBOL, "1m", 120),
                client.fetch_ohlcv(config.SYMBOL, "15m", 96),
                client.fetch_ohlcv(config.SYMBOL, "1h", 200),
                client.fetch_ohlcv(config.SYMBOL, "4h", 50),
                client.fetch_ticker(config.SYMBOL),
            )
            raw_1m, raw_15m, raw_1h, raw_4h, ticker = results
            self.live_price = ticker["last"]
            now = pd.Timestamp.now('UTC')

            # Merge fresh 1m closes into the price-history buffer used for
            # exact-target-time outcome measurement, then drop anything
            # older than the longest outcome horizon (4h) needs.
            for r in raw_1m:
                self.price_history[int(r[0])] = float(r[4])
            cutoff_ms = int(now.timestamp() * 1000) - 5 * 3600 * 1000
            if len(self.price_history) > 400:
                self.price_history = {t: p for t, p in self.price_history.items() if t >= cutoff_ms}

            def to_df(data):
                df = pd.DataFrame(data, columns=["timestamp","open","high","low","close","volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                df.set_index("timestamp", inplace=True)
                return df

            df_1m = to_df(raw_1m)
            df_15m = to_df(raw_15m)
            df_1h = to_df(raw_1h)
            df_4h = to_df(raw_4h)

            self.ohlcv_cache = {
                "1m": [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in raw_1m[-60:]],
                "15m": [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in raw_15m[-48:]],
                "1h": [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in raw_1h[-48:]],
                "4h": [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in raw_4h[-24:]],
            }

            # ── ALWAYS check SL/TP (every cycle, not just on new candle) ──
            trigger = self.paper.check_sl_tp(self.live_price)
            if trigger:
                record = self.paper.close(self.live_price, reason=trigger)
                self._log("TRADE", f"{trigger.upper()} @ ${self.live_price:,.2f} | PnL: ${record['pnl']:+.2f}")

            # ALWAYS update outcomes and equity
            outcomes = self.logger.update_outcomes(self.price_history)
            if outcomes["filled"]:
                parts = ", ".join(
                    f"{f['window']}={f['return']*100:+.2f}% (state {f['state_ts'][11:16]})"
                    for f in outcomes["filled"]
                )
                self._log("INFO", f"Outcome(s) measured: {parts}")
            if outcomes["fresh_misses"]:
                self._log("WARN", f"{outcomes['fresh_misses']} outcome(s) missed their exact target "
                                   f"time — no 1m price within {self.logger.OUTCOME_TOLERANCE_SEC}s tolerance")
            self.paper.record_equity(self.live_price)

            # Heartbeat: log every few cycles so the UI does not look dead
            if self.cycle_count <= 3 or self.cycle_count % 5 == 0:
                pos_info = ""
                if self.paper.has_position:
                    upnl = self.paper.position.unrealized_pnl(self.live_price)
                    pos_info = f" | pos_upnl=${upnl:+.2f}"
                delta_info = ""
                if self._last_heartbeat_price:
                    dpct = (self.live_price - self._last_heartbeat_price) / self._last_heartbeat_price * 100
                    delta_info = f" ({dpct:+.2f}%)"
                self._last_heartbeat_price = self.live_price
                self._log("INFO", f"Cycle {self.cycle_count} | ${self.live_price:,.2f}{delta_info}{pos_info}")

            # Only evaluate MarketState on NEW completed 1h candle
            closed_1h = df_1h[df_1h.index + pd.Timedelta(hours=1) <= now]
            if len(closed_1h) < 2:
                return
            last_closed_open = closed_1h.index[-1]   # OHLCV index = candle OPEN time
            state_ts = last_closed_open + pd.Timedelta(hours=1)  # the candle's CLOSE time
            if state_ts == self._last_state_ts:
                return
            self._last_state_ts = state_ts

            # ── Use only completed candles (time-gated, not iloc[:-1]) ──
            closed_4h = df_4h[df_4h.index + pd.Timedelta(hours=4) <= now]
            closed_15m = df_15m[df_15m.index + pd.Timedelta(minutes=15) <= now]
            closed_1m = df_1m[df_1m.index + pd.Timedelta(minutes=1) <= now]

            # State timestamp = the candle close time (not datetime.now())
            state = compile_state(closed_1h, closed_4h,
                                  df_15m=closed_15m, df_1m=closed_1m,
                                  state_ts=state_ts)
            self.last_state = state

            # Context
            context = classify(state)
            self.last_context = context

            # Decision
            atr_pct = state.state_1h.volatility.atr_norm
            has_pos = self.paper.has_position
            pos_side = self.paper.position.side if self.paper.position else None
            decision = decide(context, atr_pct, has_open_position=has_pos, position_side=pos_side)
            self.last_decision = decision

            # Direction: never default to "long" — "none" for hold/wait/neutral
            direction = "none"
            if decision.action.startswith("open_"):
                direction = "long" if "long" in decision.action else "short"
            elif context.direction_bias in ("long", "bullish") and decision.action != "hold":
                direction = "long"
            elif context.direction_bias in ("short", "bearish") and decision.action != "hold":
                direction = "short"

            # Execute
            if decision.action == "open_long" and not has_pos:
                sl = self.live_price * (1 - decision.sl_pct)
                tp = self.live_price * (1 + decision.tp_pct)
                amount = (self.paper.cash_balance * config.MAX_POSITION_PCT * decision.leverage) / self.live_price
                self.paper.open("long", amount, self.live_price, decision.leverage, sl, tp)
                self._log("TRADE", f"OPEN LONG {amount:.6f} @ ${self.live_price:,.2f}")
            elif decision.action == "open_short" and not has_pos:
                sl = self.live_price * (1 + decision.sl_pct)
                tp = self.live_price * (1 - decision.tp_pct)
                amount = (self.paper.cash_balance * config.MAX_POSITION_PCT * decision.leverage) / self.live_price
                self.paper.open("short", amount, self.live_price, decision.leverage, sl, tp)
                self._log("TRADE", f"OPEN SHORT {amount:.6f} @ ${self.live_price:,.2f}")
            elif decision.action.startswith("close_") and has_pos:
                record = self.paper.close(self.live_price, reason="context_" + context.name)
                self._log("TRADE", f"CLOSE @ ${self.live_price:,.2f} | PnL: ${record['pnl']:+.2f}")

            # Log
            self.logger.add(Candidate(
                timestamp=state.timestamp.isoformat(),
                direction=direction,
                state_price=state.ohlcv["close"],      # 1h candle close → for state/forward-return analysis
                execution_price=self.live_price,       # live price at decision time → for trading/execution analysis
                context=context.name, context_confidence=context.confidence,
                decision=decision.action, decision_reason=decision.reason,
                market_state=state.to_dict(),
            ))
            self._log("INFO", f"1h candle closed @ ${state.ohlcv['close']:,.2f} (exec ${self.live_price:,.2f}) "
                               f"→ [{context.name.upper()}] {decision.action} conf={context.confidence:.2f}")

        except Exception as e:
            self._log("ERROR", f"Cycle: {e}")
            import traceback; traceback.print_exc()

    async def loop(self):
        self.running = True
        resume_info = f" | resuming after state {self._last_state_ts.isoformat()}" if self._last_state_ts is not None else ""
        self._log("INFO", f"Trader started — {config.SYMBOL} | TFs: 1m,15m,1h,4h | eval on 1h close"
                           f" | {len(self.logger.candidates)} candidates loaded{resume_info}")
        try:
            async with ExchangeClient() as client:
                while self.running:
                    self.cycle_count += 1
                    await self.run_cycle(client)
                    await asyncio.sleep(config.CYCLE_INTERVAL)
        except Exception as e:
            self._log("ERROR", f"Loop: {e}")
            self.running = False

    async def stop(self):
        self.running = False
        if self.paper.has_position:
            self.paper.close(self.live_price, reason="manual_stop")
        self._log("INFO", "Trader stopped")

    def status(self) -> dict:
        return {
            "running": self.running,
            "cycle": self.cycle_count,
            "symbol": config.SYMBOL,
            "price": self.live_price,
            "paper": self.paper.status(self.live_price),
            "state": self.last_state.to_dict() if self.last_state else None,
            "context": self.last_context.to_dict() if self.last_context else None,
            "decision": self.last_decision.to_dict() if self.last_decision else None,
            "candidates": self.logger.summary(),
            "trade_history": self.paper.trade_history[-20:],
            "ohlcv": self.ohlcv_cache,
        }
