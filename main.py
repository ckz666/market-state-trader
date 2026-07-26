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
        self._last_1h_close = 0.0
        self.ohlcv_cache: dict = {"1m": [], "15m": [], "1h": [], "4h": []}

    def _log(self, level: str, msg: str):
        entry = {"ts": datetime.now().isoformat(), "level": level, "msg": msg}
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

            def to_df(data):
                df = pd.DataFrame(data, columns=["timestamp","open","high","low","close","volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
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

            # Only evaluate on new 1h candle
            current_close = float(df_1h["close"].iloc[-1])
            new_candle = abs(current_close - self._last_1h_close) > 0.01
            if not new_candle and self.cycle_count > 0:
                self.logger.update_outcomes(self.live_price)
                self.paper.record_equity(self.live_price)
                return
            self._last_1h_close = current_close

            # SL/TP
            trigger = self.paper.check_sl_tp(self.live_price)
            if trigger:
                record = self.paper.close(self.live_price, reason=trigger)
                self._log("TRADE", f"{trigger.upper()} @ ${self.live_price:,.2f} | PnL: ${record['pnl']:+.2f}")

            # Compile state
            state = compile_state(df_1h, df_4h, df_15m=df_15m, df_1m=df_1m)
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

            direction = "long"
            if decision.action.startswith("open_"):
                direction = "long" if "long" in decision.action else "short"
            elif context.direction_bias in ("bullish", "long"):
                direction = "long"
            elif context.direction_bias in ("bearish", "short"):
                direction = "short"

            # Execute
            if decision.action == "open_long" and not has_pos:
                sl = self.live_price * (1 - decision.sl_pct)
                tp = self.live_price * (1 + decision.tp_pct)
                amount = (self.paper.equity * config.MAX_POSITION_PCT * decision.leverage) / self.live_price
                self.paper.open("long", amount, self.live_price, decision.leverage, sl, tp)
                self._log("TRADE", f"OPEN LONG {amount:.6f} @ ${self.live_price:,.2f}")
            elif decision.action == "open_short" and not has_pos:
                sl = self.live_price * (1 + decision.sl_pct)
                tp = self.live_price * (1 - decision.tp_pct)
                amount = (self.paper.equity * config.MAX_POSITION_PCT * decision.leverage) / self.live_price
                self.paper.open("short", amount, self.live_price, decision.leverage, sl, tp)
                self._log("TRADE", f"OPEN SHORT {amount:.6f} @ ${self.live_price:,.2f}")
            elif decision.action.startswith("close_") and has_pos:
                record = self.paper.close(self.live_price, reason="context_" + context.name)
                self._log("TRADE", f"CLOSE @ ${self.live_price:,.2f} | PnL: ${record['pnl']:+.2f}")

            # Log
            self.logger.add(Candidate(
                timestamp=datetime.now(timezone.utc).isoformat(),
                direction=direction, price=self.live_price,
                context=context.name, context_confidence=context.confidence,
                decision=decision.action, decision_reason=decision.reason,
                market_state=state.to_dict(),
            ))
            self.logger.update_outcomes(self.live_price)
            self.paper.record_equity(self.live_price)
            self._log("INFO", f"[{context.name.upper()}] action={decision.action} conf={context.confidence:.2f}")

        except Exception as e:
            self._log("ERROR", f"Cycle: {e}")
            import traceback; traceback.print_exc()

    async def loop(self):
        self.running = True
        self._log("INFO", f"Trader started — {config.SYMBOL} | TFs: 1m,15m,1h,4h | eval on 1h close")
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
