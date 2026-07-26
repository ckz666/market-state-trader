"""
Paper Trading Engine — simulates positions, PnL, and risk management.
No real orders — pure simulation with fee deduction.
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import mst_config as config


@dataclass
class Position:
    symbol: str
    side: str           # "long" | "short"
    amount: float
    entry_price: float
    leverage: int
    stop_loss: float
    take_profit: float
    opened_at: str
    margin: float = 0.0
    funding_paid: float = 0.0

    def unrealized_pnl(self, current_price: float) -> float:
        if self.side == "long":
            return (current_price - self.entry_price) * self.amount
        else:
            return (self.entry_price - current_price) * self.amount

    def roe_pct(self, current_price: float) -> float:
        if self.margin <= 0: return 0.0
        return self.unrealized_pnl(current_price) / self.margin * 100

    def to_dict(self, current_price: float = 0) -> dict:
        return {
            "symbol": self.symbol, "side": self.side,
            "amount": self.amount, "entry_price": self.entry_price,
            "leverage": self.leverage, "stop_loss": self.stop_loss,
            "take_profit": self.take_profit, "opened_at": self.opened_at,
            "margin": self.margin, "unrealized_pnl": round(self.unrealized_pnl(current_price), 4),
            "roe_pct": round(self.roe_pct(current_price), 2),
        }


class PaperTrader:
    """Simulated futures trading with position tracking."""

    def __init__(self):
        self.balance = config.INITIAL_BALANCE
        self.peak_equity = self.balance
        self.position: Optional[Position] = None
        self.trade_history: list[dict] = []
        self.equity_history: list[dict] = []
        self._load()

    @property
    def has_position(self) -> bool:
        return self.position is not None

    @property
    def cash_balance(self) -> float:
        """Available cash (balance), NOT including unrealized PnL."""
        return self.balance

    def equity(self, price: float) -> float:
        """True equity = cash balance + unrealized PnL of open position."""
        if self.position:
            return self.balance + self.position.unrealized_pnl(price)
        return self.balance

    def open(self, side: str, amount: float, price: float, leverage: int,
             sl: float, tp: float):
        """Open a new position."""
        margin = (amount * price) / leverage
        fee = amount * price * config.TAKER_FEE
        self.balance -= fee  # only fee deducted; margin tracked in position, not subtracted
        self.position = Position(
            symbol=config.SYMBOL, side=side, amount=amount,
            entry_price=price, leverage=leverage,
            stop_loss=sl, take_profit=tp,
            opened_at=datetime.now(timezone.utc).isoformat(),
            margin=margin,
        )
        self._save()

    def close(self, price: float, reason: str = "manual") -> dict:
        """Close the current position."""
        if not self.position:
            return {"error": "No position"}
        pnl = self.position.unrealized_pnl(price)
        fee = self.position.amount * price * config.TAKER_FEE
        pnl -= fee + self.position.funding_paid
        self.balance += pnl  # margin was never deducted, don't add it back
        # Snapshot before closing for the trade record
        pos_side = self.position.side
        pos_entry = self.position.entry_price
        pos_amount = self.position.amount
        pos_opened = self.position.opened_at
        self.position = None
        eq = self.equity(price)
        if eq > self.peak_equity:
            self.peak_equity = eq

        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "side": pos_side,
            "entry_price": pos_entry,
            "exit_price": price,
            "amount": pos_amount,
            "pnl": round(pnl, 4),
            "reason": reason,
            "opened_at": pos_opened,
        }
        self.trade_history.append(record)
        self._save()
        return record

    def check_sl_tp(self, price: float) -> Optional[str]:
        """Check if SL or TP is hit. Returns 'sl', 'tp', or None."""
        if not self.position:
            return None
        if self.position.side == "long":
            if price <= self.position.stop_loss: return "sl"
            if price >= self.position.take_profit: return "tp"
        else:
            if price >= self.position.stop_loss: return "sl"
            if price <= self.position.take_profit: return "tp"
        return None

    def record_equity(self, price: float):
        """Record equity point for charting and update peak."""
        eq = self.equity(price)
        self.equity_history.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "equity": round(eq, 2),
        })
        self.equity_history = self.equity_history[-500:]
        if eq > self.peak_equity:
            self.peak_equity = eq

    def status(self, price: float = 0) -> dict:
        eq = self.equity(price)
        return {
            "balance": round(self.balance, 2),
            "equity": round(eq, 2),
            "peak_equity": round(self.peak_equity, 2),
            "total_pnl": round(self.balance - config.INITIAL_BALANCE, 2),
            "position": self.position.to_dict(price) if self.position else None,
            "trade_count": len(self.trade_history),
        }

    def _save(self):
        os.makedirs(config.DATA_DIR, exist_ok=True)
        data = {
            "balance": self.balance,
            "peak_equity": self.peak_equity,
            "position": self.position.to_dict() if self.position else None,
            "trades": self.trade_history[-200:],
        }
        tmp = config.STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, config.STATE_FILE)

    def _load(self):
        if not os.path.exists(config.STATE_FILE):
            return
        try:
            with open(config.STATE_FILE) as f:
                data = json.load(f)
            self.balance = data.get("balance", config.INITIAL_BALANCE)
            # backward compat: old files used 'peak_balance'
            self.peak_equity = data.get("peak_equity", data.get("peak_balance", self.balance))
            self.trade_history = data.get("trades", [])
            # Position persisted for restart safety
            pos_data = data.get("position")
            if pos_data:
                self.position = Position(
                    symbol=pos_data.get("symbol",""), side=pos_data.get("side","long"),
                    amount=pos_data.get("amount",0), entry_price=pos_data.get("entry_price",0),
                    leverage=pos_data.get("leverage",1), stop_loss=pos_data.get("stop_loss",0),
                    take_profit=pos_data.get("take_profit",0), opened_at=pos_data.get("opened_at",""),
                    margin=pos_data.get("margin",0), funding_paid=pos_data.get("funding_paid",0),
                )
        except Exception:
            pass
