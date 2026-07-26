"""
Market State data models — multi-timeframe, lossless, structured.

Timeframe hierarchy (each with its specific role):
  4h → context (regime, structure, trend alignment)
  1h → primary state (trend, momentum, location, exhaustion, volatility)
  15m → short-term impulse (direction, rejection, momentum confirmation)
  1m → microstructure (candle geometry, immediate volatility, reversal)

No scores, no weights, no trading decisions.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# 1m — Microstructure
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MicroState:
    """1-minute microstructure — execution context, not trading signal."""
    candle_direction: str = "flat"      # "bullish" | "bearish" | "flat"
    body_ratio: float = 0.0
    upper_wick_ratio: float = 0.0
    lower_wick_ratio: float = 0.0
    close_location: float = 0.5
    range_vs_avg: float = 1.0           # current 1m range / avg 1m range
    volatility_1m: float = 0.0           # std of last 5 returns
    return_5m: float = 0.0              # price change over last 5 minutes
    immediate_reversal: bool = False     # strong reversal candle in last 2 min

    def to_dict(self): return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════
# 15m — Short-term impulse
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ShortTermState:
    """15-minute short-term context — confirms or contradicts 1h primary state."""
    direction: str = "neutral"           # "bullish" | "bearish" | "neutral"
    rsi: float = 50.0
    macd_norm: float = 0.0
    momentum_aligned: bool = True        # does 15m direction match 1h direction?
    candle_direction: str = "flat"
    upper_rejection: float = 0.0         # upper wick ratio when near range high
    lower_rejection: float = 0.0         # lower wick ratio when near range low
    range_position_20: float = 0.5

    def to_dict(self): return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════
# 1h — Primary Market State (existing blocks)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TrendState:
    direction: str = "neutral"
    strength: float = 0.0
    adx: float = 0.0
    ema_cross_norm: float = 0.0

    def to_dict(self): return asdict(self)


@dataclass
class MomentumState:
    direction: str = "neutral"
    strength: float = 0.0
    acceleration: float = 0.0
    rsi: float = 50.0
    macd_norm: float = 0.0
    squeeze_fired: bool = False     # just exited compression (breakout signal)
    squeeze_active: bool = False    # currently IN compression

    def to_dict(self): return asdict(self)


@dataclass
class VolatilityState:
    regime: str = "calm"
    prob_storm: float = 0.0
    atr_norm: float = 0.0

    def to_dict(self): return asdict(self)


@dataclass
class PriceLocationState:
    range_position_20: float = 0.5
    range_position_50: float = 0.5
    bb_position: float = 0.5
    vwap_distance: float = 0.0

    def to_dict(self): return asdict(self)


@dataclass
class ExhaustionState:
    cycle_strength: float = 0.0
    reversal_pattern_count: int = 0
    upper_rejection: float = 0.0
    lower_rejection: float = 0.0
    trend_momentum_divergence: float = 0.0

    def to_dict(self): return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════
# 4h — Context (regime, structure, alignment)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Context4h:
    structure_trend: str = "unknown"     # "uptrend" | "downtrend" | "sideways" | "expanding" | "contracting"
    hh: bool = False
    hl: bool = False
    lh: bool = False
    ll: bool = False
    trend_aligned: bool = False          # does 1h trend align with 4h structure?
    regime: str = "unknown"              # "trending" | "ranging" | "transitioning"

    def to_dict(self): return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════
# Top-level MarketState
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MarketState:
    """Complete multi-timeframe market description."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Timeframe hierarchy
    context_4h: Context4h = field(default_factory=Context4h)       # regime
    state_1h: 'HourlyState' = None                                  # primary (set below)
    short_term_15m: ShortTermState = field(default_factory=ShortTermState)
    micro_1m: MicroState = field(default_factory=MicroState)

    ohlcv: dict = field(default_factory=dict)
    source_ts: dict = field(default_factory=dict)  # {"1h": ts, "4h": ts, "15m": ts, "1m": ts}

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "ohlcv": self.ohlcv,
            "source_ts": self.source_ts,
            "context_4h": self.context_4h.to_dict(),
            "state_1h": self.state_1h.to_dict() if self.state_1h else {},
            "short_term_15m": self.short_term_15m.to_dict(),
            "micro_1m": self.micro_1m.to_dict(),
        }


@dataclass
class HourlyState:
    """1h primary state — the main analysis layer."""
    trend: TrendState = field(default_factory=TrendState)
    momentum: MomentumState = field(default_factory=MomentumState)
    volatility: VolatilityState = field(default_factory=VolatilityState)
    price_location: PriceLocationState = field(default_factory=PriceLocationState)
    exhaustion: ExhaustionState = field(default_factory=ExhaustionState)

    def to_dict(self):
        return {
            "trend": self.trend.to_dict(),
            "momentum": self.momentum.to_dict(),
            "volatility": self.volatility.to_dict(),
            "price_location": self.price_location.to_dict(),
            "exhaustion": self.exhaustion.to_dict(),
        }
