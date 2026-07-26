import numpy as np
import pandas as pd
import ta

from indicators.patterns import detect_patterns
from indicators.spectral_guard import rolling_cycle_strength
from indicators.vol_regime import rolling_prob_storm


def cvd_zscore_from_ohlcv(df: pd.DataFrame, window: int = 100) -> pd.Series:
    """
    Order-flow feature: rolling z-score of cumulative taker buy/sell volume
    delta (CVD). df must have a 'taker_buy_volume' column and 'volume'.
    Bitget OHLCV has no taker_buy_volume column, so this no-ops to a neutral
    0.0 series for every caller in this repo until one opts into a source
    that provides it. Returns NaN before `window` bars of history exist —
    build_features() fills that as neutral (0.0).
    """
    if "taker_buy_volume" not in df.columns:
        return pd.Series(0.0, index=df.index)
    taker_sell = df["volume"] - df["taker_buy_volume"]
    cvd = (df["taker_buy_volume"] - taker_sell).cumsum()
    roll_mean = cvd.rolling(window).mean()
    roll_std  = cvd.rolling(window).std()
    return ((cvd - roll_mean) / roll_std.replace(0, pd.NA)).fillna(0.0)


def taker_ratio_zscore_from_ohlcv(df: pd.DataFrame, window: int = 100) -> pd.Series:
    """
    Second order-flow feature, deliberately NOT the same signal as
    cvd_zscore despite sharing a data source: this is a rolling z-score of
    the PER-BAR taker buy ratio (buy_volume / total_volume, bounded [0,1],
    mean-reverting around ~0.5) — an instantaneous pressure reading.
    cvd_zscore above is a z-score of the CUMULATIVE running sum of
    buy-minus-sell volume — a trend-following, unbounded quantity. Same
    underlying trade tape, two structurally different signals (snapshot vs.
    accumulated drift). Like cvd_zscore, no-ops to neutral 0.0 without a
    'taker_buy_volume' column, which Bitget OHLCV doesn't provide.
    """
    if "taker_buy_volume" not in df.columns:
        return pd.Series(0.0, index=df.index)
    ratio = df["taker_buy_volume"] / df["volume"].replace(0, pd.NA)
    roll_mean = ratio.rolling(window).mean()
    roll_std  = ratio.rolling(window).std()
    return ((ratio - roll_mean) / roll_std.replace(0, pd.NA)).fillna(0.0)


def _squeeze_indicators(df: pd.DataFrame, period: int = 20,
                         bb_mult: float = 2.0, kc_mult: float = 1.5) -> pd.DataFrame:
    """
    TTM-style Volatility Squeeze.
    squeeze_active=1: BB inside Keltner Channel → compression, explosive move incoming.
    squeeze_fired=1:  squeeze just released (prev bar ON, current bar OFF) → entry signal.
    squeeze_momentum: positive=bullish release, negative=bearish release.
    """
    close, high, low = df["close"], df["high"], df["low"]
    ma  = close.rolling(period).mean()
    std = close.rolling(period).std()

    # Bollinger Bands
    bb_upper = ma + bb_mult * std
    bb_lower = ma - bb_mult * std

    # Keltner Channel (ATR-based)
    tr  = pd.concat([high - low,
                     (high - close.shift(1)).abs(),
                     (low  - close.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    kc_upper = ma + kc_mult * atr
    kc_lower = ma - kc_mult * atr

    squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    fired   = squeeze.shift(1).fillna(False) & ~squeeze   # was ON last bar, now OFF

    # Momentum: close vs midpoint of recent range + MA
    highest = high.rolling(period).max()
    lowest  = low.rolling(period).min()
    momentum = close - ((highest + lowest) / 2 + ma) / 2
    momentum_norm = momentum / close   # normalize by price

    return pd.DataFrame({
        "squeeze_active":   squeeze.astype(int),
        "squeeze_fired":    fired.astype(int),
        "squeeze_momentum": momentum_norm,
    }, index=df.index)


def _resample_htf_indicators(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample 1h OHLC to a higher timeframe (derived from the same data, no
    extra fetch) and compute a few indicators on it. Shifted by one period
    before the caller reindexes it back onto the 1h index, so each 1h bar only
    ever sees the last fully-closed higher-timeframe bar — never the one it's
    currently inside of (that would leak the future into the training label).
    """
    o = df["open"].resample(rule).first()
    h = df["high"].resample(rule).max()
    l = df["low"].resample(rule).min()
    c = df["close"].resample(rule).last()
    htf = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).dropna()

    # ADX needs >= 2x its window (28 for window=14) or the ta library indexes
    # past the end of the series instead of returning NaN — verified empirically,
    # not documented. Callers with a small df (e.g. Grid's fetch) would otherwise crash here.
    if len(htf) < 30:
        empty_idx = df.index[:0]
        return pd.DataFrame({"rsi": pd.Series(dtype=float, index=empty_idx),
                              "adx": pd.Series(dtype=float, index=empty_idx),
                              "ema_cross_norm": pd.Series(dtype=float, index=empty_idx),
                              "macd_diff": pd.Series(dtype=float, index=empty_idx)})

    rsi  = ta.momentum.RSIIndicator(htf["close"]).rsi()
    adx  = ta.trend.ADXIndicator(htf["high"], htf["low"], htf["close"], 14).adx()
    ema9, ema21 = ta.trend.ema_indicator(htf["close"], 9), ta.trend.ema_indicator(htf["close"], 21)
    macd_diff = ta.trend.MACD(htf["close"]).macd_diff()

    out = pd.DataFrame({
        "rsi":            rsi,
        "adx":            adx,
        "ema_cross_norm": (ema9 - ema21) / htf["close"],
        "macd_diff":      macd_diff,
    })
    return out.shift(1)


def _pattern_signal(df: pd.DataFrame) -> pd.Series:
    """Rolling candlestick-pattern signal: bullish minus bearish pattern count
    over the trailing 5-candle window ending at each bar. Reuses the same
    pattern detector the live confluence scorer uses, so the ML model can
    learn nonlinear combinations of the same signal instead of only getting
    it as fixed confluence points."""
    signal = pd.Series(0.0, index=df.index)
    for i in range(4, len(df)):
        pats = detect_patterns(df.iloc[i - 4: i + 1])
        bulls = sum(1 for v in pats.values() if v == "bullish")
        bears = sum(1 for v in pats.values() if v == "bearish")
        signal.iloc[i] = bulls - bears
    return signal


def build_features(df: pd.DataFrame, funding_series: pd.Series = None,
                    precomputed_pattern_signal: pd.Series = None,
                    precomputed_prob_storm: pd.Series = None,
                    precomputed_cvd_zscore: pd.Series = None,
                    precomputed_taker_ratio_zscore: pd.Series = None) -> pd.DataFrame:
    """
    precomputed_pattern_signal / precomputed_prob_storm: optional, already-computed
    _pattern_signal()/rolling_prob_storm() results covering (at least) df's index range.
    Both are strictly causal with a fixed trailing lookback, so a value for a given
    timestamp is identical whether computed on the full history or on a window ending
    at that timestamp — safe to reindex from a precomputed series instead of recomputing.
    Nothing in this repo currently passes these; they're accepted as optional
    reindex-from-precomputed hooks for callers that recompute build_features()
    repeatedly over sliding windows (e.g. a future backtest/walk-forward tool).

    precomputed_cvd_zscore / precomputed_taker_ratio_zscore: see
    cvd_zscore_from_ohlcv() / taker_ratio_zscore_from_ohlcv() — both no-op to
    neutral 0.0 when df lacks a 'taker_buy_volume' column, which is true for
    every live caller in this repo (Bitget OHLCV doesn't include it).
    """
    f = pd.DataFrame(index=df.index)

    # Momentum (3 core features, non-redundant)
    f["returns_1"]     = df["close"].pct_change(1)
    f["returns_3"]     = df["close"].pct_change(3)
    f["rsi"]           = ta.momentum.RSIIndicator(df["close"]).rsi()

    # Trend (3 features: direction + strength + MACD histogram)
    ema_9              = ta.trend.ema_indicator(df["close"], 9)
    ema_21             = ta.trend.ema_indicator(df["close"], 21)
    f["ema_cross_norm"]= (ema_9 - ema_21) / df["close"]
    f["macd_diff"]     = ta.trend.MACD(df["close"]).macd_diff()
    adx_ind            = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], 14)
    f["adx"]           = adx_ind.adx()

    # Volatility (2 features: position in BB + regime)
    bb                 = ta.volatility.BollingerBands(df["close"])
    f["bb_pct"]        = bb.bollinger_pband()
    f["atr_norm"]      = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range() / df["close"]

    # Volume (2 features: relative volume + OBV flow)
    vol_sma            = df["volume"].rolling(14).mean()
    f["volume_ratio"]  = df["volume"] / vol_sma
    obv                = ta.volume.OnBalanceVolumeIndicator(df["close"], df["volume"]).on_balance_volume()
    f["obv_norm"]      = obv.pct_change(5)

    # VWAP distance (1 feature: price vs fair value)
    typical            = (df["high"] + df["low"] + df["close"]) / 3
    vwap               = (typical * df["volume"]).rolling(24).sum() / df["volume"].rolling(24).sum()
    f["vwap_dist"]     = (df["close"] - vwap) / df["close"]

    # Volatility Squeeze (3 features: compression state + fired signal + momentum direction)
    sq = _squeeze_indicators(df)
    f["squeeze_active"]   = sq["squeeze_active"]
    f["squeeze_fired"]    = sq["squeeze_fired"]
    f["squeeze_momentum"] = sq["squeeze_momentum"]

    # Funding rate (contrarian on-chain feature — positive = longs overextended = bearish).
    # Bitget's funding history caps at ~100 records (~33 days) regardless of what's
    # requested, far short of the price history we can get elsewhere — neutral-fill
    # rows before funding coverage starts instead of dropping them, same reasoning
    # as the 4H-indicator warmup above.
    if funding_series is not None and not funding_series.empty:
        aligned = funding_series.reindex(df.index, method="ffill")
        # Normalize: typical rate 0.01% = 1.0, extreme ±5x = ±5.0
        f["funding_norm"] = ((aligned / 0.0001).clip(-5, 5)).fillna(0.0)
        # Trend: 3-period change (are longs paying more or less?)
        f["funding_trend"] = (aligned.diff(3) / 0.0001).fillna(0.0)
    else:
        f["funding_norm"]  = 0.0
        f["funding_trend"] = 0.0

    # Order flow (1 feature, 2026-07-23): rolling z-score of taker buy/sell volume
    # delta (CVD) — see cvd_zscore_from_ohlcv() docstring for why it's z-scored
    # (Binance-trained / Bitget-live source mismatch) and inert-by-default rationale.
    f["cvd_zscore"] = (precomputed_cvd_zscore.reindex(df.index).fillna(0.0)
                        if precomputed_cvd_zscore is not None else cvd_zscore_from_ohlcv(df))

    # Second order-flow feature (1 feature, 2026-07-23): see
    # taker_ratio_zscore_from_ohlcv() docstring for why this is deliberately
    # not redundant with cvd_zscore above despite sharing a data source.
    f["taker_ratio_zscore"] = (precomputed_taker_ratio_zscore.reindex(df.index).fillna(0.0)
                                if precomputed_taker_ratio_zscore is not None
                                else taker_ratio_zscore_from_ohlcv(df))

    # 4H context (4 features: resampled from this same 1h data, no extra fetch —
    # lets the model see whether the bigger-picture trend agrees with the 1h read).
    # Neutral-filled rather than left NaN during the 4H-indicator warmup window,
    # so early rows aren't dropped wholesale from an already-small dataset.
    htf_4h = _resample_htf_indicators(df, "4h")
    aligned_4h = htf_4h.reindex(df.index, method="ffill")
    f["rsi_4h"]            = aligned_4h["rsi"].fillna(50.0)
    f["adx_4h"]            = aligned_4h["adx"].fillna(0.0)
    f["ema_cross_norm_4h"] = aligned_4h["ema_cross_norm"].fillna(0.0)
    f["macd_diff_4h"]      = aligned_4h["macd_diff"].fillna(0.0)

    # Candlestick pattern signal (1 feature): lets the ensemble learn nonlinear
    # combinations of the same patterns the confluence scorer already checks
    f["pattern_signal"] = (precomputed_pattern_signal.reindex(df.index).fillna(0)
                            if precomputed_pattern_signal is not None else _pattern_signal(df))

    # Cycle strength (1 feature): detrended, differenced, Hann-windowed dominant-
    # frequency power — see ai/spectral_guard.py. Deliberately NOT computed on raw
    # price (that would just re-detect the random-walk spectral tilt as a fake
    # cycle every time); values at/below NOISE_FLOOR are indistinguishable from
    # chance and the model has to learn that, same as any other noisy feature.
    f["cycle_strength"] = rolling_cycle_strength(df["close"])

    # Vol regime (1 feature): sticky-Markov P(storm) — previously sizing-only
    # (ai/vol_regime.py::classify_vol_regime multiplies risk_pct post-hoc), now
    # also given to the model directly so it can learn regime-conditional
    # patterns instead of only having its output de-rated after the fact.
    f["prob_storm"] = (precomputed_prob_storm.reindex(df.index).fillna(0.0)
                        if precomputed_prob_storm is not None else rolling_prob_storm(df))

    # volume_ratio/vwap_dist divide by rolling volume sums that can be exactly
    # zero on thin symbols or data gaps, producing +-inf rather than NaN — inf
    # survives dropna() downstream and poisons the scaler/model fit, so convert
    # it to NaN here where the rest of the pipeline already knows how to handle it.
    f = f.replace([np.inf, -np.inf], np.nan)

    return f


def detect_market_structure(df: pd.DataFrame, n: int = 5, min_swing_atr: float = 0.5) -> dict:
    """
    Identify swing highs/lows (pivot points) to classify market structure:
    uptrend (HH+HL), downtrend (LL+LH), expanding, contracting, or sideways.
    n = candles on each side required to confirm a pivot.
    min_swing_atr = minimum pivot-to-pivot move, as a multiple of the recent
    average candle range, required to count as meaningfully higher/lower —
    without this, noise-level wiggles inside a flat range register as a full
    "trend" just as readily as a real move would.
    """
    if len(df) < n * 2 + 4:
        return {"trend": "unknown", "last_swing_high": 0.0, "last_swing_low": 0.0,
                "pivot_highs": [], "pivot_lows": []}

    highs = df["high"].values
    lows  = df["low"].values

    pivot_highs: list[float] = []
    pivot_lows:  list[float] = []

    for i in range(n, len(df) - n):
        window_h = highs[i - n: i + n + 1]
        window_l = lows[i - n: i + n + 1]
        if highs[i] == window_h.max():
            pivot_highs.append(float(highs[i]))
        if lows[i] == window_l.min():
            pivot_lows.append(float(lows[i]))

    min_swing = float((df["high"] - df["low"]).tail(20).mean()) * min_swing_atr

    trend = "sideways"
    if len(pivot_highs) >= 2 and len(pivot_lows) >= 2:
        hh = pivot_highs[-1] > pivot_highs[-2] + min_swing  # higher high
        hl = pivot_lows[-1]  > pivot_lows[-2]  + min_swing  # higher low
        lh = pivot_highs[-1] < pivot_highs[-2] - min_swing  # lower high
        ll = pivot_lows[-1]  < pivot_lows[-2]  - min_swing  # lower low

        if hh and hl:   trend = "uptrend"
        elif lh and ll: trend = "downtrend"
        elif hh and ll: trend = "expanding"
        elif lh and hl: trend = "contracting"

    return {
        "trend": trend,
        "last_swing_high": pivot_highs[-1] if pivot_highs else 0.0,
        "last_swing_low":  pivot_lows[-1]  if pivot_lows  else 0.0,
        "pivot_highs": pivot_highs[-3:],
        "pivot_lows":  pivot_lows[-3:],
    }


def calc_ichimoku(df: pd.DataFrame, tenkan_n: int = 9, kijun_n: int = 26,
                   senkou_b_n: int = 52, displacement: int = 26) -> dict:
    """
    Ichimoku Cloud. Senkou spans are shifted forward by `displacement` so that
    iloc[-1] reflects the cloud boundary aligned with the current candle
    (i.e. computed from data `displacement` bars ago, as per standard usage).
    """
    if len(df) < senkou_b_n + displacement:
        return {"available": False}

    high, low, close = df["high"], df["low"], df["close"]
    tenkan = (high.rolling(tenkan_n).max() + low.rolling(tenkan_n).min()) / 2
    kijun  = (high.rolling(kijun_n).max()  + low.rolling(kijun_n).min())  / 2
    senkou_a = ((tenkan + kijun) / 2).shift(displacement)
    senkou_b = ((high.rolling(senkou_b_n).max() + low.rolling(senkou_b_n).min()) / 2).shift(displacement)

    span_a, span_b = senkou_a.iloc[-1], senkou_b.iloc[-1]
    if pd.isna(span_a) or pd.isna(span_b):
        return {"available": False}

    price = float(close.iloc[-1])
    cloud_top, cloud_bottom = float(max(span_a, span_b)), float(min(span_a, span_b))

    if price > cloud_top:
        position = "above"
    elif price < cloud_bottom:
        position = "below"
    else:
        position = "inside"

    tk_cross = "none"
    if len(tenkan) >= 2 and not pd.isna(tenkan.iloc[-2]) and not pd.isna(kijun.iloc[-2]):
        prev_diff = tenkan.iloc[-2] - kijun.iloc[-2]
        cur_diff  = tenkan.iloc[-1] - kijun.iloc[-1]
        if prev_diff <= 0 and cur_diff > 0:
            tk_cross = "bullish"
        elif prev_diff >= 0 and cur_diff < 0:
            tk_cross = "bearish"

    return {
        "available": True,
        "tenkan": round(float(tenkan.iloc[-1]), 4),
        "kijun": round(float(kijun.iloc[-1]), 4),
        "cloud_top": round(cloud_top, 4),
        "cloud_bottom": round(cloud_bottom, 4),
        "cloud_bullish": bool(span_a > span_b),   # future cloud color
        "price_vs_cloud": position,
        "tk_cross": tk_cross,
    }


def get_indicators(df: pd.DataFrame, features: pd.DataFrame = None) -> dict:
    """
    Return current indicator values + market structure for context.
    `features`: optional pre-computed build_features(df) result — pass this when the
    caller already built it (e.g. right before calling predict() on the same df) to
    avoid recomputing the expensive feature pipeline (_pattern_signal, rolling_prob_storm)
    a second time on identical data. Defaults to None so existing callers are unaffected.
    """
    f = features if features is not None else build_features(df)
    last = f.iloc[-1]
    adx = float(last.get("adx", 0))

    # ATR in absolute terms (not normalised) for position sizing
    atr_norm = float(last.get("atr_norm", 0))
    close    = float(df["close"].iloc[-1])
    atr_abs  = atr_norm * close

    ms = detect_market_structure(df)
    ichimoku = calc_ichimoku(df)

    # Squeeze: compute on full df for fired detection (prev bar needed)
    sq     = _squeeze_indicators(df)
    sq_cur = sq.iloc[-1]

    return {
        "rsi":             round(float(last.get("rsi", 0)), 2),
        "macd_diff":       round(float(last.get("macd_diff", 0)), 4),
        "bb_pct":          round(float(last.get("bb_pct", 0.5)), 3),
        "ema_cross_norm":  round(float(last.get("ema_cross_norm", 0)), 5),
        "volume_ratio":    round(float(last.get("volume_ratio", 1)), 2),
        "atr_norm":        round(atr_norm, 5),
        "atr":             round(atr_abs, 4),
        "adx":             round(adx, 1),
        "regime":          detect_regime(adx),
        "vwap_dist":       round(float(last.get("vwap_dist", 0)), 4),
        "market_structure":ms["trend"],
        "swing_high":      round(ms["last_swing_high"], 4),
        "swing_low":       round(ms["last_swing_low"], 4),
        "squeeze_active":  int(sq_cur["squeeze_active"]),
        "squeeze_fired":   int(sq_cur["squeeze_fired"]),
        "squeeze_momentum":round(float(sq_cur["squeeze_momentum"]), 5),
        "cycle_strength":  round(float(last.get("cycle_strength", 0)), 4),
        "prob_storm":      round(float(last.get("prob_storm", 0)), 4),
        "ichimoku":        ichimoku,
    }


def detect_regime(adx: float) -> str:
    if adx >= 40: return "strong_trend"
    if adx >= 25: return "trending"
    if adx >= 20: return "transitioning"
    return "ranging"
