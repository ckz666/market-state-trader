"""
Forschungs-Loop — sammelt prospektive Daten, handelt nicht.

Ersetzt den früheren `main.py`, der beides in einem tat: Paper-Trading mit der
5-Regime-Engine **und** Datensammlung. Die Handelsseite ist am 2026-07-28 nach
`regime-trader` ausgezogen (github.com/ckz666/regime-trader). Was hier bleibt,
ist ausschliesslich Erhebung:

1. **`data/candidates.json`** — je geschlossener 1h-Kerze ein Kandidat mit
   MarketState, Kontext, Entscheidung und den Forward-Returns (15m/30m/1h/4h).
2. **`data/shadow_signals.json`** — der Shadow Recorder, der die eingefrorenen
   Forschungsregeln mitlaufen lässt und bei jedem Signal das Orderbuch
   festhält. Reine Beobachtung, nie ein Trade.

## Der Grund, warum der Paper-Trader raus musste — und er ist inhaltlich

`decide()` nimmt `has_open_position`. `scripts/backfill.py` übergibt dort
**immer** `False` — alle 57.565 historischen Kandidaten sind also
positionsfrei erzeugt. Der alte Live-Loop reichte dagegen den echten Zustand
des Paper-Traders durch.

Gemessen am 2026-07-28, bevor das behoben wurde:

| `decision` | historisch (57.565) | live (48) |
|---|---|---|
| `hold` | 36.096 | 44 |
| `open_short` / `open_long` | 11.625 / 9.844 | 3 / 0 |
| `close_short` | **0** | **1** |

`close_*` **kann im Forschungsdatensatz nicht vorkommen** — die live
gesammelten Zeilen waren auf diesem Feld also nicht mit den historischen
vergleichbar. Dieser Loop ruft `decide()` mit `has_open_position=False`, genau
wie der Backfill. Damit sind live und historisch wieder dieselbe Messung.

## Betrieb

Läuft als `mst-research.service`. Kein Web-Interface — der Stand steht in den
beiden JSON-Dateien:

    systemctl status mst-research
    python3 -c "import json;d=json.load(open('data/shadow_signals.json'));print(len(d))"
"""

import asyncio
import pandas as pd
from datetime import datetime, timezone

from exchange_client import ExchangeClient
from observation.compiler import compile as compile_state
from context import classify
from strategy import decide
from storage import CandidateLogger, Candidate
from shadow import ShadowRecorder
import mst_config as config


class ResearchCollector:
    def __init__(self):
        self.logger = CandidateLogger()
        # Observation-only: runs the RESEARCH rules (decision_rule_v1 + the
        # 24h candidate) and captures the order book at each signal. Never
        # trades. See shadow/recorder.py for why.
        self.shadow = ShadowRecorder()
        self.running = False
        self.cycle_count = 0
        self.live_price = 0.0
        self.last_state = None
        self.last_context = None
        self.last_decision = None
        self.log: list[dict] = []
        # Dedup marker (candle CLOSE / state timestamp) für „einmal je
        # geschlossener 1h-Kerze". Aus dem letzten persistierten Kandidaten
        # wiederhergestellt, damit ein Neustart innerhalb derselben Stunde
        # keinen Doppeleintrag erzeugt.
        self._last_state_ts = self._restore_last_state_ts()
        self.price_history: dict[int, float] = {}  # 1m close ts_ms -> price
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
        print(f"[{entry['ts'][11:19]}] [{level}] {msg}", flush=True)

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

            # Frische 1m-Schlusskurse in den Puffer, aus dem die Outcomes zur
            # exakten Zielzeit gelesen werden; alles älter als der längste
            # Horizont (4h) fällt raus.
            for r in raw_1m:
                self.price_history[int(r[0])] = float(r[4])
            cutoff_ms = int(now.timestamp() * 1000) - 5 * 3600 * 1000
            if len(self.price_history) > 400:
                self.price_history = {t: p for t, p in self.price_history.items() if t >= cutoff_ms}

            def to_df(data):
                df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                df.set_index("timestamp", inplace=True)
                return df

            df_1m, df_15m = to_df(raw_1m), to_df(raw_15m)
            df_1h, df_4h = to_df(raw_1h), to_df(raw_4h)

            # Outcomes fortschreiben — der eigentliche Zweck dieses Loops.
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

            self.shadow.on_price(self.live_price)

            if self.cycle_count <= 3 or self.cycle_count % 10 == 0:
                delta_info = ""
                if self._last_heartbeat_price:
                    dpct = (self.live_price - self._last_heartbeat_price) / self._last_heartbeat_price * 100
                    delta_info = f" ({dpct:+.2f}%)"
                self._last_heartbeat_price = self.live_price
                self._log("INFO", f"Cycle {self.cycle_count} | ${self.live_price:,.2f}{delta_info}")

            # Nur auf NEU geschlossener 1h-Kerze auswerten
            closed_1h = df_1h[df_1h.index + pd.Timedelta(hours=1) <= now]
            if len(closed_1h) < 2:
                return
            state_ts = closed_1h.index[-1] + pd.Timedelta(hours=1)  # Kerzen-SCHLUSS
            if state_ts == self._last_state_ts:
                return
            self._last_state_ts = state_ts

            closed_4h = df_4h[df_4h.index + pd.Timedelta(hours=4) <= now]
            closed_15m = df_15m[df_15m.index + pd.Timedelta(minutes=15) <= now]
            closed_1m = df_1m[df_1m.index + pd.Timedelta(minutes=1) <= now]

            state = compile_state(closed_1h, closed_4h, df_15m=closed_15m,
                                  df_1m=closed_1m, state_ts=state_ts)
            self.last_state = state

            context = classify(state)
            self.last_context = context

            # **`has_open_position=False` ist hier keine Vereinfachung, sondern
            # die Bedingung für Vergleichbarkeit** — `scripts/backfill.py`
            # übergibt denselben Wert, und nur so bedeutet das Feld `decision`
            # in den live gesammelten Zeilen dasselbe wie in den 57.565
            # historischen. Siehe Modulkopf.
            atr_pct = state.state_1h.volatility.atr_norm
            decision = decide(context, atr_pct, has_open_position=False, position_side=None)
            self.last_decision = decision

            # Richtung: nie auf „long" zurückfallen — „none" bei hold/wait/neutral
            direction = "none"
            if decision.action.startswith("open_"):
                direction = "long" if "long" in decision.action else "short"
            elif context.direction_bias in ("long", "bullish") and decision.action != "hold":
                direction = "long"
            elif context.direction_bias in ("short", "bearish") and decision.action != "hold":
                direction = "short"

            self.logger.add(Candidate(
                timestamp=state.timestamp.isoformat(),
                direction=direction,
                state_price=state.ohlcv["close"],
                execution_price=self.live_price,
                context=context.name, context_confidence=context.confidence,
                decision=decision.action, decision_reason=decision.reason,
                market_state=state.to_dict(),
            ))
            self._log("INFO", f"1h candle closed @ ${state.ohlcv['close']:,.2f} "
                              f"→ [{context.name.upper()}] {decision.action} "
                              f"conf={context.confidence:.2f}")

            # ── Shadow: was würden die FORSCHUNGS-Kandidaten tun? ──
            # Das Orderbuch wird nur geholt, wenn ein Signal wirklich feuert —
            # ein Zusatzaufruf auf ~2 % der Kerzen.
            try:
                cls = self.shadow.classify(state)
                book = None
                if cls and cls["decision"] == "long_candidate":
                    book = await client.fetch_order_book(config.SYMBOL, limit=200)
                res = self.shadow.on_new_state(state, self.live_price, book)
                if res and res["decision"] != "no_signal":
                    extra = ""
                    if res.get("opened"):
                        extra = " → shadow 24h position OPENED"
                    elif res.get("skipped_option_a"):
                        extra = " → skipped (Option A: shadow position already open)"
                    self._log("SHADOW", f"{res['decision']} "
                                        f"(LPL={res['lpl_q']} {res['lpl']:+.3f}, "
                                        f"Vol={res['vol_q']} {res['vol']:.5f}){extra}")
            except Exception as e:
                self._log("WARN", f"Shadow recorder: {e}")

        except Exception as e:
            self._log("ERROR", f"Cycle: {e}")
            import traceback
            traceback.print_exc()

    async def loop(self):
        self.running = True
        resume = (f" | resuming after state {self._last_state_ts.isoformat()}"
                  if self._last_state_ts is not None else "")
        self._log("INFO", f"Research collector started — {config.SYMBOL} | eval on 1h close"
                          f" | {len(self.logger.candidates)} candidates loaded{resume}")
        try:
            async with ExchangeClient() as client:
                while self.running:
                    self.cycle_count += 1
                    await self.run_cycle(client)
                    await asyncio.sleep(config.CYCLE_INTERVAL)
        except Exception as e:
            self._log("ERROR", f"Loop: {e}")
            self.running = False

    def status(self) -> dict:
        return {
            "running": self.running,
            "cycle": self.cycle_count,
            "symbol": config.SYMBOL,
            "price": self.live_price,
            "candidates": self.logger.summary(),
            "context": self.last_context.to_dict() if self.last_context else None,
            "decision": self.last_decision.to_dict() if self.last_decision else None,
            "shadow": self.shadow.status(),
        }


if __name__ == "__main__":
    import json

    collector = ResearchCollector()
    try:
        asyncio.run(collector.loop())
    except KeyboardInterrupt:
        print("\n" + json.dumps(collector.status()["shadow"], indent=2))
