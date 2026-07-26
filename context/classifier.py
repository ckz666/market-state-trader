"""
Market Context — discrete classification of the current state into
one of five named contexts. No scores, no weights — rule-based from
empirical analysis (see 2×2 state matrix findings).

Contexts:
  CONTINUATION   — trend + momentum aligned, price not extended → follow trend
  MEAN_REVERSION — divergence detected, price not extreme → counter-trend
  EXTENDED       — price extended (bb > 1.0), momentum still pushing → avoid/exit
  COMPRESSED     — low volatility, squeeze active → wait for breakout
  TRANSITION     — mixed/weak signals → no clear edge
"""
from dataclasses import dataclass, asdict
from typing import Optional

from observation.models import MarketState
import mst_config as config


@dataclass
class MarketContext:
    name: str                   # "continuation" | "mean_reversion" | "extended" | "compressed" | "transition"
    direction_bias: str         # "long" | "short" | "neutral"
    confidence: float           # 0.0 – 1.0
    rationale: str
    suggested_action: str       # "allow_long" | "allow_short" | "avoid_long" | "avoid_short" | "wait" | "reduce"

    def to_dict(self):
        return asdict(self)


def classify(state: MarketState) -> MarketContext:
    """Classify a MarketState into a discrete context.

    Decision tree (order matters — first match wins):
    1. EXTENDED:     bb_position > 1.0 → overextended, avoid trend-following
    2. COMPRESSED:   squeeze active or very low ATR → wait
    3. MEAN_REVERSION: divergence (trend↓ mom↑ or trend↑ mom↓) AND not extended
    4. CONTINUATION: trend + momentum aligned, not extended, ADX trending
    5. TRANSITION:   everything else → no clear edge
    """
    bb = state.state_1h.price_location.bb_position
    adx = state.state_1h.trend.adx
    divergence = state.state_1h.exhaustion.trend_momentum_divergence
    mom_dir = state.state_1h.momentum.direction
    trend_dir = state.state_1h.trend.direction
    mom_str = state.state_1h.momentum.strength
    atr = state.state_1h.volatility.atr_norm
    # squeeze_fired = just exited compression (breakout signal, NOT compression)
    # squeeze would be active if we had it in state — for now, only use ATR

    # Multi-TF enrichments
    st_15m_rejection = state.short_term_15m.upper_rejection > 0.3 or state.short_term_15m.lower_rejection > 0.3
    st_15m_aligned = state.short_term_15m.momentum_aligned
    micro_reversal = state.micro_1m.immediate_reversal

    # 1. EXTENDED
    if bb > config.BB_EXTENDED:
        if mom_dir == "bullish":
            return MarketContext(
                name="extended", direction_bias="neutral",
                confidence=min((bb - 1.0) * 5 + 0.3, 0.95),
                rationale=f"Price extended (bb={bb:.2f}), bullish momentum overextended → avoid long",
                suggested_action="avoid_long",
            )
        elif mom_dir == "bearish":
            return MarketContext(
                name="extended", direction_bias="neutral",
                confidence=min((bb - 1.0) * 5 + 0.3, 0.95),
                rationale=f"Price extended (bb={bb:.2f}), bearish momentum overextended → avoid short",
                suggested_action="avoid_short",
            )
        # Symmetric: price below lower BB → avoid shorts (lower extension)
        if bb < 0.0 and mom_dir == "bearish":
            return MarketContext(
                name="extended", direction_bias="neutral",
                confidence=min(abs(bb) * 5 + 0.3, 0.95),
                rationale=f"Price below lower BB (bb={bb:.2f}), bearish momentum overextended → avoid short",
                suggested_action="avoid_short",
            )

    # 2. COMPRESSED — low volatility, no clear direction
    # Note: squeeze_fired means breakout just happened, NOT compressed.
    # Only use ATR for compression detection.
    if atr < 0.005:
        return MarketContext(
            name="compressed", direction_bias="neutral",
            confidence=0.6,
            rationale=f"Low volatility (atr={atr:.4f}) → wait for breakout",
            suggested_action="wait",
        )

    # 3. MEAN REVERSION
    if divergence >= config.DIVERGENCE_THRESHOLD and bb < config.BB_EXTENDED:
        if trend_dir == "bearish" and mom_dir == "bullish":
            return MarketContext(
                name="mean_reversion", direction_bias="long",
                confidence=min(divergence * 0.7 + 0.3, 0.9),
                rationale=f"Bearish trend + bullish momentum divergence (div={divergence:.1f}), not extended → mean reversion long possible",
                suggested_action="allow_long",
            )
        elif trend_dir == "bullish" and mom_dir == "bearish":
            return MarketContext(
                name="mean_reversion", direction_bias="short",
                confidence=min(divergence * 0.7 + 0.3, 0.9),
                rationale=f"Bullish trend + bearish momentum divergence (div={divergence:.1f}), not extended → mean reversion short possible",
                suggested_action="allow_short",
            )

    # 4. CONTINUATION
    aligned = (
        (trend_dir == "bullish" and mom_dir in ("bullish", "neutral")) or
        (trend_dir == "bearish" and mom_dir in ("bearish", "neutral"))
    )
    if aligned and adx >= config.ADX_TRENDING and bb < config.BB_FAVORABLE:
        conf = min(adx / 50 * 0.5 + mom_str * 0.5, 0.9)
        return MarketContext(
            name="continuation", direction_bias=trend_dir,
            confidence=round(conf, 3),
            rationale=f"Trend ({trend_dir}, adx={adx:.0f}) + momentum aligned, price favorable (bb={bb:.2f}) → follow trend",
            suggested_action="allow_long" if trend_dir == "bullish" else "allow_short",
        )

    # 5. TRANSITION
    return MarketContext(
        name="transition", direction_bias="neutral",
        confidence=0.3,
        rationale=f"Mixed signals: trend={trend_dir}, mom={mom_dir}, adx={adx:.0f}, bb={bb:.2f} → no clear edge",
        suggested_action="wait",
    )
