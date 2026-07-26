"""Async wrapper for Bitget Futures API using ccxt."""
import ccxt.async_support as ccxt
import asyncio
import time
import aiohttp
from typing import Optional
import mst_config as config

_TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000,
         "4h": 14_400_000, "1d": 86_400_000}


def _tf_ms(timeframe: str) -> int:
    return _TF_MS.get(timeframe, 3_600_000)


def to_futures_symbol(symbol: str) -> str:
    """Convert 'BTC/USDT' -> 'BTC/USDT:USDT' for Bitget USDT-M perpetuals."""
    if symbol.endswith("/USDT") and ":USDT" not in symbol:
        return symbol + ":USDT"
    return symbol


class FuturesClient:
    def __init__(self):
        self._exchange = ccxt.bitget({
            "apiKey": config.BITGET_API_KEY,
            "secret": config.BITGET_SECRET,
            "password": config.BITGET_PASSPHRASE,
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
        })

    async def fetch_ticker(self, symbol: str) -> dict:
        return await self._exchange.fetch_ticker(to_futures_symbol(symbol))

    async def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 200) -> list:
        sym = to_futures_symbol(symbol)
        if limit <= 1000:
            return await self._exchange.fetch_ohlcv(sym, timeframe, limit=limit)
        all_candles: list = []
        since = None
        remaining = limit
        while remaining > 0:
            batch_size = min(remaining, 1000)
            batch = await self._exchange.fetch_ohlcv(sym, timeframe, limit=batch_size, since=since)
            if not batch:
                break
            all_candles = batch + all_candles
            remaining -= len(batch)
            if len(batch) < batch_size:
                break
            since = batch[0][0] - _tf_ms(timeframe) * batch_size
        return all_candles[-limit:]

    async def fetch_ohlcv_range(self, symbol: str, timeframe: str, since_ms: int, until_ms: int,
                                 limit: int = 1000, progress_cb=None) -> list:
        """Fetch ALL candles in [since_ms, until_ms) via forward since-pagination.
        Unlike fetch_ohlcv() (which walks backward from "now" for the last N
        candles — what the live loop uses), this walks forward from an explicit
        historical start, the standard ccxt pattern for backfilling a range.
        Additive: does not change fetch_ohlcv()'s behavior."""
        sym = to_futures_symbol(symbol)
        tf_ms = _tf_ms(timeframe)
        all_candles: list = []
        cursor = since_ms
        batches = 0
        while cursor < until_ms:
            batch = await self._exchange.fetch_ohlcv(sym, timeframe, since=cursor, limit=limit)
            if not batch:
                break
            all_candles.extend(batch)
            batches += 1
            if progress_cb:
                progress_cb(batches, all_candles[-1][0])
            last_ts = batch[-1][0]
            if last_ts < cursor:
                break  # safety: exchange returned non-advancing data
            cursor = last_ts + tf_ms
            if len(batch) < limit:
                break  # fewer than requested → reached the end of available history
        return [c for c in all_candles if since_ms <= c[0] < until_ms]

    async def fetch_order_book(self, symbol: str, limit: int = 20) -> dict:
        return await self._exchange.fetch_order_book(to_futures_symbol(symbol), limit)

    async def fetch_funding_rate(self, symbol: str) -> dict | None:
        try:
            fr = await self._exchange.fetch_funding_rate(to_futures_symbol(symbol))
            rate = fr.get("fundingRate")
            if rate is None:
                return None
            return {"rate": rate, "next_ts": fr.get("nextFundingDatetime", "")}
        except Exception:
            return None

    async def fetch_funding_rate_history(self, symbol: str, limit: int = 100) -> list:
        try:
            return await self._exchange.fetch_funding_rate_history(to_futures_symbol(symbol), limit=limit)
        except Exception:
            return []

    async def estimate_execution(self, symbol: str, side: str, notional: float) -> dict:
        """Walk the orderbook to estimate fill price, slippage, and fill %.
        'buy' walks the ask side, 'sell' walks the bid side."""
        try:
            ob = await self.fetch_order_book(symbol, limit=20)
            levels = ob.get("asks" if side == "buy" else "bids", [])
            if not levels:
                return {}
            remaining = notional
            fill_cost = 0.0
            filled_qty = 0.0
            for price, size in levels:
                level_notional = price * size
                if remaining <= level_notional:
                    fill_cost += price * remaining
                    filled_qty += remaining / price
                    remaining = 0
                    break
                fill_cost += price * size
                filled_qty += size
                remaining -= level_notional
            avg_price = fill_cost / filled_qty if filled_qty > 0 else 0.0
            slippage = abs(avg_price - levels[0][0]) / levels[0][0] if levels else 0.0
            return {
                "avg_price": round(avg_price, 8),
                "slippage": round(slippage, 6),
                "fill_pct": round(1.0 - remaining / notional, 4) if notional > 0 else 1.0,
            }
        except Exception:
            return {}

    async def fetch_maintenance_margin_rate(self, symbol: str, notional: float = 0.0) -> float:
        try:
            tiers = await self._exchange.fetch_market_leverage_tiers(to_futures_symbol(symbol))
            rate = 0.005
            for t in tiers:
                min_n, max_n = t.get("minNotional", 0.0), t.get("maxNotional")
                if notional >= min_n and (max_n is None or notional < max_n):
                    rate = t.get("maintenanceMarginRate", 0.005)
                    break
            return rate
        except Exception:
            return 0.005

    async def set_leverage(self, symbol: str, leverage: int):
        await self._exchange.set_leverage(leverage, to_futures_symbol(symbol))

    async def open_long(self, symbol: str, amount: float, leverage: int) -> dict:
        await self.set_leverage(symbol, leverage)
        return await self._exchange.create_order(
            to_futures_symbol(symbol), "market", "buy", amount,
            params={"tdMode": "cross"})

    async def open_short(self, symbol: str, amount: float, leverage: int) -> dict:
        await self.set_leverage(symbol, leverage)
        return await self._exchange.create_order(
            to_futures_symbol(symbol), "market", "sell", amount,
            params={"tdMode": "cross"})

    async def close_position(self, symbol: str, side: str, amount: float) -> dict:
        close_side = "sell" if side == "long" else "buy"
        return await self._exchange.create_order(
            to_futures_symbol(symbol), "market", close_side, amount,
            params={"reduceOnly": True})

    async def fetch_positions(self) -> list:
        return await self._exchange.fetch_positions()

    async def close(self):
        await self._exchange.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

# Wrapper for the new MarketStateTrader
class ExchangeClient:
    def __init__(self):
        self._client = FuturesClient()
    async def __aenter__(self):
        await self._client.__aenter__()
        return self
    async def __aexit__(self, *args):
        await self._client.__aexit__(*args)
    async def fetch_ohlcv(self, symbol, timeframe, limit=300):
        return await self._client.fetch_ohlcv(symbol, timeframe, limit)
    async def fetch_ohlcv_range(self, symbol, timeframe, since_ms, until_ms, limit=1000, progress_cb=None):
        return await self._client.fetch_ohlcv_range(symbol, timeframe, since_ms, until_ms, limit, progress_cb)
    async def fetch_ticker(self, symbol):
        return await self._client.fetch_ticker(symbol)
    async def fetch_funding_rate(self, symbol):
        return await self._client.fetch_funding_rate(symbol)
