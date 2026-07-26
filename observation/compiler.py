"""
MarketState compiler — multi-timeframe (1m/15m/1h/4h).

Compiles one enriched MarketState with timeframes in their specific roles:
  4h → context (structure, regime)
  1h → primary state (trend, momentum, location, volatility, exhaustion)
  15m → short-term impulse (direction, momentum confirmation, rejection)
  1m → microstructure (candle geometry, immediate reversal)
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

from observation.models import (
    MarketState, HourlyState, Context4h, ShortTermState, MicroState,
    TrendState, MomentumState, VolatilityState, PriceLocationState, ExhaustionState,
)


def compile(df_1h: pd.DataFrame, df_4h: pd.DataFrame,
            df_15m: Optional[pd.DataFrame] = None,
            df_1m: Optional[pd.DataFrame] = None) -> MarketState:
    """Compile full multi-TF MarketState."""

    from indicators.ml_signal import get_indicators, detect_market_structure

    # ── 4H Context (real pivot data, not derived from label) ──
    ms_4h = detect_market_structure(df_4h) if len(df_4h) > 12 else {}
    ind_4h = get_indicators(df_4h) if len(df_4h) > 30 else {}
    ph = ms_4h.get("pivot_highs", [])
    pl = ms_4h.get("pivot_lows", [])
    # Derive HH/HL/LH/LL from actual pivot deltas (not from trend label)
    hh = hl = lh = ll = False
    if len(ph) >= 2:
        hh = ph[-1] > ph[-2]
        lh = ph[-1] < ph[-2]
    if len(pl) >= 2:
        hl = pl[-1] > pl[-2]
        ll = pl[-1] < pl[-2]
    context_4h = Context4h(
        structure_trend=ms_4h.get("trend", "unknown"),
        hh=hh, hl=hl, lh=lh, ll=ll,
        regime="trending" if ind_4h.get("adx", 0) >= 25 else ("ranging" if ind_4h.get("adx", 0) < 20 else "transitioning"),
    )

    # ── 1H Primary State ──
    indicators = get_indicators(df_1h)
    c = float(df_1h["close"].iloc[-1])

    ema = indicators.get("ema_cross_norm", 0)
    adx = indicators.get("adx", 0)
    trend_dir = "bullish" if ema > 0.0005 else ("bearish" if ema < -0.0005 else "neutral")
    trend_str = min(max(adx / 50.0, 0), 1.0) * 0.6 + min(abs(ema) / 0.005, 1.0) * 0.4
    trend = TrendState(direction=trend_dir, strength=round(trend_str, 4),
                       adx=round(adx, 1), ema_cross_norm=round(ema, 6))

    rsi = indicators.get("rsi", 50)
    macd = indicators.get("macd_diff", 0)
    sq_fired = bool(indicators.get("squeeze_fired", 0))
    macd_bull, rsi_bull = macd > 0, rsi > 50
    mom_dir = "bullish" if (macd_bull and rsi_bull) else ("bearish" if (not macd_bull and not rsi_bull) else "neutral")
    mom_str = min(abs(rsi - 50) / 50, 1) * 0.4 + min(abs(macd) / 0.0005, 1) * 0.6
    sq_mom = indicators.get("squeeze_momentum", 0)
    accel = min(abs(sq_mom) * 3, 1) if ((macd_bull and sq_mom > 0) or (not macd_bull and sq_mom < 0)) else -min(abs(sq_mom) * 3, 1)
    momentum = MomentumState(direction=mom_dir, strength=round(mom_str, 4),
                             acceleration=round(accel, 4), rsi=round(rsi, 2),
                             macd_norm=round(macd, 6), squeeze_fired=sq_fired)

    from indicators.vol_regime import classify_vol_regime
    vol = classify_vol_regime(df_1h)
    volatility = VolatilityState(regime=vol["regime"], prob_storm=vol["prob_storm"],
                                 atr_norm=round(indicators.get("atr_norm", 0), 6))

    def _rng(w):
        if len(df_1h) < w: return 0.5
        hi = float(df_1h["high"].iloc[-w:].max())
        lo = float(df_1h["low"].iloc[-w:].min())
        return round((c - lo) / (hi - lo), 4) if hi > lo else 0.5
    r20 = _rng(20)
    price_location = PriceLocationState(
        range_position_20=r20, range_position_50=_rng(50),
        bb_position=round(indicators.get("bb_pct", 0.5), 4),
        vwap_distance=round(indicators.get("vwap_dist", 0), 6),
    )

    divergence = 0.0
    if trend_dir == "bullish" and mom_dir == "bearish": divergence = 0.7
    elif trend_dir == "bearish" and mom_dir == "bullish": divergence = 0.7
    elif trend_dir != mom_dir and mom_dir == "neutral": divergence = 0.35
    exhaustion = ExhaustionState(
        cycle_strength=round(indicators.get("cycle_strength", 0), 4),
        
        upper_rejection=round(_wick(df_1h, "up"), 4) if r20 > 0.75 else 0.0,
        lower_rejection=round(_wick(df_1h, "dn"), 4) if r20 < 0.25 else 0.0,
        trend_momentum_divergence=divergence,
    )

    state_1h = HourlyState(trend=trend, momentum=momentum, volatility=volatility,
                           price_location=price_location, exhaustion=exhaustion)

    # ── 15M Short-term ──
    short_term = ShortTermState()
    if df_15m is not None and len(df_15m) >= 20:
        sti = get_indicators(df_15m)
        st_rsi = sti.get("rsi", 50); st_macd = sti.get("macd_diff", 0)
        st_dir = "bullish" if (st_macd > 0 and st_rsi > 50) else ("bearish" if (st_macd < 0 and st_rsi < 50) else "neutral")
        st_r20 = _rng_15m(df_15m, 20)
        short_term = ShortTermState(
            direction=st_dir, rsi=round(st_rsi, 2), macd_norm=round(st_macd, 6),
            momentum_aligned=bool(st_dir == mom_dir or st_dir == "neutral" or mom_dir == "neutral"),
            candle_direction=_candle_dir(df_15m),
            upper_rejection=round(_wick(df_15m, "up"), 4) if st_r20 > 0.75 else 0.0,
            lower_rejection=round(_wick(df_15m, "dn"), 4) if st_r20 < 0.25 else 0.0,
            range_position_20=round(st_r20, 4),
        )

    # ── 1M Microstructure ──
    micro = MicroState()
    if df_1m is not None and len(df_1m) >= 10:
        m_ret = df_1m["close"].pct_change().dropna()
        m_vol = float(m_ret.tail(5).std()) if len(m_ret) >= 5 else 0.0
        m_ret5 = float(df_1m["close"].iloc[-1] / df_1m["close"].iloc[-6] - 1) if len(df_1m) >= 6 else 0.0
        cd, br, uw, dw, cl = _candle_metrics(df_1m)
        reversal = False
        if len(df_1m) >= 3:
            c0, c1 = df_1m.iloc[-1], df_1m.iloc[-2]
            rev = (c0["close"] > c0["open"] and c1["close"] < c1["open"]) or \
                  (c0["close"] < c0["open"] and c1["close"] > c1["open"])
            if rev:
                tr_c0, tr_c1 = c0["high"] - c0["low"], c1["high"] - c1["low"]
                mx = max(tr_c0, tr_c1)
                if mx > 0: reversal = abs(c0["close"] - c1["close"]) / mx > 0.5
        avg_rng = float((df_1m["high"] - df_1m["low"]).tail(10).mean()) if len(df_1m) >= 10 else 1.0
        cur_rng = float(df_1m["high"].iloc[-1] - df_1m["low"].iloc[-1])
        micro = MicroState(
            candle_direction=cd, body_ratio=br, upper_wick_ratio=uw,
            lower_wick_ratio=dw, close_location=cl,
            range_vs_avg=round(cur_rng / max(avg_rng, 1e-10), 4),
            volatility_1m=round(m_vol, 6), return_5m=round(m_ret5, 6),
            immediate_reversal=bool(reversal),
        )

    # ── Alignment ──
    context_4h.trend_aligned = bool(
        (trend_dir == "bullish" and context_4h.structure_trend == "uptrend") or
        (trend_dir == "bearish" and context_4h.structure_trend == "downtrend")
    )

    return MarketState(
        timestamp=datetime.now(),
        context_4h=context_4h, state_1h=state_1h,
        short_term_15m=short_term, micro_1m=micro,
        ohlcv={"open": float(df_1h["open"].iloc[-1]), "high": float(df_1h["high"].iloc[-1]),
               "low": float(df_1h["low"].iloc[-1]), "close": c,
               "volume": float(df_1h["volume"].iloc[-1])},
    )


# ── Helpers ──

def _candle_metrics(df):
    c = df.iloc[-1]; o, h, l, cl = float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"])
    tr = max(h - l, 1e-10); body = abs(cl - o); br = min(body / tr, 1.0)
    if cl > o: dir_, uw, dw = "bullish", h - cl, o - l
    elif cl < o: dir_, uw, dw = "bearish", h - o, cl - l
    else: dir_, uw, dw = "flat", h - cl, cl - l
    return dir_, round(br, 4), round(min(uw / tr, 1.0), 4), round(min(dw / tr, 1.0), 4), round((cl - l) / tr, 4)

def _candle_dir(df): return _candle_metrics(df)[0]
def _wick(df, side): return _candle_metrics(df)[2] if side == "up" else _candle_metrics(df)[3]

def _rng_15m(df, w):
    if len(df) < w: return 0.5
    c = float(df["close"].iloc[-1])
    hi = float(df["high"].iloc[-w:].max()); lo = float(df["low"].iloc[-w:].min())
    return round((c - lo) / (hi - lo), 4) if hi > lo else 0.5
