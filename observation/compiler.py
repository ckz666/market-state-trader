"""
MarketState compiler — orchestrates all observers into one MarketState.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

from observation.models import (
    MarketState, CandleState, TrendState, MomentumState,
    VolatilityState, StructureState, PriceLocationState, ExhaustionState,
)


def _to_df(ohlcv: list) -> pd.DataFrame:
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


def compile(df_1h: pd.DataFrame, df_4h: Optional[pd.DataFrame] = None,
            df_1d: Optional[pd.DataFrame] = None) -> MarketState:
    """Compile full MarketState from OHLCV DataFrames."""
    last = df_1h.iloc[-1]
    o, h, l, c, v = float(last["open"]), float(last["high"]), float(last["low"]), float(last["close"]), float(last.get("volume", 0))

    # ── Candle geometry ──
    candle = _compute_candle(df_1h)

    # ── Indicators ──
    from indicators.ml_signal import get_indicators, detect_market_structure, build_features
    indicators = get_indicators(df_1h)
    ind_1d = get_indicators(df_1d) if df_1d is not None and len(df_1d) > 30 else None
    ms_4h = detect_market_structure(df_4h) if df_4h is not None and len(df_4h) > 12 else {}

    # ── Trend ──
    ema = indicators.get("ema_cross_norm", 0)
    adx = indicators.get("adx", 0)
    trend_dir = "bullish" if ema > 0.0005 else ("bearish" if ema < -0.0005 else "neutral")
    trend_str = min(max(adx / 50.0, 0), 1.0) * 0.6 + min(abs(ema) / 0.005, 1.0) * 0.4
    struct_trend = ms_4h.get("trend", "unknown") if ms_4h else "unknown"
    daily_align = "neutral"
    if ind_1d:
        d_ema = ind_1d.get("ema_cross_norm", 0)
        d_rsi = ind_1d.get("rsi", 50)
        if trend_dir == "bullish" and d_ema > 0 and d_rsi > 50: daily_align = "aligned"
        elif trend_dir == "bearish" and d_ema < 0 and d_rsi < 50: daily_align = "aligned"
        elif (trend_dir == "bullish" and d_ema < 0) or (trend_dir == "bearish" and d_ema > 0): daily_align = "opposing"
    struct_align = "neutral"
    if trend_dir == "bullish" and struct_trend == "uptrend": struct_align = "aligned"
    elif trend_dir == "bearish" and struct_trend == "downtrend": struct_align = "aligned"
    elif (trend_dir == "bullish" and struct_trend == "downtrend") or (trend_dir == "bearish" and struct_trend == "uptrend"): struct_align = "opposing"

    trend = TrendState(
        direction=trend_dir, strength=round(trend_str, 4),
        persistence=round(trend_str * 0.85, 4), adx=round(adx, 1),
        ema_cross_norm=round(ema, 6), daily_alignment=daily_align,
        structure_alignment=struct_align,
    )

    # ── Momentum ──
    rsi = indicators.get("rsi", 50)
    macd = indicators.get("macd_diff", 0)
    sq_fired = bool(indicators.get("squeeze_fired", 0))
    sq_momentum = indicators.get("squeeze_momentum", 0)
    macd_bull, rsi_bull = macd > 0, rsi > 50
    mom_dir = "bullish" if (macd_bull and rsi_bull) else ("bearish" if (not macd_bull and not rsi_bull) else "neutral")
    mom_str = min(abs(rsi - 50) / 50, 1) * 0.4 + min(abs(macd) / 0.0005, 1) * 0.6
    accel = min(abs(sq_momentum) * 3, 1) if ((macd_bull and sq_momentum > 0) or (not macd_bull and sq_momentum < 0)) else -min(abs(sq_momentum) * 3, 1)

    momentum = MomentumState(
        direction=mom_dir, strength=round(mom_str, 4),
        acceleration=round(accel, 4), rsi=round(rsi, 2),
        macd_norm=round(macd, 6), squeeze_fired=sq_fired,
        squeeze_momentum=round(sq_momentum, 4),
    )

    # ── Volatility ──
    from indicators.vol_regime import classify_vol_regime
    vol = classify_vol_regime(df_1h)
    volatility = VolatilityState(
        regime=vol["regime"], prob_storm=vol["prob_storm"],
        atr_norm=round(indicators.get("atr_norm", 0), 6),
        continuous_risk_multiplier=vol["continuous_risk_multiplier"],
    )

    # ── Structure ──
    if ms_4h:
        ph = ms_4h.get("pivot_highs", [])
        pl = ms_4h.get("pivot_lows", [])
        tl = ms_4h.get("trend", "unknown")
        last_sh = ph[-1] if len(ph) >= 1 else None
        prev_sh = ph[-2] if len(ph) >= 2 else None
        last_sl = pl[-1] if len(pl) >= 1 else None
        prev_sl = pl[-2] if len(pl) >= 2 else None
        hd = round((last_sh - prev_sh) / prev_sh * 100, 4) if last_sh and prev_sh and prev_sh > 0 else None
        ld = round((last_sl - prev_sl) / prev_sl * 100, 4) if last_sl and prev_sl and prev_sl > 0 else None
    else:
        tl, last_sh, prev_sh, last_sl, prev_sl, hd, ld = "unknown", None, None, None, None, None, None

    structure = StructureState(
        trend_label=tl, hh=(hd or 0) > 0 if hd is not None else (tl == "uptrend"),
        hl=(ld or 0) > 0 if ld is not None else (tl == "uptrend"),
        lh=(hd or 0) < 0 if hd is not None else (tl == "downtrend"),
        ll=(ld or 0) < 0 if ld is not None else (tl == "downtrend"),
        last_swing_high=last_sh, last_swing_low=last_sl,
        high_delta_pct=hd, low_delta_pct=ld,
    )

    # ── Price Location ──
    def _range_pos(window):
        if len(df_1h) < window: return 0.5
        hi = float(df_1h["high"].iloc[-window:].max())
        lo = float(df_1h["low"].iloc[-window:].min())
        return round((c - lo) / (hi - lo), 4) if hi > lo else 0.5

    r20 = _range_pos(20)
    r50 = _range_pos(50)
    h20 = float(df_1h["high"].iloc[-20:].max()) if len(df_1h) >= 20 else c
    l20 = float(df_1h["low"].iloc[-20:].min()) if len(df_1h) >= 20 else c
    price_location = PriceLocationState(
        range_position_20=r20, range_position_50=r50,
        distance_to_recent_high=round((h20 - c) / c, 6),
        distance_to_recent_low=round((c - l20) / c, 6),
        bb_position=round(indicators.get("bb_pct", 0.5), 4),
        vwap_distance=round(indicators.get("vwap_dist", 0), 6),
    )

    # ── Exhaustion ──
    cycle_str = round(indicators.get("cycle_strength", 0), 4)
    rev_count = 0
    upper_rej = candle.upper_wick_ratio if r20 > 0.75 else 0.0
    lower_rej = candle.lower_wick_ratio if r20 < 0.25 else 0.0
    divergence = 0.0
    if trend_dir == "bullish" and mom_dir == "bearish": divergence = 0.7
    elif trend_dir == "bearish" and mom_dir == "bullish": divergence = 0.7
    elif trend_dir == "bullish" and mom_dir == "neutral": divergence = 0.35
    elif trend_dir == "bearish" and mom_dir == "neutral": divergence = 0.35

    exhaustion = ExhaustionState(
        cycle_strength=cycle_str, prob_storm=volatility.prob_storm,
        reversal_pattern_count=rev_count, upper_rejection=round(upper_rej, 4),
        lower_rejection=round(lower_rej, 4),
        trend_momentum_divergence=divergence,
    )

    return MarketState(
        timestamp=datetime.now(),
        candle=candle, trend=trend, momentum=momentum,
        volatility=volatility, structure=structure,
        price_location=price_location, exhaustion=exhaustion,
        ohlcv={"open": o, "high": h, "low": l, "close": c, "volume": v},
    )


def _compute_candle(df):
    if len(df) < 2: return CandleState()
    c = df.iloc[-1]
    o, h, l, cl = float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"])
    tr = max(h - l, 1e-10)
    body = abs(cl - o)
    body_ratio = round(min(body / tr, 1.0), 4)
    if cl > o:
        uw, dw = h - cl, o - l
        direction = "bullish"
    elif cl < o:
        uw, dw = h - o, cl - l
        direction = "bearish"
    else:
        uw, dw = h - cl, cl - l
        direction = "flat"
    upper_wick = round(min(uw / tr, 1.0), 4)
    lower_wick = round(min(dw / tr, 1.0), 4)
    close_loc = round((cl - l) / tr, 4)
    ranges = df["high"].iloc[-11:-1] - df["low"].iloc[-11:-1]
    avg_range = float(ranges.mean()) if len(ranges) > 0 else tr
    range_exp = round(tr / max(avg_range, 1e-10), 4)
    return CandleState(
        body_ratio=body_ratio, upper_wick_ratio=upper_wick,
        lower_wick_ratio=lower_wick, close_location=close_loc,
        direction=direction, range_expansion=range_exp,
    )
