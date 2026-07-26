"""
Strategy Engine — converts MarketContext into concrete trading decisions.

Per-context rules:
  CONTINUATION   → open position in trend direction (with SL/TP)
  MEAN_REVERSION → open counter-trend position (tighter SL)
  EXTENDED       → close any position in the extended direction, no new entries
  COMPRESSED     → wait, no action
  TRANSITION     → wait, no action
"""
from dataclasses import dataclass
from typing import Optional

from context.classifier import MarketContext
import mst_config as config


@dataclass
class TradingDecision:
    action: str         # "open_long" | "open_short" | "close_long" | "close_short" | "hold"
    reason: str
    confidence: float
    sl_pct: float = 0.0
    tp_pct: float = 0.0
    leverage: int = 5

    def to_dict(self):
        return {
            "action": self.action, "reason": self.reason,
            "confidence": self.confidence,
            "sl_pct": round(self.sl_pct, 4),
            "tp_pct": round(self.tp_pct, 4),
            "leverage": self.leverage,
        }


def decide(context: MarketContext, atr_pct: float,
           has_open_position: bool = False,
           position_side: Optional[str] = None) -> TradingDecision:
    """Convert a MarketContext into a TradingDecision.

    Parameters
    ----------
    context : MarketContext
        Classified market context.
    atr_pct : float
        ATR as percentage of price (for SL/TP sizing).
    has_open_position : bool
        Whether a position is currently open.
    position_side : str, optional
        "long" or "short" if a position is open.
    """
    ctx = context.name

    # ── EXTENDED: close if we're in the extended direction ──
    if ctx == "extended":
        if has_open_position and position_side:
            if context.suggested_action == "avoid_long" and position_side == "long":
                return TradingDecision(
                    action="close_long", reason=context.rationale,
                    confidence=context.confidence,
                )
            elif context.suggested_action == "avoid_short" and position_side == "short":
                return TradingDecision(
                    action="close_short", reason=context.rationale,
                    confidence=context.confidence,
                )
        return TradingDecision(action="hold", reason=context.rationale, confidence=context.confidence)

    # ── COMPRESSED / TRANSITION: wait ──
    if ctx in ("compressed", "transition"):
        return TradingDecision(action="hold", reason=context.rationale, confidence=context.confidence)

    # ── CONTINUATION: open if no position ──
    if ctx == "continuation" and not has_open_position:
        sl = max(atr_pct * config.SL_ATR_MULT, 0.005)
        tp = atr_pct * config.TP_ATR_MULT
        action = "open_long" if context.direction_bias == "bullish" else "open_short"
        return TradingDecision(
            action=action, reason=context.rationale,
            confidence=context.confidence, sl_pct=sl, tp_pct=tp,
        )

    # ── MEAN_REVERSION: open counter-trend with tighter SL ──
    if ctx == "mean_reversion" and not has_open_position:
        sl = max(atr_pct * 0.8, 0.004)  # tighter stop for counter-trend
        tp = atr_pct * 2.0                # quicker target
        action = "open_long" if context.direction_bias == "long" else "open_short"
        return TradingDecision(
            action=action, reason=context.rationale,
            confidence=context.confidence, sl_pct=sl, tp_pct=tp,
        )

    return TradingDecision(action="hold", reason="Position already open or no signal", confidence=0.0)
