"""
Market State data models — lossless, structured description of the market
at one point in time. No scores, no weights, no trading decisions.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class CandleState:
    body_ratio: float = 0.0
    upper_wick_ratio: float = 0.0
    lower_wick_ratio: float = 0.0
    close_location: float = 0.5
    direction: str = "flat"
    range_expansion: float = 1.0
    patterns: dict = field(default_factory=dict)

    def to_dict(self): return asdict(self)


@dataclass
class TrendState:
    direction: str = "neutral"
    strength: float = 0.0
    persistence: float = 0.0
    adx: float = 0.0
    ema_cross_norm: float = 0.0
    daily_alignment: str = "neutral"
    structure_alignment: str = "neutral"

    def to_dict(self): return asdict(self)


@dataclass
class MomentumState:
    direction: str = "neutral"
    strength: float = 0.0
    acceleration: float = 0.0
    rsi: float = 50.0
    macd_norm: float = 0.0
    squeeze_fired: bool = False
    squeeze_momentum: float = 0.0

    def to_dict(self): return asdict(self)


@dataclass
class VolatilityState:
    regime: str = "calm"
    prob_storm: float = 0.0
    atr_norm: float = 0.0
    continuous_risk_multiplier: float = 1.0

    def to_dict(self): return asdict(self)


@dataclass
class StructureState:
    trend_label: str = "unknown"
    hh: bool = False
    hl: bool = False
    lh: bool = False
    ll: bool = False
    last_swing_high: Optional[float] = None
    last_swing_low: Optional[float] = None
    high_delta_pct: Optional[float] = None
    low_delta_pct: Optional[float] = None

    def to_dict(self): return asdict(self)


@dataclass
class PriceLocationState:
    range_position_20: float = 0.5
    range_position_50: float = 0.5
    distance_to_recent_high: float = 0.0
    distance_to_recent_low: float = 0.0
    bb_position: float = 0.5
    vwap_distance: float = 0.0

    def to_dict(self): return asdict(self)


@dataclass
class ExhaustionState:
    cycle_strength: float = 0.0
    prob_storm: float = 0.0
    reversal_pattern_count: int = 0
    upper_rejection: float = 0.0
    lower_rejection: float = 0.0
    trend_momentum_divergence: float = 0.0

    def to_dict(self): return asdict(self)


@dataclass
class MarketState:
    """Complete, lossless market description at one point in time."""
    timestamp: datetime = field(default_factory=datetime.now)
    candle: CandleState = field(default_factory=CandleState)
    trend: TrendState = field(default_factory=TrendState)
    momentum: MomentumState = field(default_factory=MomentumState)
    volatility: VolatilityState = field(default_factory=VolatilityState)
    structure: StructureState = field(default_factory=StructureState)
    price_location: PriceLocationState = field(default_factory=PriceLocationState)
    exhaustion: ExhaustionState = field(default_factory=ExhaustionState)
    ohlcv: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "ohlcv": self.ohlcv,
            "candle": self.candle.to_dict(),
            "trend": self.trend.to_dict(),
            "momentum": self.momentum.to_dict(),
            "volatility": self.volatility.to_dict(),
            "structure": self.structure.to_dict(),
            "price_location": self.price_location.to_dict(),
            "exhaustion": self.exhaustion.to_dict(),
        }
